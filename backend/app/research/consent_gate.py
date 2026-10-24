from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.schemas.research import ConsentCreate, ConsentRecord
from app.storage.database import get_db


async def record_consent(data: ConsentCreate) -> ConsentRecord:
    db = await get_db()
    try:
        p_cursor = await db.execute(
            "SELECT participant_id FROM participants WHERE participant_id = ? AND study_id = ?",
            (data.participant_id, data.study_id),
        )
        if not await p_cursor.fetchone():
            raise ValueError(
                f"Participant {data.participant_id} does not belong to study {data.study_id}"
            )

        now = datetime.now(timezone.utc).isoformat()
        consent_id = str(uuid.uuid4())
        record = ConsentRecord(
            consent_id=consent_id,
            participant_id=data.participant_id,
            study_id=data.study_id,
            consent_version=data.consent_version,
            consented_at=now,
        )
        await db.execute(
            "INSERT INTO consents "
            "(consent_id, participant_id, study_id, protocol_version_id, "
            "consent_document_version_id, consented_at, payload) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                consent_id, data.participant_id, data.study_id,
                None, None, now, record.model_dump_json(),
            ),
        )
        await db.commit()
        return record
    finally:
        await db.close()


async def has_valid_consent(participant_id: str, study_id: str) -> bool:
    db = await get_db()
    try:
        p_cursor = await db.execute(
            "SELECT participant_id FROM participants WHERE participant_id = ? AND study_id = ?",
            (participant_id, study_id),
        )
        if not await p_cursor.fetchone():
            return False

        cursor = await db.execute(
            "SELECT payload FROM consents "
            "WHERE participant_id = ? AND study_id = ? "
            "ORDER BY consented_at DESC LIMIT 1",
            (participant_id, study_id),
        )
        row = await cursor.fetchone()
        if not row:
            return False
        record = ConsentRecord.model_validate_json(row["payload"])
        return not record.withdrawn
    finally:
        await db.close()


async def get_consent(participant_id: str, study_id: str) -> ConsentRecord | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT payload FROM consents "
            "WHERE participant_id = ? AND study_id = ? "
            "ORDER BY consented_at DESC LIMIT 1",
            (participant_id, study_id),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return ConsentRecord.model_validate_json(row["payload"])
    finally:
        await db.close()


async def withdraw_consent(participant_id: str, study_id: str) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT consent_id, payload FROM consents "
            "WHERE participant_id = ? AND study_id = ? "
            "ORDER BY consented_at DESC LIMIT 1",
            (participant_id, study_id),
        )
        row = await cursor.fetchone()
        if not row:
            return False
        record = ConsentRecord.model_validate_json(row["payload"])
        record.withdrawn = True
        record.withdrawn_at = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "UPDATE consents SET withdrawn_at = ?, payload = ? WHERE consent_id = ?",
            (record.withdrawn_at, record.model_dump_json(), row["consent_id"]),
        )
        await db.commit()
        return True
    finally:
        await db.close()
