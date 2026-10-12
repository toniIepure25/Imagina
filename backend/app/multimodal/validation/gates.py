"""Scientific acceptance-gate records for real-data validation.

Criteria are declared in code (``Criterion``) and serialized into every result *before* metrics are compared, so a
reader can check that thresholds were not tuned to the outcome. Verdicts: PASS / FAIL / INCONCLUSIVE / BLOCKED.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

Verdict = Literal["PASS", "FAIL", "INCONCLUSIVE", "BLOCKED"]


@dataclass(frozen=True)
class Criterion:
    metric: str
    direction: Literal[">=", "<="]
    pass_threshold: float
    fail_threshold: float
    rationale: str

    def judge(self, value: float | None) -> Verdict:
        if value is None:
            return "INCONCLUSIVE"
        if self.direction == ">=":
            return "PASS" if value >= self.pass_threshold else ("FAIL" if value < self.fail_threshold
                                                               else "INCONCLUSIVE")
        return "PASS" if value <= self.pass_threshold else ("FAIL" if value > self.fail_threshold
                                                           else "INCONCLUSIVE")


@dataclass
class GateResult:
    experiment: str
    dataset: dict
    participants: dict
    task_and_labels: str
    design: str
    metric_definitions: dict
    criteria: list[Criterion]
    results: dict = field(default_factory=dict)
    baseline: dict = field(default_factory=dict)
    leakage_checks: dict = field(default_factory=dict)
    negative_controls: dict = field(default_factory=dict)
    generalization: dict = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    verdicts: dict = field(default_factory=dict)
    verdict: Verdict = "INCONCLUSIVE"
    blocked_reason: str = ""
    code_commit: str = ""
    created_at: str = ""

    def decide(self, values: dict[str, float | None]) -> Verdict:
        if self.blocked_reason:
            self.verdict = "BLOCKED"
            return self.verdict
        self.verdicts = {c.metric: c.judge(values.get(c.metric)) for c in self.criteria}
        vs = set(self.verdicts.values())
        self.verdict = "FAIL" if "FAIL" in vs else ("INCONCLUSIVE" if "INCONCLUSIVE" in vs else "PASS")
        return self.verdict

    def write(self, path: Path) -> Path:
        self.created_at = datetime.now(timezone.utc).isoformat()
        try:
            self.code_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        except Exception:  # noqa: BLE001
            self.code_commit = "unknown"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, default=_default))
        return path


def blocked(experiment: str, reason: str, **kw: Any) -> GateResult:
    g = GateResult(experiment=experiment, dataset=kw.get("dataset", {}), participants={}, task_and_labels="",
                   design="", metric_definitions={}, criteria=[], blocked_reason=reason)
    g.decide({})
    return g


def _default(o):
    import numpy as np

    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)
