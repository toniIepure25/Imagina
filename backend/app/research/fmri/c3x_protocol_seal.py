"""C3X protocol seal — preregistration committed BEFORE any candidate imagery
reliability value is inspected. Freezes the qualification question, candidate
ranking (design/access only), the dataset-agnostic RUN-DISJOINT reliability
estimator (by code hash), the null/bootstrap construction, the subject and
dataset reliability gates, the D1-first conditional rule, the reliability spaces,
the vividness ordering, and the no-geometry guard.
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


def _sha_json(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _code_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"


def main() -> None:
    reports = Path(os.environ.get("C3X_REPORTS_DIR", "reports/c3x"))
    reports.mkdir(parents=True, exist_ok=True)
    fmri = Path(os.environ.get("C3X_FMRI_DIR", "backend/app/research/fmri"))
    res = Path("results/c3x")

    seal = {
        "artifact": "C3X_PROTOCOL_SEAL",
        "gate": "C3X",
        "title": "External Imagery Dataset Qualification",
        "is_not_c4": True, "no_reconstruction": True, "no_geometry_in_c3x": True,
        "scientific_parent_c3r": "25a0524becbdcf6880c5dd571bba4fcaffb7ed0d",
        "c3r_decision": "C3R_NO_RELIABLE_IMAGERY_IN_REMAINING_COHORT",
        "branch": "research/external-imagery-qualification-c3x",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "SEALED_BEFORE_RELIABILITY_INSPECTION",

        "central_question": "Which reproducibly obtainable fMRI imagery dataset provides measurable "
                            "stimulus-specific imagery reliability with a compatible perception "
                            "condition, sufficient to identify perception<->imagery geometry?",
        "measurement_priority": "stimulus-specific IMAGERY RELIABILITY (not decoder accuracy / "
                                "reconstruction / published performance)",
        "candidates": {
            "D1_ds001506_DIR": "HIGH_PRIORITY_FOR_RELIABILITY_TEST",
            "D2_ds005191_MindCaptioning": "MEDIUM_PRIORITY",
            "D3_7T_letters_Senden": "BLOCKED_ACCESS",
        },
        "ranking_frozen_before_outcomes": True,
        "first_empirical_target": "D1 (ds001506)",
        "conditional_rule": "inspect D2 neural outcomes ONLY if D1 does not reach "
                            "DATASET_RELIABILITY_PASS; never to choose a better-looking dataset.",

        "estimator": {
            "module": "app.research.fmri.c3x_reliability",
            "primary_statistic": "run-disjoint split-half reliability (Pearson r of concatenated "
                                 "content-mean patterns across whole-run halves, Spearman-Brown); "
                                 "reduces to the C3G split-half quantity on a run-less fixture",
            "n_rep_point": 200, "n_rep_resample": 60,
            "c3x_reliability_sha256": _sha256_file(fmri / "c3x_reliability.py"),
            "inherited_c3g_geometry_sha256": _sha256_file(fmri / "c3g_geometry.py"),
        },
        "null_construction": {"method": "permute the content-label vector; recompute run-disjoint "
                                        "reliability with the same estimator", "n_perm": 1000,
                              "one_sided": True},
        "bootstrap": {"method": "non-straddling: fixed run-disjoint halves, resample trials WITHIN "
                                "each half with replacement", "n_boot": 1000, "ci": "2.5/97.5 pct"},
        "split_seed_robustness": {"seeds": ["seed", "seed+100", "seed+200"], "seed_base": 20260826},

        "d1_data_source": {
            "canonical": "KamitaniLab figshare preprocessed bdpy VC release, DOI "
                         "10.6084/m9.figshare.7033577.v16 (official V1-V4/VC ROIs + per-sample "
                         "stimulus/run labels)",
            "reason": "OpenNeuro ds001506 BIDS is raw BOLD with no ROI masks; the figshare VC release "
                      "is the field-standard reproducible source and small (~460 MB)",
            "imagery_files": {"sub-01": 22713854, "sub-02": 22713863, "sub-03": 22713953},
            "perception_test_files": {"sub-01": 14830631, "sub-02": 14830697, "sub-03": 14830856},
            "content_label": "imagined category/image identity (from bdpy labels)",
            "run_label": "acquisition run (for run-disjoint splits)",
            "imagery_window": "imagery-period response (bdpy preprocessed sample per trial)",
        },
        "reliability_spaces": {"d1_primary": "VC (visual-cortex aggregate)",
                               "d1_secondary": ["V1", "V2", "V3", "V4"]},

        "subject_gate": {
            "SUBJECT_RELIABILITY_PASS": "R_I > 0 AND perm p < 0.05 AND bootstrap CI lower > 0 AND "
                                        "min over split seeds > 0",
            "SUBJECT_RELIABILITY_MARGINAL": "positive point but CI includes 0 OR p >= 0.05",
            "SUBJECT_RELIABILITY_NOISE_FLOOR": "R_I <= 0",
        },
        "dataset_gate": {
            "DATASET_RELIABILITY_PASS": ">=2 subjects with imagery PASS AND matched perception "
                                       "reliable (guards against one anomalous subject)",
            "DATASET_RELIABILITY_PROMISING": "one clear pass or multiple positive-but-underpowered",
            "DATASET_RELIABILITY_FAIL": "no subject provides demonstrably reliable imagery",
            "DATASET_QUALITY_BLOCKED": "matched perception itself unreliable for all subjects",
        },
        "measurement_ceiling": "report R_I ceiling, R_P ceiling, and attenuation ratio R_I/R_P per "
                               "dataset before any geometry/decoder claim",
        "vividness_ordering": "primary reliability uses ALL valid imagery trials; vividness-"
                              "conditioned analyses are SECONDARY and run only after the primary "
                              "status is frozen; no high-vividness-only confirmatory sample.",
        "controls": ["stimulus-label permutation", "run-label-only", "trial-order-only",
                     "cue-only (D2)", "mean-pattern", "ROI-size control", "random-voxel control",
                     "cross-run leakage audit"],
        "decision_states": ["C3X_EXTERNAL_IMAGERY_DATASET_QUALIFIED",
                            "C3X_RESTRICTED_TOPOGRAPHIC_IMAGERY_DATASET_QUALIFIED",
                            "C3X_NO_AVAILABLE_DATASET_MEETS_RELIABILITY_GATE"],
        "next_gate_if_qualified": "C3XR - External State-Geometry Replication (NOT started in C3X)",

        "artifact_hashes": {
            "d1_metadata_audit": _sha_json(res / "d1_metadata_audit.json"),
            "d2_metadata_audit": _sha_json(res / "d2_metadata_audit.json"),
            "d3_metadata_audit": _sha_json(res / "d3_metadata_audit.json"),
            "candidate_inventory": _sha_json(res / "c3x_candidate_inventory.json"),
            "ranking": _sha_json(res / "c3x_ranking.json"),
        },
        "code_sha": _code_sha(),
        "scope": "DATASET_QUALIFICATION_ONLY; conditional on prospectively measured imagery "
                 "reliability; NOT an unbiased population/prevalence estimate",
    }
    seal["self_hash"] = hashlib.sha256(json.dumps(seal, sort_keys=True, default=str).encode()).hexdigest()
    out = reports / "c3x_protocol_seal.json"
    json.dump(seal, open(out, "w"), indent=2)
    print(f"Wrote {out}")
    print(json.dumps({"status": seal["status"], "self_hash": seal["self_hash"][:16],
                      "estimator_hash": seal["estimator"]["c3x_reliability_sha256"][:12],
                      "first_target": seal["first_empirical_target"]}, indent=2))


if __name__ == "__main__":
    main()
