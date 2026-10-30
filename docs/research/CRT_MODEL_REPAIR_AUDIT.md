# CRT Model Repair Audit

## Status

- **Date:** 2026-10-30.
- **Scope:** `ANIMUS-CRT-v1`, simulation-only Stage 0E.
- **Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.
- **Purpose:** document why the Stage 0C/0D prediction model was replaced, what the replacement
  assumes, and which earlier results are downgraded.

## 1. The two defects

### 1.1 Oracle prediction

The Stage 0C/0D simulator computed a prediction from the **true source**:

```python
probability = prediction_likelihood(test, true_source, params.pi)
```

A real participant does not have `true_source`. This makes prediction accuracy an upper bound, not a
behavioural measurement. The defect is not repaired by calling the result "simulation"; it changes the
meaning of the prediction contrast and the specificity control.

### 1.2 Double counting

The old source update used the prediction as an independent likelihood:

```text
m_i(s | p, o, a) proportional to m_i(s) * P(p | a, s) * P(o | a, s)
```

If the prediction was generated from the same source belief, the prediction and the outcome are not
independent. Counting both inflates the posterior and can create an apparent diagnostic advantage.

The analysis plan disclosed oracle use for **recovery** only. The main simulation and specificity arm
were not covered by that disclosure. The Stage 0E audit treats this as a model error, not a stylistic
choice.

## 2. Repaired generative model

### 2.1 Belief-based prediction

For participant `i`, source posterior `m_i`, and test `a`:

```text
q_i(a) = sum_s m_i(s) * p_as
P(P = 1 | a, m_i) = sigmoid(pi_i * logit(q_i(a)))
```

Properties:

- `pi_i = 0`: source-neutral prediction, `P = 0.5`.
- `pi_i = 1`: exact posterior predictive.
- `pi_i > 1`: overconfident readout; `pi_i < 1`: underconfident readout.
- The prediction is a **function of the current belief**, not of the hidden source.

### 2.2 Outcome-only source update

```text
m_i(s | o, a) proportional to m_i(s) * P(o | a, s)
```

The prediction is not in the likelihood. This is the key identification restriction: the model does
not allow a prediction generated from `m_i` to be reused as independent evidence.

### 2.3 What the prediction is for

The prediction remains scientifically useful as:

1. a **readout** of the forward model (`q_i`);
2. a **policy signal** for meta-EIG test selection;
3. an **assay** of prospective reality testing;
4. a candidate **error signal** for a later error-attribution model, provided that model does not
   double count.

## 3. Identification and falsification

The repaired model makes the following testable distinctions:

| Model | Prediction source | Source update | Distinguishing pattern |
| --- | --- | --- | --- |
| `M0` outcome-only SDT | None | Outcome | No prediction effect; source accuracy explained by `d'`, bias, confidence |
| `M1` higher-order precision | Precision readout | Outcome | Confidence/precision predicts attribution; no independent prediction effect |
| `M2` single belief readout | `q_i(a)` | Outcome | Prediction accuracy tracks the posterior predictive; no oracle inflation |
| `M3` dual counterfactual | `p_seen`, `p_imagined` | Outcome | Hypothesis-specific reports and discrepancy; accuracy advantage only if policy changes |
| `M4` dual + error attribution | Dual | Outcome + attribution | Prediction error changes later test selection or confidence, not the current source likelihood |

The repair **falsifies** any claim that the Stage 0D specificity result is human prediction evidence.
It does not falsify CRT as a design; it changes what must be demonstrated.

## 4. Audit results

From [`CRT_STAGE0E_MODEL_REPAIR.json`](../../results/crt/CRT_STAGE0E_MODEL_REPAIR.json), 24 simulated
participants, 60 trials, seed 20261030:

| Quantity | Oracle | Belief |
| --- | ---: | ---: |
| Prediction advantage | 0.127778 | 0.026389 |
| Prediction accuracy | 0.623165 | 0.532993 |
| Specificity decision | PASS | REVIEW |

- Oracle inflation: **0.101389**.
- Oracle prediction-accuracy gap: **0.090172**.
- Stage 0D specificity reproduced under belief: **false**.

The belief prediction accuracy is close to chance. This is expected when the current source posterior
is uncertain and the test likelihoods are not strongly separated at the start of a trial. It is not a
failure of the repair; it is the honest readout.

## 5. Calibration check

The nested posterior PIT check uses randomized PIT:

```text
u = F(true_source - 1) + Uniform(0, 1) * P(true_source)
```

For 1,000 simulations and two tests:

- mean PIT: `0.499434`;
- chi-square: `15.92` with 9 df (critical `21.666`);
- decision: `CRT_STAGE0E_PIT_PASS`.

This is a **posterior calibration** check for the assumed generative model. It is not full hierarchical
SBC and does not validate the likelihood table against human data.

### 5.1 Conditional recovery and SBC

The follow-up audit fixes `d`, guessing, and response bias and recovers prediction precision `pi` over
a uniform prior on `[0.40, 2.00]`:

- parameter recovery: relative RMSE `0.201650`, bias `0.037556`, correlation `0.776806`;
- conditional SBC: mean PIT `0.539280`, chi-square `8.50` with 9 df (critical `21.67`);
- `M0` versus `M2` BIC recovery: balanced accuracy `0.937500`.

The artifact is [`CRT_STAGE0E_RECOVERY.json`](../../results/crt/CRT_STAGE0E_RECOVERY.json), gate
`ANIMUS_P5_CRT_RECOVERY_BELIEF`. This is **conditional** SBC, not full hierarchical SBC, and it does not
identify `M3` or `M4`.

## 6. Consequences

1. The Stage 0D specificity gate is downgraded from `PASS` to `LIMITED`.
2. The Stage 0C prediction contrast is provisional, not human evidence.
3. The Stage 0E model-repair gate is `PASS` only in the sense that the audit is complete and the
   repaired model is internally consistent.
4. The oracle arm remains in the code as a benchmark; it must never be the default for a human-facing
   simulation.
5. Any manuscript must report oracle inflation when citing the earlier result.

## 7. Residual risks

- The likelihood table is hand-specified; a wrong table can still produce a false specificity result.
- `pi_i` is a free precision parameter; it can absorb prediction noise and must be identified with
  independent calibration data.
- The PIT check assumes the prior and likelihood are correct; it does not detect all misspecification.
- The dual-prediction model has not yet been fitted to the simulated data; its parameters are not
  recovered. Only `M0` versus `M2` is covered by the conditional recovery audit.
- The conditional recovery fixes `d`, guessing, and response bias; a joint recovery with those
  parameters free remains untested.
- The source update still assumes conditional independence of tests given the source. Real tests may
  share method variance.

## 8. Next step

Extend recovery to `M3` and `M4`, add a policy-level dual manipulation, and run a misspecified-likelihood
calibration study before registering a human-factors pilot.
