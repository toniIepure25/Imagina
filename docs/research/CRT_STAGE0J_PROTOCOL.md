# CRT Stage 0J — target-scale readiness protocol

**Status:** draft; not executed. **Human data:** none. **Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.

This protocol defines the computational gate between the Stage 0I simulation package and any human
study. It does not authorize recruitment. A `PASS` is simulation evidence; a `BLOCKED` result is an
honest stop.

## 1. Question

Can the target design separate the five confirmatory source-monitoring models with calibrated
posteriors and acceptable recovery before human data are collected?

## 2. Models

Confirmatory: `M0`, `M2`, `M4`, `M6`, `M7`. Exploratory models are excluded from the readiness
decision. The model definitions are in `analysis/crt/full_model.py`; the NumPyro mirror is in
`analysis/crt/numpyro_model.py`.

## 3. Target design

| Parameter | Value |
|---|---|
| Recruited N | 480 |
| Analysed N | 432 |
| Trials per participant | 240 |
| Occasions | 2 |
| Primary contrast | prediction consistency, diagnostic vs non-diagnostic |
| Co-primary | source accuracy; false-seen rate for imagined items |

## 4. Computational checks

1. **NUTS SBC** for every confirmatory model.
   - Target profile: 50 SBC simulations, 1,000 posterior draws, 1,000 warmup, 1 chain.
   - Coverage window: 0.93–0.97.
   - Mean-rank window: 0.40–0.60.
   - Rhat/ESS are not yet enforced in the SBC loop; this is a recorded limitation, not a pass.
   - No model may pass below 50 SBC simulations.
2. **Recovery** among the same five models.
   - BIC-based selection, 20 replicates per model.
   - Balanced accuracy threshold: 0.85.
   - BIC recovery is a limitation, not a NUTS marginal-likelihood comparison.
3. **Readiness decision.**
   - `PASS` only if every SBC model passes and recovery passes.
   - `REVIEW` if any check fails or is underpowered.
   - `BLOCKED` if NumPyro/JAX is unavailable.
4. **No threshold tuning.** Thresholds are frozen before the run. A failure is reported.

## 5. Execution

```bash
# wiring check only; cannot PASS
python -m analysis.crt.target_scale --smoke --check

# target run; requires explicit compute acknowledgement
python -m analysis.crt.target_scale --target --confirm-compute --write
```

The target run must be benchmarked on one model first. Record GPU type, wall time, memory, and
divergences. If one model exceeds the compute cap, stop and report; do not silently reduce the design.

## 6. Artifact

`results/crt/CRT_STAGE0J_TARGET_SCALE.json`, schema
[`science/schemas/crt_target_scale.schema.json`](../../science/schemas/crt_target_scale.schema.json),
gate `ANIMUS_P5_CRT_STAGE0J_TARGET_SCALE`.

Required content: git SHA, environment, seeds, config, SBC metrics, recovery confusion, failures,
limitations. The artifact is registered in `science/registry/artifacts.yaml`.

## 7. Failure modes

| Failure | Action |
|---|---|
| NumPyro/JAX absent | `BLOCKED`; do not substitute Laplace for a confirmatory pass |
| Divergences or Rhat > 1.01 | `REVIEW`; reparameterize or increase warmup, report both |
| Coverage outside window | `REVIEW`; do not widen the window after seeing results |
| Recovery below 0.85 | `REVIEW`; narrow the model set or redesign |
| Compute cap exceeded | stop; report partial run; do not human-study |
| Design still confuses M0/M6 | narrow claim or change paradigm |

## 8. What a PASS does not mean

- It does not validate the task in humans.
- It does not establish that any model is true.
- It does not authorize decoding, clinical, or consciousness claims.
- It does not replace calibration N=80, ethics, registration, or independent review.

## 9. Next gate

Only after a `PASS` or a documented decision to proceed with a narrowed claim:

1. calibration N=80;
2. ethics/DPIA;
3. Stage 1 registration;
4. adversarial collaboration sign-off;
5. human data collection.
