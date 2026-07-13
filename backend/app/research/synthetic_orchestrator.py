"""Synthetic study orchestrator — runs a complete synthetic workflow.

Executes: study creation, protocol freeze, yoked library, participants,
sequence allocation, all sessions (adaptive/fixed/yoked), and export.
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from app.research.event_sinks import CollectingEventSink
from app.research.feedback_policies import (
    AdaptiveFeedbackPolicy,
    FixedResearchFeedbackPolicy,
    FrozenYokedFeedbackPolicy,
)
from app.research.id_generator import DeterministicIdGenerator
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
from app.storage.migration_runner import run_migrations

logger = logging.getLogger(__name__)


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
    db_path: str,
    study_id: str = "synthetic-001",
    participant_count: int = 6,
    seed: int = 42,
    trials_per_session: int = 5,
    windows_per_trial: int = 3,
    export_dir: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await run_migrations(db)

    try:
        return await _execute_study(
            db, study_id, participant_count, seed,
            trials_per_session, windows_per_trial, export_dir, run_id,
        )
    finally:
        await db.close()


async def _execute_study(
    db: aiosqlite.Connection,
    study_id: str,
    participant_count: int,
    seed: int,
    trials_per_session: int,
    windows_per_trial: int,
    export_dir: str | None,
    run_id: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        "INSERT OR REPLACE INTO studies "
        "(study_id, title, application_mode, data_classification, lifecycle_status, "
        "study_seed, created_at, updated_at) "
        "VALUES (?, ?, 'research', 'synthetic', 'active', ?, ?, ?)",
        (study_id, f"Synthetic Study {study_id}", seed, now, now),
    )

    protocol_id = f"{study_id}-pv1"
    protocol_hash = hashlib.sha256(f"{study_id}:{seed}:protocol".encode()).hexdigest()[:16]
    await db.execute(
        "INSERT OR REPLACE INTO protocol_versions "
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
        await db.execute(
            "INSERT OR REPLACE INTO participants "
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

    for pid in participant_ids:
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
            condition = conditions_seq[session_idx].value

            session_id = f"{study_id}-{pid}-s{session_idx}"
            await db.execute(
                "INSERT OR REPLACE INTO research_sessions "
                "(research_session_id, study_id, participant_id, protocol_version_id, "
                "allocation_id, session_index, condition, data_classification, "
                "signal_provider_id, policy_id, policy_version, runtime_seed, "
                "status, state_version, planned_at, software_version, git_sha) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'synthetic', "
                "'simulated.deterministic', ?, '1.0', ?, "
                "'planned', 0, ?, '0.5.0', 'synthetic')",
                (
                    session_id, study_id, pid, protocol_id,
                    allocation_id, session_idx, condition, condition,
                    seed + session_idx,
                    now,
                ),
            )
            await db.commit()

            clock = DeterministicClock()
            id_gen = DeterministicIdGenerator(study_id, protocol_hash, seed + session_idx)
            sink = CollectingEventSink()
            safety = SyntheticSafetyMonitor()

            if condition == "adaptive":
                policy = AdaptiveFeedbackPolicy()
            elif condition == "fixed":
                policy = FixedResearchFeedbackPolicy()
            else:
                traj_id = await assign_trajectory(db, library_id, seed, pid, session_idx)
                points = await get_trajectory_points(db, traj_id)
                policy = FrozenYokedFeedbackPolicy(points, trajectory_id=traj_id)

            runtime = ResearchSessionRuntime(
                db=db, clock=clock, id_gen=id_gen,
                feedback_policy=policy, safety_monitor=safety,
                event_sink=sink,
            )

            try:
                await runtime.run_session(
                    session_id,
                    trial_count=trials_per_session,
                    windows_per_trial=windows_per_trial,
                )
                sessions_completed += 1
            except Exception as exc:
                logger.error("Session %s failed: %s", session_id, exc)
                sessions_failed += 1

    final_run_id = run_id or str(uuid.uuid4())
    if not run_id:
        await db.execute(
            "INSERT INTO runtime_runs "
            "(run_id, study_id, status, total_sessions, completed_sessions, "
            "failed_sessions, runtime_seed, created_at, ended_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                final_run_id, study_id,
                "completed_with_failures" if sessions_failed > 0 else "completed",
                participant_count * 3, sessions_completed, sessions_failed,
                seed, now, datetime.now(timezone.utc).isoformat(),
            ),
        )
        await db.commit()

    export_result = None
    if export_dir:
        export_result = await export_synthetic_dataset(db, study_id, export_dir)

    return {
        "study_id": study_id,
        "run_id": final_run_id,
        "participants": participant_count,
        "sessions_completed": sessions_completed,
        "sessions_failed": sessions_failed,
        "library_id": library_id,
        "protocol_id": protocol_id,
        "export": export_result,
    }


async def export_synthetic_dataset(
    db: aiosqlite.Connection,
    study_id: str,
    output_dir: str,
) -> dict[str, Any]:
    os.makedirs(output_dir, exist_ok=True)

    metadata = {
        "study_id": study_id,
        "data_classification": "synthetic",
        "export_schema_version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "Synthetic engineering validation only — not human-subject or neuroscientific evidence.",
    }
    _write_json(os.path.join(output_dir, "metadata.json"), metadata)

    study_row = await (await db.execute(
        "SELECT * FROM studies WHERE study_id = ?", (study_id,)
    )).fetchone()
    _write_json(os.path.join(output_dir, "study.json"), dict(study_row))

    pv_rows = await (await db.execute(
        "SELECT * FROM protocol_versions WHERE study_id = ?", (study_id,)
    )).fetchall()
    _write_json(os.path.join(output_dir, "protocol.json"), [dict(r) for r in pv_rows])

    await _export_table(db, output_dir, "participants.csv",
                        "SELECT * FROM participants WHERE study_id = ?", (study_id,))
    await _export_table(db, output_dir, "allocations.csv",
                        "SELECT * FROM sequence_allocations WHERE study_id = ?", (study_id,))
    await _export_table(db, output_dir, "sessions.csv",
                        "SELECT * FROM research_sessions WHERE study_id = ?", (study_id,))
    await _export_table(db, output_dir, "trials.csv",
                        "SELECT t.* FROM trials t JOIN research_sessions rs "
                        "ON t.research_session_id = rs.research_session_id "
                        "WHERE rs.study_id = ?", (study_id,))
    await _export_table(db, output_dir, "trial_responses.csv",
                        "SELECT tr.* FROM trial_responses tr JOIN trials t "
                        "ON tr.trial_id = t.trial_id JOIN research_sessions rs "
                        "ON t.research_session_id = rs.research_session_id "
                        "WHERE rs.study_id = ?", (study_id,))
    await _export_table(db, output_dir, "feedback_records.csv",
                        "SELECT fr.* FROM feedback_records fr JOIN research_sessions rs "
                        "ON fr.research_session_id = rs.research_session_id "
                        "WHERE rs.study_id = ?", (study_id,))
    await _export_table(db, output_dir, "safety_events.csv",
                        "SELECT se.* FROM safety_events se JOIN research_sessions rs "
                        "ON se.research_session_id = rs.research_session_id "
                        "WHERE rs.study_id = ?", (study_id,))

    checksums = {}
    for fname in os.listdir(output_dir):
        fpath = os.path.join(output_dir, fname)
        if os.path.isfile(fpath):
            with open(fpath, "rb") as f:
                checksums[fname] = hashlib.sha256(f.read()).hexdigest()

    checksum_path = os.path.join(output_dir, "checksums.sha256")
    with open(checksum_path, "w") as f:
        for name, h in sorted(checksums.items()):
            f.write(f"{h}  {name}\n")

    export_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO export_runs "
        "(export_id, study_id, data_classification, output_path, created_at) "
        "VALUES (?, ?, 'synthetic', ?, ?)",
        (export_id, study_id, output_dir, datetime.now(timezone.utc).isoformat()),
    )
    await db.commit()

    return {
        "export_id": export_id,
        "output_dir": output_dir,
        "files": list(checksums.keys()),
        "checksums": checksums,
    }


async def _export_table(
    db: aiosqlite.Connection,
    output_dir: str,
    filename: str,
    query: str,
    params: tuple = (),
) -> None:
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    if not rows:
        with open(os.path.join(output_dir, filename), "w", newline="") as f:
            f.write("")
        return

    columns = [desc[0] for desc in cursor.description]
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([row[col] for col in columns])


def _write_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)
