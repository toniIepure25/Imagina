"""Per-session serialization for the local Studio service.

The product runs as a single local process. Serializing all mutations for one session prevents two
requests from committing from the same head and losing a branch update. Reads take the same lock so a
snapshot can never observe a half-applied in-memory commit.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator


class SessionLockRegistry:
    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}

    def lock(self, session_id: str) -> asyncio.Lock:
        lock = self._locks.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[session_id] = lock
        return lock

    @asynccontextmanager
    async def hold(self, session_id: str) -> AsyncIterator[None]:
        lock = self.lock(session_id)
        async with lock:
            yield

    def forget(self, session_id: str) -> None:
        lock = self._locks.get(session_id)
        if lock is not None and not lock.locked() and not lock._waiters:  # type: ignore[attr-defined]
            self._locks.pop(session_id, None)


__all__ = ["SessionLockRegistry"]
