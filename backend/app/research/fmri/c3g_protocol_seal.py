"""C3G protocol seal — preregistration committed BEFORE any confirmatory C3G
outcome is inspected. Fixes hypotheses, metrics, controls, tests, multiplicity
correction, decision rules, seeds, model classes, and hashes the analysis code
for tamper-evidence. Once committed, criteria are not changed because of results;
any later unplanned analysis is labelled EXPLORATORY_POST_HOC.
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
    reports = Path(os.environ.get("C3G_REPORTS_DIR", "reports/c3g"))
    reports.mkdir(parents=True, exist_ok=True)
    fmri = Path(os.environ.get("C3G_FMRI_DIR", "backend/app/research/fmri"))

    seal = {
        "artifact": "C3G_PROTOCOL_SEAL",
        "gate": "C3G",
        "title": "State-Specific Neural Geometry",
        "subject": "subj01",
        "source_c3m_sha": "11445aa90486865ae1fcb33b4e3699e6e501f419",
        "branch": "research/state-specific-geometry-c3g",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "SEALED_BEFORE_CONFIRMATORY_INSPECTION",
        "is_not_c4": True,
        "central_question": (
            "After correcting cross-session nonstationarity (here by construction: perception and "
            "imagery are the SAME-session, same-content Set-B vision vs imagery trials), is the "
            "residual perception->imagery degradation explained by simple signal "
            "attenuation/reliability loss, or a reproducible state-specific representational-"
            "geometry transformation?"),
        "states": {
            "P_perception": "Set-B VISION betas, 48 trials (6 content x 8 reps), rows visB 192:240",
            "I_imagery": "Set-B IMAGERY betas, 96 trials (6 content x 16 reps), rows imgB 336:384+624:672",
            "anchor": "core-NSD X_p (6000, betas_fithrf) for reliability/dimensionality reference",
            "session_confound": "eliminated by construction (P and I same NSD-Imagery session)",
        },
        "spaces": {
            "primary": "nsdgeneral (V=15587)",
            "secondary_hierarchical": ["V1", "V2", "V3", "hV4", "ventral", "lateral", "parietal"],
        },
        "hypotheses": {
            "H_attenuation": "P->I difference is reliability/gain/noise degradation only.",
            "H_state_geometry": "A residual state-specific geometry transformation remains after "
                                "matching reliability.",
            "H_null": "No reliable P<->I geometry difference survives.",
        },
        "primary_metrics_nsdgeneral": {
            "G1": "centroid displacement (normalized)",
            "G3_participation_ratio": "effective dimensionality (state diff, subsample-matched n=48, "
                                      "bootstrap 1000, state-label permutation 1000)",
            "G3_eigenspectrum_logdiv": "log eigenspectrum divergence (top 20)",
            "G4_subspace_overlap": "mean cos^2 of top-10 principal angles (state diff + permutation)",
            "G6_cka": "linear CKA on 6 content-avg patterns (content-label permutation)",
            "G7_procrustes_disparity": "orthogonal Procrustes disparity on 6 content patterns",
            "G8_rdm_correlation": "crossnobis 6x6 RDM correlation P vs I (content permutation)",
        },
        "critical_control_SNR_matched_perception": {
            "definition": "Degrade P with isotropic Gaussian noise until its split-half reliability "
                          "equals I's measured split-half reliability (bisection; imagery labels NOT "
                          "used). Recompute the degraded-P vs I geometry.",
            "role": "Distinguishes H_attenuation from H_state_geometry.",
            "target_reliability": "I's measured split-half reliability (a design input, computed by "
                                  "the same estimator; recorded at run time).",
        },
        "other_controls": ["state-label permutation (shuffled pairing)", "content-label permutation",
                           "capacity-matched random maps (transform stage)", "gain-only model",
                           "identity"],
        "statistical_tests": {
            "state_difference": "state-label permutation p (two-sided, 1000 perms, +1 smoothing), "
                                "subsample-matched to n=48; bootstrap 95% CI on the P->I difference "
                                "(1000 resamples).",
            "content_similarity": "content-label permutation p (1000).",
            "multiplicity": "Benjamini-Hochberg FDR at q=0.05 across the primary testable metric "
                            "family {G3_participation_ratio, G4_subspace_overlap, G6_cka, "
                            "G8_rdm_correlation} in nsdgeneral. ROI family corrected SEPARATELY "
                            "(BH within the 7 ROIs per metric). Decoder-space and transforms are "
                            "secondary and not part of the primary FDR family.",
        },
        "decision_rules": {
            "primary_family": ["G3_participation_ratio", "G4_subspace_overlap", "G6_cka",
                               "G8_rdm_correlation"],
            "C3G_STATE_GEOMETRY_SUPPORTED": (
                "ALL of: (A) the SNR-matched degraded-perception does NOT reproduce the imagery "
                "phenotype -- i.e. imagery still differs from degraded-perception on >=1 primary "
                "metric (degP-vs-I bootstrap CI on that metric EXCLUDES 0, or degP-vs-I permutation "
                "p < FDR threshold); (B) >=1 primary metric shows a reliable raw P<->I difference "
                "after BH-FDR q=0.05; (C) the qualitative result is not driven by a single ROI or "
                "content (robustness Phase 9); (D) robust across the sealed perturbations."),
            "C3G_SIMPLE_ATTENUATION_SUPPORTED": (
                "A perm-significant raw P<->I difference exists (B holds) BUT the SNR-matched "
                "degraded-perception REPRODUCES the imagery phenotype on ALL primary geometry "
                "metrics (each degP-vs-I bootstrap CI INCLUDES 0), i.e. reliability loss explains "
                "the difference."),
            "C3G_STATE_GEOMETRY_NULL": (
                "No primary metric shows a reliable raw P<->I difference after BH-FDR (B fails)."),
            "BLOCKED": "Provenance / content correspondence / leakage-free evaluation / sample size "
                       "invalidates the intended inference (see stop conditions).",
        },
        "sample_size_posture": (
            "Trial-level distributional geometry (G1,G3,G4) uses 144 pooled trials -> permutation "
            "well powered. Content-level metrics (G6,G7,G8) and all supervised transforms use K=6 "
            "content items -> UNDERPOWERED; transforms (run_c3g_transforms) are SECONDARY and cannot "
            "change the primary decision. A negative transform result is reported as underpowered, "
            "not as content-dependence."),
        "permitted_model_classes": ["identity", "scalar gain", "diagonal (regularized)",
                                    "orthogonal Procrustes", "low-rank linear (rank<=K-2)"],
        "complexity_constraints": "Shared-subspace rank <= K-2 = 4; no flexible neural networks; "
                                  "T6 nonlinear only if all linear models fail (they are underpowered "
                                  "here, so T6 is not invoked).",
        "robustness_phase9": ["ROI subsets", "reliability/noise seed variation", "k_subspace in "
                              "{5,10,20}", "n_top spectrum in {10,20,40}", "trial bootstrap",
                              "leave-one-content-out", "crossnobis fold count"],
        "exclusions": ["Set C conceptual imagery", "attention runs",
                       "nsd00000 from core-perception content match"],
        "seeds": {"c3g_analysis_permutation_bootstrap": 20260826},
        "code_hashes": {
            "c3g_geometry.py": _sha256_file(fmri / "c3g_geometry.py"),
            "c3g_data_contract.py": _sha256_file(fmri / "c3g_data_contract.py"),
            "run_c3g_analysis.py": _sha256_file(fmri / "run_c3g_analysis.py"),
            "run_c3g_transforms.py": _sha256_file(fmri / "run_c3g_transforms.py"),
        },
        "data_manifest_self_hash": json.load(
            open(Path("results/c3g/c3g_data_manifest.json")))["self_hash"],
        "code_sha": _code_sha(),
        "scope": "SINGLE_SUBJECT_subj01_ONLY_NOT_POPULATION_EVIDENCE",
    }
    seal["self_hash"] = hashlib.sha256(json.dumps(seal, sort_keys=True, default=str).encode()).hexdigest()
    out = reports / "c3g_protocol_seal.json"
    json.dump(seal, open(out, "w"), indent=2)
    print(f"Wrote {out}")
    print(json.dumps({"status": seal["status"], "self_hash": seal["self_hash"][:16],
                      "code_hashes": {k: v[:12] for k, v in seal["code_hashes"].items()}}, indent=2))


if __name__ == "__main__":
    main()
