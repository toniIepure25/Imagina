"""C3XC dataset decision — applies the SEALED >=2/6 gate. No new measurement.

Qualified iff >=2/6 subjects with imagery PASS AND matched perception PASS AND cue control
acceptable (CLEAN/CONTROLLED). Exactly 1 -> LIMITED. 0 -> FAIL. Contract/cue failure -> BLOCKED.
A PASS authorizes ONLY a future D2-content-scoped (semantic/event video-recall) analysis; never
C3XR/C3XR-CAT/reconstruction/captioning/C4.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from app.research.fmri.c3xb_reliability import subject_reliability_gate

SUBS = ["S1", "S2", "S3", "S4", "S5", "S6"]


def main() -> None:
    out_dir = Path(os.environ.get("C3XC_OUT_DIR", "results/c3xc"))
    seal = json.load(open(os.environ.get("C3XC_SEAL", "reports/c3xc/c3xc_protocol_seal.json")))
    cert = json.load(open(out_dir / "subject_certification.json"))
    subs = os.environ.get("C3XC_SUBJECTS_DEC", ",".join(SUBS)).split(",")

    per = {}
    n_imagery_pass = n_both_pass = 0
    hvc_gt_v1_pass = []  # cue control assessed over the RELIABLE (imagery-PASS) subjects
    for s in subs:
        r = json.load(open(out_dir / f"c3xc_reliability_{s}.json"))
        ri, rp = r["R_I_VC"], r["R_P_VC"]
        gi = subject_reliability_gate(ri)
        # point-only R_P (sealed fallback): reliable if point R_P >= 0.2 (far above noise;
        # anchored by the full-inference anchor subject). Full-inference subjects use the gate.
        if rp.get("point_only"):
            gp = "SUBJECT_RELIABILITY_PASS" if rp["reliability"] >= 0.2 else "SUBJECT_RELIABILITY_MARGINAL"
        else:
            gp = subject_reliability_gate(rp)
        contract_ok = cert["subjects"][s]["status"] == "CERTIFIED"
        both = (gi == "SUBJECT_RELIABILITY_PASS" and gp == "SUBJECT_RELIABILITY_PASS" and contract_ok)
        n_imagery_pass += int(gi == "SUBJECT_RELIABILITY_PASS")
        n_both_pass += int(both)
        if gi == "SUBJECT_RELIABILITY_PASS":
            hvc_gt_v1_pass.append(bool(r["cue_roi_profile_control"]["hvc_gt_v1"]))
        per[s] = {"R_I_VC": ri["reliability"], "R_I_p": ri["perm_p_one_sided"],
                  "R_I_ci95": ri["bootstrap_ci95"], "R_I_gate": gi,
                  "R_P_VC": rp["reliability"], "R_P_p": rp.get("perm_p_one_sided"),
                  "R_P_ci95": rp.get("bootstrap_ci95"), "R_P_point_only": bool(rp.get("point_only")),
                  "R_P_gate": gp,
                  "attenuation_VC": r.get("attenuation_VC"), "contract": cert["subjects"][s]["status"],
                  "hvc_gt_v1": bool(r["cue_roi_profile_control"]["hvc_gt_v1"]),
                  "imagery_and_perception_pass": both}

    # cue verdict: imagery shows no stimulus (structural, seal) -> target-presentation leakage
    # absent; the cue control asks whether the RELIABLE (imagery-PASS) signal is HVC-dominant
    # (recall content) rather than V1-dominant (early-visual cue artifact). Assessed over the
    # PASS subjects; a near-noise MARGINAL subject's ROI profile is uninformative about
    # contamination of the reliable signal.
    hvc_gt_v1_all_pass = bool(hvc_gt_v1_pass) and all(hvc_gt_v1_pass)
    cue_state = "CUE_CONTROLLED" if hvc_gt_v1_all_pass else "CUE_AMBIGUOUS"
    cue_ok = cue_state in ("CUE_CLEAN", "CUE_CONTROLLED")

    all_contract = all(cert["subjects"][s]["status"] == "CERTIFIED" for s in subs)
    if not all_contract:
        decision, qualified = "C3XC_BLOCKED_D2_DATA_CONTRACT", False
    elif n_both_pass >= 2 and cue_ok:
        decision, qualified = "C3XC_D2_SEMANTIC_IMAGERY_QUALIFIED", True
    elif n_both_pass == 1 and cue_ok:
        decision, qualified = "C3XC_D2_SEMANTIC_IMAGERY_LIMITED", False
    else:
        decision, qualified = "C3XC_D2_SEMANTIC_IMAGERY_FAIL", False

    obj = {"artifact": "C3XC_DECISION", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "seal_self_hash": seal["self_hash"],
           "dataset": "Mind Captioning ds005191 v1.0.2 / figshare 25808179 v2",
           "content_scope": "internally-generated SEMANTIC/EVENT video-recall (NOT static/category/exact)",
           "per_subject": per, "n_subjects": len(subs),
           "n_imagery_pass": n_imagery_pass, "n_imagery_and_perception_pass": n_both_pass,
           "cue_state": cue_state, "cue_control_acceptable": cue_ok,
           "hvc_gt_v1_over_pass_subjects": hvc_gt_v1_all_pass,
           "decision": decision, "dataset_qualified": qualified,
           "authorizes": ("a FUTURE separately-prespecified D2-content-scoped (semantic/event video-"
                          "recall) reliability-bounded analysis ONLY" if qualified else "nothing"),
           "does_NOT_authorize": "C3XR; C3XR-CAT; reconstruction; captioning/semantic decoding; C4",
           "no_geometry_computed": True, "no_reconstruction": True, "not_c4": True}
    obj["self_hash"] = hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(obj, open(out_dir / "C3XC_DECISION.json", "w"), indent=2)
    print(f"n_imagery_pass={n_imagery_pass}/{len(subs)} both_pass={n_both_pass}/{len(subs)} cue={cue_state}")
    print(f"DECISION: {decision} | qualified={qualified}")


if __name__ == "__main__":
    main()
