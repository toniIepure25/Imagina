"""ANIMUS-P2-XR cross-dataset replication decision (frozen before outcomes).

Inherits the P2 subject gate and dataset gate UNCHANGED (app.core.animus.p2.gate). Each replication dataset
is decided INDEPENDENTLY with the historical rule required_passes = max(2, ceil(N_valid/3)); the two dataset
decisions are then combined by the prospectively frozen rule:

    BOTH datasets VALIDATED            -> ANIMUS_P2XR_INDEPENDENT_REPLICATION_PASS
    exactly ONE dataset VALIDATED      -> ANIMUS_P2XR_INDEPENDENT_REPLICATION_LIMITED
    NEITHER dataset VALIDATED          -> ANIMUS_P2XR_INDEPENDENT_REPLICATION_FAIL

No pooled/meta-analytic rescue can convert two non-VALIDATED datasets into a PASS. A genuine technical or
provenance condition that prevents valid execution is reported as ANIMUS_P2XR_BLOCKED_<reason> upstream.
"""
from __future__ import annotations

from app.core.animus.p2.gate import dataset_gate, required_passes, subject_pass

PASS = "ANIMUS_P2XR_INDEPENDENT_REPLICATION_PASS"
LIMITED = "ANIMUS_P2XR_INDEPENDENT_REPLICATION_LIMITED"
FAIL = "ANIMUS_P2XR_INDEPENDENT_REPLICATION_FAIL"


def dataset_status(subject_results: list[dict], n_eligible: int) -> dict:
    """Apply the inherited P2 subject + dataset gate to one dataset's per-subject results.

    n_eligible is the frozen (pre-outcome) participant denominator. n_valid counts subjects that met the
    technical contract (data_contract + atlas_qc); n_pass counts subjects that passed the full subject gate.
    Returns the raw P2 decision string plus a simplified status in {VALIDATED, LIMITED, FAIL, BLOCKED}.
    """
    n_valid = sum(1 for s in subject_results if s.get("data_contract_pass") and s.get("atlas_qc_pass"))
    n_pass = sum(1 for s in subject_results if subject_pass(s))
    raw = dataset_gate(n_pass, n_valid, n_eligible)
    if raw.endswith("VALIDATED"):
        status = "VALIDATED"
    elif raw.endswith("LIMITED"):
        status = "LIMITED"
    elif raw.endswith("FAIL"):
        status = "FAIL"
    else:
        status = "BLOCKED"
    return {"n_eligible": n_eligible, "n_valid": n_valid, "n_pass": n_pass,
            "required_passes": required_passes(n_eligible), "raw_decision": raw, "status": status}


def cross_dataset_decision(dataset_statuses: dict[str, dict]) -> str:
    """Combine per-dataset statuses (values from dataset_status) by the frozen cross-dataset rule."""
    validated = sum(1 for d in dataset_statuses.values() if d.get("status") == "VALIDATED")
    total = len(dataset_statuses)
    if total == 0:
        return FAIL
    if validated == total:
        return PASS
    if validated >= 1:
        return LIMITED
    return FAIL
