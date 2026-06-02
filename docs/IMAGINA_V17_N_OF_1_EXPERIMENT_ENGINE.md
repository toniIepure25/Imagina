# IMAGINA V17 — Controlled N-of-1 Experiment Engine

## What V17 Adds

V17 turns IMAGINA from an adaptive optimizer into a controlled personal experiment platform. V16 could say "based on your history, this focus seems best." V17 answers: "does this optimized plan actually outperform your baseline plan under a structured controlled personal experiment?"

## V16 vs V17

| | V16 | V17 |
|---|-----|-----|
| **Analysis** | Response model per focus | Controlled experiment analysis |
| **Control** | None | Baseline vs treatment conditions |
| **Design** | None | AB, BA, ABAB, randomized, dose-response |
| **Evidence** | Response scores | Evidence score (0-100) + category |
| **Claims** | Best/worst focus | Safe claim + forbidden claims list |
| **Reporting** | Optimization summary | N-of-1 experiment report (JSON + MD) |

## Experiment Architecture

```
V16 Optimized Plan + V14 Baseline Plan
             │
    design_n_of_1_experiment(AB, 14 days)
             │
    ┌─────────────────────────────────┐
    │  Block 1: Baseline (days 1-7)   │
    │  Calibration checkpoint (day 1) │
    │  Daily check-ins                │
    ├─────────────────────────────────┤
    │  Block 2: Optimized (days 8-14) │
    │  Calibration checkpoint (day 8) │
    │  Daily check-ins                │
    ├─────────────────────────────────┤
    │  Final Calibration (day 15)     │
    └─────────────────────────────────┘
             │
    analyze_n_of_1_experiment()
    → direction: optimized_better/baseline_better/inconclusive
    → confounds: fatigue_difference, adherence_difference
    → confidence: low/medium/high
             │
    compute_n_of_1_evidence_score()
    → evidence_score: 0-100
    → category: weak / exploratory / promising / strong / very strong
             │
    generate_n_of_1_experiment_report()
    → JSON + Markdown reports
```

## Supported Designs

| Design | Blocks | Strength Score | Description |
|--------|--------|---------------|-------------|
| AB | 2 | 6/15 | Week 1 baseline, week 2 optimized |
| BA | 2 | 6/15 | Week 1 optimized, week 2 baseline |
| ABAB | 4 | 12/15 | 4 alternating blocks |
| randomized_blocks | 4 | 15/15 | Randomly ordered blocks |
| dose_response | 3 | 10/15 | Low/normal/high intensity |

## Experiment Lifecycle

1. **Design** — `design_n_of_1_experiment(user_id, experiment_type, design, duration_days)`
2. **Start** — `start_n_of_1_experiment(user_id, experiment_id)`
3. **Execute** — `complete_experiment_day()` for each day
4. **Calibrate** — `attach_experiment_calibration()` for checkpoint days
5. **Close** — `close_n_of_1_experiment(user_id, experiment_id)`
6. **Analyze** — `analyze_n_of_1_experiment()` → direction, confounds, confidence
7. **Score** — `compute_n_of_1_evidence_score()` → 0-100 with components
8. **Report** — `generate_n_of_1_experiment_report()` → JSON + Markdown

## Evidence Score Formula (0-100)

| Component | Max | Description |
|-----------|-----|-------------|
| PID effect strength | 35 | abs(pid_delta_advantage) × 200, capped |
| Adherence quality | 20 | avg adherence × 20 |
| Fatigue control | 15 | 15 - (max_fatigue × 2), floor 0 |
| Checkpoint completeness | 15 | calibration checkpoints / total days × 15 |
| Design strength | 15 | AB/BA=6, ABAB=12, randomized=15, dose_response=10 |
| Confound penalty | -10 | -3 per confound detected |

## Evidence Categories

| Score | Category | Meaning |
|-------|----------|---------|
| 86-100 | very_strong_personal_signal | Interesting personal observation — not clinical validation |
| 71-85 | strong_personal_signal | Results consistent with personal benefit |
| 51-70 | promising_personal_signal | More sessions would strengthen confidence |
| 31-50 | exploratory_signal | Suggestive but not conclusive |
| 0-30 | weak_evidence | Normal for early exploratory work |

## Eligibility Criteria

- At least 2 completed PID v2 calibration sessions
- Baseline adaptive plan exists
- Optimized plan exists (auto-generated if missing)
- Average fatigue < 8/10
- Average adherence ≥ 0.4

