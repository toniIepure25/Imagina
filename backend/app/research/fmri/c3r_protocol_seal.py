"""C3R protocol seal — preregistration committed BEFORE any subj02/05/07 imagery
reliability value is inspected. Fixes the subjects, dataset/beta variant, row
mapping, primary quantity, the INHERITED C3G reliability estimator (by code
hash), the null and bootstrap construction, the reliability-gate rules, the
vision/imagery quality classification, and the acquisition scope. Once committed,
criteria are not changed because of observed results.
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


def _code_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"


def main() -> None:
    reports = Path(os.environ.get("C3R_REPORTS_DIR", "reports/c3r"))
    reports.mkdir(parents=True, exist_ok=True)
    fmri = Path(os.environ.get("C3R_FMRI_DIR", "backend/app/research/fmri"))

    seal = {
        "artifact": "C3R_PROTOCOL_SEAL",
        "gate": "C3R",
        "title": "Prospective Imagery Reliability Replication and Foundation Gate",
        "is_not_c4": True,
        "no_reconstruction": True,
        "no_geometry_in_c3r": True,
        "scientific_parent": "df81474def42f517b45af73cab13742e9adf7a05",
        "technical_parent": "7a04b1c1c2080d91afa7f96787bcabc2f550c947",
        "c3g_source": "11445aa90486865ae1fcb33b4e3699e6e501f419",
        "branch": "research/imagery-reliability-replication-c3r",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "SEALED_BEFORE_RELIABILITY_INSPECTION",
        "c3g_ci_status": "PENDING_RUNNER_INFRASTRUCTURE",
        "c3g_ci_run": "32985840538",

        "subjects": ["subj02", "subj05", "subj07"],
        "dataset": "NSD-Imagery",
        "beta_variant": "func1pt8mm/nsdimagerybetas_fithrf",
        "row_mapping": {
            "source": "certified upstream NSD-Imagery row mapping "
                      "(results/c3_nsdimagery_beta_event_manifest.json, "
                      "event_manifest_hash 6d63e4b6c21d93eb...), design-determined and "
                      "subject-independent; NOT re-derived per participant",
            "visB": "192:240", "imgB_1": "336:384", "imgB_2": "624:672",
            "setB_vision_trials": 48, "setB_imagery_trials": 96,
            "contents": 6, "repeats_per_content": 16,
        },
        "primary_roi": "nsdgeneral AND ncsnr > 0 (per subject)",
        "ncsnr_source": "nsddata_betas/ppdata/{subj}/func1pt8mm/betas_fithrf/ncsnr.nii.gz "
                        "(perception ncsnr, matching the C3/C3G selection policy; a small standalone "
                        "file, NOT the 40-session perception betas)",
        "voxel_selection_policy": "nsdgeneral_membership AND perception_ncsnr>0 (identical policy to "
                                  "C3; per-subject voxel count will differ)",
        "secondary_rois": ["V1", "V2", "V3", "hV4", "ventral", "lateral", "parietal"],

        "primary_quantity": "R_I = Set-B imagery stimulus-pattern split-half reliability in "
                            "nsdgeneral (per subject)",
        "inherited_estimator": {
            "function": "app.research.fmri.c3g_geometry.split_half_reliability",
            "spec": "per-content split of the 16 imagery reps into two halves, mean pattern per "
                    "content, Pearson r of the concatenated 6-content mean-pattern vectors across "
                    "halves, averaged over N_REP random splits, Spearman-Brown corrected",
            "n_rep_point": 200,
            "c3g_geometry_sha256": _sha256_file(fmri / "c3g_geometry.py"),
            "c3r_reliability_sha256": _sha256_file(fmri / "c3r_reliability.py"),
        },
        "null_construction": {
            "method": "permute the content-label vector across the 96 imagery trials (preserves "
                      "16 reps/content, run structure, ROI dimension, marginal distribution) and "
                      "recompute reliability with the SAME estimator",
            "n_perm": 1000, "n_rep_resample": 60, "one_sided": True,
        },
        "bootstrap": {"method": "resample the 16 reps WITHIN each content with replacement "
                                "(preserves 6x16 shape), recompute reliability", "n_boot": 1000,
                      "ci": "percentile 2.5/97.5"},
        "split_seed_robustness": {"seeds": ["seed", "seed+100", "seed+200"], "seed_base": 20260826},

        "reliability_gate_rules": {
            "RELIABILITY_PASS": "R_I > 0 AND permutation p < 0.05 AND bootstrap CI lower bound > 0 "
                                "AND min over split seeds > 0",
            "RELIABILITY_MARGINAL": "positive point estimate but CI includes 0 OR permutation "
                                    "p >= 0.05 (retained descriptively; NOT used for confirmatory "
                                    "geometry)",
            "RELIABILITY_NOISE_FLOOR": "R_I <= 0 or indistinguishable from the empirical null",
        },
        "vision_control": {
            "quantity": "R_P = same-session Set-B VISION split-half reliability (same estimator)",
            "classes": ["VISION_RELIABLE_IMAGERY_RELIABLE",
                        "VISION_RELIABLE_IMAGERY_NOISE_FLOOR",
                        "VISION_UNRELIABLE_SESSION_QUALITY_BLOCKER"],
            "rule": "a low-imagery result with UNRELIABLE same-session vision is a session/quality "
                    "blocker, NOT cognitive attenuation",
        },
        "practical_effect_bins_descriptive_only": ["R_I>0.05", "R_I>0.10", "R_I>0.20"],
        "subj01_reference_descriptive_only": 0.011,

        "acquisition_scope": {
            "phase1": "imagery only: betas_nsdimagery.hdf5 + nsdgeneral + prf-visualrois + streams + "
                      "ncsnr per subject. NO core-NSD perception betas yet.",
            "phase5_conditional": "40-session perception foundation ONLY for RELIABILITY_PASS "
                                  "subjects (rolling extraction; frozen C3 model family).",
        },
        "selection_rule": "participant selection depends ONLY on the sealed imagery-reliability "
                          "criterion; NEVER on geometry outcomes (which are not computed in C3R). "
                          "Any later geometry inference is CONDITIONAL ON PROSPECTIVELY QUALIFYING "
                          "IMAGERY RELIABILITY, not an unbiased prevalence estimate.",
        "gate_decision_states": ["C3R_RELIABLE_IMAGERY_FOUND",
                                 "C3R_NO_RELIABLE_IMAGERY_IN_REMAINING_COHORT",
                                 "C3R_BLOCKED_BY_DATA_ACCESS_OR_INTEGRITY"],
        "code_sha": _code_sha(),
        "scope": "PROSPECTIVE_RELIABILITY_SCREEN_conditional_qualified_cohort_only",
    }
    seal["self_hash"] = hashlib.sha256(json.dumps(seal, sort_keys=True, default=str).encode()).hexdigest()
    out = reports / "c3r_protocol_seal.json"
    json.dump(seal, open(out, "w"), indent=2)
    print(f"Wrote {out}")
    print(json.dumps({"status": seal["status"], "self_hash": seal["self_hash"][:16],
                      "estimator_hash": seal["inherited_estimator"]["c3g_geometry_sha256"][:12],
                      "subjects": seal["subjects"]}, indent=2))


if __name__ == "__main__":
    main()
