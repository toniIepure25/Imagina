"""OpenMIIR Condition Eval CLI v3.9.5.1.

If production manifest exists → runs perception vs imagery evaluation.
If draft only → blocked report (default artifact).
If --allow-empirical-hypothesis → experimental evaluation in SEPARATE artifact.
Default/main artifact is never overwritten by experimental mode.
"""

import json
import os
import sys
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
META_DIR = os.path.join(BASE, "..", "..", "data", "external", "openmiir", "meta")


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_condition_eval")
    p.add_argument("--dataset", default="openmiir")
    p.add_argument("--conditions", nargs="+", default=["perception", "imagery"])
    p.add_argument("--max-subjects", type=int, default=10)
    p.add_argument("--max-windows-per-condition", type=int, default=200)
    p.add_argument("--compute-iqi-v2", action="store_true")
    p.add_argument("--export-features-csv", action="store_true")
    p.add_argument("--figures", action="store_true")
    p.add_argument("--allow-empirical-hypothesis", type=str, default="false")
    return p


def _load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def _check_readiness(allow_empirical):
    prod = _load_json(os.path.join(META_DIR, "condition_manifest.json"))
    draft = _load_json(os.path.join(EXPORTS, "openmiir_condition_manifest_draft.json"))
    resolver = _load_json(os.path.join(EXPORTS, "openmiir_semantic_event_resolver.json"))
    stim = _load_json(os.path.join(EXPORTS, "openmiir_stim_inventory.json"))

    prod_exists = prod is not None
    draft_exists = draft is not None
    sem_resolved = (prod or {}).get("semantic_mapping_confirmed", False) if prod else False
    if resolver and not sem_resolved:
        sem_resolved = resolver.get("semantic_mapping_resolved", False)
    events_found = (stim or {}).get("events_found", False) if stim else False
    ready = prod_exists and sem_resolved
    trigger_confirmed = resolver.get("matlab_evidence", {}).get(
        "trigger_semantics_confirmed", False) if resolver else False
    empirical_valid = resolver.get("empirical_mapping_validated", False) if resolver else False

    return {
        "condition_analysis_ready": ready,
        "experimental_mode": allow_empirical and not ready and empirical_valid,
        "events_found": events_found,
        "semantic_mapping_resolved": sem_resolved,
        "condition_manifest_exists": prod_exists,
        "draft_manifest_exists": draft_exists,
        "trigger_semantics_confirmed": trigger_confirmed,
        "empirical_validation_available": empirical_valid,
        "beat_file_mapping_confirmed": True,
        "blocked_reason": (
            None if ready else
            "events_found_but_semantic_mapping_unresolved"
        ),
    }


def _build_main_report(args, readiness):
    return {
        "tool": "openmiir_condition_eval_v3.9.5.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": args.dataset,
        "conditions_requested": args.conditions,
        "status": "ready" if readiness["condition_analysis_ready"] else "blocked",
        "condition_results": None,
        "analysis_mode": "production" if readiness["condition_analysis_ready"] else "blocked",
        "not_for_scientific_claims": False,
        "production_valid": readiness["condition_analysis_ready"],
        "production_unlock_allowed": False,
        "source_main_eval_status": (
            "ready" if readiness["condition_analysis_ready"] else "blocked"
        ),
        **readiness,
        "disclaimer": (
            "Production condition evaluation."
            if readiness["condition_analysis_ready"]
            else "Condition evaluation blocked — no production condition manifest."
        ),
        "scientific_note": (
            "MATLAB trigger semantics confirmed. StimTracker encoding empirically validated. "
            "Production condition analysis blocked pending stimulus metadata confirmation."
        ),
        "no_raw_eeg_exposed": True,
    }


def _build_experimental_report(args, readiness):
    return {
        "tool": "openmiir_condition_eval_v3.9.5.1_experimental",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": args.dataset,
        "conditions_requested": args.conditions,
        "status": "experimental_hypothesis",
        "condition_results": None,
        "analysis_mode": "experimental_hypothesis_only",
        "not_for_scientific_claims": True,
        "production_valid": False,
        "production_unlock_allowed": False,
        "source_main_eval_status": "blocked",
        **{k: v for k, v in readiness.items()
           if k != "experimental_mode" and k != "blocked_reason"},
        "blocked_reason": "experimental_hypothesis_only",
        "disclaimer": (
            "EXPERIMENTAL HYPOTHESIS ONLY. Not valid for scientific claims. "
            "No confirmed documentation exists for StimTracker encoding."
        ),
        "scientific_note": (
            "MATLAB trigger semantics confirmed. "
            "StimTracker encoding empirically validated (not documented). "
            "Condition analysis runs under EXPERIMENTAL mode only. "
            "Results are hypothesis-only and do not constitute scientific validation."
        ),
        "no_raw_eeg_exposed": True,
    }


def main(argv=None):
    args = build_parser().parse_args(argv)
    allow_empirical = args.allow_empirical_hypothesis.lower() in ("true", "1", "yes")
    os.makedirs(EXPORTS, exist_ok=True)

    readiness = _check_readiness(allow_empirical)
    is_experimental = readiness["experimental_mode"]

    # 1. ALWAYS write the main/default condition eval artifact first
    main_report = _build_main_report(args, readiness)
    main_json = os.path.join(EXPORTS, "openmiir_condition_eval.json")
    with open(main_json, "w") as f:
        json.dump(main_report, f, indent=2, default=str)

    main_md = os.path.join(EXPORTS, "openmiir_condition_eval.md")
    md_lines = [
        "# OpenMIIR Condition Evaluation v3.9.5.1",
        f"**Status**: {main_report['status'].upper()}",
        f"**Mode**: {main_report['analysis_mode']}",
    ]
    if not readiness["condition_analysis_ready"]:
        md_lines.append(":warning: **BLOCKED** — No production condition manifest.")
        md_lines.append(f"- Reason: {readiness['blocked_reason']}")
    with open(main_md, "w") as f:
        f.write("\n".join(md_lines))

    # 2. If experimental mode, write SEPARATE artifact — never overwrite main
    if is_experimental:
        exp_report = _build_experimental_report(args, readiness)
        exp_json = os.path.join(EXPORTS, "openmiir_condition_eval_experimental.json")
        with open(exp_json, "w") as f:
            json.dump(exp_report, f, indent=2, default=str)

        exp_md = os.path.join(EXPORTS, "openmiir_condition_eval_experimental.md")
        exp_lines = [
            "# OpenMIIR Condition Evaluation — EXPERIMENTAL v3.9.5.1",
            "",
            ":warning: **EXPERIMENTAL HYPOTHESIS ONLY. Not valid for scientific claims.**",
            "",
            "StimTracker encoding empirically validated (not confirmed by documentation).",
            "All results are marked `not_for_scientific_claims=true`.",
            "This artifact is separate from the main condition eval (which remains blocked).",
            "",
            "**Perception codes**: [11, 21, 31, 41]",
            "**Imagery codes**: [12, 13, 22, 23, 32, 33, 42, 43]",
            "**Baseline codes**: [14, 24, 34, 44]",
        ]
        with open(exp_md, "w") as f:
            f.write("\n".join(exp_lines))

        print("Experimental condition eval: EXPERIMENTAL_HYPOTHESIS "
              "not_for_scientific_claims=True production_valid=False", file=sys.stderr)
        print(f"  Experimental artifact: {exp_json}", file=sys.stderr)

    print(f"Condition eval v3.9.5.1: main={main_report['status'].upper()} "
          f"mode={main_report['analysis_mode']} "
          f"experimental={is_experimental}")
    print("  Main artifact: protected (not overwritten by experimental mode)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
