"""Research governance services — readiness evaluation and capability reporting.

The environment variable IMAGINA_STUDY_MODE controls the application's
operating mode but is NOT ethics approval. Human data collection requires
database-backed evidence of protocol freeze, ethics review, and valid consent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.storage.database import get_db


class AllocationIntegrityError(Exception):
    pass


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
                    "SELECT consent_id, protocol_version_id, consent_document_version_id, withdrawn_at "
                    "FROM consents "
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
                elif not c_row["protocol_version_id"]:
                    checks.append(ReadinessCheck(
                        "valid_consent", "failed",
                        "Consent record has null protocol_version_id",
                    ))
                elif not c_row["consent_document_version_id"]:
                    checks.append(ReadinessCheck(
                        "valid_consent", "failed",
                        "Consent record has null consent_document_version_id",
                    ))
                elif protocol_id and c_row["protocol_version_id"] != protocol_id:
                    checks.append(ReadinessCheck(
                        "valid_consent", "failed",
                        f"Consent references protocol '{c_row['protocol_version_id']}' "
                        f"but active protocol is '{protocol_id}'",
                    ))
                else:
                    cdv_row = await (await db.execute(
                        "SELECT status FROM consent_document_versions "
                        "WHERE consent_document_version_id = ? AND study_id = ?",
                        (c_row["consent_document_version_id"], study_id),
                    )).fetchone()
                    if not cdv_row:
                        checks.append(ReadinessCheck(
                            "valid_consent", "failed",
                            "Consent references unknown consent document version",
                        ))
                    elif cdv_row["status"] != "active":
                        checks.append(ReadinessCheck(
                            "valid_consent", "failed",
                            f"Consent document version status is '{cdv_row['status']}', not 'active'",
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


async def evaluate_synthetic_readiness(
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

        classification = study_row["data_classification"]
        if classification != "synthetic":
            checks.append(ReadinessCheck(
                "data_classification", "failed",
                f"Study classification is '{classification}', must be 'synthetic'",
            ))
        else:
            checks.append(ReadinessCheck("data_classification", "passed", "Study classified as synthetic"))

        p_row = await (await db.execute(
            "SELECT participant_kind FROM participants WHERE participant_id = ? AND study_id = ?",
            (participant_id, study_id),
        )).fetchone()
        if not p_row:
            checks.append(ReadinessCheck("participant_belongs", "failed", "Participant not found in study"))
        elif p_row["participant_kind"] not in ("synthetic", "synthetic_agent"):
            checks.append(ReadinessCheck(
                "participant_kind", "failed",
                f"Participant kind is '{p_row['participant_kind']}', must be synthetic",
            ))
        else:
            checks.append(ReadinessCheck("participant_kind", "passed", "Synthetic participant confirmed"))

        protocol_id = study_row["active_protocol_version_id"]
        if not protocol_id:
            checks.append(ReadinessCheck("protocol_frozen", "failed", "No active protocol version set"))
        else:
            pv_row = await (await db.execute(
                "SELECT status FROM protocol_versions WHERE protocol_version_id = ?",
                (protocol_id,),
            )).fetchone()
            if not pv_row or pv_row["status"] != "frozen":
                checks.append(ReadinessCheck("protocol_frozen", "failed", "Active protocol is not frozen"))
            else:
                checks.append(ReadinessCheck("protocol_frozen", "passed", "Protocol frozen"))

        alloc_row = await (await db.execute(
            "SELECT allocation_id FROM sequence_allocations WHERE participant_id = ? AND study_id = ?",
            (participant_id, study_id),
        )).fetchone()
        if not alloc_row:
            checks.append(ReadinessCheck("sequence_allocated", "failed", "No sequence allocation found"))
        else:
            checks.append(ReadinessCheck("sequence_allocated", "passed", "Sequence allocated"))

        allowed = all(c.status in ("passed", "skipped") for c in checks)
        return ReadinessResult(allowed=allowed, checks=checks)
    finally:
        await db.close()


@dataclass
class CapabilityDetail:
    schema_available: bool
    service_available: bool
    runtime_gate_active: bool
    status: str
    detail: str


def _cap(schema: bool, service: bool, runtime: bool, detail: str) -> dict:
    if runtime:
        status = "verified_runtime"
    elif service:
        status = "implemented"
    elif schema:
        status = "partial"
    else:
        status = "unavailable"
    return {
        "schema_available": schema,
        "service_available": service,
        "runtime_gate_active": runtime,
        "status": status,
        "detail": detail,
    }


async def get_system_capabilities() -> dict:
    db = await get_db()
    try:
        from app.core.config import settings
        from app.storage.migration_runner import current_version

        migration_version = await current_version(db)

        fk_cursor = await db.execute("PRAGMA foreign_keys")
        fk_row = await fk_cursor.fetchone()
        fk_enabled = bool(fk_row and fk_row[0] == 1)

        has_governance_schema = migration_version >= 2
        has_runtime_schema = migration_version >= 3

        return {
            "study_mode": settings.study_mode,
            "database_foreign_keys_enabled": fk_enabled,
            "migration_version": migration_version,
            "human_collection_allowed": False,
            "synthetic_runtime_available": has_runtime_schema,
            "protocol_freeze": _cap(
                schema=has_governance_schema,
                service=has_governance_schema,
                runtime=False,
                detail="Protocol freeze schema and service exist; not yet checked by session runtime"
                if has_governance_schema
                else "Governance schema not applied",
            ),
            "consent_tracking": _cap(
                schema=has_governance_schema,
                service=has_governance_schema,
                runtime=False,
                detail="Consent version tracking with protocol/document validation"
                if has_governance_schema
                else "Governance schema not applied",
            ),
            "condition_blinding": _cap(
                schema=has_governance_schema,
                service=has_governance_schema,
                runtime=has_governance_schema,
                detail="Public API hides assignment data"
                if has_governance_schema
                else "API separation not available",
            ),
            "sequence_allocation": _cap(
                schema=has_governance_schema,
                service=has_governance_schema,
                runtime=False,
                detail="Williams balanced allocator with transactional persistence"
                if has_governance_schema
                else "Allocation schema not available",
            ),
            "synthetic_runtime": _cap(
                schema=has_runtime_schema,
                service=has_runtime_schema,
                runtime=has_runtime_schema,
                detail="Persistent synthetic experiment runtime available"
                if has_runtime_schema
                else "Runtime schema not yet applied (Merge Gate B)",
            ),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        await db.close()
