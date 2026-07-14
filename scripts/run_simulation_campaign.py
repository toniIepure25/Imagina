#!/usr/bin/env python3
"""Run the research-mode simulation campaign.

Usage:
    python scripts/run_simulation_campaign.py [--replicates 1000] [--batch 100] [--output results/campaign.json]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.research.simulation_campaign import (
    CORE_SCENARIOS,
    campaign_hash,
    run_full_campaign,
)


def _fmt(v, digits=4):
    if v is None:
        return "N/A"
    return f"{v:.{digits}f}"


def main():
    parser = argparse.ArgumentParser(description="Run simulation campaign")
    parser.add_argument("--replicates", type=int, default=1000)
    parser.add_argument("--batch", type=int, default=100)
    parser.add_argument("--participants", type=int, default=18)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--scenarios", type=str, nargs="*", default=None)
    parser.add_argument("--persist", action="store_true", help="Persist results to DB")
    args = parser.parse_args()

    scenarios = CORE_SCENARIOS
    if args.scenarios:
        scenarios = {k: v for k, v in CORE_SCENARIOS.items() if k in args.scenarios}

    def checkpoint(bs):
        print(f"  Batch {bs.batch_index}: {bs.scenario_id} "
              f"valid={bs.n_valid}/{bs.n_iterations} "
              f"type_i={_fmt(bs.type_i_error)} power={_fmt(bs.power)} "
              f"coverage={_fmt(bs.coverage)} ({bs.elapsed_s:.1f}s)")

    print(f"Starting campaign: {args.replicates} replicates, "
          f"{len(scenarios)} scenarios, batch_size={args.batch}")
    print(f"Scenarios: {', '.join(scenarios.keys())}")
    print()

    result = run_full_campaign(
        total_replicates=args.replicates,
        batch_size=args.batch,
        n_participants=args.participants,
        base_seed=args.seed,
        scenarios=scenarios,
        checkpoint_callback=checkpoint,
    )

    print()
    print("=" * 72)
    print(f"Campaign: {result.campaign_id}")
    print(f"Total replicates: {result.total_replicates}")
    print(f"Elapsed: {result.elapsed_s:.1f}s")
    print(f"Overall pass: {result.overall_pass}")
    print()

    for sid, ss in result.scenario_summaries.items():
        status = "PASS" if ss.calibration_pass else "FAIL"
        valid_str = f"valid={ss.n_valid_replicates}/{ss.total_replicates}"
        print(f"[{status}] {sid}: ({valid_str})")
        print(f"  oracle={_fmt(ss.oracle_effect, 6)} (SE={_fmt(ss.oracle_se, 6)})")
        print(f"  type_i={_fmt(ss.type_i_error)} (SE={_fmt(ss.type_i_se)})")
        print(f"  power={_fmt(ss.power)} (SE={_fmt(ss.power_se)})")
        print(f"  bias={_fmt(ss.bias, 6)} (SE={_fmt(ss.bias_se, 6)})")
        print(f"  rmse={_fmt(ss.rmse, 6)}")
        print(f"  coverage={_fmt(ss.coverage)} (SE={_fmt(ss.coverage_se)})")
        print(f"  convergence={_fmt(ss.convergence_rate)}")
        print(f"  fallback={_fmt(ss.fallback_rate)}")
        print(f"  valid_inference={_fmt(ss.valid_inference_rate)}")
        print(f"  neg_control_fp={_fmt(ss.negative_control_fp_rate)}")
        if ss.issues:
            for issue in ss.issues:
                print(f"  ISSUE: {issue}")
        print()

    if result.gate_issues:
        print("GATE ISSUES:")
        for issue in result.gate_issues:
            print(f"  - {issue}")

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        print(f"\nResults saved to: {args.output}")
        print(f"Campaign hash: {campaign_hash(result)}")

    if args.persist:
        import asyncio
        asyncio.run(_persist_campaign(result))
        print("Campaign persisted to DB.")

    return 0 if result.overall_pass else 1


async def _persist_campaign(result):
    from app.storage.database import get_db, init_db

    await init_db()
    db = await get_db()
    try:
        await db.execute(
            """INSERT OR REPLACE INTO simulation_runs
               (study_id, scenario_id, mode, n_iterations, n_participants, base_seed,
                status, started_at, completed_at)
               VALUES (?, 'campaign', 'research', ?, 0, 0, 'completed',
                       datetime('now'), datetime('now'))""",
            (result.campaign_id, result.total_replicates),
        )
        campaign_json = json.dumps(result.to_dict(), default=str)
        await db.execute(
            """INSERT OR REPLACE INTO simulation_summaries
               (run_id, summary_json)
               VALUES ((SELECT id FROM simulation_runs WHERE study_id = ?), ?)""",
            (result.campaign_id, campaign_json),
        )
        await db.commit()
    finally:
        await db.close()


if __name__ == "__main__":
    sys.exit(main())
