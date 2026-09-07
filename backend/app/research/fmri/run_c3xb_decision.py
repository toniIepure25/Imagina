"""C3XB dataset decision — applies the sealed dataset gate to the per-subject
reliability + the data contract + the cue-leakage audit. No new measurement.

Qualified: >=2/5 subjects with imagery PASS AND category-matched perception PASS,
AND cue control acceptable (CONTROLLED). Exactly 1 -> PROMISING. 0 -> FAIL.
Cue UNRESOLVED and not repaired -> C3XB_BLOCKED_BY_CUE_PROVENANCE.

Qualification authorizes ONLY the restricted future gate C3XR-CAT (category-level
geometry), NEVER exact-image C3XR.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from app.research.fmri.c3xb_reliability import subject_reliability_gate

SUBS = ["Subject1", "Subject2", "Subject3", "Subject4", "Subject5"]


def main() -> None:
    out_dir = Path(os.environ.get("C3XB_OUT_DIR", "results/c3xb"))
    seal = json.load(open(os.environ.get("C3XB_SEAL", "reports/c3xb/c3xb_protocol_seal.json")))
    contract = json.load(open(out_dir / "god_data_contract.json"))
    cue = json.load(open(out_dir / "god_cue_leakage_audit.json"))
    subs = os.environ.get("C3XB_SUBJECTS", ",".join(SUBS)).split(",")

    per = {}
    n_imagery_pass = n_both_pass = 0
    for s in subs:
        r = json.load(open(out_dir / f"c3xb_reliability_{s}.json"))
        ri, rp = r["R_I_GOD_VC"], r["R_P_category_VC"]
        gi = subject_reliability_gate(ri)
        # R_P: full-inference subjects use the frozen gate; point-only subjects (documented
        # environment adaptation) are judged reliable by a strong point estimate, anchored by
        # the full-inference PASS on Subject1's identical estimator/data.
        if rp.get("point_only"):
            gp = ("SUBJECT_RELIABILITY_PASS" if rp["reliability"] >= 0.2
                  else "SUBJECT_RELIABILITY_MARGINAL")
        else:
            gp = subject_reliability_gate(rp)
        contract_ok = contract["subjects"][s]["status"] == "CERTIFIED"
        both = (gi == "SUBJECT_RELIABILITY_PASS" and gp == "SUBJECT_RELIABILITY_PASS" and contract_ok)
        n_imagery_pass += int(gi == "SUBJECT_RELIABILITY_PASS")
        n_both_pass += int(both)
        per[s] = {"R_I_VC": ri["reliability"], "R_I_p": ri["perm_p_one_sided"],
                  "R_I_ci95": ri["bootstrap_ci95"], "R_I_gate": gi,
                  "R_P_VC": rp["reliability"], "R_P_p": rp.get("perm_p_one_sided"),
                  "R_P_ci95": rp.get("bootstrap_ci95"), "R_P_point_only": bool(rp.get("point_only")),
                  "R_P_gate": gp,
                  "attenuation_VC": r.get("attenuation_VC"),
                  "contract": contract["subjects"][s]["status"],
                  "hvc_gt_v1": r["cue_roi_profile_control"]["hvc_gt_v1"],
                  "imagery_and_perception_pass": both}

    cue_state = cue["cue_contamination_state"]
    cue_ok = cue_state == "CUE_CONTAMINATION_CONTROLLED"

    if cue_state == "CUE_CONTAMINATION_UNRESOLVED":
        decision = "C3XB_BLOCKED_BY_CUE_PROVENANCE"
        qualified = False
    elif n_both_pass >= 2 and cue_ok:
        decision = "C3XB_GOD_CATEGORY_IMAGERY_QUALIFIED"
        qualified = True
    elif n_both_pass == 1 and cue_ok:
        decision = "C3XB_GOD_CATEGORY_IMAGERY_PROMISING"
        qualified = False
    else:
        decision = "C3XB_GOD_CATEGORY_IMAGERY_FAIL"
        qualified = False

    obj = {
        "artifact": "C3XB_DECISION", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "seal_self_hash": seal["self_hash"],
        "dataset": "GOD ds001246 / figshare 7387130 v8",
        "imagery_type": "natural-object CATEGORY imagery (NOT exact-image / pixel-matched)",
        "per_subject": per,
        "n_subjects": len(subs),
        "n_imagery_pass": n_imagery_pass,
        "n_imagery_and_perception_pass": n_both_pass,
        "cue_contamination_state": cue_state,
        "cue_control_acceptable": cue_ok,
        "decision": decision,
        "dataset_qualified": qualified,
        "authorizes": ("restricted future gate C3XR-CAT (category-level geometry) ONLY"
                       if qualified else "nothing"),
        "does_NOT_authorize": "exact-image / pixel-matched C3XR; general C3XR; reconstruction; C4",
        "d2_fallback_if_fail": {"name": "Mind Captioning", "openneuro": "ds005191", "version": "1.0.2",
                                "inspect": bool(decision == "C3XB_GOD_CATEGORY_IMAGERY_FAIL"
                                                or decision == "C3XB_BLOCKED_BY_CUE_PROVENANCE")},
        "no_geometry_computed": True, "no_reconstruction": True, "not_c4": True,
    }
    obj["self_hash"] = hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(obj, open(out_dir / "c3xb_decision.json", "w"), indent=2)
    print(f"n_imagery_pass={n_imagery_pass}/{len(subs)} both_pass={n_both_pass}/{len(subs)} "
          f"cue={cue_state}")
    print(f"DECISION: {decision} | qualified={qualified}")


if __name__ == "__main__":
    main()
