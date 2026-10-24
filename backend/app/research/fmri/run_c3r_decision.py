"""C3R Phase 4 — reliability-qualified cohort decision.

Aggregates the sealed per-subject reliability screens (no new measurement) and
issues the C3R gate decision under the sealed rule. Rebuilds the combined
summary. Phase 5 (perception foundation) is triggered ONLY for RELIABILITY_PASS
subjects; if none qualify, no perception data is acquired and no geometry is run.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

SUBJECTS = ["subj02", "subj05", "subj07"]


def main() -> None:
    out_dir = Path(os.environ.get("C3R_OUT_DIR", "results/c3r"))
    seal = json.load(open(os.environ.get("C3R_SEAL", "reports/c3r/c3r_protocol_seal.json")))

    per = {}
    for s in SUBJECTS:
        d = json.load(open(out_dir / f"c3r_reliability_{s}.json"))
        ri, rp = d["R_I_nsdgeneral"], d["R_P_nsdgeneral"]
        per[s] = {
            "R_I": ri["reliability"], "R_I_ci95": ri["bootstrap_ci95"],
            "R_I_perm_p": ri["perm_p_one_sided"], "R_I_split_seed_min": ri["split_seed_min"],
            "R_P": rp["reliability"], "R_P_ci95": rp["bootstrap_ci95"],
            "R_P_perm_p": rp["perm_p_one_sided"],
            "imagery_gate": d["imagery_gate"], "vision_gate": d["vision_gate"],
            "quality_class": d["quality_class"],
            "practical_effect_flags": d["practical_effect_flags_imagery"],
        }

    qualified = [s for s in SUBJECTS if per[s]["imagery_gate"] == "RELIABILITY_PASS"]
    marginal = [s for s in SUBJECTS if per[s]["imagery_gate"] == "RELIABILITY_MARGINAL"]
    noise_floor = [s for s in SUBJECTS if per[s]["imagery_gate"] == "RELIABILITY_NOISE_FLOOR"]
    blockers = [s for s in SUBJECTS if per[s]["quality_class"] == "VISION_UNRELIABLE_SESSION_QUALITY_BLOCKER"]
    imagery_specific_attenuation = [s for s in SUBJECTS
                                    if per[s]["quality_class"] == "VISION_RELIABLE_IMAGERY_NOISE_FLOOR"]

    decision = "C3R_RELIABLE_IMAGERY_FOUND" if qualified else "C3R_NO_RELIABLE_IMAGERY_IN_REMAINING_COHORT"

    obj = {
        "artifact": "C3R_DECISION", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "seal_self_hash": seal["self_hash"],
        "subj01_reference_descriptive": 0.011,
        "per_subject": per,
        "qualified_subjects": qualified,
        "marginal_subjects": marginal,
        "noise_floor_subjects": noise_floor,
        "session_quality_blockers": blockers,
        "imagery_specific_attenuation_subjects": imagery_specific_attenuation,
        "decision": decision,
        "phase5_perception_foundation_triggered": bool(qualified),
        "subjects_eligible_for_future_c3g_replication": qualified,
        "interpretation": (
            "No participant in the remaining NSD-Imagery cohort (subj02/05/07) shows demonstrably "
            "reliable stimulus-specific imagery signal above the noise floor in nsdgeneral under the "
            "sealed criterion, so a state-geometry replication is NOT scientifically identifiable in "
            "this cohort. This is a MEASUREMENT-BOUND conclusion, NOT evidence that perception and "
            "imagery share a representation. subj02 (reliable vision, imagery at noise floor) "
            "replicates subj01's imagery-specific attenuation; subj05/subj07 additionally have "
            "unreliable same-session VISION (session-quality blockers), so their low imagery cannot "
            "even be attributed to cognitive attenuation."
            if not qualified else
            "At least one participant shows prospectively reliable imagery; see qualified_subjects. "
            "Geometry is NOT computed in C3R."),
        "scope": "conditional_qualified_cohort_only; qualification by prospectively measured imagery "
                 "reliability; NOT an unbiased population prevalence estimate",
        "no_geometry_computed": True,
    }
    obj["self_hash"] = hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(obj, open(out_dir / "c3r_decision.json", "w"), indent=2)

    summ = {"artifact": "C3R_RELIABILITY_SUMMARY", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "subj01_reference_descriptive": 0.011, "subjects": per, "decision": decision}
    summ["self_hash"] = hashlib.sha256(json.dumps(summ, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(summ, open(out_dir / "c3r_reliability_summary.json", "w"), indent=2)

    print(f"DECISION: {decision}")
    print(f"qualified={qualified} marginal={marginal} noise_floor={noise_floor}")
    print(f"session_quality_blockers={blockers}")
    print(f"imagery_specific_attenuation={imagery_specific_attenuation}")
    print(f"phase5_triggered={obj['phase5_perception_foundation_triggered']}")


if __name__ == "__main__":
    main()
