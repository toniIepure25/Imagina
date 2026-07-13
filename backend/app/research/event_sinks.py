"""Event sink protocol and implementations for the research runtime.

The runtime publishes domain events through sinks. Persistence happens via
repositories (authoritative for domain tables). Event sinks publish already
committed domain events for subscribers (WebSocket, logging, test collection).
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

import aiosqlite


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


class PersistentOutboxWriter:
    """Writes events to runtime_event_outbox inside the caller's transaction."""

    def __init__(self, db: aiosqlite.Connection):
        self._db = db
        self._pending: list[RuntimeEvent] = []

    async def publish(self, event: RuntimeEvent) -> None:
        self._pending.append(event)

    async def flush(self) -> None:
        for event in self._pending:
            await self._db.execute(
                "INSERT INTO runtime_event_outbox "
                "(outbox_id, research_session_id, event_type, payload_json, "
                "created_at, dispatch_attempts) "
                "VALUES (?, ?, ?, ?, ?, 0)",
                (
                    str(uuid.uuid4()),
                    event.research_session_id,
                    event.event_type,
                    json.dumps(event.payload, default=str),
                    event.timestamp.isoformat(),
                ),
            )
        self._pending.clear()

    async def flush_within_transaction(self) -> int:
        """Write pending events as part of the current transaction (no commit)."""
        count = 0
        for event in self._pending:
            await self._db.execute(
                "INSERT INTO runtime_event_outbox "
                "(outbox_id, research_session_id, event_type, payload_json, "
                "created_at, dispatch_attempts) "
                "VALUES (?, ?, ?, ?, ?, 0)",
                (
                    str(uuid.uuid4()),
                    event.research_session_id,
                    event.event_type,
                    json.dumps(event.payload, default=str),
                    event.timestamp.isoformat(),
                ),
            )
            count += 1
        self._pending.clear()
        return count
