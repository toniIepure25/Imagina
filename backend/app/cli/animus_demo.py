"""ANIMUS-P1 seeded demo — a reviewer should understand the product in under five minutes.

    python -m app.cli.animus_demo --mode blind-benchmark
    python -m app.cli.animus_demo --mode imagination-amplifier
    python -m app.cli.animus_demo --mode synthetic-neural
    python -m app.cli.animus_demo --mode behavioral-only

Every mode runs the full closed loop and prints a replayable result. No human/neural data; deterministic.
"""
from __future__ import annotations

import argparse

from app.core.animus.benchmark import make_target, run_trial
from app.core.animus.models import SOURCE_SIMULATED_NEURAL
from app.core.animus.sdk import animus


def _flagship(observation_mode):
    """Flagship: hidden target 'a stone castle at night, in fog, with a red moon'. The controller never
    sees it; the evaluator reports similarity progression."""
    target = make_target(0, seed=1)
    target.label = "stone_castle_night_fog_red_moon"
    for c in ("STATIC", "RANDOM", "ANIMUS_ACTIVE"):
        r = run_trial(c, target, trial_seed=1, max_iterations=8, observation_mode=observation_mode)
        series = " -> ".join(f"v{i}:{s:.2f}" for i, s in enumerate(r.similarity_series))
        print(f"  {c:16s} {series}")
        print(f"      final={r.final_similarity:.3f} gain={r.loop_gain:.3f} "
              f"attr_acc={r.attribute_accuracy:.2f} reach_iter={r.iterations_to_threshold} "
              f"replay={r.replay_hash[:10]}")


def _amplifier():
    """Interactive amplifier (MODE A): a scripted user refines a candidate; no hidden target/similarity."""
    s = animus.start(mode="amplifier", controller="ANIMUS_ACTIVE", seed=7)
    s.generate(n=1)
    print("  v0 scene:", s.state()["scene_graph"]["attributes"])
    for direction in ("more_blue", "darker", "more_detailed", "more_depth", "wider"):
        s.feedback(channel="attribute_correction", direction=direction)
    s.feedback(channel="object_correction", object="castle", op="add")
    s.feedback(channel="object_correction", object="moon", op="add")
    st = s.state()
    print("  v1 scene:", st["scene_graph"]["attributes"], "objects:", st["scene_graph"]["objects"])
    print("  global_uncertainty:", st["global_uncertainty"], "| claim:", st["claim_label"])
    print("  replay:", s.replay()["final_belief_hash"][:12])
    s.complete()


def main():
    ap = argparse.ArgumentParser(description="ANIMUS-P1 demo")
    ap.add_argument("--mode", default="blind-benchmark",
                    choices=["blind-benchmark", "imagination-amplifier", "synthetic-neural",
                             "behavioral-only"])
    args = ap.parse_args()
    print(f"=== ANIMUS-P1 demo :: {args.mode} ===")
    if args.mode == "imagination-amplifier":
        _amplifier()
    elif args.mode == "behavioral-only":
        _flagship(observation_mode=None)
    else:  # blind-benchmark or synthetic-neural
        _flagship(observation_mode=SOURCE_SIMULATED_NEURAL)
    print("done (deterministic; no human or neural data).")


if __name__ == "__main__":
    main()
