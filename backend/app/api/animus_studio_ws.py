"""Live ANIMUS Studio channel.

The channel is intentionally small: it sends a full snapshot on connect and then forwards durable
bus events. The subscription is created *before* the snapshot is read so a commit cannot fall into
the gap between reading state and joining the bus.
"""
from __future__ import annotations

import asyncio
import json
import re
from contextlib import suppress

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.animus.studio.bus import animus_bus
from app.core.animus.studio.errors import (
    StudioArchived,
    StudioConflict,
    StudioCorruptState,
    StudioError,
    StudioNotFound,
    StudioPersistenceError,
    StudioValidationError,
)
from app.core.animus.studio.service import studio_service
from app.core.config import settings

router = APIRouter(tags=["animus-studio"])

_SESSION_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,80}$")
_MAX_MESSAGE_BYTES = 64 * 1024


def _error_message(exc: StudioError) -> tuple[str, str]:
    if isinstance(exc, StudioArchived):
        return "session_archived", str(exc)
    if isinstance(exc, StudioConflict):
        return "stale_version", str(exc)
    if isinstance(exc, StudioNotFound):
        return "not_found", str(exc)
    if isinstance(exc, StudioValidationError):
        return "invalid_request", str(exc)
    if isinstance(exc, StudioPersistenceError):
        return "persistence_failed", str(exc)
    if isinstance(exc, StudioCorruptState):
        return "corrupt_local_state", str(exc)
    return "studio_error", str(exc)


@router.websocket("/ws/animus/{session_id}")
async def websocket_animus(ws: WebSocket, session_id: str) -> None:
    allowed_origins = {
        origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()
    }
    origin = ws.headers.get("origin")
    if origin is not None and origin not in allowed_origins:
        await ws.close(code=1008)
        return
    if not _SESSION_PATTERN.fullmatch(session_id):
        await ws.close(code=1008)
        return

    await ws.accept()
    # Join before reading the snapshot. A mutation that commits while get_session() is running is
    # queued and forwarded immediately after the snapshot instead of being lost.
    queue = await animus_bus.subscribe(session_id)
    try:
        try:
            snapshot = await studio_service.get_session(session_id)
        except StudioNotFound:
            await ws.send_json({
                "type": "error",
                "code": "not_found",
                "message": f"unknown studio session {session_id}",
            })
            await ws.close()
            return
        except StudioError as exc:
            code, message = _error_message(exc)
            await ws.send_json({"type": "error", "code": code, "message": message})
            await ws.close(code=1011)
            return

        send_lock = asyncio.Lock()

        async def send(payload: dict) -> None:
            async with send_lock:
                await ws.send_json(payload)

        async def forward_events() -> None:
            while True:
                event = await queue.get()
                if event.get("type") == "resync_required":
                    await send(event)
                    continue
                await send({**event, "type": "event", "event_type": event.get("type")})

        await send({"type": "snapshot", "session": snapshot})
        forward_task = asyncio.create_task(forward_events())
        try:
            while True:
                raw = await ws.receive_text()
                if len(raw.encode("utf-8")) > _MAX_MESSAGE_BYTES:
                    await ws.close(code=1009)
                    return
                try:
                    message = json.loads(raw)
                except (TypeError, ValueError):
                    await send({"type": "error", "code": "invalid_json", "message": "Malformed message"})
                    continue
                if not isinstance(message, dict):
                    await send({
                        "type": "error",
                        "code": "invalid_message",
                        "message": "A message must be an object",
                    })
                    continue
                kind = message.get("type", "")
                if kind == "ping":
                    await send({"type": "pong"})
                elif kind == "intent":
                    text = message.get("text", "")
                    if not isinstance(text, str) or not text.strip() or len(text) > 400:
                        await send({
                            "type": "error",
                            "code": "invalid_request",
                            "message": "Intent text must be 1-400 characters",
                        })
                        continue
                    expected = message.get("expected_version_id")
                    if expected is not None and (not isinstance(expected, str) or len(expected) > 80):
                        await send({
                            "type": "error",
                            "code": "invalid_request",
                            "message": "expected_version_id must be a short string",
                        })
                        continue
                    try:
                        updated = await studio_service.apply_intent(
                            session_id, text, expected_version_id=expected)
                    except StudioError as exc:
                        code, error_message = _error_message(exc)
                        await send({"type": "error", "code": code, "message": error_message})
                    else:
                        await send({"type": "snapshot", "session": updated})
                else:
                    await send({
                        "type": "error",
                        "code": "unsupported_message",
                        "message": "Unsupported message type",
                    })
        except WebSocketDisconnect:
            pass
        finally:
            forward_task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await forward_task
    finally:
        await animus_bus.unsubscribe(session_id, queue)
