"""ANIMUS-P2 REAL product bridge — runs ONLY after a VALIDATED scientific decision.

For each subject that PASSED the frozen subject gate, this reproduces the EXACT sealed per-subject decode
(identical grouped-by-identity split, fold-safe normalizer, nested-validation ridge, bootstrap-ensemble
uncertainty) to obtain held-out decoded latents + uncertainty + true target embeddings, then runs the
already-sealed `neural_initialization_experiment` comparing UNINFORMED / NEURAL_ONLY / BEHAVIORAL_ONLY /
NEURAL_PLUS_BEHAVIORAL loops with NO product tuning. It also materializes a ValidatedPerceptionNeuralDecoder
with full provenance (real model weights hash) and records that hash into the model manifest.

Fail-closed: if the live scientific decision is not ANIMUS_P2_PERCEPTION_DECODER_VALIDATED, or no passing
subject bundles are present, it writes nothing and exits without fabricating a gain.

Usage:
    PYTHONPATH=. python app/research/animus_p2/run_p2_product_bridge.py --features-dir /work/animus_p2r/features
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys

import numpy as np

from app.core.animus.p2.capability import PERCEPTION_NEURAL_CONTENT, ScientificCapabilityAuthorization
from app.core.animus.p2.decoder import (
    BootstrapEnsembleDecoder,
    ValidatedPerceptionNeuralDecoder,
    _ridge_fit,
    select_alpha,
)
from app.core.animus.p2.features import FoldSafeNormalizer
from app.core.animus.p2.integration import (
    ValidatedPerceptionObservationProvider,
    belief_fusion_respects_uncertainty,
    neural_initialization_experiment,
)
from app.core.animus.p2.splits import freeze_identity_split, trial_partition

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
OUT = os.path.join(ROOT, "results", "animus_p2")
SUBJ_DIR = os.path.join(OUT, "subjects")
DECISION = os.path.join(OUT, "ANIMUS_P2_SCIENTIFIC_DECISION.json")
SEAL = os.path.join(OUT, "animus_p2_protocol_seal.json")
SPLIT_SEED = 20260909


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


def _decode_holdout(X, stimulus_ids, Y):
    """Reproduce the sealed decode to get held-out (pred, unc, true) and the fitted full-train weights."""
    X = np.asarray(X, float)
    Y = np.asarray(Y, float)
    stimulus_ids = [str(s) for s in stimulus_ids]
    split = freeze_identity_split(stimulus_ids, seed=SPLIT_SEED)
    part = trial_partition(stimulus_ids, split)
    tr, va, te = part == "train", part == "val", part == "test"
    norm = FoldSafeNormalizer().fit(X[tr])
    Xtr, Xva, Xte = norm.transform(X[tr]), norm.transform(X[va]), norm.transform(X[te])
    alpha, _ = select_alpha(Xtr, Y[tr], Xva, Y[va])
    ens = BootstrapEnsembleDecoder(alpha=alpha, n_boot=20).fit(Xtr, Y[tr])
    pred, unc = ens.predict_with_uncertainty(Xte)
    weights = _ridge_fit(Xtr, Y[tr], alpha)  # point-estimate weights for the materialized decoder
    return pred, unc, Y[te], weights, alpha, int(tr.sum()), int(te.sum())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features-dir", default=os.path.join(OUT, "features"))
    args = ap.parse_args()

    if not os.path.exists(SEAL):
        print("FIREWALL: protocol seal missing; bridge locked.")
        return 2
    dec = json.load(open(DECISION, encoding="utf-8"))
    if dec.get("decision") != "ANIMUS_P2_PERCEPTION_DECODER_VALIDATED":
        print(f"GATE: decision is {dec.get('decision')} != VALIDATED; real product bridge not authorized. "
              "Nothing written (no fabrication).")
        return 0

    # Capability must be usable for PERCEPTION (fail-closed via the same authorization the product consults).
    auth = ScientificCapabilityAuthorization().validate_perception(dec["decision"])
    auth.enforce(PERCEPTION_NEURAL_CONTENT)

    passing = []
    for f in sorted(glob.glob(os.path.join(SUBJ_DIR, "sub-*.json"))):
        s = json.load(open(f, encoding="utf-8"))
        if s.get("pass"):
            passing.append(s["subject"])
    if not passing:
        print("No passing subjects; nothing to bridge.")
        return 0

    per_subject = {}
    weights_hashes = {}
    for subject in passing:
        bundle = os.path.join(args.features_dir, f"{subject}.npz")
        if not os.path.exists(bundle):
            print(f"{subject}: feature bundle missing at {bundle}; skipping (no fabrication).")
            continue
        d = np.load(bundle, allow_pickle=True)
        pred, unc, true, weights, alpha, n_tr, n_te = _decode_holdout(d["X"], list(d["stimulus_ids"]), d["Y"])
        exp = neural_initialization_experiment(pred, unc, None, true, seed=SPLIT_SEED)

        w_hash = hashlib.sha256(np.ascontiguousarray(weights, dtype=np.float64).tobytes()).hexdigest()
        weights_hashes[subject] = w_hash
        provenance = {
            "training_dataset": "NOD ds004496 v2.1.2",
            "training_subjects": [subject],
            "roi": "Wang25 primary union (MNI152NLin2009cAsym:res-2)",
            "embedding_model": "open_clip:ViT-B-32 laion2b_s34b_b79k",
            "split_seal_hash": freeze_identity_split([str(x) for x in d["stimulus_ids"]],
                                                     seed=SPLIT_SEED)["test_hash"],
            "model_weights_hash": w_hash,
            "calibration_hash": hashlib.sha256(
                np.ascontiguousarray(unc, dtype=np.float64).tobytes()).hexdigest(),
            "scientific_decision_hash": dec["self_hash"],
            "ridge_alpha": alpha,
        }
        # Materialize the gated real decoder + provider (asserts full provenance; fail-closed).
        vdec = ValidatedPerceptionNeuralDecoder(weights=weights, provenance=provenance)
        _provider = ValidatedPerceptionObservationProvider(vdec, auth)  # constructs iff capability usable
        assert _provider.source_type == "VALIDATED_PERCEPTION_NEURAL"

        per_subject[subject] = {
            "n_train_trials": n_tr, "n_test_trials": n_te, "ridge_alpha": alpha,
            "model_weights_hash": w_hash,
            "median_neural_initialization_gain": exp["median_neural_initialization_gain"],
            "gain_bootstrap_ci95": exp["gain_bootstrap_ci95"],
            "neural_init_gain_positive": exp["neural_init_gain_positive"],
            "neural_faster": exp["neural_faster"],
            "fused_ge_both": exp["fused_ge_both"],
            "mode_medians": exp["mode_medians"],
            "median_initial_similarity_uninformed": exp["median_initial_similarity_uninformed"],
            "median_initial_similarity_neural": exp["median_initial_similarity_neural"],
            "median_iters_to_threshold_uninformed": exp["median_iters_to_threshold_uninformed"],
            "median_iters_to_threshold_neural": exp["median_iters_to_threshold_neural"],
        }
        print(f"{subject}: gain={exp['median_neural_initialization_gain']:.4f} "
              f"ci={exp['gain_bootstrap_ci95']} positive={exp['neural_init_gain_positive']} "
              f"faster={exp['neural_faster']} fused_ge_both={exp['fused_ge_both']}")

    if not per_subject:
        print("No passing-subject feature bundles available; bridge not run (no fabrication).")
        return 0

    fusion = belief_fusion_respects_uncertainty()
    gains = [v["median_neural_initialization_gain"] for v in per_subject.values()]
    bridge = {
        "artifact": "ANIMUS_P2_PRODUCT_BRIDGE",
        "milestone": "ANIMUS-P2",
        "authorized_because": "ANIMUS_P2_PERCEPTION_DECODER_VALIDATED",
        "modes": ["UNINFORMED", "NEURAL_ONLY", "BEHAVIORAL_ONLY", "NEURAL_PLUS_BEHAVIORAL"],
        "product_tuning": "NONE (sealed bridge; no parameters fit to product outcome)",
        "passing_subjects": passing,
        "per_subject": per_subject,
        "median_gain_across_subjects": float(np.median(gains)),
        "all_subjects_gain_positive": bool(all(v["neural_init_gain_positive"] for v in per_subject.values())),
        "belief_fusion_respects_uncertainty": fusion,
        "scientific_decision_hash": dec["self_hash"],
        "imagery_remains_unauthorized": True,
    }
    json.dump(_sh(bridge), open(os.path.join(OUT, "product_bridge.json"), "w"), indent=2)

    # record real weights hashes into the model manifest
    manp = os.path.join(OUT, "model_manifest.json")
    if os.path.exists(manp):
        man = json.load(open(manp, encoding="utf-8"))
        man["validated_subjects"] = passing
        man["model_weights_sha256"] = weights_hashes
        json.dump(_sh(man), open(manp, "w"), indent=2)
    print(f"wrote product_bridge.json (median gain {np.median(gains):.4f}) and recorded weights hashes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
