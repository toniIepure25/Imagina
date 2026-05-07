import asyncio
import json
from typing import Any

from fastapi import WebSocket

from app.core.time import utcnow


class ConnectionManager:
    def __init__(self):
        self._active: dict[str, WebSocket] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        self._active[session_id] = ws
        self._locks[session_id] = asyncio.Lock()

    def disconnect(self, session_id: str):
        self._active.pop(session_id, None)
        self._locks.pop(session_id, None)

    def is_connected(self, session_id: str) -> bool:
        return session_id in self._active

    async def send(self, session_id: str, msg_type: str, payload: Any):
        ws = self._active.get(session_id)
        if not ws:
            return
        if isinstance(payload, dict):
            safe_payload = payload
        else:
            safe_payload = json.loads(json.dumps(payload, default=str))
        data = {
            "type": msg_type,
            "timestamp": utcnow().isoformat(),
            "payload": safe_payload,
        }
        lock = self._locks.get(session_id)
        if lock:
            async with lock:
                await ws.send_json(data)
        else:
            await ws.send_json(data)


ws_manager = ConnectionManager()
