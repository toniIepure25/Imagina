"""Tests for outbox pattern — persistent event dispatch and atomicity."""
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
    async def test_publish_writes_inline(self, outbox_db):
        writer = PersistentOutboxWriter(outbox_db)
        ts = datetime.now(timezone.utc)
        await writer.publish(RuntimeEvent("test_event", "rs1", {"key": "val"}, ts))
        await outbox_db.commit()

        pending = await count_pending(outbox_db)
        assert pending == 1

    async def test_multiple_publishes_before_commit(self, outbox_db):
        writer = PersistentOutboxWriter(outbox_db)
        ts = datetime.now(timezone.utc)
        await writer.publish(RuntimeEvent("ev1", "rs1", {"a": 1}, ts))
        await writer.publish(RuntimeEvent("ev2", "rs1", {"b": 2}, ts))
        await outbox_db.commit()

        pending = await count_pending(outbox_db)
        assert pending == 2


class TestOutboxDispatcher:
    async def test_dispatch_marks_published(self, outbox_db):
        writer = PersistentOutboxWriter(outbox_db)
        ts = datetime.now(timezone.utc)
        await writer.publish(RuntimeEvent("ev1", "rs1", {"a": 1}, ts))
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


class TestTransactionalAtomicity:
    async def test_rollback_removes_domain_and_outbox(self, outbox_db):
        """1. Failure before commit: no domain record, no outbox record."""
        writer = PersistentOutboxWriter(outbox_db)
        ts = datetime.now(timezone.utc)
        await outbox_db.execute(
            "INSERT INTO trials (trial_id, research_session_id, trial_index, "
            "stimulus_id, status, state_version, planned_at) "
            "VALUES ('t-rollback', 'rs1', 99, 'stim', 'planned', 0, ?)",
            (ts.isoformat(),),
        )
        await writer.publish(RuntimeEvent("trial_created", "rs1", {"trial_id": "t-rollback"}, ts))
        await outbox_db.rollback()

        trial = await (await outbox_db.execute(
            "SELECT trial_id FROM trials WHERE trial_id = 't-rollback'"
        )).fetchone()
        assert trial is None
        assert await count_pending(outbox_db) == 0

    async def test_commit_preserves_both_domain_and_outbox(self, outbox_db):
        """2. Commit-then-crash: domain + outbox both exist, outbox pending."""
        writer = PersistentOutboxWriter(outbox_db)
        ts = datetime.now(timezone.utc)
        await outbox_db.execute(
            "INSERT INTO trials (trial_id, research_session_id, trial_index, "
            "stimulus_id, status, state_version, planned_at) "
            "VALUES ('t-commit', 'rs1', 98, 'stim', 'planned', 0, ?)",
            (ts.isoformat(),),
        )
        await writer.publish(RuntimeEvent("trial_created", "rs1", {"trial_id": "t-commit"}, ts))
        await outbox_db.commit()

        trial = await (await outbox_db.execute(
            "SELECT trial_id FROM trials WHERE trial_id = 't-commit'"
        )).fetchone()
        assert trial is not None
        assert await count_pending(outbox_db) == 1

    async def test_dispatcher_restart_delivers_pending(self, outbox_db):
        """3. Dispatcher restart: pending event is delivered."""
        writer = PersistentOutboxWriter(outbox_db)
        ts = datetime.now(timezone.utc)
        await writer.publish(RuntimeEvent("restart_ev", "rs1", {"data": 1}, ts))
        await outbox_db.commit()

        assert await count_pending(outbox_db) == 1

        consumer = CollectingOutboxConsumer()
        dispatched = await dispatch_pending(outbox_db, consumer)
        assert dispatched == 1
        assert consumer.received[0]["event_type"] == "restart_ev"
        assert await count_pending(outbox_db) == 0

    async def test_duplicate_dispatch_idempotent(self, outbox_db):
        """4. Duplicate dispatch: consumer receives once only."""
        writer = PersistentOutboxWriter(outbox_db)
        ts = datetime.now(timezone.utc)
        await writer.publish(RuntimeEvent("dup_ev", "rs1", {"x": 1}, ts))
        await outbox_db.commit()

        consumer = CollectingOutboxConsumer()
        await dispatch_pending(outbox_db, consumer)
        d2 = await dispatch_pending(outbox_db, consumer)
        assert d2 == 0
        assert len(consumer.received) == 1

    async def test_consumer_failure_leaves_retryable(self, outbox_db):
        """5. Consumer failure: event remains pending, attempt/error tracked."""
        writer = PersistentOutboxWriter(outbox_db)
        ts = datetime.now(timezone.utc)
        await writer.publish(RuntimeEvent("fail_ev", "rs1", {"a": 1}, ts))
        await outbox_db.commit()

        class FailOnce:
            def __init__(self):
                self.calls = 0
                self.received = []

            async def handle(self, event_type, payload, session_id, created_at):
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("Transient")
                self.received.append(event_type)

        consumer = FailOnce()
        await dispatch_pending(outbox_db, consumer)
        assert await count_pending(outbox_db) == 1

        row = await (await outbox_db.execute(
            "SELECT dispatch_attempts, last_error FROM runtime_event_outbox LIMIT 1"
        )).fetchone()
        assert row["dispatch_attempts"] == 1
        assert "Transient" in row["last_error"]

        await dispatch_pending(outbox_db, consumer)
        assert await count_pending(outbox_db) == 0
        assert len(consumer.received) == 1

    async def test_feedback_window_atomicity(self, outbox_db):
        """6. Feedback + outbox event: both present after commit, neither after rollback."""
        writer = PersistentOutboxWriter(outbox_db)
        ts = datetime.now(timezone.utc)

        await outbox_db.execute(
            "INSERT INTO feedback_records "
            "(feedback_record_id, research_session_id, window_index, "
            "condition, policy_id, policy_version, pid_value, iqi_value, "
            "scene_params_json, reason_code, safety_override, timestamp_utc, mono_elapsed) "
            "VALUES ('fb-atom-1', 'rs1', 0, 'adaptive', 'adaptive', '1.0', 0.3, 0.5, "
            "'{}', 'ok', 0, ?, 0.0)",
            (ts.isoformat(),),
        )
        await writer.publish(RuntimeEvent("feedback_recorded", "rs1", {"feedback_id": "fb-atom-1"}, ts))
        await outbox_db.commit()

        fb = await (await outbox_db.execute(
            "SELECT feedback_record_id FROM feedback_records WHERE feedback_record_id = 'fb-atom-1'"
        )).fetchone()
        assert fb is not None
        assert await count_pending(outbox_db) >= 1

        consumer = CollectingOutboxConsumer()
        await dispatch_pending(outbox_db, consumer)

        await outbox_db.execute(
            "INSERT INTO feedback_records "
            "(feedback_record_id, research_session_id, window_index, "
            "condition, policy_id, policy_version, pid_value, iqi_value, "
            "scene_params_json, reason_code, safety_override, timestamp_utc, mono_elapsed) "
            "VALUES ('fb-atom-2', 'rs1', 1, 'adaptive', 'adaptive', '1.0', 0.3, 0.5, "
            "'{}', 'ok', 0, ?, 0.0)",
            (ts.isoformat(),),
        )
        await writer.publish(RuntimeEvent("feedback_recorded", "rs1", {"feedback_id": "fb-atom-2"}, ts))
        await outbox_db.rollback()

        fb2 = await (await outbox_db.execute(
            "SELECT feedback_record_id FROM feedback_records WHERE feedback_record_id = 'fb-atom-2'"
        )).fetchone()
        assert fb2 is None
        pending_after = await count_pending(outbox_db)
        assert pending_after == 0


class TestProductionOutbox:
    async def test_orchestrator_writes_outbox_events(self):
        """Production orchestrator uses PersistentOutboxWriter inline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "prod_outbox.db")
            db = await aiosqlite.connect(db_path)
            db.row_factory = aiosqlite.Row
            await db.execute("PRAGMA foreign_keys = ON")
            await run_migrations(db)

            from app.research.synthetic_orchestrator import run_synthetic_study

            await run_synthetic_study(
                db=db, study_id="outbox-prod",
                participant_count=2, seed=42,
                trials_per_session=2, windows_per_trial=2,
            )

            row = await (await db.execute(
                "SELECT COUNT(*) as cnt FROM runtime_event_outbox"
            )).fetchone()
            assert row["cnt"] > 0

            published = await (await db.execute(
                "SELECT COUNT(*) as cnt FROM runtime_event_outbox WHERE published_at IS NOT NULL"
            )).fetchone()
            assert published["cnt"] == row["cnt"]

            pending = await count_pending(db)
            assert pending == 0

            await db.close()
