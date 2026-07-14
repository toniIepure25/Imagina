# Simulation Report — IMAGINA Gate C0

> **Status:** Synthetic simulation only. Not real-world evidence.

## Simulation Framework

Monte Carlo simulation-based operating characteristic estimation.

- **Engine:** `backend/app/research/design_simulation.py`
- **Agent model:** `backend/app/research/cognitive_agent.py`
- **Analysis:** `backend/app/research/statistics/confirmatory.py`
- **Counterbalancing:** Williams sequences

## Scenario Grid

| Scenario | Description |
|----------|-------------|
| strict_null | All conditions have identical causal effects |
| small_adaptive | Small genuine adaptive benefit (d≈0.2) |
| medium_adaptive | Medium adaptive benefit (d≈0.5) |
| subjective_only | Vividness improves, precision does not |
| practice_only | All conditions improve equally across sessions |
| placebo_expectancy | Adaptive label affects self-report only |
| carryover | Adaptive effects persist into later conditions |
| differential_dropout | Low performers drop out differentially |
| perceptual_control_only | Motor/perceptual improvement without imagery improvement |

## Operating Characteristics

Estimated per scenario:
- Statistical power
- Type-I error (with Monte Carlo SE)
- Bias (mean estimate − true effect)
- RMSE
- 95% CI coverage
- Convergence rate

## Design Recommendation

Based on simulation grid (not a single favorable scenario):
- Participant count, sessions per participant, trials per task
- Expected analyzable observations
- Power and Type-I error estimates with Monte Carlo uncertainty

## Limitations

1. Monte Carlo SE reflects finite simulation iterations; values are not exact.
2. Synthetic agents are mathematical constructs, not validated human models.
3. Simulation power ≠ real-world power.
4. All design recommendations are provisional pending human pilot data.
