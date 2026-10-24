"""Provenance and longitudinal reliability for the Scene Threshold observatory.

The observatory is descriptive. It shows which variables were directly probed, which remained at the
prior, how much a single source changes a posterior, and whether estimates are stable across
occasions. It does not explain *why* a memory looks the way it does and it does not produce a composite
score.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from app.core.animus.studio.epistemic import (
    EpistemicBelief,
    EpistemicProbe,
    init_belief,
    update_belief,
)
from app.core.animus.studio.sdt import test_retest

PROVENANCE_VALUES = ("direct_probe", "prior", "abstained", "mixed")


def _replay(probes: Sequence[EpistemicProbe], records: Sequence[Mapping[str, Any]],
            skip_index: int | None = None) -> EpistemicBelief:
    belief = init_belief(tuple(probes))
    by_id = {probe.probe_id: probe for probe in probes}
    for index, record in enumerate(records):
        if skip_index is not None and index == skip_index:
            continue
        probe = by_id.get(str(record.get("probe_id") or ""))
        if probe is None:
            continue
        belief = update_belief(
            belief,
            probe,
            choice=str(record.get("choice") or ""),
            confidence=float(record.get("confidence") or 0.5),
            abstained=bool(record.get("abstained")),
        )
    return belief


def _uncertainty(probability: float) -> float:
    return round(1.0 - abs(2.0 * probability - 1.0), 6)


def _provenance(records: Sequence[tuple[int, Mapping[str, Any]]]) -> str:
    answered = [record for _, record in records if not bool(record.get("abstained"))]
    abstained = [record for _, record in records if bool(record.get("abstained"))]
    if answered and abstained:
        return "mixed"
    if answered:
        return "direct_probe"
    if abstained:
        return "abstained"
    return "prior"


def _evidence_label(probe: EpistemicProbe) -> str:
    if probe.probe_type == "spatial_relation":
        subject = probe.metadata.get("subject_label") or "subject"
        obj = probe.metadata.get("object_label") or "object"
        return f"{subject} / {obj}"
    return str(probe.metadata.get("label") or probe.variable_id)


def _dependence_group(probe: EpistemicProbe) -> str:
    if probe.probe_type == "object_presence":
        return probe.variable_id
    subject = probe.metadata.get("subject_id") or "subject"
    obj = probe.metadata.get("object_id") or "object"
    return f"pair:{subject}:{obj}"


def build_evidence(probes: Sequence[EpistemicProbe], belief: EpistemicBelief,
                   records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_probe: dict[str, list[tuple[int, Mapping[str, Any]]]] = {}
    for index, record in enumerate(records):
        probe_id = str(record.get("probe_id") or "")
        if probe_id:
            by_probe.setdefault(probe_id, []).append((index, record))
    evidence: list[dict[str, Any]] = []
    for probe in probes:
        direct = by_probe.get(probe.probe_id, [])
        probability = belief.probability(probe.variable_id)
        deltas: list[float] = []
        for index, record in direct:
            if bool(record.get("abstained")):
                continue
            try:
                without = _replay(probes, records, index)
            except (ValueError, TypeError):
                continue
            deltas.append(abs(probability - without.probability(probe.variable_id)))
        sources = [
            {
                "probe_id": probe.probe_id,
                "probe_type": probe.probe_type,
                "choice": record.get("choice") or "",
                "confidence": record.get("confidence"),
                "abstained": bool(record.get("abstained")),
                "information_gain": record.get("information_gain"),
                "created_at": record.get("created_at"),
            }
            for _, record in direct
        ]
        evidence.append({
            "variable_id": probe.variable_id,
            "label": _evidence_label(probe),
            "probe_type": probe.probe_type,
            "provenance": _provenance(direct),
            "posterior": round(probability, 6),
            "uncertainty": _uncertainty(probability),
            "n_sources": len(direct),
            "leave_one_out_delta": round(max(deltas), 6) if deltas else 0.0,
            "dependence_group": _dependence_group(probe),
            "sources": sources,
        })
    return evidence


def build_reliability(contrasts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    completed = [
        item for item in contrasts
        if item.get("status") == "completed" and isinstance(item.get("result"), Mapping)
    ]
    occasions = [
        {
            "contrast_id": item.get("contrast_id"),
            "occasion": item.get("occasion") or "baseline",
            "form_id": item.get("form_id") or "A",
            "completed_at": item.get("completed_at"),
            "dprime": (item.get("result") or {}).get("dprime"),
            "thresholds": (item.get("result") or {}).get("thresholds") or {},
        }
        for item in completed
    ]
    if len(occasions) < 2:
        return {
            "status": "insufficient",
            "reason": "fewer than two completed occasions",
            "n_occasions": len(occasions),
            "occasions": occasions,
            "r": None,
            "r_ci": None,
            "sem": None,
            "mdc95": None,
            "mean_change": None,
            "dprime_change": None,
        }
    baseline = next(
        (item for item in occasions if item.get("occasion") == "baseline"), occasions[0])
    follow_up = next(
        (item for item in reversed(occasions) if item.get("occasion") == "follow_up"),
        occasions[-1],
    )
    first = {key: float(value["threshold"]) for key, value in
             (baseline.get("thresholds") or {}).items()
             if isinstance(value, Mapping) and value.get("threshold") is not None
             and not value.get("censored")}
    second = {key: float(value["threshold"]) for key, value in
              (follow_up.get("thresholds") or {}).items()
              if isinstance(value, Mapping) and value.get("threshold") is not None
              and not value.get("censored")}
    reliability = test_retest(first, second)
    reliability.update({
        "n_occasions": len(occasions),
        "occasions": occasions,
        "dprime_change": (
            round(float(follow_up["dprime"]) - float(baseline["dprime"]), 6)
            if baseline.get("dprime") is not None and follow_up.get("dprime") is not None
            else None
        ),
        "note": ("Pearson r is reported only when at least three aligned feature estimates exist; "
                 "otherwise the occasion change is descriptive only."),
    })
    return reliability


def build_observatory(*, session_id: str, source_version_id: str, scene_hash: str,
                      reconstruction: Mapping[str, Any], evidence: Sequence[Mapping[str, Any]],
                      discrimination: Mapping[str, Any],
                      reliability: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "source_version_id": source_version_id,
        "scene_hash": scene_hash,
        "belief": {
            "objects": list(reconstruction.get("objects") or []),
            "relations": list(reconstruction.get("relations") or []),
            "uncertainty": dict(reconstruction.get("uncertainty") or {}),
            "scores": dict(reconstruction.get("scores") or {}),
            "protocol_version": reconstruction.get("protocol_version"),
            "scoring_version": reconstruction.get("scoring_version"),
        },
        "evidence": list(evidence),
        "discrimination": dict(discrimination),
        "reliability": dict(reliability),
        "boundaries": [
            "The observatory describes behavioural evidence, not neural content or imagery strength.",
            "Provenance is a record of model inputs, not a causal explanation of memory.",
            "No composite score, percentile, diagnosis, or training claim is produced.",
        ],
    }


__all__ = [
    "PROVENANCE_VALUES",
    "build_evidence",
    "build_reliability",
    "build_observatory",
]