## Outcome Directions

- **strong_optimized_signal**: PID_delta > 0.10 (optimized PID decreased more)
- **optimized_better**: PID_delta > 0.05
- **baseline_better**: PID_delta < -0.05
- **inconclusive**: No clear difference

## Forbidden Claims (in every report)

1. Not clinical improvement or medical benefit
2. Not diagnostic
3. Not therapeutic
4. Not BCI validation
5. Not mind-reading or dream decoding
6. Not generalizable to other users
7. Not causal proof

## Safe Claim Formula

All results are framed as "personal exploratory observations," never as clinical evidence. Every report includes a `safe_claim` field using cautious language like "suggests," "consistent with," or "a positive personal observation — not clinical validation."

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/adaptive/experiments/{user_id}/design` | POST | Design new experiment |
| `/adaptive/experiments/{user_id}/start` | POST | Start experiment |
| `/adaptive/experiments/{user_id}/latest` | GET | Get latest experiment |
| `/adaptive/experiments/{user_id}/{eid}` | GET | Get specific experiment |
| `/adaptive/experiments/{user_id}` | GET | List experiments |
| `/adaptive/experiments/{user_id}/{eid}/day/{day}/complete` | POST | Complete day |
| `/adaptive/experiments/{user_id}/{eid}/day/{day}/attach-calibration` | POST | Attach calibration |
| `/adaptive/experiments/{user_id}/{eid}/close` | POST | Close experiment |
| `/adaptive/experiments/{user_id}/{eid}/analysis` | GET | Analyze experiment |
| `/adaptive/experiments/{user_id}/{eid}/evidence-score` | GET | Evidence score |
| `/adaptive/experiments/{user_id}/{eid}/report` | GET | Generate report |

## UI Panels

### NOf1ExperimentPanel (New)
- Design selector: AB, BA, ABAB, Randomized
- Full day-by-day listing with condition badges (baseline/optimized)
- Inline check-in form with sliders
- Calibration checkpoint indicators (PID display)
- Start/Close experiment buttons
- Embedded analysis summary

### NOf1EvidencePanel (New)
- Evidence score badge (category + numeric)
- Component score bars (PID effect, adherence, fatigue, checkpoints, design)
- Confound penalty display
- Safe claim text
- Limitations list
- Refresh button

## How to Run Tests

```bash
cd backend
python3 -m ruff check .
python3 -m app.cli.imagina_v13_pid_calibration_test
python3 -m app.cli.imagina_v14_adaptive_loop_test
python3 -m app.cli.imagina_v15_execution_loop_test
python3 -m app.cli.imagina_v16_optimization_test
python3 -m app.cli.imagina_v17_n_of_1_experiment_test
```

The V17 test:
1. Creates 4 calibration sessions + baseline/optimized plans + 2 full-adherence executions
2. Designs AB experiment (14 days)
3. Starts experiment
4. Completes all 7 baseline days
5. Attaches calibration to baseline block (PID=0.136)
6. Completes all 7 optimized days
7. Attaches calibration to optimized block (PID=0.100)
8. Closes experiment
9. Analyzes experiment (direction=inconclusive, no confounds)
10. Computes evidence score (35/100, exploratory_signal)
11. Generates report with safe claim
12. Verifies personal profile has n_of_1_experiment_summary
13. Lists experiments
14. Tests sparse user behavior
15. Verifies safety flags on all artifacts

## Storage

```
data/imagina/n_of_1_experiments/{user_id}/{experiment_id}/manifest.json
data/imagina/n_of_1_experiments/{user_id}/{experiment_id}/daily_logs.jsonl
data/imagina/n_of_1_experiments/{user_id}/latest_experiment.json
data/imagina/reports/{user_id}/n_of_1_experiment_{experiment_id}.json
data/imagina/reports/{user_id}/n_of_1_experiment_{experiment_id}.md
```

## Future V18 Direction

- Multi-experiment meta-analysis
- Automatic sample-size recommendation (how many more experiments for confidence?)
- Cross-experiment pattern detection
- Push notifications for experiment milestones
- PDF export of experiment reports
- Integration with real sensor data behind metadata preflight gates

---

*IMAGINA V17 turns the adaptive imagery-training system into a controlled personal experiment platform: it lets users test whether optimized plans outperform baseline plans under structured N-of-1 designs, using PID checkpoints, adherence/fatigue controls, and transparent evidence scoring. It remains non-clinical, non-diagnostic, non-BCI, and not mind-reading.*
