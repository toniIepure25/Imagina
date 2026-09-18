"""ANIMUS-P1 benchmark campaign runner (design/product-only; NO human or neural data).

Runs the blind-target campaign across all baseline controllers, aggregates the acceptance metrics, and
writes the four result artifacts + the ANIMUS_P1_DECISION.json. Also runs the privacy and determinism
audits. Deterministic under fixed seeds; safe for CI (deterministic adapters only).
"""
from __future__ import annotations

import hashlib
import json
import os
import statistics as st
import sys

from app.core.animus.benchmark import SIMILARITY_THRESHOLD, run_campaign
from app.core.animus.candidate_generator import (
    DeterministicSceneGenerator,
    PrivacyViolation,
    assert_no_forbidden_content,
)
from app.core.animus.controller import AnimusActiveController, RandomController, StaticController
from app.core.animus.models import ImaginationBeliefState

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
OUT = os.path.join(ROOT, "results", "animus_p1")

ANIMUS = AnimusActiveController.name
RANDOM = RandomController.name
STATIC = StaticController.name


def _sh(o: dict) -> dict:
    o = dict(o)
    o.pop("self_hash", None)
    o["self_hash"] = hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()
    return o


def _median(xs):
    return float(st.median(xs)) if xs else 0.0


def _by_controller(trials: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for t in trials:
        out.setdefault(t["controller"], []).append(t)
    return out


def summarize(campaign: dict) -> dict:
    by = _by_controller(campaign["trials"])
    per = {}
    for c, ts in by.items():
        gains = [t["loop_gain"] for t in ts]
        finals = [t["final_similarity"] for t in ts]
        unc_dec = [t["uncertainty_before"] - t["uncertainty_after"] for t in ts]
        reached = [t for t in ts if t["iterations_to_threshold"] <= campaign["max_iterations"]]
        it2 = [t["iterations_to_threshold"] for t in reached]
        # censored iterations-to-threshold over ALL trials (non-reaching = max_iterations + 1). This is the
        # fair comparison: a controller that rarely reaches threshold is penalized, not flattered by
        # conditioning only on its easy wins.
        it2_censored = [t["iterations_to_threshold"] for t in ts]
        valid_frac = sum(1 for t in ts if t["valid"]) / len(ts)
        per[c] = {
            "n": len(ts),
            "median_loop_gain": _median(gains),
            "median_final_similarity": _median(finals),
            "median_uncertainty_reduction": _median(unc_dec),
            "valid_fraction": valid_frac,
            "reached_threshold_fraction": len(reached) / len(ts),
            "median_iterations_to_threshold_reached": _median(it2) if it2 else None,
            "median_iterations_to_threshold_censored": _median(it2_censored),
            "median_attribute_accuracy": _median([t["attribute_accuracy"] for t in ts]),
            "median_object_accuracy": _median([t["object_accuracy"] for t in ts]),
        }
    return per


def privacy_audit() -> dict:
    """Prove a generation payload cannot carry raw neural arrays / identifiers, and that the belief->spec
    bridge sanitizes. Tries several forbidden payloads and requires each to be rejected."""
    gen = DeterministicSceneGenerator()
    belief = ImaginationBeliefState.broad_prior()
    cset = gen.generate(belief, {"seed": 1, "n": 1})
    ok_clean = True
    try:
        assert_no_forbidden_content(cset.candidates[0].to_dict())
    except PrivacyViolation:
        ok_clean = False
    rejected = 0
    bad_payloads = [
        {"raw_neural": [0.1] * 10}, {"eeg": [1, 2, 3]}, {"participant_id": "sub-01"},
        {"medical": {"dob": "1990"}}, {"forward_operator": [[1, 0], [0, 1]]},
        {"embedding": list(range(1000))},
    ]
    for p in bad_payloads:
        try:
            assert_no_forbidden_content(p)
        except PrivacyViolation:
            rejected += 1
    return {"clean_payload_accepted": ok_clean, "forbidden_payloads_tested": len(bad_payloads),
            "forbidden_payloads_rejected": rejected,
            "pass": ok_clean and rejected == len(bad_payloads)}


def determinism_audit(n_targets: int = 8) -> dict:
    a = run_campaign(n_targets=n_targets, seed_families=(1,), controllers=[ANIMUS], max_iterations=8)
    b = run_campaign(n_targets=n_targets, seed_families=(1,), controllers=[ANIMUS], max_iterations=8)
    ha = [t["replay_hash"] for t in a["trials"]]
    hb = [t["replay_hash"] for t in b["trials"]]
    return {"n_trials": len(ha), "identical_replay_hashes": ha == hb,
            "campaign_hash": hashlib.sha256(json.dumps(ha, sort_keys=True).encode()).hexdigest()[:16],
            "pass": ha == hb}


def decide(per: dict, privacy: dict, determinism: dict) -> dict:
    a, r, s = per[ANIMUS], per[RANDOM], per[STATIC]
    gain_improvement = (a["median_loop_gain"] - r["median_loop_gain"]) / abs(r["median_loop_gain"]) \
        if r["median_loop_gain"] else float("inf")
    # fair (censored) iterations-to-threshold: non-reaching runs counted as max+1
    a_it = a["median_iterations_to_threshold_censored"]
    r_it = r["median_iterations_to_threshold_censored"]
    fewer_iters = a_it < r_it
    checks = {
        "animus_beats_static_gain": a["median_loop_gain"] > s["median_loop_gain"],
        "animus_beats_random_gain": a["median_loop_gain"] > r["median_loop_gain"],
        "valid_completed_loops_ge_95pct": a["valid_fraction"] >= 0.95,
        "median_loop_gain_positive": a["median_loop_gain"] > 0,
        "median_uncertainty_decreases": a["median_uncertainty_reduction"] > 0,
        "animus_gain_ge_20pct_better_than_random": gain_improvement >= 0.20,
        "animus_fewer_iters_than_random": fewer_iters,
        "privacy_invariant_pass": privacy["pass"],
        "deterministic_replay_pass": determinism["pass"],
    }
    all_pass = all(checks.values())
    decision = "ANIMUS_P1_VERTICAL_SLICE_PASS" if all_pass else "ANIMUS_P1_VERTICAL_SLICE_PARTIAL"
    return {"decision": decision, "all_checks_pass": all_pass, "checks": checks,
            "gain_improvement_over_random": round(float(gain_improvement), 4),
            "animus_median_iters_to_threshold": a_it, "random_median_iters_to_threshold": r_it}


def main(n_targets: int = 100, seed_families=(1, 2, 3)) -> int:
    os.makedirs(OUT, exist_ok=True)
    campaign = run_campaign(n_targets=n_targets, seed_families=seed_families, max_iterations=8)
    per = summarize(campaign)
    privacy = privacy_audit()
    determinism = determinism_audit()

    summary = {"artifact": "ANIMUS_P1_BENCHMARK_SUMMARY", "milestone": "ANIMUS-P1",
               "n_targets": n_targets, "seed_families": list(seed_families),
               "total_trials": len(campaign["trials"]), "similarity_threshold": SIMILARITY_THRESHOLD,
               "observation_mode": campaign["observation_mode"],
               "imaginer_params": campaign["imaginer_params"], "per_controller": per}
    comparison = {"artifact": "ANIMUS_P1_CONTROLLER_COMPARISON", "milestone": "ANIMUS-P1",
                  "baselines": list(per.keys()), "per_controller": per,
                  "note": "all baselines reported; no cherry-picking"}
    decision = {"artifact": "ANIMUS_P1_DECISION", "milestone": "ANIMUS-P1",
                "scientific_parent": "b3eca7c", **decide(per, privacy, determinism),
                "external_scientific_status": {
                    "imagery_reliability": "LIMITED cohort evidence (C3XAT-R1)",
                    "independent_replication": "not yet executed (C3XRA ready, not run)",
                    "content_decoder": "not validated", "geometry": "not authorized",
                    "neural_reconstruction": "not validated"},
                "claim_level_operating_ceiling": "L1_BEHAVIORAL_ASSISTED"}

    json.dump(_sh(summary), open(os.path.join(OUT, "benchmark_summary.json"), "w"), indent=2)
    json.dump(_sh(comparison), open(os.path.join(OUT, "controller_comparison.json"), "w"), indent=2)
    json.dump(_sh({"artifact": "ANIMUS_P1_PRIVACY_AUDIT", "milestone": "ANIMUS-P1", **privacy}),
              open(os.path.join(OUT, "privacy_audit.json"), "w"), indent=2)
    json.dump(_sh({"artifact": "ANIMUS_P1_DETERMINISM_AUDIT", "milestone": "ANIMUS-P1", **determinism}),
              open(os.path.join(OUT, "determinism_audit.json"), "w"), indent=2)
    json.dump(_sh(decision), open(os.path.join(OUT, "ANIMUS_P1_DECISION.json"), "w"), indent=2)

    print("=== ANIMUS-P1 benchmark ===")
    for c, m in per.items():
        print(f"{c:22s} gain={m['median_loop_gain']:.3f} final={m['median_final_similarity']:.3f} "
              f"reach={m['reached_threshold_fraction']:.2f} "
              f"it2thr={m['median_iterations_to_threshold_reached']}")
    print("decision:", decision["decision"], "| all_pass:", decision["all_checks_pass"])
    for k, v in decision["checks"].items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    return 0 if decision["all_checks_pass"] else 1


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    sys.exit(main(n_targets=n))
