"""Injectable clock abstractions for deterministic testing and replay.

Domain logic must not call datetime.now(), time.monotonic(), or asyncio.sleep() directly.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Protocol


class RuntimeClock(Protocol):
    def utc_now(self) -> datetime: ...
    def monotonic(self) -> float: ...
    async def sleep(self, seconds: float) -> None: ...


class WallClock:
    def utc_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def monotonic(self) -> float:
        return time.monotonic()

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


class DeterministicClock:
    def __init__(self, start_utc: datetime | None = None, tick_ms: int = 2000):
        self._base = start_utc or datetime(2026, 1, 1, tzinfo=timezone.utc)
        self._tick_ms = tick_ms
        self._ticks = 0
        self._mono_base = 0.0

    def utc_now(self) -> datetime:
        from datetime import timedelta
        result = self._base + timedelta(milliseconds=self._ticks * self._tick_ms)
        self._ticks += 1
        return result

    def monotonic(self) -> float:
        result = self._mono_base + (self._ticks * self._tick_ms / 1000.0)
        return result

    async def sleep(self, seconds: float) -> None:
        pass

    def reset(self) -> None:
        self._ticks = 0
