"""In-process pub/sub for ANIMUS Studio events.

The studio is local-first and single-process; a tiny asyncio queue fan-out is enough for live updates. A
slow client must never block a scene commit, but it also must not silently miss updates: when its queue
overflows the bus drops the backlog and inserts a ``resync_required`` marker so the client can refresh.
"""
from __future__ import annotations

import asyncio
from typing import Any


class AnimusEventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, session_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=64)
        async with self._lock:
            self._subscribers.setdefault(session_id, set()).add(queue)
        return queue

    async def unsubscribe(self, session_id: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(session_id)
            if subscribers is not None:
                subscribers.discard(queue)
                if not subscribers:
                    self._subscribers.pop(session_id, None)

    async def publish(self, session_id: str, event: dict[str, Any]) -> None:
        async with self._lock:
            queues = list(self._subscribers.get(session_id, ()))
        for queue in queues:
            if queue.full():
                while True:
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                try:
                    queue.put_nowait({"type": "resync_required", "reason": "queue_overflow"})
                except asyncio.QueueFull:
                    pass
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def subscriber_count(self, session_id: str) -> int:
        return len(self._subscribers.get(session_id, ()))


animus_bus = AnimusEventBus()

__all__ = ["AnimusEventBus", "animus_bus"]
