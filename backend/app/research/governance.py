"""Research governance services — readiness evaluation and capability reporting.

The environment variable IMAGINA_STUDY_MODE controls the application's
operating mode but is NOT ethics approval. Human data collection requires
database-backed evidence of protocol freeze, ethics review, and valid consent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.storage.database import get_db


@dataclass
class ReadinessCheck:
    check: str
    status: str
    reason: str


@dataclass
class ReadinessResult:
    allowed: bool
    checks: list[ReadinessCheck] = field(default_factory=list)


async def evaluate_collection_readiness(
    study_id: str,
    participant_id: str,
) -> ReadinessResult:
    checks: list[ReadinessCheck] = []
    db = await get_db()
    try:
        study_row = await (await db.execute(
            "SELECT lifecycle_status, data_classification, active_protocol_version_id FROM studies WHERE study_id = ?",
            (study_id,),
        )).fetchone()
        if not study_row:
            checks.append(ReadinessCheck("study_exists", "failed", "Study not found"))
            return ReadinessResult(allowed=False, checks=checks)
        checks.append(ReadinessCheck("study_exists", "passed", "Study exists"))

        lifecycle = study_row["lifecycle_status"]
        if lifecycle not in ("active", "enrolling"):
            checks.append(ReadinessCheck(
                "study_lifecycle", "failed",
                f"Study lifecycle is '{lifecycle}', must be 'active' or 'enrolling'",
            ))
        else:
            checks.append(ReadinessCheck("study_lifecycle", "passed", f"Study lifecycle: {lifecycle}"))

        protocol_id = study_row["active_protocol_version_id"]
        if not protocol_id:
            checks.append(ReadinessCheck(
                "protocol_frozen", "failed",
                "No active protocol version set",
            ))
        else:
            pv_row = await (await db.execute(
                "SELECT status FROM protocol_versions WHERE protocol_version_id = ?",
                (protocol_id,),
            )).fetchone()
            if not pv_row or pv_row["status"] != "frozen":
                checks.append(ReadinessCheck(
                    "protocol_frozen", "failed",
                    "Active protocol version is not frozen",
                ))
            else:
                checks.append(ReadinessCheck("protocol_frozen", "passed", "Protocol is frozen"))

            er_row = await (await db.execute(
                "SELECT status FROM ethics_reviews "
                "WHERE study_id = ? AND protocol_version_id = ? "
                "AND status IN ('approved', 'exempt') "
                "ORDER BY recorded_at DESC LIMIT 1",
                (study_id, protocol_id),
            )).fetchone()
            if not er_row:
                checks.append(ReadinessCheck(
                    "ethics_approved", "failed",
                    "No approved or exempt ethics review for active protocol",
                ))
            else:
                checks.append(ReadinessCheck(
                    "ethics_approved", "passed",
                    f"Ethics review status: {er_row['status']}",
                ))

        p_row = await (await db.execute(
            "SELECT participant_id, study_id, participant_kind, eligibility_confirmed, withdrawn_at "
            "FROM participants WHERE participant_id = ? AND study_id = ?",
            (participant_id, study_id),
        )).fetchone()
        if not p_row:
            checks.append(ReadinessCheck(
                "participant_belongs", "failed",
                "Participant not found in this study",
            ))
        else:
            checks.append(ReadinessCheck("participant_belongs", "passed", "Participant belongs to study"))

            if not p_row["eligibility_confirmed"]:
                checks.append(ReadinessCheck(
                    "eligibility_confirmed", "failed",
                    "Participant eligibility not confirmed",
                ))
            else:
                checks.append(ReadinessCheck("eligibility_confirmed", "passed", "Eligibility confirmed"))

            if p_row["withdrawn_at"]:
                checks.append(ReadinessCheck("not_withdrawn", "failed", "Participant has withdrawn"))
            else:
                checks.append(ReadinessCheck("not_withdrawn", "passed", "Participant has not withdrawn"))

            if p_row["participant_kind"] == "human_research":
                c_row = await (await db.execute(
                    "SELECT consent_id, withdrawn_at FROM consents "
                    "WHERE participant_id = ? AND study_id = ? "
                    "ORDER BY consented_at DESC LIMIT 1",
                    (participant_id, study_id),
                )).fetchone()
                if not c_row:
                    checks.append(ReadinessCheck(
                        "valid_consent", "failed",
                        "No consent record found",
                    ))
                elif c_row["withdrawn_at"]:
                    checks.append(ReadinessCheck(
                        "valid_consent", "failed",
                        "Most recent consent has been withdrawn",
                    ))
                else:
                    checks.append(ReadinessCheck("valid_consent", "passed", "Valid consent on file"))
            else:
                checks.append(ReadinessCheck(
                    "valid_consent", "skipped",
                    f"Consent check skipped for participant_kind={p_row['participant_kind']}",
                ))

            alloc_row = await (await db.execute(
                "SELECT allocation_id FROM sequence_allocations "
                "WHERE participant_id = ? AND study_id = ?",
                (participant_id, study_id),
            )).fetchone()
            if not alloc_row:
                checks.append(ReadinessCheck(
                    "sequence_allocated", "failed",
                    "No sequence allocation found",
                ))
            else:
                checks.append(ReadinessCheck("sequence_allocated", "passed", "Sequence allocated"))

        allowed = all(c.status == "passed" or c.status == "skipped" for c in checks)
        return ReadinessResult(allowed=allowed, checks=checks)
    finally:
        await db.close()


async def get_system_capabilities() -> dict:
    db = await get_db()
    try:
        from app.core.config import settings
        from app.storage.migration_runner import _current_version, _ensure_version_table

        await _ensure_version_table(db)
        migration_version = await _current_version(db)

        fk_cursor = await db.execute("PRAGMA foreign_keys")
        fk_row = await fk_cursor.fetchone()
        fk_enabled = bool(fk_row and fk_row[0] == 1)

        return {
            "study_mode": settings.study_mode,
            "database_foreign_keys_enabled": fk_enabled,
            "migration_version": migration_version,
            "human_collection_allowed": False,
            "protocol_freeze_enforced": migration_version >= 2,
            "consent_version_enforced": migration_version >= 2,
            "condition_blinding_api_enforced": migration_version >= 2,
            "synthetic_runtime_available": False,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        await db.close()
