"""ANIMUS-P2-XR pre-outcome power / Type-I audit (§16).

Exercises the FROZEN, inherited decision machinery on synthetic data BEFORE any real replication outcome:
(a) the inherited subject gate (app.core.animus.p2.gate.subject_pass) on null vs signal subject-summary
draws, confirming Type-I control at the subject level; (b) the cross-dataset decision operating
characteristics under null / weak (NOD-like) / moderate / strong / heterogeneous per-subject effect rates.
No real neural data, no gate tuning. Writes results/animus_p2xr/power_audit.json (self-hashed).
"""
from __future__ import annotations

import hashlib
import json
import os

import numpy as np

from app.core.animus.p2.gate import subject_pass
from app.research.animus_p2xr.decision import PASS, cross_dataset_decision, dataset_status

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
OUT = os.path.join(ROOT, "results", "animus_p2xr")
SEED = 20260909
N_BOLD5000 = 4
N_THINGS = 3


def _subject_summary(rng, is_signal: bool) -> dict:
    """A synthetic per-subject result dict shaped like the confirmatory output, drawn under a null or a
    genuine-signal generative model. Only fields the inherited subject gate reads are modeled."""
    if is_signal:
        m = float(rng.normal(0.08, 0.02))
        perm_p = float(rng.uniform(0.0, 0.005))
        ci_lo = float(m - abs(rng.normal(0.02, 0.005)))
        seeds_pos = True
    else:
        m = float(rng.normal(0.0, 0.003))
        perm_p = float(rng.uniform(0.05, 1.0))
        ci_lo = float(rng.normal(-0.002, 0.004))
        seeds_pos = m > 0 and rng.random() < 0.15
    return {"data_contract_pass": True, "atlas_qc_pass": True, "margin_M": m,
            "permutation_p": perm_p, "bootstrap_ci_lower": ci_lo, "all_seeds_positive": bool(seeds_pos)}


def _simulate(rng, p_bold: float, p_things: float, n_iter: int = 4000) -> dict:
    outcomes = {PASS: 0, "ANIMUS_P2XR_INDEPENDENT_REPLICATION_LIMITED": 0,
                "ANIMUS_P2XR_INDEPENDENT_REPLICATION_FAIL": 0}
    for _ in range(n_iter):
        b = [_subject_summary(rng, rng.random() < p_bold) for _ in range(N_BOLD5000)]
        t = [_subject_summary(rng, rng.random() < p_things) for _ in range(N_THINGS)]
        ds = {"ds001499": dataset_status(b, N_BOLD5000), "ds004192": dataset_status(t, N_THINGS)}
        outcomes[cross_dataset_decision(ds)] += 1
    return {k: v / n_iter for k, v in outcomes.items()}


def main() -> int:
    rng = np.random.default_rng(SEED)

    # (a) subject-gate Type-I / sensitivity on 20000 draws each
    n = 20000
    null_pass = sum(subject_pass(_subject_summary(rng, False)) for _ in range(n)) / n
    sig_pass = sum(subject_pass(_subject_summary(rng, True)) for _ in range(n)) / n

    # (b) cross-dataset operating characteristics
    scenarios = {
        "null": (0.0, 0.0),
        "weak_nod_like_0.33": (0.33, 0.33),
        "moderate_0.5": (0.5, 0.5),
        "strong_0.8": (0.8, 0.8),
        "heterogeneous_bold0.6_things0.1": (0.6, 0.1),
    }
    sim = {name: _simulate(rng, pb, pt) for name, (pb, pt) in scenarios.items()}

    audit = {
        "artifact": "ANIMUS_P2XR_POWER_AUDIT", "milestone": "ANIMUS-P2XR", "seed": SEED,
        "n_bold5000": N_BOLD5000, "n_things": N_THINGS,
        "subject_gate": {"null_pass_rate": round(null_pass, 5), "signal_pass_rate": round(sig_pass, 5)},
        "cross_dataset_operating_characteristics": sim,
        "checks": {
            "subject_type_i_below_0.01": null_pass < 0.01,
            "subject_sensitivity_above_0.8": sig_pass > 0.8,
            "null_cross_pass_rate_below_0.001": sim["null"][PASS] < 0.001,
            "heterogeneous_single_dataset_never_pass": sim["heterogeneous_bold0.6_things0.1"][PASS] < 0.02,
            "strong_effect_pass_rate_above_0.5": sim["strong_0.8"][PASS] > 0.5,
        },
    }
    audit["all_checks_pass"] = all(audit["checks"].values())
    h = dict(audit)
    h.pop("self_hash", None)
    audit["self_hash"] = hashlib.sha256(json.dumps(h, sort_keys=True, default=str).encode()).hexdigest()
    os.makedirs(OUT, exist_ok=True)
    json.dump(audit, open(os.path.join(OUT, "power_audit.json"), "w"), indent=2)
    print("subject null_pass", round(null_pass, 5), "signal_pass", round(sig_pass, 5))
    for k, v in sim.items():
        print(f"  {k}: {v}")
    print("all_checks_pass", audit["all_checks_pass"])
    return 0 if audit["all_checks_pass"] else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
