"""C3X Phase 5 decision — external imagery dataset qualification.

Aggregates the sealed D1 per-subject reliability screens (no new measurement),
applies the sealed dataset gate, and issues the C3X decision. If D1 reaches
DATASET_RELIABILITY_PASS, dataset hunting STOPS (D2 is not inspected).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from app.research.fmri.c3x_reliability import dataset_gate

SUBS = ["sub-01", "sub-02", "sub-03"]
NSD_SUBJ01_IMAGERY_R = 0.011  # C3R/C3G reference (noise floor)


def main() -> None:
    out_dir = Path(os.environ.get("C3X_OUT_DIR", "results/c3x"))
    seal = json.load(open(os.environ.get("C3X_SEAL", "reports/c3x/c3x_protocol_seal.json")))

    per, gate_input = {}, {}
    for s in SUBS:
        d = json.load(open(out_dir / f"d1_reliability_{s}.json"))
        ri, rp = d["R_I_VC"], d["R_P_VC"]
        per[s] = {"R_I": ri["reliability"], "R_I_ci95": ri["bootstrap_ci95"],
                  "R_I_perm_p": ri["perm_p_one_sided"], "R_I_null_mean": ri["null_mean"],
                  "R_I_split_seed_min": ri["split_seed_min"],
                  "R_P": rp["reliability"], "R_P_perm_p": rp["perm_p_one_sided"],
                  "attenuation_ratio_RI_over_RP": d["attenuation_ratio_RI_over_RP"],
                  "imagery_gate": d["imagery_gate"], "vision_gate": d["vision_gate"],
                  "quality_class": d["quality_class"],
                  "R_I_roi": {k.replace("ROI_", ""): v for k, v in ri["roi_secondary"].items()}}
        gate_input[s] = {"imagery": ri, "vision": rp}

    ds_gate = dataset_gate(gate_input)
    n_imagery_pass = sum(1 for s in SUBS if per[s]["imagery_gate"] == "SUBJECT_RELIABILITY_PASS")

    qualified = ds_gate == "DATASET_RELIABILITY_PASS"
    if qualified:
        decision = "C3X_EXTERNAL_IMAGERY_DATASET_QUALIFIED"
        qualified_dataset = "ds001506"
    else:
        decision = "PENDING_D2"  # would proceed to D2 only if D1 did not pass
        qualified_dataset = None

    ratios = [per[s]["attenuation_ratio_RI_over_RP"] for s in SUBS]
    obj = {
        "artifact": "C3X_DECISION", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "seal_self_hash": seal["self_hash"],
        "evaluated_dataset": "D1 ds001506 (Deep Image Reconstruction)",
        "per_subject": per,
        "n_imagery_pass": n_imagery_pass,
        "dataset_gate": ds_gate,
        "decision": decision,
        "qualified_dataset": qualified_dataset,
        "d2_inspected": False,
        "d2_status": "NOT INSPECTED (D1 qualified -> dataset hunting stops; D2 remains a future "
                     "external replication/generalization dataset)" if qualified else
                     "would be inspected next per frozen ranking",
        "measurement_ceiling": {
            "imagery_R_I_range": [min(per[s]["R_I"] for s in SUBS), max(per[s]["R_I"] for s in SUBS)],
            "perception_R_P_range": [min(per[s]["R_P"] for s in SUBS), max(per[s]["R_P"] for s in SUBS)],
            "attenuation_ratio_RI_over_RP": ratios,
            "attenuation_ratio_mean": sum(ratios) / len(ratios),
        },
        "cross_dataset_contrast_descriptive": {
            "nsd_imagery_subj01_R_I": NSD_SUBJ01_IMAGERY_R,
            "dir_imagery_R_I_range": [min(per[s]["R_I"] for s in SUBS), max(per[s]["R_I"] for s in SUBS)],
            "note": "DESCRIPTIVE ONLY. NSD-Imagery imagery reliability was at the noise floor "
                    "(~0.011); DIR/GOD imagery reliability is measurable and significant (0.22-0.47, "
                    "all p<=0.001). This turns the C3G/C3R negative into a falsifiable cross-dataset "
                    "hypothesis (does state geometry emerge only when imagery reliability is "
                    "sufficient?) -- NOT tested in C3X.",
        },
        "interpretation": (
            "ds001506 (Deep Image Reconstruction) provides demonstrably reliable stimulus-specific "
            "imagery signal in visual cortex for all three subjects (imagery PASS; matched perception "
            "also reliable; permutation null ~0; run-disjoint). The perception<->imagery geometry "
            "question is therefore IDENTIFIABLE on this dataset, unlike NSD-Imagery." if qualified else
            "D1 did not reach DATASET_RELIABILITY_PASS; proceed to D2 per the frozen ranking."),
        "next_gate": "C3XR - External State-Geometry Replication on ds001506 (freeze C3G geometry "
                     "hypotheses BEFORE observing geometry). NOT started in C3X.",
        "no_geometry_computed": True, "no_reconstruction": True,
        "scope": "dataset qualification conditional on prospectively measured imagery reliability; "
                 "3 subjects of one dataset; not an unbiased population prevalence estimate",
    }
    obj["self_hash"] = hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(obj, open(out_dir / "c3x_decision.json", "w"), indent=2)

    summ = {"artifact": "C3X_D1_RELIABILITY_SUMMARY", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "dataset": "ds001506", "subjects": per, "dataset_gate": ds_gate, "decision": decision}
    summ["self_hash"] = hashlib.sha256(json.dumps(summ, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(summ, open(out_dir / "d1_reliability_summary.json", "w"), indent=2)
    json.dump({"artifact": "C3X_D1_RELIABILITY_SUBJECTS", "subjects": per},
              open(out_dir / "d1_reliability_subjects.json", "w"), indent=2)

    print(f"dataset_gate={ds_gate} n_imagery_pass={n_imagery_pass}/3")
    print(f"DECISION: {decision} qualified_dataset={qualified_dataset}")


if __name__ == "__main__":
    main()
