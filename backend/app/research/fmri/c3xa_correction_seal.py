"""C3XA correction-rules seal — committed BEFORE any corrected reliability outcome
is inspected. Freezes the fixation-exclusion and family-stratification rules, the
matched-perception conditions, the requalification rule (with PRIMARY future
geometry family = natural_10 defined BEFORE corrected natural-only outcomes), and
reuses the FROZEN C3X run-disjoint estimator UNCHANGED (only the valid-sample mask
is corrected).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def _sha_bytes(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _code_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"


def main() -> None:
    reports = Path(os.environ.get("C3XA_REPORTS_DIR", "reports/c3xa"))
    reports.mkdir(parents=True, exist_ok=True)
    fmri = Path(os.environ.get("C3XA_FMRI_DIR", "backend/app/research/fmri"))
    res = Path("results/c3xa")

    seal = {
        "artifact": "C3XA_CORRECTION_SEAL",
        "gate": "C3XA",
        "title": "DIR Target-Contract Correction and Dataset Requalification",
        "is_not_c4": True, "no_geometry": True, "no_reconstruction": True,
        "c3x_final_sha": "d1a482ed89a10abf72376838d43332445857349f",
        "branch": "research/c3x-dir-target-contract-c3xa",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "SEALED_BEFORE_CORRECTED_RELIABILITY_INSPECTION",
        "provisional_c3x_status": "C3X_QUALIFICATION_PROVISIONAL_PENDING_TARGET_CONTRACT_CORRECTION",

        "estimator_unchanged": {
            "note": "the frozen C3X run-disjoint estimator, permutation null, non-straddling "
                    "bootstrap, split seeds, subject gate, and dataset gate are REUSED UNCHANGED; "
                    "only the valid-sample mask is corrected (fixation excluded, family-stratified).",
            "c3x_reliability_sha256": _sha256_file(fmri / "c3x_reliability.py"),
        },
        "target_contract": {
            "source": "results/c3xa/c3xa_target_contract.json",
            "hash": _sha_bytes(res / "c3xa_target_contract.json"),
            "natural_labels": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "artificial_labels": [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25],
            "fixation_label": 26,
            "expected_target_samples": 500, "expected_fixation_samples": 20,
        },
        "correction_rules": {
            "fixation_exclusion": "Label 26 (fixation) is excluded from ALL primary reliability; "
                                  "500 target samples/subject (was 520).",
            "family_stratification": "report R_I_natural (10 natural labels) and R_I_artificial "
                                     "(15 artificial labels) SEPARATELY; a naive combined 25-target "
                                     "reliability can be inflated by reproducible natural-vs-"
                                     "artificial SEPARATION and is reported only as a confounded "
                                     "comparison, never as the qualification statistic.",
            "matched_perception": {"natural": "perceptionNaturalImageTest",
                                   "artificial": "perceptionArtificialImage",
                                   "level": "family-condition matched control (bdpy exposes no "
                                            "per-target exact image filename)"},
        },
        "fixation_sensitivity_diagnostic": "report R_I including fixation vs excluding fixation and "
                                           "fixation-only pattern repeatability; explanatory only, "
                                           "cannot alter the corrected gate.",
        "primary_future_geometry_family": "natural_10 (matches C3G Set-B natural images) -- defined "
                                          "BEFORE corrected natural-only outcomes are inspected.",
        "secondary_family": "artificial_15 (strong secondary replication family).",
        "requalification_rule": {
            "D1_remains_qualified_for_C3XR_iff": ">=2 of 3 subjects show R_I_natural > 0 AND "
                "permutation p < 0.05 AND bootstrap CI lower > 0 AND split robustness > 0, AND "
                "R_P_natural reliable (matched natural perception)",
            "principle": "same conservative C3X dataset principle (>=2 subjects reliable imagery + "
                         "reliable matched perception), applied to the correct NATURAL matched "
                         "family; rule fixed BEFORE corrected outcomes.",
        },
        "possible_outcomes": {
            "C3X_EXTERNAL_IMAGERY_DATASET_QUALIFIED_CONFIRMED": "natural family survives -> C3XR "
                "authorized (primary=natural_10, secondary=artificial_15)",
            "C3X_RESTRICTED_ARTIFICIAL_IMAGERY_DATASET_QUALIFIED": "only artificial qualifies -> no "
                "broad natural-image geometry claim",
            "C3X_QUALIFICATION_REVOKED_BY_TARGET_CONTRACT_CORRECTION": "reliability collapses after "
                "fixation/family correction -> do not start C3XR; proceed to D2 as ranked",
            "C3XA_BLOCKED_TARGET_IDENTITY_PROVENANCE": "mapping unresolved",
        },
        "seeds": {"seed_base": 20260826, "n_perm": 1000, "n_boot": 1000},
        "no_geometry_callable_from_c3xa": True,
        "code_sha": _code_sha(),
    }
    seal["self_hash"] = hashlib.sha256(json.dumps(seal, sort_keys=True, default=str).encode()).hexdigest()
    out = reports / "c3xa_correction_seal.json"
    json.dump(seal, open(out, "w"), indent=2)
    print(f"Wrote {out}")
    print(json.dumps({"status": seal["status"], "self_hash": seal["self_hash"][:16],
                      "primary_family": seal["primary_future_geometry_family"]}, indent=2))


if __name__ == "__main__":
    main()
