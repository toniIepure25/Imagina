"""Tests for transport-independent research session runtime."""
import os
import tempfile

import aiosqlite
import pytest

from app.research.event_sinks import CollectingEventSink
from app.research.id_generator import DeterministicIdGenerator
from app.research.runtime import (
    FeedbackContext,
    FeedbackDecision,
    ResearchSessionRuntime,
    SafetyDecision,
)
from app.research.runtime_clock import DeterministicClock
from app.storage.migration_runner import run_migrations


class MockPolicy:
    policy_id = "adaptive"
    policy_version = "1.0"

    async def compute(self, context: FeedbackContext) -> FeedbackDecision:
        return FeedbackDecision(
            scene_params={"scene_clarity": 0.5 + context.iqi * 0.3},
            prompt_text="Continue imagining.",
            reason="adaptive_compute",
            policy_id=self.policy_id,
            policy_version=self.policy_version,
        )


class MockFixedPolicy:
    policy_id = "fixed"
    policy_version = "1.0"

    async def compute(self, context: FeedbackContext) -> FeedbackDecision:
        return FeedbackDecision(
            scene_params={"scene_clarity": 0.5},
            prompt_text="Continue imagining.",
            reason="fixed",
            policy_id=self.policy_id,
            policy_version=self.policy_version,
        )


class MockSafetyMonitor:
    def __init__(self, stop_at_window: int | None = None):
        self._stop_at = stop_at_window

    async def check(self, state, window_index, elapsed_s) -> SafetyDecision:
        if self._stop_at is not None and window_index >= self._stop_at:
            return SafetyDecision(
                should_stop=True, severity="warning",
                reason_code="fatigue_high", metric_name="fatigue",
                metric_value=0.85, action="stop_session",
            )
        return SafetyDecision(should_stop=False)


