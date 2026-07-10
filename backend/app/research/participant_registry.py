from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.research.randomization import generate_condition_sequence
from app.schemas.research import FeedbackCondition, Participant, ParticipantCreate
from app.storage.database import get_db


async def create_participant(data: ParticipantCreate, conditions: list[FeedbackCondition]) -> Participant:
    db = await get_db()
    try:
        now = datetime.now(timezone.utc).isoformat()
        participant_id = str(uuid.uuid4())
        seed = int(uuid.uuid4().int % (2**31))
        sequence = generate_condition_sequence(conditions, seed)

        participant = Participant(
            participant_id=participant_id,
            pseudonym=data.pseudonym,
            study_id=data.study_id,
            eligibility_confirmed=data.eligibility_confirmed,
            condition_sequence=sequence,
            sessions_completed=0,
            created_at=now,
            randomization_seed=seed,
        )
        sql = (
            "INSERT INTO participants"
            " (participant_id, study_id, pseudonym, created_at, payload)"
            " VALUES (?, ?, ?, ?, ?)"
        )
        await db.execute(
            sql,
            (participant_id, data.study_id, data.pseudonym, now, participant.model_dump_json()),
        )
        await db.commit()
        return participant
    finally:
        await db.close()


async def get_participant(participant_id: str) -> Participant | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT payload FROM participants WHERE participant_id = ?", (participant_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return Participant.model_validate_json(row["payload"])
    finally:
        await db.close()


async def list_participants(study_id: str) -> list[Participant]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT payload FROM participants WHERE study_id = ? ORDER BY created_at",
            (study_id,),
        )
        rows = await cursor.fetchall()
        return [Participant.model_validate_json(r["payload"]) for r in rows]
    finally:
        await db.close()


async def update_sessions_completed(participant_id: str, count: int) -> None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT payload FROM participants WHERE participant_id = ?", (participant_id,))
        row = await cursor.fetchone()
        if not row:
            return
        participant = Participant.model_validate_json(row["payload"])
        participant.sessions_completed = count
        await db.execute(
            "UPDATE participants SET payload = ? WHERE participant_id = ?",
            (participant.model_dump_json(), participant_id),
        )
        await db.commit()
    finally:
        await db.close()
