"""C3XA requalification decision — applies the sealed correction rule to the
fixation-excluded, family-stratified corrected reliability (no new measurement).

D1 remains qualified for C3XR iff >=2/3 subjects show reliable NATURAL imagery
(R_I_natural>0, perm p<0.05, bootstrap CI lower>0, split-robust) AND reliable
matched natural perception. Artificial is a secondary family.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

SUBS = ["sub-01", "sub-02", "sub-03"]


def _pass(r):
    return (r["reliability"] > 0 and r["perm_p_one_sided"] < 0.05
            and r["bootstrap_ci95"][0] > 0 and min(r["split_seed_values"]) > 0)


def main() -> None:
    out_dir = Path(os.environ.get("C3XA_OUT_DIR", "results/c3xa"))
    seal = json.load(open(os.environ.get("C3XA_SEAL", "reports/c3xa/c3xa_correction_seal.json")))

    c3x_dir = Path(os.environ.get("C3X_REL_DIR", "results/c3x"))
    per = {}
    nat_pass = art_pass = rp_nat_ok = 0
    for s in SUBS:
        d = json.load(open(out_dir / f"c3xa_imagery_reliability_corrected_{s}.json"))
        rin, ria = d["R_I_natural"], d["R_I_artificial"]
        rpn, rpa = d["R_P_natural"], d["R_P_artificial"]
        # R_P_natural FULL-inference reliability is established by C3X on the identical
        # perceptionNaturalImageTest data + estimator; the local C3XA R_P_natural is point-only.
        c3x = json.load(open(c3x_dir / f"d1_reliability_{s}.json"))
        rpn_full = c3x["R_P_VC"]
        nat = _pass(rin)
        art = _pass(ria)
        rpn_ok = _pass(rpn_full)
        nat_pass += int(nat)
        art_pass += int(art)
        rp_nat_ok += int(rpn_ok)
        per[s] = {
            "R_I_natural": rin["reliability"], "R_I_natural_p": rin["perm_p_one_sided"],
            "R_I_natural_ci95": rin["bootstrap_ci95"], "R_I_natural_pass": nat,
            "R_I_artificial": ria["reliability"], "R_I_artificial_p": ria["perm_p_one_sided"],
            "R_I_artificial_pass": art,
            "R_P_natural_point_c3xa": rpn["reliability"],
            "R_P_natural_c3x_full": rpn_full["reliability"],
            "R_P_natural_c3x_full_p": rpn_full["perm_p_one_sided"],
            "R_P_natural_c3x_full_ci95": rpn_full["bootstrap_ci95"],
            "R_P_natural_reliable": rpn_ok,
            "R_P_artificial_point": rpa["reliability"],
            "attenuation_natural": d.get("attenuation_natural"),
            "attenuation_artificial": d.get("attenuation_artificial"),
            "R_I_combined_25_confounded": d["R_I_combined_25_confounded"]["reliability"],
            "R_I_including_fixation_oldC3X": d["R_I_including_fixation_oldC3X"]["reliability"],
            "fixation_only_repeatability": d["fixation_diagnostic"]["fixation_only_repeatability"],
        }

    natural_qualifies = nat_pass >= 2 and rp_nat_ok >= 2
    artificial_qualifies = art_pass >= 2
    if natural_qualifies:
        decision = "C3X_EXTERNAL_IMAGERY_DATASET_QUALIFIED_CONFIRMED"
        c3xr_authorized = True
        primary_family, secondary_family = "natural_10", "artificial_15"
    elif artificial_qualifies:
        decision = "C3X_RESTRICTED_ARTIFICIAL_IMAGERY_DATASET_QUALIFIED"
        c3xr_authorized = False
        primary_family, secondary_family = "artificial_15", None
    else:
        decision = "C3X_QUALIFICATION_REVOKED_BY_TARGET_CONTRACT_CORRECTION"
        c3xr_authorized = False
        primary_family = secondary_family = None

    obj = {
        "artifact": "C3XA_DECISION", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "seal_self_hash": seal["self_hash"],
        "correction": "fixation (Label 26) excluded; family-stratified; matched perception per family",
        "per_subject": per,
        "n_natural_imagery_pass": nat_pass, "n_artificial_imagery_pass": art_pass,
        "n_natural_perception_reliable": rp_nat_ok,
        "natural_family_qualifies": natural_qualifies,
        "artificial_family_qualifies": artificial_qualifies,
        "decision": decision,
        "supersedes_c3x_decision": "C3X_EXTERNAL_IMAGERY_DATASET_QUALIFIED (historical; based on the "
                                   "pre-correction 26-label contract)",
        "c3xr_authorized": c3xr_authorized,
        "primary_C3XR_family": primary_family, "secondary_family": secondary_family,
        "fixation_sensitivity_note": "compare R_I_including_fixation_oldC3X vs R_I_combined_25 vs "
                                     "family-stratified; and fixation_only_repeatability per subject",
        "family_confound_note": "combined 25-target reliability is reported as CONFOUNDED (natural-vs-"
                                "artificial separation); qualification uses WITHIN-family natural.",
        "no_geometry_computed": True, "no_reconstruction": True,
        "next_gate_if_authorized": "C3XR External State-Geometry Replication on ds001506 (primary "
                                   "natural_10) - NOT started in C3XA",
    }
    obj["self_hash"] = hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(obj, open(out_dir / "c3xa_decision.json", "w"), indent=2)
    print(f"nat_pass={nat_pass}/3 art_pass={art_pass}/3 rp_nat_ok={rp_nat_ok}/3")
    print(f"DECISION: {decision} | c3xr_authorized={c3xr_authorized} primary={primary_family}")


if __name__ == "__main__":
    main()
