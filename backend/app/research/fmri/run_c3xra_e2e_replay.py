"""C3XRA synthetic end-to-end replay (design-only; NO human data).

Runs the frozen primary conjunction on every synthetic scenario and checks that each yields the CORRECT
decision: signal scenarios PASS, null/leakage/fingerprint/shuffle scenarios do NOT produce a valid primary
joint PASS. Also checks the contamination channel carries no imagery, the estimator unit is
run_pair_disjoint, and a cohort gate replay. Writes results/c3xra/synthetic_e2e_replay.json (self-hashed).
Reduced resamples are used for replay speed; the sealed confirmatory numbers live in
c3xra_analysis.SEALED_INFERENCE and the C3XRP precision seal holds the Type-I RATE.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

from app.research.fmri import c3xra_analysis as A

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
_OUT = os.path.join(_ROOT, "results", "c3xra", "synthetic_e2e_replay.json")

N_PERM = 120
N_BOOT = 120
VOX = 50
N_UNITS = 7
N_ID = 24

# expected: should a valid PRIMARY joint PASS be allowed?
EXPECT_JOINT_PASS = {
    "strict_null": False,
    "imagery_only": True,
    "imagery_plus_contam": True,
    "perception_stable_img_null": False,
    "cue_only": False,
    "postvideo_only": False,
    "delta_zero": False,
    "delta_positive": True,
    "motion": True,
    "session_effects": True,
    "adv_perfect_cue_leakage": False,
    "adv_perfect_postvideo_leakage": False,
    "adv_session_fingerprint_no_identity": False,
    "adv_identity_shuffled_within": False,
    "adv_identity_shuffled_across": False,
}
ADVERSARIAL = [k for k in EXPECT_JOINT_PASS if k.startswith("adv_")]


def _sh(o):
    o = dict(o)
    o.pop("self_hash", None)
    o["self_hash"] = hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()
    return o


def main():
    rows = []
    ok = True
    max_pred_img = 0.0
    for name, expect in EXPECT_JOINT_PASS.items():
        tup = A.simulate_scenario(name, n_units=N_UNITS, n_id=N_ID, vox=VOX)
        meta = tup[-1]
        res = A.analyze_subject(*tup[:7], n_perm=N_PERM, n_boot=N_BOOT)
        agree = (res["joint_pass"] == expect)
        ok = ok and agree
        max_pred_img = max(max_pred_img, meta["pred_has_zero_imagery"])
        rows.append({"scenario": name, "expected_joint_pass": expect,
                     "observed_joint_pass": res["joint_pass"], "agree": agree,
                     "imagery_pass": res["imagery_pass"], "perception_pass": res["perception_pass"],
                     "delta_pass": res["delta_pass"], "R_I": round(res["R_I"], 3),
                     "R_I_perm_p": round(res["R_I_perm_p"], 4), "R_P": round(res["R_P"], 3),
                     "delta_point": round(res["delta_point"], 4),
                     "delta_ci_lo": round(res["delta_ci_lo"], 4)})
        print(f"{name:38s} exp={int(expect)} obs={int(res['joint_pass'])} agree={agree} "
              f"R_I={res['R_I']:.2f} dp={res['delta_point']:.3f} dlo={res['delta_ci_lo']:.3f}",
              flush=True)

    adv_ok = all(r["observed_joint_pass"] is False for r in rows if r["scenario"] in ADVERSARIAL)
    # cohort gate replay: 3 pass of 9 eligible/valid -> QUALIFIED (required_passes=3)
    cg_qual = A.cohort_decision(3, 9, 9)
    cg_incomplete = A.cohort_decision(3, 8, 9)
    cg_limited = A.cohort_decision(1, 9, 9)
    cg_ok = (cg_qual == "C3XRP_REPLICATION_QUALIFIED"
             and cg_incomplete == "C3XRP_BLOCKED_INCOMPLETE_MEASUREMENT"
             and cg_limited == "C3XRP_REPLICATION_LIMITED")

    out = {"artifact": "C3XRA_SYNTHETIC_E2E_REPLAY", "gate": "C3XRA", "synthetic_only": True,
           "n_perm_replay": N_PERM, "n_boot_replay": N_BOOT,
           "sealed_confirmatory": A.SEALED_INFERENCE,
           "estimator_unit": "run_pair_disjoint",
           "contamination_channel_max_imagery_corr": round(max_pred_img, 4),
           "contamination_operator_imagery_free": max_pred_img < 0.15,
           "scenarios": rows, "all_scenarios_agree": ok,
           "adversarial_scenarios": ADVERSARIAL,
           "no_adversarial_valid_pass": adv_ok,
           "cohort_gate_replay": {"qualified": cg_qual, "incomplete": cg_incomplete, "limited": cg_limited},
           "cohort_gate_ok": cg_ok,
           "pass": bool(ok and adv_ok and cg_ok and max_pred_img < 0.15)}
    with open(_OUT, "w", encoding="utf-8") as f:
        json.dump(_sh(out), f, indent=2)
    print("E2E PASS", out["pass"], "| agree", ok, "| adv_ok", adv_ok, "| cohort_ok", cg_ok,
          "| pred_img", round(max_pred_img, 3), flush=True)
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
