# IMAGINA V16 — Adaptive Optimization Engine

## What V16 Adds

V16 turns IMAGINA from a plan execution tracker into an adaptive optimization system. It analyzes completed plan executions, estimates which training focuses work best for the user, detects fatigue and adherence limitations, compares completed plans, and generates an optimized next plan.

V14 generated plans. V15 executed them. V16 learns from them.

## V15 vs V16

| | V15 | V16 |
|---|-----|-----|
| **Execution** | Day-by-day tracking | Same |
| **Response** | Per-execution category | Multi-execution response model + scoring |
| **Fatigue** | Basic avg per execution | Pattern detection: by day, by focus, correlations |
| **Optimization** | None | Best/worst focus, fatigue/adherence model, optimized next plan |
| **Comparison** | None | Plan A/B comparator, focus rankings |
| **Decision** | Manual judgment | Automated recommendation with transparent reasoning |

## Optimization Architecture

```
Completed Executions (≥2)
    │
    ├─→ Plan Response Model ─→ response_score per focus
    │                          best_focus / worst_focus
    │
    ├─→ Fatigue/Adherence Model ─→ risk levels
    │                               session_length rec
    │                               rest pattern rec
    │
    ├─→ PID Improvement Tracker ─→ overall trend
    │
    └─→ Next Plan Optimizer ─→ recommendation_type
                                recommended_focus
                                adjusted difficulty/duration/rest
                                      │
                                      ▼
                              Optimized Adaptive Plan
```

## Plan Response Model

### Response Score Formula

```
pid_gain = max(0, -mean_pid_change) / 0.15
adherence_bonus = mean_adherence × 0.25
focus_bonus = mean_focus_quality / 10 × 0.15
fatigue_penalty = mean_fatigue / 10 × 0.20
instability_penalty = pid_change_std × 0.20

response_score = max(0.01, min(0.99,
    pid_gain + adherence_bonus + focus_bonus - fatigue_penalty - instability_penalty))
```

Higher score = the training focus appears to work better for this user.

## Fatigue & Adherence Model

Detects:
- Fatigue by day index (e.g., fatigue increases after day 3)
- Fatigue by training focus (which focus is most tiring)
- Skipped day clustering (days tend to be skipped after day 3)
- Difficulty-fatigue correlation
- Recommendations: session length, rest pattern, intensity adjustment

## Next-Plan Optimizer Decision Rules

| Condition | Recommendation |
|-----------|---------------|
| No data or < 2 executions | Fallback to V14 standard plan |
| Fatigue risk = high | fatigue_resistance, shorter sessions, rest days |
| Adherence risk = high | Simplify exercises, reduce duration |
| Best focus = current focus, score > 0.55 | Continue best focus, increase difficulty slightly |
| Best focus != current focus | Switch to best-responding focus |
| Current focus response < 0.40 | Switch to alternative focus or baseline_rebuild |
| PID trend declining | Rebuild baseline, reduce difficulty |

## Plan A/B Comparator

Compares last 2 completed executions:
- PID change difference
- Adherence difference  
- Fatigue difference
- Response category comparison
- Winner logic: PID improved more by ≥0.05 AND fatigue not higher by >2
- Inconclusive if PID changes too similar or adherence gap > 0.3

## Focus Rankings

Groups all completed executions by training_focus and ranks by response_score.
Top focus = recommended for personalized training.

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/adaptive/optimization/response-model/{user_id}` | GET | Focus-level response analysis |
| `/adaptive/optimization/fatigue-adherence/{user_id}` | GET | Fatigue/adherence patterns + recs |
| `/adaptive/optimization/next-plan/{user_id}` | GET | Optimized next-plan recommendation |
| `/adaptive/optimization/generate-plan/{user_id}` | POST | Generate optimized 7-day plan |
| `/adaptive/optimization/compare-executions/{user_id}` | POST | Compare 2 specific executions |
| `/adaptive/optimization/compare-focuses/{user_id}` | GET | Rank training focuses |

## UI Panels

### AdaptiveOptimizationPanel (New)
- Fatigue risk badge (low/medium/high) with average value
- Adherence risk badge with percentage
- Best/worst focus highlight
- Response score bar chart per focus
- Next-plan recommendation with reasoning
- Fatigue/adherence recommendations
- Generate Optimized Plan button

### PlanComparisonPanel (New)
- Winner badge (Plan A / Plan B / Inconclusive)
- Side-by-side comparison: focus, PID change, adherence
- Delta values for PID, adherence
- Confidence level
- Focus rankings table (top 5)
- Interpretation text

## How to Run Tests

```bash
cd backend
python3 -m ruff check .
python3 -m app.cli.imagina_v13_pid_calibration_test
python3 -m app.cli.imagina_v14_adaptive_loop_test
python3 -m app.cli.imagina_v15_execution_loop_test
python3 -m app.cli.imagina_v16_optimization_test
```

The V16 test:
1. Creates 4 calibration sessions + adaptive plan + 2 completed executions
2. Builds plan response model (best_focus, response scores per focus)
3. Analyzes fatigue/adherence (risk levels, session length rec)
4. Recommends optimized next plan (simplify_for_adherence → vividness_foundation)
5. Generates optimized adaptive plan with adjustments (0.7x duration, -1 difficulty)
6. Compares last 2 executions
7. Compares training focuses (rankings)
8. Verifies personal profile contains adaptive_optimization_summary
9. Verifies safety flags on all artifacts
10. Tests sparse user behavior
11. Tests insufficient data recommendation fallback

## Safety Boundaries

All V16 artifacts include:
- `analysis_mode: "personal_exploratory_training"`
- `not_clinical: true`, `not_diagnostic: true`
- `not_mind_reading: true`, `not_bci_claim: true`
- `production_valid: false`
- Scientific boundary disclaimer

All interpretations use cautious wording: "suggests," "consistent with," "personal exploratory trend," "not a clinical outcome."

## Future V17 Direction

- Multi-execution A/B testing with controlled difficulty levels
- Push notifications for optimized plan readiness
- Automated periodic optimization (weekly recompute)
- PDF export of optimization reports
- Integration with real sensor data behind metadata preflight gates

---

*IMAGINA V16 turns the adaptive imagery-training loop into an optimization system: it analyzes completed plan executions, estimates which training focuses work best for the user, detects fatigue and adherence limitations, compares plans, and generates an optimized next plan. It remains non-clinical, non-diagnostic, non-BCI, and not mind-reading.*
