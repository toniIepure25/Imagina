"""Collect phase-2 gate verdicts into results/phase2/SUMMARY.json (numbers for the reports come from here)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else "results/phase2")
summary = {}
for p in sorted(root.glob("*.json")):
    if p.name in ("SUMMARY.json",) or ".run1_" in p.name:
        continue
    d = json.loads(p.read_text())
    if "verdict" not in d:
        continue
    summary[d["experiment"]] = {
        "file": p.name, "verdict": d["verdict"], "verdicts": d.get("verdicts", {}),
        "criteria": [{k: c[k] for k in ("metric", "direction", "pass_threshold", "fail_threshold")}
                     for c in d.get("criteria", [])],
        "blocked_reason": d.get("blocked_reason", ""), "code_commit": d.get("code_commit", ""),
    }
(root / "SUMMARY.json").write_text(json.dumps(summary, indent=2))
for k, v in summary.items():
    print(f"{v['verdict']:13s} {k}  {v['verdicts']}")