@pytest.fixture
async def runtime_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "runtime_test.db")
        db = await aiosqlite.connect(path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await run_migrations(db)
        await db.execute(
            "INSERT INTO studies (study_id, title, data_classification, created_at, updated_at) "
            "VALUES ('s1', 'Test', 'synthetic', '2026-01-01', '2026-01-01')"
        )
        await db.execute(
            "INSERT INTO protocol_versions (protocol_version_id, study_id, version, status, created_at) "
            "VALUES ('pv1', 's1', '1.0', 'frozen', '2026-01-01')"
        )
        await db.execute(
            "INSERT INTO participants (participant_id, study_id, pseudonym, participant_kind, created_at) "
            "VALUES ('p1', 's1', 'SYNTH-001', 'synthetic', '2026-01-01')"
        )
        await db.execute(
            "INSERT INTO sequence_allocations "
            "(allocation_id, study_id, participant_id, sequence_id, sequence_label, allocated_at) "
            "VALUES ('a1', 's1', 'p1', 'ABC', 'ABC', '2026-01-01')"
        )
        await db.execute(
            "INSERT INTO research_sessions "
            "(research_session_id, study_id, participant_id, protocol_version_id, "
            "allocation_id, session_index, condition, data_classification, "
            "signal_provider_id, policy_id, policy_version, runtime_seed, "
            "status, state_version, planned_at, software_version) "
            "VALUES ('rs1', 's1', 'p1', 'pv1', 'a1', 0, 'adaptive', 'synthetic', "
            "'simulated.deterministic', 'adaptive', '1.0', 42, 'planned', 0, '2026-01-01', '0.5.0')"
        )
        await db.commit()
        yield db
        await db.close()


class TestRuntimeExecution:
    async def test_session_completes(self, runtime_db):
        clock = DeterministicClock()
        id_gen = DeterministicIdGenerator("s1", "proto_hash", 42)
        sink = CollectingEventSink()
        policy = MockPolicy()
        safety = MockSafetyMonitor()

        runtime = ResearchSessionRuntime(
            db=runtime_db, clock=clock, id_gen=id_gen,
            feedback_policy=policy, safety_monitor=safety,
            event_sink=sink,
        )

        result = await runtime.run_session("rs1", trial_count=3, windows_per_trial=2)
        assert result == "completed"

        row = await (await runtime_db.execute(
            "SELECT status FROM research_sessions WHERE research_session_id='rs1'"
        )).fetchone()
        assert row["status"] == "completed"

    async def test_trials_persisted(self, runtime_db):
        clock = DeterministicClock()
        id_gen = DeterministicIdGenerator("s1", "proto_hash", 42)
        sink = CollectingEventSink()

        runtime = ResearchSessionRuntime(
            db=runtime_db, clock=clock, id_gen=id_gen,
            feedback_policy=MockPolicy(), safety_monitor=MockSafetyMonitor(),
            event_sink=sink,
        )

        await runtime.run_session("rs1", trial_count=3, windows_per_trial=2)

        cursor = await runtime_db.execute(
            "SELECT COUNT(*) FROM trials WHERE research_session_id='rs1'"
        )
        count = (await cursor.fetchone())[0]
        assert count == 3

    async def test_feedback_records_persisted(self, runtime_db):
        clock = DeterministicClock()
        id_gen = DeterministicIdGenerator("s1", "proto_hash", 42)
        sink = CollectingEventSink()

        runtime = ResearchSessionRuntime(
            db=runtime_db, clock=clock, id_gen=id_gen,
            feedback_policy=MockPolicy(), safety_monitor=MockSafetyMonitor(),
            event_sink=sink,
        )

        await runtime.run_session("rs1", trial_count=2, windows_per_trial=3)

        cursor = await runtime_db.execute(
            "SELECT COUNT(*) FROM feedback_records WHERE research_session_id='rs1'"
        )
        count = (await cursor.fetchone())[0]
        assert count == 6  # 2 trials * 3 windows

    async def test_safety_stop_terminates(self, runtime_db):
        clock = DeterministicClock()
        id_gen = DeterministicIdGenerator("s1", "proto_hash", 42)
        sink = CollectingEventSink()
        safety = MockSafetyMonitor(stop_at_window=1)

        runtime = ResearchSessionRuntime(
            db=runtime_db, clock=clock, id_gen=id_gen,
            feedback_policy=MockPolicy(), safety_monitor=safety,
            event_sink=sink,
        )

        result = await runtime.run_session("rs1", trial_count=5, windows_per_trial=3)
        assert result == "safety_stopped"

        row = await (await runtime_db.execute(
            "SELECT status FROM research_sessions WHERE research_session_id='rs1'"
        )).fetchone()
        assert row["status"] == "safety_stopped"

    async def test_events_published(self, runtime_db):
        clock = DeterministicClock()
        id_gen = DeterministicIdGenerator("s1", "proto_hash", 42)
        sink = CollectingEventSink()

        runtime = ResearchSessionRuntime(
            db=runtime_db, clock=clock, id_gen=id_gen,
            feedback_policy=MockPolicy(), safety_monitor=MockSafetyMonitor(),
            event_sink=sink,
        )

        await runtime.run_session("rs1", trial_count=2, windows_per_trial=2)

        event_types = [e.event_type for e in sink.events]
        assert "session_ready" in event_types
        assert "session_started" in event_types
        assert "session_completed" in event_types
        assert "trial_completed" in event_types

    async def test_deterministic_ids(self, runtime_db):
        clock = DeterministicClock()
        id_gen = DeterministicIdGenerator("s1", "proto_hash", 42)
        sink = CollectingEventSink()

        runtime = ResearchSessionRuntime(
            db=runtime_db, clock=clock, id_gen=id_gen,
            feedback_policy=MockPolicy(), safety_monitor=MockSafetyMonitor(),
            event_sink=sink,
        )

        await runtime.run_session("rs1", trial_count=2, windows_per_trial=1)

        cursor = await runtime_db.execute(
            "SELECT trial_id FROM trials WHERE research_session_id='rs1' ORDER BY trial_index"
        )
        ids = [row["trial_id"] for row in await cursor.fetchall()]
        assert len(ids) == 2
        assert ids[0] != ids[1]
        assert all("-" in tid for tid in ids)

    async def test_fixed_policy_constant_output(self, runtime_db):
        clock = DeterministicClock()
        id_gen = DeterministicIdGenerator("s1", "proto_hash", 42)
        sink = CollectingEventSink()

        runtime = ResearchSessionRuntime(
            db=runtime_db, clock=clock, id_gen=id_gen,
            feedback_policy=MockFixedPolicy(), safety_monitor=MockSafetyMonitor(),
            event_sink=sink,
        )

        await runtime.run_session("rs1", trial_count=2, windows_per_trial=2)

        import json
        cursor = await runtime_db.execute(
            "SELECT scene_params_json FROM feedback_records WHERE research_session_id='rs1'"
        )
        rows = await cursor.fetchall()
        params_list = [json.loads(r["scene_params_json"]) for r in rows]
        assert all(p["scene_clarity"] == 0.5 for p in params_list)
