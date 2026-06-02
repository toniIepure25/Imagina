# IMAGINA V18 — Evidence Dashboard + Research Export Pack

## What V18 Adds

V18 turns IMAGINA from a controlled personal experiment engine into a research evidence platform. It collects all evidence across calibration, adaptive plans, optimized plans, execution history, N-of-1 experiments, fatigue/adherence, and PID trends, then generates a unified evidence model, quality audit, timeline, recommendations, and an exportable thesis/portfolio-ready research package.

## V17 vs V18

| | V17 | V18 |
|---|-----|-----|
| **Evidence** | Per-experiment analysis | Unified evidence model across all data |
| **Quality** | Experiment-level scoring | System-wide quality audit (0-100) |
| **Timeline** | None | Chronological evidence event timeline |
| **Recommendations** | None | Evidence-based next research action |
| **Export** | None | 8-file research export pack |

## Evidence Architecture

```
All IMAGINA Data
    │
    ├─→ Unified Evidence Model
    │   · Data inventory (calibrations, plans, executions, experiments)
    │   · PID summary (first/latest/trend)
    │   · Training summary (best/worst focus, fatigue/adherence risk)
    │   · Experiment summary (direction, evidence score)
    │   · Evidence status: insufficient / exploratory / promising / strong
    │
    ├─→ Evidence Quality Auditor
    │   · Score: 0-100
    │   · Checks: calibration, execution, experiment, checkpoints, fatigue, safety
    │   · Categories: weak / usable / good / strong
    │
    ├─→ Evidence Timeline Builder
    │   · All events sorted chronologically
    │   · Types: calibration, plan, execution, experiment, export
    │
    ├─→ Research Recommendation Engine
    │   · Actions: calibrate, execute, experiment, repeat, reduce_fatigue, export
    │   · Priority: low/medium/high
    │   · Blocks export flag
    │
    └─→ Research Export Pack
        · 8 files: evidence_model, quality_audit, personal_summary,
          experiment_summary, safe_claims, limitations, methods, README
```

## Evidence Status Categories

| Status | Criteria |
|--------|----------|
| insufficient | < 3 calibrations or no completed executions |
| exploratory | Calibrations + executions, no completed N-of-1 |
| promising_personal | N-of-1 with evidence score ≥ 50 |
| strong_personal | ≥ 2 N-of-1 experiments, consistent optimized_better, score ≥ 70 |

## Quality Audit Components

| Check | Max Score |
|-------|-----------|
| Calibration completeness | 20 |
| Execution completeness | 20 |
| Experiment completeness | 25 |
| Checkpoint completeness | 15 |
| Fatigue/adherence control | 10 |
| Report/export readiness | 10 |

Critical issues cap score at 50.

## Export Pack Contents

```
research_exports/{user_id}/{timestamp}_{id}/
  evidence_model.json          — Unified evidence summary
  evidence_quality_audit.json  — Quality score + check results
  personal_summary.md          — Human-readable personal summary
  experiment_summary.md        — N-of-1 experiment results
  safe_claims.md               — Allowed + forbidden claims
  limitations.md               — Inherent system limitations
  methods.md                   — Explanation of methods
  README.md                    — Overview, usage, safety boundary
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/evidence/{user_id}/model` | GET | Unified evidence model |
| `/evidence/{user_id}/quality-audit` | GET | Evidence quality audit |
| `/evidence/{user_id}/timeline` | GET | Evidence timeline |
| `/evidence/{user_id}/recommendation` | GET | Next research action |
| `/evidence/{user_id}/export-pack` | POST | Generate research export pack |

## UI Panels

### EvidenceDashboardPanel (New)
- Evidence status badge
- Quality score + category
- Data inventory grid (calibrations, plans, executions, experiments)
- PID change + trend indicators
- Recent timeline preview (last 5 events)
- Critical issue warnings
- Research recommendation with why/priority
- Export Research Pack button

### EvidenceQualityPanel (New)
- Quality score display with category color
- Passed checks (green checks)
- Warnings (amber warnings)
- Critical issues (red crosses)
- Recommended next actions

### EvidenceTimelinePanel (New)
- Compact chronological event list
- Event type icons (C/E/X/P)
- Title + event type + summary
- Date stamps
- Up to 10 most recent events

## Test Results

```
V18 EVIDENCE DASHBOARD: ALL TESTS PASSED
  Evidence model: status=exploratory, 10 calibrations, 2 executions, 1 experiment ✓
  Quality audit: 70/100 (good), 6 passed, 0 warnings, 0 critical ✓
  Timeline: 15 events ✓
  Recommendation: evidence_sufficient_for_portfolio_demo (low priority) ✓
  Export pack: 8 files verified on disk ✓
  Profile evidence_summary: ✓
  Sparse user: insufficient ✓
  No raw EEG in export: ✓
  Safety flags: All OK ✓

V13/V14/V15/V16/V17 regression: ALL TESTS PASSED
ruff: clean, frontend: compiled, verify.sh: 7/8 pass
```

## Final Claim

> IMAGINA V18 turns the controlled personal experiment system into a research evidence platform: it summarizes all calibration, execution, optimization, and N-of-1 experiment data into a unified evidence model, audits evidence quality, builds a timeline, recommends next research actions, and exports a thesis/portfolio-ready research pack. It remains non-clinical, non-diagnostic, non-BCI, and not mind-reading.
