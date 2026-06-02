# IMAGINA V21 — Longitudinal Imagery Skill Tree + Mastery Progression Engine

## What V21 Adds

V21 turns guided imagery practice into a long-term skill development system. It tracks progress across nine imagery dimensions, assigns transparent skill levels (1-5), detects plateaus, unlocks milestones, recommends difficulty adjustments, generates weekly progress reports, and updates the curriculum based on actual session history.

## V20 vs V21

| | V20 | V21 |
|---|-----|-----|
| **Sessions** | Guided phase-by-phase | Same, now feeding skill model |
| **Progress** | Per-session report | Longitudinal skill tree (9 dims × 5 levels) |
| **Achievement** | None | 12 milestone types |
| **Plateau** | None | Plateau/regression detection |
| **Difficulty** | Adaptive feedback only | Data-driven difficulty policy |
| **Reports** | Session-level | Weekly progress reports |
| **Curriculum** | None | Automatic curriculum updates |

## Skill Tree (9 Branches × 5 Levels)

| Level | Name | Threshold | Min Sessions |
|-------|------|-----------|-------------|
| 1 | Foundation | Unlock ~0.40 | 3 |
| 2 | Control | Unlock ~0.55 | 5 |
| 3 | Stability Under Load | Unlock ~0.65 | 8 |
| 4 | Complex Integration | Unlock ~0.75 | 12 |
| 5 | Mastery / Transfer | Unlock ~0.85 | 16 |

## Unlock Progress Formula

```
unlock_progress = IQI×0.35 + current_score×0.25 + stability×0.15
                + confidence×0.15 + (1-fatigue)×0.10
```

## Longitudinal Skill Model

Tracks per dimension:
- current_score, baseline_score, delta_from_baseline
- trend (improving/stable/declining) via linear regression
- current_level (1-5), unlock_progress (0-1)
- plateau_risk (low/medium/high)
- avg IQI/PID, fatigue, effort, confidence

## Plateau Detection

Detects:
- dimension_plateau (6+ sessions, last 4 changes < 0.03)
- fatigue_plateau (avg fatigue ≥ 6/10)
- overtraining_risk (high fatigue + declining IQIs)
- Recommends interventions: category switch, difficulty reduction, rest

## Mastery Milestones (12)

first_guided_session, first_task_plan, level2 vividness/stability/detail, first level 3, consistency_5, consistency_10, fatigue managed, multisensory explorer, meta-control, plateau resolved

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /skill-tree` | 9 branches × 5 levels |
| `GET /skill-tree/{dimension}` | Single branch |
| `GET /skill-model/{uid}` | Build longitudinal model |
| `GET /mastery-milestones/{uid}` | Milestone achievements |
| `GET /plateaus/{uid}` | Plateau analysis |
| `POST /difficulty-recommendation/{uid}` | Difficulty policy |
| `POST /weekly-progress/{uid}` | Generate weekly report |
| `GET /weekly-progress/{uid}` | Latest weekly report |
| `POST /curriculum-update/{uid}` | Trigger curriculum update |
| `GET /curriculum-update/{uid}` | Latest curriculum update |

## Test Results

```
V21 SKILL TREE: 9 branches, 24 sessions, 9 dims with levels ✓
  8 milestones achieved, 4 pending ✓
  Plateau detected (high risk), difficulty=decrease ✓
  Weekly report: 18 sessions, IQI=0.57 ✓
  Curriculum: motion → vividness ✓
  Profile + safety: OK ✓

V13-V20 regression: ALL TESTS PASSED
ruff: clean, frontend: compiled, verify.sh: 7/8 pass
```

## Final Claim

> IMAGINA V21 turns guided imagery practice into a long-term skill development system: it tracks progress across nine imagery dimensions, assigns transparent skill levels, detects plateaus, unlocks milestones, recommends difficulty changes, generates weekly progress reports, and updates the curriculum from actual session history. It remains non-clinical, non-diagnostic, non-BCI, and not mind-reading.
