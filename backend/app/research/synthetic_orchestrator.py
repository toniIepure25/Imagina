"""Synthetic study orchestrator — runs a complete synthetic workflow.

Executes: study creation, protocol freeze, yoked library, participants,
sequence allocation, all sessions (adaptive/fixed/yoked), and export.
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from app.research.event_sinks import PersistentOutboxWriter
from app.research.export_service import export_synthetic_dataset
from app.research.feedback_policies import (
    AdaptiveFeedbackPolicy,
    FixedResearchFeedbackPolicy,
    FrozenYokedFeedbackPolicy,
)
from app.research.id_generator import DeterministicIdGenerator
from app.research.manifest import create_session_manifest, seal_session_completion
from app.research.outbox import LoggingOutboxConsumer, dispatch_pending
from app.research.replay_validator import compute_session_replay_hash
from app.research.runtime import ResearchSessionRuntime, SafetyDecision
from app.research.runtime_clock import DeterministicClock
from app.research.sequence_allocator import WILLIAMS_SEQUENCES, allocate_sequence
from app.research.yoked_library import (
    assign_trajectory,
    create_library,
    freeze_library,
    generate_trajectories,
    get_trajectory_points,
)

logger = logging.getLogger(__name__)


class OrchestratorError(Exception):
    pass


class StudySetupError(OrchestratorError):
    pass


class SessionExecutionError(OrchestratorError):
    def __init__(self, session_id: str, condition: str, cause: Exception):
        self.session_id = session_id
        self.condition = condition
        self.cause = cause
        super().__init__(f"Session {session_id} ({condition}) failed: {cause}")


class SyntheticSafetyMonitor:
    async def check(self, state, window_index, elapsed_s) -> SafetyDecision:
        fatigue = state.get("fatigue", 0)
        if fatigue > 0.85:
            return SafetyDecision(
                should_stop=True, severity="warning",
                reason_code="fatigue_high", metric_name="fatigue",
                metric_value=fatigue, action="stop_session",
            )
        return SafetyDecision(should_stop=False)


async def run_synthetic_study(
    db: aiosqlite.Connection,
    study_id: str = "synthetic-001",
    participant_count: int = 6,
    seed: int = 42,
    trials_per_session: int = 5,
    windows_per_trial: int = 3,
    export_dir: str | None = None,
    run_id: str | None = None,
    abort_check: Any = None,
) -> dict[str, Any]:
    return await _execute_study(
        db, study_id, participant_count, seed,
        trials_per_session, windows_per_trial, export_dir, run_id, abort_check,
    )


async def _execute_study(
    db: aiosqlite.Connection,
    study_id: str,
    participant_count: int,
    seed: int,
    trials_per_session: int,
    windows_per_trial: int,
    export_dir: str | None,
    run_id: str | None = None,
    abort_check: Any = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()

    existing_study = await (await db.execute(
        "SELECT study_id FROM studies WHERE study_id = ?", (study_id,)
    )).fetchone()
    if not existing_study:
        await db.execute(
            "INSERT INTO studies "
            "(study_id, title, application_mode, data_classification, lifecycle_status, "
            "study_seed, created_at, updated_at) "
            "VALUES (?, ?, 'research', 'synthetic', 'active', ?, ?, ?)",
            (study_id, f"Synthetic Study {study_id}", seed, now, now),
        )

    protocol_id = f"{study_id}-pv1"
    protocol_hash = hashlib.sha256(f"{study_id}:{seed}:protocol".encode()).hexdigest()[:16]
    existing_pv = await (await db.execute(
        "SELECT protocol_version_id FROM protocol_versions WHERE protocol_version_id = ?",
        (protocol_id,),
    )).fetchone()
    if not existing_pv:
        await db.execute(
            "INSERT INTO protocol_versions "
            "(protocol_version_id, study_id, version, status, frozen_at, protocol_hash, created_at) "
            "VALUES (?, ?, '1.0', 'frozen', ?, ?, ?)",
            (protocol_id, study_id, now, protocol_hash, now),
        )

    await db.execute(
        "UPDATE studies SET active_protocol_version_id = ? WHERE study_id = ?",
        (protocol_id, study_id),
    )
    await db.commit()

    schedule_hash = hashlib.sha256(f"{study_id}:{seed}:schedule".encode()).hexdigest()[:16]
    library_id = await create_library(db, study_id, protocol_id, schedule_hash, seed)
    total_windows = trials_per_session * windows_per_trial
    await generate_trajectories(db, library_id, 6, total_windows, schedule_hash)
    await freeze_library(db, library_id)

    participant_ids: list[str] = []
    for i in range(participant_count):
        pid = f"{study_id}-p{i:03d}"
        existing_p = await (await db.execute(
            "SELECT participant_id FROM participants WHERE participant_id = ?", (pid,)
        )).fetchone()
        if not existing_p:
            await db.execute(
                "INSERT INTO participants "
                "(participant_id, study_id, pseudonym, participant_kind, "
                "eligibility_confirmed, created_at) "
                "VALUES (?, ?, ?, 'synthetic', 1, ?)",
                (pid, study_id, f"SYNTH-{i:03d}", now),
            )
        participant_ids.append(pid)
    await db.commit()

    for pid in participant_ids:
        await allocate_sequence(study_id, pid, seed, db=db)

    sessions_completed = 0
    sessions_failed = 0
    sessions_aborted = 0
    session_errors: list[SessionExecutionError] = []
    run_aborted = False

    for pid in participant_ids:
        if run_aborted:
            break

        if abort_check and await abort_check():
            run_aborted = True
            break

        alloc_row = await (await db.execute(
            "SELECT allocation_id, sequence_label FROM sequence_allocations "
            "WHERE study_id = ? AND participant_id = ?",
            (study_id, pid),
        )).fetchone()

        seq_label = alloc_row["sequence_label"]
        allocation_id = alloc_row["allocation_id"]
        conditions_seq = None
        for label, seq in WILLIAMS_SEQUENCES:
            if label == seq_label:
                conditions_seq = seq
                break

        for session_idx in range(3):
            if abort_check and await abort_check():
                run_aborted = True
                break

            condition = conditions_seq[session_idx].value
            session_id = f"{study_id}-{pid}-s{session_idx}"
            session_seed = seed + session_idx

            existing_sess = await (await db.execute(
                "SELECT research_session_id FROM research_sessions WHERE research_session_id = ?",
                (session_id,)
            )).fetchone()
            if not existing_sess:
                await db.execute(
                    "INSERT INTO research_sessions "
                    "(research_session_id, study_id, participant_id, protocol_version_id, "
                    "allocation_id, session_index, condition, data_classification, "
                    "signal_provider_id, policy_id, policy_version, runtime_seed, "
                    "status, state_version, planned_at, software_version, git_sha) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, 'synthetic', "
                    "'synthetic.deterministic', ?, '1.0', ?, "
                    "'planned', 0, ?, '0.5.0', 'synthetic')",
                    (
                        session_id, study_id, pid, protocol_id,
                        allocation_id, session_idx, condition, condition,
                        session_seed, now,
                    ),
                )
                await db.commit()

            yoked_traj_id = None
            if condition == "yoked":
                yoked_traj_id = await assign_trajectory(db, library_id, seed, pid, session_idx)

            await create_session_manifest(
                db, session_id,
                study_id=study_id,
                protocol_version_id=protocol_id,
                protocol_hash=protocol_hash,
                participant_id=pid,
                allocation_id=allocation_id,
                condition=condition,
                session_index=session_idx,
                data_classification="synthetic",
                runtime_seed=session_seed,
                signal_provider_id="synthetic.deterministic",
                policy_id=condition,
                policy_version="1.0",
                yoked_trajectory_id=yoked_traj_id,
                yoked_library_id=library_id if condition == "yoked" else None,
                yoked_schedule_hash=schedule_hash if condition == "yoked" else None,
                trial_count=trials_per_session,
                windows_per_trial=windows_per_trial,
            )
            await db.commit()

            clock = DeterministicClock()
            id_gen = DeterministicIdGenerator(study_id, protocol_hash, session_seed)
            sink = PersistentOutboxWriter(db)
            safety = SyntheticSafetyMonitor()

            if condition == "adaptive":
                policy = AdaptiveFeedbackPolicy()
            elif condition == "fixed":
                policy = FixedResearchFeedbackPolicy()
            else:
                points = await get_trajectory_points(db, yoked_traj_id)
                policy = FrozenYokedFeedbackPolicy(points, trajectory_id=yoked_traj_id)

            runtime = ResearchSessionRuntime(
                db=db, clock=clock, id_gen=id_gen,
                feedback_policy=policy, safety_monitor=safety,
                event_sink=sink,
                abort_check=abort_check,
            )

            try:
                terminal_reason = await runtime.run_session(
                    session_id,
                    trial_count=trials_per_session,
                    windows_per_trial=windows_per_trial,
                )

                if terminal_reason == "aborted":
                    sessions_aborted += 1
                    run_aborted = True
                else:
                    sessions_completed += 1

                content_hash_result = await compute_session_replay_hash(db, session_id)
                await seal_session_completion(
                    db, session_id,
                    terminal_status=terminal_reason,
                    terminal_reason=terminal_reason,
                    content_hash=content_hash_result["content_hash"],
                    sealed_at=datetime.now(timezone.utc),
                )
                await db.commit()
                await dispatch_pending(db, LoggingOutboxConsumer())
            except Exception as exc:
                err = SessionExecutionError(session_id, condition, exc)
                session_errors.append(err)
                logger.error("Session %s failed: %s", session_id, exc)
                sessions_failed += 1

    final_run_id = run_id or str(uuid.uuid4())
    if not run_id:
        if run_aborted:
            final_status = "aborted"
        elif sessions_failed > 0:
            final_status = "completed_with_failures"
        else:
            final_status = "completed"
        await db.execute(
            "INSERT INTO runtime_runs "
            "(run_id, study_id, status, total_sessions, completed_sessions, "
            "failed_sessions, runtime_seed, created_at, ended_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                final_run_id, study_id, final_status,
                participant_count * 3, sessions_completed, sessions_failed,
                seed, now, datetime.now(timezone.utc).isoformat(),
            ),
        )
        await db.commit()

    export_result = None
    if export_dir and not run_aborted:
        export_result = await export_synthetic_dataset(db, study_id, export_dir, allow_overwrite=True)

    return {
        "study_id": study_id,
        "run_id": final_run_id,
        "participants": participant_count,
        "sessions_completed": sessions_completed,
        "sessions_failed": sessions_failed,
        "sessions_aborted": sessions_aborted,
        "aborted": run_aborted,
        "library_id": library_id,
        "protocol_id": protocol_id,
        "export": export_result,
        "errors": [str(e) for e in session_errors] if session_errors else [],
    }
