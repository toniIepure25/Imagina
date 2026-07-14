"""Sensitivity and robustness analyses."""
from __future__ import annotations

from typing import Any

from app.research.statistics.confirmatory import AnalysisResult, run_primary_analysis


def run_sensitivity_analyses(
    trial_data: list[dict[str, Any]],
) -> dict[str, AnalysisResult]:
    """Run the suite of prespecified sensitivity analyses."""
    results: dict[str, AnalysisResult] = {}

    results["primary"] = run_primary_analysis(trial_data)

    no_carryover = [t for t in trial_data if t.get("carryover_indicator", "none") == "none"]
    if no_carryover:
        results["without_carryover"] = run_primary_analysis(no_carryover, estimand_id="sensitivity_no_carryover")

    results["with_carryover"] = run_primary_analysis(trial_data, estimand_id="sensitivity_with_carryover")

    complete = _complete_cases(trial_data)
    if complete:
        results["complete_case"] = run_primary_analysis(complete, estimand_id="sensitivity_complete_case")

    neg_control = [t for t in trial_data if t.get("is_perceptual_control", False)]
    if neg_control:
        results["negative_control"] = run_primary_analysis(neg_control, estimand_id="negative_control")

    subjective = [
        {**t, "composite_error": t.get("vividness", 4.0)} for t in trial_data if "vividness" in t
    ]
    if subjective:
        results["subjective_vividness"] = run_primary_analysis(subjective, estimand_id="subjective_secondary")

    return results


def _complete_cases(trial_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter to participants with data in all conditions."""
    from collections import defaultdict
    by_pid: dict[str, set[str]] = defaultdict(set)
    for t in trial_data:
        by_pid[t["participant_id"]].add(t["condition"])

    complete_pids = {pid for pid, conds in by_pid.items() if len(conds) >= 3}
    return [t for t in trial_data if t["participant_id"] in complete_pids]
