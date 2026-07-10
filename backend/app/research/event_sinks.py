"""Event sink protocol and implementations for the research runtime.

The runtime publishes domain events through sinks. Persistence happens via
repositories (authoritative for domain tables). Event sinks publish already
committed domain events for subscribers (WebSocket, logging, test collection).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass
class RuntimeEvent:
    event_type: str
    research_session_id: str
    payload: dict[str, Any]
    timestamp: datetime
    trial_id: str | None = None


class EventSink(Protocol):
    async def publish(self, event: RuntimeEvent) -> None: ...
    async def flush(self) -> None: ...


class CollectingEventSink:
    def __init__(self) -> None:
        self.events: list[RuntimeEvent] = []

    async def publish(self, event: RuntimeEvent) -> None:
        self.events.append(event)

    async def flush(self) -> None:
        pass

    def clear(self) -> None:
        self.events.clear()


class CompositeEventSink:
    def __init__(self, sinks: list[EventSink] | None = None):
        self._sinks: list[EventSink] = sinks or []

    def add(self, sink: EventSink) -> None:
        self._sinks.append(sink)

    async def publish(self, event: RuntimeEvent) -> None:
        for sink in self._sinks:
            await sink.publish(event)

    async def flush(self) -> None:
        for sink in self._sinks:
            await sink.flush()


class NullEventSink:
    async def publish(self, event: RuntimeEvent) -> None:
        pass

    async def flush(self) -> None:
        pass
