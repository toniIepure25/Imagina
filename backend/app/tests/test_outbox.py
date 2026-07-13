"""Tests for outbox pattern — persistent event dispatch."""
import os
import tempfile
from datetime import datetime, timezone

import aiosqlite
import pytest

from app.research.event_sinks import PersistentOutboxWriter, RuntimeEvent
from app.research.outbox import CollectingOutboxConsumer, count_pending, dispatch_pending
from app.storage.migration_runner import run_migrations


@pytest.fixture
async def outbox_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_outbox.db")
        db = await aiosqlite.connect(db_path)
        db.row_factory = aiosqlite.Row
        await run_migrations(db)
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO studies (study_id, title, application_mode, data_classification, "
            "lifecycle_status, created_at, updated_at) "
            "VALUES ('s1', 'Test', 'research', 'synthetic', 'active', ?, ?)",
            (now, now),
        )
        await db.execute(
            "INSERT INTO protocol_versions (protocol_version_id, study_id, version, "
            "status, created_at) VALUES ('pv1', 's1', 'v1', 'draft', ?)", (now,),
        )
        await db.execute(
            "INSERT INTO participants (participant_id, study_id, participant_kind, "
            "pseudonym, created_at) "
            "VALUES ('p1', 's1', 'synthetic', 'agent-1', ?)", (now,),
        )
        await db.execute(
            "INSERT INTO research_sessions (research_session_id, study_id, participant_id, "
            "protocol_version_id, allocation_id, session_index, condition, "
            "data_classification, signal_provider_id, policy_id, policy_version, "
            "runtime_seed, status, state_version, planned_at, software_version, git_sha) "
            "VALUES ('rs1', 's1', 'p1', 'pv1', 'a1', 0, 'adaptive', 'synthetic', "
            "'sim', 'adaptive', '1.0', 42, 'planned', 0, ?, '0.5.0', 'test')", (now,),
        )
        await db.commit()
        yield db
        await db.close()


class TestPersistentOutboxWriter:
    async def test_writes_events_to_outbox(self, outbox_db):
        writer = PersistentOutboxWriter(outbox_db)
        ts = datetime.now(timezone.utc)
        await writer.publish(RuntimeEvent("test_event", "rs1", {"key": "val"}, ts))
        await writer.flush()
        await outbox_db.commit()

        pending = await count_pending(outbox_db)
        assert pending == 1

    async def test_flush_within_transaction(self, outbox_db):
        writer = PersistentOutboxWriter(outbox_db)
        ts = datetime.now(timezone.utc)
        await writer.publish(RuntimeEvent("ev1", "rs1", {"a": 1}, ts))
        await writer.publish(RuntimeEvent("ev2", "rs1", {"b": 2}, ts))
        count = await writer.flush_within_transaction()
        assert count == 2
        await outbox_db.commit()

        pending = await count_pending(outbox_db)
        assert pending == 2


class TestOutboxDispatcher:
    async def test_dispatch_marks_published(self, outbox_db):
        writer = PersistentOutboxWriter(outbox_db)
        ts = datetime.now(timezone.utc)
        await writer.publish(RuntimeEvent("ev1", "rs1", {"a": 1}, ts))
        await writer.flush()
        await outbox_db.commit()

        consumer = CollectingOutboxConsumer()
        dispatched = await dispatch_pending(outbox_db, consumer)
        assert dispatched == 1
        assert len(consumer.received) == 1
        assert consumer.received[0]["event_type"] == "ev1"

        pending = await count_pending(outbox_db)
        assert pending == 0

    async def test_idempotent_redispatch(self, outbox_db):
        writer = PersistentOutboxWriter(outbox_db)
        ts = datetime.now(timezone.utc)
        await writer.publish(RuntimeEvent("ev1", "rs1", {"x": 1}, ts))
        await writer.flush()
        await outbox_db.commit()

        consumer = CollectingOutboxConsumer()
        await dispatch_pending(outbox_db, consumer)
        dispatched2 = await dispatch_pending(outbox_db, consumer)
        assert dispatched2 == 0
        assert len(consumer.received) == 1

    async def test_failed_dispatch_tracks_error(self, outbox_db):
        writer = PersistentOutboxWriter(outbox_db)
        ts = datetime.now(timezone.utc)
        await writer.publish(RuntimeEvent("ev1", "rs1", {"a": 1}, ts))
        await writer.flush()
        await outbox_db.commit()

        class FailingConsumer:
            async def handle(self, *args, **kwargs):
                raise RuntimeError("Consumer down")

        dispatched = await dispatch_pending(outbox_db, FailingConsumer())
        assert dispatched == 0

        row = await (await outbox_db.execute(
            "SELECT dispatch_attempts, last_error FROM runtime_event_outbox LIMIT 1"
        )).fetchone()
        assert row["dispatch_attempts"] == 1
        assert "Consumer down" in row["last_error"]

        pending = await count_pending(outbox_db)
        assert pending == 1

    async def test_no_partial_on_rollback(self, outbox_db):
        """If we rollback before commit, outbox events should not appear."""
        writer = PersistentOutboxWriter(outbox_db)
        ts = datetime.now(timezone.utc)
        await writer.publish(RuntimeEvent("ev1", "rs1", {"a": 1}, ts))
        count = await writer.flush_within_transaction()
        assert count == 1
        await outbox_db.rollback()

        pending = await count_pending(outbox_db)
        assert pending == 0
