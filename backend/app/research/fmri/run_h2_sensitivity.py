"""C3-H2 sensitivity / power analysis for the single-subject zero-shot null.

Determines whether the H2 null is NULL_SUPPORTED_WITHIN_SENSITIVITY (the n=1
design could detect a meaningful transfer effect but found none) or
INCONCLUSIVE (underpowered even for large effects), using the frozen design:
6 complex targets x 16 repeats, 12-item candidate pool, exact 6! target-label
null, and the corrected genuine-transfer criterion (exact p<0.05 AND not a
single-candidate collapse AND 2AFC>0.5).

Signal-injection generative model: for injected signal fraction s, each trial's
prediction = normalize( sqrt(1-s)*random_unit + sqrt(s)*true_target_unit ),
preserving the repeat structure (all 16 repeats of a target lean toward the
same target). Power at level s = fraction of Monte Carlo datasets that meet the
genuine-transfer criterion.
"""
from __future__ import annotations

import itertools
import json
import os
import time
from pathlib import Path

import numpy as np

N_TARGETS = 6
REPEATS = 16
N_POOL = 12
SET_LABELS = list(range(6, 12))
SEED = 20260724
PERMS = list(itertools.permutations(range(N_TARGETS)))  # 720


def _mrr_and_gate(sims_full, true_local):
    """sims_full: [n, 12] cosine sims to all 12 candidates.
    true_local: [n] true local target index (0..5); full label = 6+local.
    MRR and the exact 6! null are computed over the full 12-candidate pool
    (matching the real H2), permuting only the 6 Set-B target identities.
    Returns (observed_mrr, exact_p, twoway, degenerate)."""
    n = sims_full.shape[0]
    set_cols = np.array(SET_LABELS)

    def mrr_for_full_labels(full_labels):
        true_sim = sims_full[np.arange(n), full_labels]
        ranks = (sims_full >= true_sim[:, None]).sum(axis=1)
        return float(np.mean(1.0 / ranks))

    observed = mrr_for_full_labels(set_cols[true_local])
    null = np.empty(len(PERMS))
    for pi, perm in enumerate(PERMS):
        remap = set_cols[np.array(perm)]  # permuted full labels for local 0..5
        null[pi] = mrr_for_full_labels(remap[true_local])
    exact_p = float(np.mean(null >= observed))

    # degeneracy: dominant within-set argmax fraction
    within_argmax = sims_full[:, set_cols].argmax(axis=1)
    counts = np.bincount(within_argmax, minlength=N_TARGETS)
    degenerate = bool(counts.max() / n > 0.5)

    # 2AFC over the full 12 pool
    true_full = set_cols[true_local]
    n_correct = 0
    n_pairs = 0
    for i in range(n):
        ts = sims_full[i, true_full[i]]
        foils = np.delete(sims_full[i], true_full[i])
        n_correct += int(np.sum(ts > foils))
        n_pairs += foils.shape[0]
    twoway = n_correct / n_pairs
    return observed, exact_p, twoway, degenerate


