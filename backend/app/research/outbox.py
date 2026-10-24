"""Outbox dispatcher — reads committed outbox rows, dispatches, marks published.

The outbox pattern ensures domain records and events are atomically committed.
The dispatcher runs after commit to forward events to downstream consumers.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Protocol

import aiosqlite

logger = logging.getLogger(__name__)


class OutboxConsumer(Protocol):
    async def handle(self, event_type: str, payload: dict[str, Any],
                     session_id: str, created_at: str) -> None: ...


class CollectingOutboxConsumer:
    def __init__(self) -> None:
        self.received: list[dict[str, Any]] = []

    async def handle(self, event_type: str, payload: dict[str, Any],
                     session_id: str, created_at: str) -> None:
        self.received.append({
            "event_type": event_type,
            "payload": payload,
            "session_id": session_id,
            "created_at": created_at,
        })


class LoggingOutboxConsumer:
    async def handle(self, event_type: str, payload: dict[str, Any],
                     session_id: str, created_at: str) -> None:
        logger.info("Outbox event: %s session=%s", event_type, session_id)


async def dispatch_pending(
    db: aiosqlite.Connection,
    consumer: OutboxConsumer,
    batch_size: int = 100,
) -> int:
    rows = await (await db.execute(
        "SELECT outbox_id, research_session_id, event_type, payload_json, created_at "
        "FROM runtime_event_outbox "
        "WHERE published_at IS NULL "
        "ORDER BY created_at ASC "
        "LIMIT ?",
        (batch_size,),
    )).fetchall()

    dispatched = 0
    for row in rows:
        outbox_id = row["outbox_id"]
        try:
            payload = json.loads(row["payload_json"])
            await consumer.handle(
                row["event_type"], payload,
                row["research_session_id"], row["created_at"],
            )
            now = datetime.now(timezone.utc).isoformat()
            await db.execute(
                "UPDATE runtime_event_outbox "
                "SET published_at = ?, dispatch_attempts = dispatch_attempts + 1 "
                "WHERE outbox_id = ?",
                (now, outbox_id),
            )
            dispatched += 1
        except Exception as exc:
            await db.execute(
                "UPDATE runtime_event_outbox "
                "SET dispatch_attempts = dispatch_attempts + 1, last_error = ? "
                "WHERE outbox_id = ?",
                (str(exc), outbox_id),
            )
            logger.warning("Outbox dispatch failed for %s: %s", outbox_id, exc)

    if dispatched > 0:
        await db.commit()
    return dispatched


async def count_pending(db: aiosqlite.Connection) -> int:
    row = await (await db.execute(
        "SELECT COUNT(*) FROM runtime_event_outbox WHERE published_at IS NULL"
    )).fetchone()
    return row[0] if row else 0
