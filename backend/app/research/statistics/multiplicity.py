"""Multiplicity correction for confirmatory endpoint analysis."""
from __future__ import annotations

from typing import Any


def holm_correction(p_values: list[tuple[str, float]], alpha: float = 0.05) -> list[dict[str, Any]]:
    """Apply Holm-Bonferroni correction to a list of (name, p_value) pairs."""
    n = len(p_values)
    sorted_pairs = sorted(p_values, key=lambda x: x[1])

    results: list[dict[str, Any]] = []
    rejected_so_far = True
    for i, (name, p) in enumerate(sorted_pairs):
        adjusted_alpha = alpha / (n - i)
        significant = rejected_so_far and p <= adjusted_alpha
        if not significant:
            rejected_so_far = False
        results.append({
            "endpoint": name,
            "raw_p": round(p, 6),
            "adjusted_alpha": round(adjusted_alpha, 6),
            "rank": i + 1,
            "significant": significant,
            "classification": "confirmatory",
        })

    return results


def classify_endpoints(
    primary_p: float,
    secondary_p_values: list[tuple[str, float]],
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Apply hierarchical testing: primary first, then secondary with Holm."""
    primary_significant = primary_p <= alpha

    secondary_results: list[dict[str, Any]] = []
    if primary_significant and secondary_p_values:
        secondary_results = holm_correction(secondary_p_values, alpha)
    elif secondary_p_values:
        secondary_results = [
            {"endpoint": name, "raw_p": round(p, 6), "significant": False,
             "classification": "exploratory_due_to_primary_ns"}
            for name, p in secondary_p_values
        ]

    return {
        "primary": {
            "p_value": round(primary_p, 6),
            "significant": primary_significant,
            "alpha": alpha,
        },
        "secondary": secondary_results,
        "procedure": "hierarchical_holm",
    }
