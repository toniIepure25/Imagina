from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.schemas.research import (
    ConditionAssignment,
    FeedbackCondition,
    Study,
    StudyCreate,
)
from app.storage.database import get_db


async def create_study(data: StudyCreate) -> Study:
    db = await get_db()
    try:
        now = datetime.now(timezone.utc).isoformat()
        study = Study(
            study_id=data.study_id,
            title=data.title,
            protocol_version=data.protocol_version,
            conditions=data.conditions,
            description=data.description,
            ethics_status=data.ethics_status,
            ethics_reference=data.ethics_reference,
            created_at=now,
            status="created",
        )
        await db.execute(
            "INSERT INTO studies "
            "(study_id, title, application_mode, data_classification, lifecycle_status, "
            "study_seed, created_at, updated_at, payload) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                study.study_id, study.title, "pilot", "synthetic", "draft",
                None, now, now, study.model_dump_json(),
            ),
        )
        await db.commit()
        return study
    finally:
        await db.close()


async def get_study(study_id: str) -> Study | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT payload FROM studies WHERE study_id = ?", (study_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return Study.model_validate_json(row["payload"])
    finally:
        await db.close()


async def list_studies() -> list[Study]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT payload FROM studies ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [Study.model_validate_json(r["payload"]) for r in rows]
    finally:
        await db.close()


async def get_condition_for_session(
    participant_id: str, study_id: str, session_index: int,
) -> ConditionAssignment | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT payload FROM condition_assignments "
            "WHERE participant_id = ? AND study_id = ? AND session_index = ?",
            (participant_id, study_id, session_index),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return ConditionAssignment.model_validate_json(row["payload"])
    finally:
        await db.close()


async def assign_condition(
    participant_id: str, study_id: str, session_index: int, condition: FeedbackCondition,
) -> ConditionAssignment:
    db = await get_db()
    try:
        now = datetime.now(timezone.utc).isoformat()
        assignment = ConditionAssignment(
            participant_id=participant_id,
            study_id=study_id,
            session_index=session_index,
            condition=condition,
            assigned_at=now,
        )
        assignment_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO condition_assignments "
            "(assignment_id, participant_id, study_id, session_index, condition, assigned_at, payload) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                assignment_id, participant_id, study_id, session_index,
                condition.value, now, assignment.model_dump_json(),
            ),
        )
        await db.commit()
        return assignment
    finally:
        await db.close()


def require_study_mode(current_mode: str, minimum: str) -> bool:
    hierarchy = {"demo": 0, "benchmark": 1, "pilot": 2, "approved_study": 3}
    return hierarchy.get(current_mode, 0) >= hierarchy.get(minimum, 0)
