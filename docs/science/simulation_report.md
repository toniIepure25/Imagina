# Simulation Report — IMAGINA Gate C0.1

> **Status:** Synthetic simulation only. Not real-world evidence.
> All operating characteristics are estimated from synthetic cognitive agents,
> not from real human participants or neural measurements.

## Simulation Framework

Monte Carlo simulation-based operating characteristic estimation with
observed-scale causal oracle truth, full task battery, applied dropout,
and calibrated multi-estimator inference.

- **Engine:** `backend/app/research/design_simulation.py` (v2.1)
- **Campaign:** `backend/app/research/simulation_campaign.py` (v1.0)
- **Agent model:** `backend/app/research/cognitive_agent.py` (v2.0)
- **Analysis:** `backend/app/research/statistics/confirmatory.py` (v2.0)
- **Oracle:** `backend/app/research/causal_oracle.py` (v1.0)
- **RNG:** `backend/app/research/rng_registry.py` (v1.0)
- **Counterbalancing:** Williams sequences (6 sequences for 3 conditions)
- **Design:** `backend/app/research/crossover_design.py` (v1.0)

## RNG System

All scientific randomness uses `hashlib.sha256`-based deterministic seed
derivation through named streams. No dependence on Python built-in `hash()`.
Streams: population, allocation, stimulus, latent_state, motor_noise,
imagery_noise, self_report, dropout, bootstrap, randomization_test,
calibration, oracle, simulation, schedule.

- RNG version: 1.0
- RNG version hash: `41281c2ed503d5d0...`

## Oracle Estimand

The causal oracle computes counterfactual potential outcomes on the
observed composite reconstruction error scale:

```
E[Y(adaptive) - Y(yoked)]
```

For each agent and trial, both adaptive and yoked potential outcomes are
generated using common random numbers and scored with production scoring
code. The oracle effect is the population average of these within-unit
differences.

- Oracle version: 1.0
- Strict-null oracle effect: −0.001035 (SE: 0.000018)
- Small-effect oracle effect: −0.026453 (SE: 0.000329)
- Medium-effect oracle effect: −0.043371 (SE: 0.000536)

## Scenario Grid

| Scenario | Description |
|----------|-------------|
| strict_null | All conditions have identical causal effects |
| small_adaptive | Small genuine adaptive benefit (precision, control) |
| medium_adaptive | Medium adaptive benefit (precision, control, stability) |
| subjective_only | Vividness improves, precision does not |
| practice_only | All conditions improve equally across sessions |
| placebo_expectancy | Adaptive label affects self-report only |
| carryover | Adaptive effects persist into later conditions |
| differential_dropout | Low performers drop out differentially |
| perceptual_control_only | Motor/perceptual improvement without imagery improvement |

## Estimators

Three prespecified estimators:

1. **Estimator A (primary):** GEE-like marginal crossover estimator with
   period, sequence, baseline, task family, and carryover adjustment.
   Participant clusters with robust covariance.
2. **Estimator B (sensitivity):** Hierarchical MixedLM with participant
   random intercept and condition random slope. Singularity/boundary
   detection.
3. **Estimator C (robustness):** Randomization inference respecting
   Williams sequence assignments.

Confidence intervals: Cluster bootstrap (deterministic streams).

Fallback semantics: `inference_valid=False` when primary model does not
converge. Fallback results never counted as rejection or coverage.

## Operating Characteristics (Unit Mode, N=15)

| Metric | Strict Null | Medium Adaptive |
|--------|-------------|-----------------|
| Oracle effect | −0.001035 | −0.043371 |
| Type-I error | 0.0000 | — |
| Power | — | 0.0000 |
| Bias | — | −0.000452 |
| RMSE | — | 0.005648 |
| Coverage | 0.0000 | 0.0000 |
| Convergence | 0.0000 | 0.0000 |
| Fallback rate | 1.0000 | 1.0000 |
| Valid inference | 0.0000 | 0.0000 |
| NC FP rate | 0.0000 | — |

**Known limitation:** The primary GEE/MixedLM models consistently fall
back to the aggregate estimator with the default N=18 participant design.
This is because the model complexity (condition × period × task_family ×
carryover adjustment) exceeds what can be reliably estimated with 18
clusters in the crossover. Coverage and power are consequently 0 in
unit mode because `inference_valid=False` replicates are excluded.

This limitation is correctly detected by the campaign calibration checks
and flagged as a gate issue. Resolution requires either (a) larger
sample sizes, (b) simplified model terms, or (c) human pilot data to
determine the appropriate model complexity.

## Simulation Modes

| Mode | Iterations | Purpose |
|------|-----------|---------|
| unit | 15 | Structural invariants only |
| ci | 150 | Broad regression thresholds |
| research | 1000 | Checkpointed, resumable, for operating characteristics |
| publication_candidate | 5000+ | Configurable for final evidence |

## Design

- Design version: 1.0
- Design hash: `2868b4816a96bf91...`
- Endpoint registry hash: `24c56b2d2db81fba...`
- Scoring version: 1.0
- Battery version: 1.0

## Limitations

1. Monte Carlo SE reflects finite simulation iterations; values are not exact.
2. Synthetic agents are mathematical constructs, not validated human models.
3. Simulation power ≠ real-world power.
4. All design recommendations are provisional pending human pilot data.
5. Primary estimator convergence is limited by sample size relative to
   model complexity. Human pilot studies with adaptive sample sizes are
   needed to determine the appropriate model specification.
6. Coverage = 0 in current unit-mode simulations because primary model
   always falls back. This is a structural limitation, not a fast-mode
   artifact.
7. No real EEG, human participants, or clinical claims are made.

## Remaining Human-Validation Blockers

- Human psychometric reliability (test-retest, split-half)
- Human construct validity (convergent/discriminant)
- Usability and participant burden assessment
- Recruitment feasibility for N≥18 crossover design
- Ethics board approval
- Real neural measurement integration (EEG/fNIRS)
- External independent replication