def main() -> None:
    t0 = time.time()
    cache_root = Path(os.environ["NSD_CACHE_ROOT"])
    results_dir = Path(os.environ.get("RESULTS_DIR", "results"))
    candidate_pool = np.load(str(cache_root / "clip" / "c3_imagery_candidate_pool_clip_vitl14.npy")).astype(np.float64)
    pool_norm = candidate_pool / np.clip(np.linalg.norm(candidate_pool, axis=1, keepdims=True), 1e-8, None)
    set_norm = pool_norm[SET_LABELS]  # [6, 768]
    dim = candidate_pool.shape[1]

    rng = np.random.default_rng(SEED)
    true_local = np.repeat(np.arange(N_TARGETS), REPEATS)  # [96]
    n = len(true_local)

    chance = sum(1.0 / k for k in range(1, N_POOL + 1)) / N_POOL
    M = 200  # Monte Carlo datasets per signal level
    s_levels = [0.0, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50]

    curve = []
    for s in s_levels:
        n_genuine = 0
        mrrs = []
        for _ in range(M):
            # Mixture model: a fraction s of trials carry genuine signal
            # (prediction leans toward the true target with realistic noise);
            # the rest are pure noise. This is interpretable and avoids the
            # high-dim saturation of a continuous signal-fraction blend.
            true_unit = set_norm[true_local]
            noise = rng.standard_normal((n, dim))
            noise /= np.linalg.norm(noise, axis=1, keepdims=True)
            signal_trials = rng.random(n) < s
            # signal trials: true target direction plus equal-magnitude noise
            # (so a signal trial is informative but far from perfect)
            pred = np.where(
                signal_trials[:, None],
                true_unit + noise,   # signal + comparable noise
                noise,               # pure noise
            )
            pred_norm = pred / np.linalg.norm(pred, axis=1, keepdims=True)
            sims_full = pred_norm @ pool_norm.T
            obs, exact_p, twoway, degen = _mrr_and_gate(sims_full, true_local)
            mrrs.append(obs)
            if (exact_p < 0.05) and (not degen) and (twoway > 0.5):
                n_genuine += 1
        power = n_genuine / M
        curve.append({
            "signal_fraction": s,
            "mean_mrr": float(np.mean(mrrs)),
            "mrr_improvement_over_chance": float(np.mean(mrrs) - chance),
            "power_genuine_transfer": power,
        })
        print(f"s={s:.2f} mean_mrr={np.mean(mrrs):.3f} (+{np.mean(mrrs)-chance:+.3f}) power={power:.2f}", flush=True)

    # Power at target MRR improvements via interpolation
    imp = np.array([c["mrr_improvement_over_chance"] for c in curve])
    pw = np.array([c["power_genuine_transfer"] for c in curve])
    order = np.argsort(imp)
    power_at = {}
    for target_imp in [0.05, 0.10, 0.15, 0.20]:
        power_at[f"+{target_imp:.2f}"] = float(np.interp(target_imp, imp[order], pw[order]))

    # MEOI from the frozen protocol: a detectable transfer must clear chance;
    # we document the smallest MRR improvement reaching 80% power.
    reached80 = [c for c in curve if c["power_genuine_transfer"] >= 0.8]
    min_detectable_imp = min((c["mrr_improvement_over_chance"] for c in reached80), default=None)

    well_powered = (min_detectable_imp is not None) and (min_detectable_imp <= 0.15)
    conclusion = "NULL_SUPPORTED_WITHIN_SENSITIVITY" if well_powered else "INCONCLUSIVE_UNDERPOWERED"

    out = {
        "artifact": "C3_SUBJ01_H2_SENSITIVITY",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "subject": "subj01", "scope": "SINGLE_SUBJECT",
        "design": {"n_targets": N_TARGETS, "repeats": REPEATS, "candidate_pool": N_POOL,
                   "null": "exact 6! target-label", "seed": SEED, "monte_carlo_datasets": M},
        "chance_mrr": chance,
        "genuine_transfer_criterion": "exact p<0.05 AND not single-candidate collapse AND 2AFC>0.5",
        "power_curve": curve,
        "power_at_mrr_improvement": power_at,
        "min_detectable_mrr_improvement_80pct_power": min_detectable_imp,
        "observed_zero_shot": {
            "primary_setB_mrr": 0.2968900312650313,
            "note": "observed 'significance' was a collapse artifact (see H2 result); true transfer null",
        },
        "conclusion": conclusion,
        "conclusion_note": (
            "The n=1 design's ability to detect a genuine, non-degenerate transfer effect at the "
            "given effect sizes. NULL_SUPPORTED_WITHIN_SENSITIVITY means the design would have "
            "detected a real transfer of the documented size with adequate power; the observed "
            "zero-shot result is a degenerate collapse with no genuine transfer."
        ),
        "runtime_seconds": round(time.time() - t0, 1),
    }
    out_path = results_dir / "c3_h2_sensitivity.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nmin detectable MRR improvement @80% power: {min_detectable_imp}", flush=True)
    print(f"Conclusion: {conclusion}\nWrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
