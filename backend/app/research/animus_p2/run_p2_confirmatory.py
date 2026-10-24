"""ANIMUS-P2 confirmatory executor — REAL perception decode from staged features.

This is the `run_p2_confirmatory` the protocol references. It runs ONLY after the protocol seal is committed
+ CI-green (firewall). It consumes per-subject staged feature bundles (produced by the cluster
feature-extraction job: Wang25-ROI betas + frozen-encoder stimulus embeddings) and runs the EXACT sealed
per-subject pipeline, then the dataset gate, writing results/animus_p2/subjects/*.json and a model manifest.

Feature bundle format (per subject, .npz): X (n_trials, n_vox) Wang25 betas, stimulus_ids (n_trials str),
Y (n_trials, dim) target embeddings, optional categories (n_trials str), optional low_level (n_trials, k).

Usage:
    PYTHONPATH=. python app/research/animus_p2/run_p2_confirmatory.py --features-dir /work/animus_p2/features

If no feature bundles are present, it exits without writing subject results (the decision stays
CONFIRMATORY_PENDING) — it never fabricates outcomes.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys

import numpy as np

from app.core.animus.p2.pipeline import evaluate_subject_arrays

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
OUT = os.path.join(ROOT, "results", "animus_p2")
SUBJ_DIR = os.path.join(OUT, "subjects")
SEAL = os.path.join(OUT, "animus_p2_protocol_seal.json")


def _native(o):
    if isinstance(o, dict):
        return {k: _native(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_native(v) for v in o]
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


def _sh(o):
    o = _native(dict(o))
    o.pop("self_hash", None)
    o["self_hash"] = hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()
    return o


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features-dir", default=os.path.join(OUT, "features"))
    ap.add_argument("--n-perm", type=int, default=1000)
    ap.add_argument("--n-boot", type=int, default=1000)
    args = ap.parse_args()

    # FIREWALL: confirmatory requires the committed protocol seal.
    if not os.path.exists(SEAL):
        print("FIREWALL: protocol seal missing; confirmatory locked. Aborting.")
        return 2

    bundles = sorted(glob.glob(os.path.join(args.features_dir, "*.npz")))
    if not bundles:
        print(f"No feature bundles in {args.features_dir}; confirmatory pending (no fabrication). "
              "Run the cluster feature-extraction job first.")
        return 0

    os.makedirs(SUBJ_DIR, exist_ok=True)
    written = []
    for b in bundles:
        d = np.load(b, allow_pickle=True)
        subject = str(d["subject"]) if "subject" in d else os.path.splitext(os.path.basename(b))[0]
        res = evaluate_subject_arrays(
            subject=subject, X=d["X"], stimulus_ids=list(d["stimulus_ids"]), Y=d["Y"],
            categories=list(d["categories"]) if "categories" in d else None,
            low_level=d["low_level"] if "low_level" in d else None,
            atlas_qc_pass=bool(d["atlas_qc_pass"]) if "atlas_qc_pass" in d else True,
            n_perm=args.n_perm, n_boot=args.n_boot)
        res["feature_bundle_sha256"] = hashlib.sha256(open(b, "rb").read()).hexdigest()
        path = os.path.join(SUBJ_DIR, f"{subject}.json")
        json.dump(_sh(res), open(path, "w"), indent=2)
        written.append(subject)
        print(f"{subject}: M={res['margin_M']} perm_p={res['permutation_p']} "
              f"ci_lo={res['bootstrap_ci_lower']} 2afc={res['two_afc']['accuracy']} PASS={res['pass']}")

    # model manifest
    manifest = {"artifact": "ANIMUS_P2_MODEL_MANIFEST", "milestone": "ANIMUS-P2",
                "subjects": written, "features_dir": args.features_dir,
                "protocol_seal": SEAL, "n_perm": args.n_perm, "n_boot": args.n_boot,
                "reproduction": "run_p2_confirmatory --features-dir <dir>"}
    json.dump(_sh(manifest), open(os.path.join(OUT, "model_manifest.json"), "w"), indent=2)
    print(f"wrote {len(written)} subject result(s); now run run_p2_decision.py for the dataset gate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
