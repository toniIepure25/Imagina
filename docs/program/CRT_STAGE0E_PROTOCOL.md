# CRT Stage 0E Protocol — Model Repair and Construct Audit

## Status

- **Date:** 2026-10-30.
- **Protocol:** `ANIMUS-CRT-v1`.
- **Scope:** simulation-only Stage 0E. No human data, neural data, clinical sample, API, database, UI, or
  claim upgrade is authorized by this document.
- **Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.
- **Decision rule:** a Stage 0E `PASS` is a design and model-audit result. It is **not** human
  validation and does not authorize a measurement claim.
- **Primary question:** does the CRT prediction and specificity result survive removal of oracle
  prediction and prediction/outcome double counting?

## 1. Why Stage 0E exists

Stage 0C and Stage 0D used a simulator in which the participant predicted a test outcome from the
**true source** and then treated the prediction as an independent source likelihood. Both choices are
oracle assumptions:

1. A human does not know the true source when predicting.
2. A prediction generated from the same belief that is later updated by the outcome is not independent
   evidence. Counting it twice inflates source accuracy and can manufacture a diagnostic-specificity
   advantage.

Stage 0E repairs the generative model before any human study is registered. The repair is more
important than adding another hand-set gate.

## 2. Repaired model

Let `m_i(s)` be the participant's current source posterior before test `a`. The belief-based predicted
probability of a positive outcome is

```text
q_i(a) = sum_s m_i(s) * p_as
P(P = 1 | a, m_i) = sigmoid(pi_i * logit(q_i(a)))
```

where `p_as` is the test likelihood under source `s` and `pi_i` is prediction precision. At `pi_i = 1`
this is the posterior predictive. At `pi_i = 0` it is source-neutral (`0.5`).

The source update is **outcome-only**:

```text
m_i(s | o, a) proportional to m_i(s) * P(o | a, s)
```

The prediction does not enter the source likelihood. It is a readout of the forward model, a policy
signal, and a candidate assay of prospective reality testing. This removes the double-counting path.

### Prediction sources

| Mode | Use | Claim status |
| --- | --- | --- |
| `belief` | Primary human-facing model: predict from current posterior. | Design model |
| `oracle` | Historical benchmark only. | Not a human model |
| `prior` | Source-neutral prior predictive baseline. | Sensitivity check |
| `nondiagnostic` | `pi = 0`; prediction independent of source. | Matched control |

The oracle inflation is reported explicitly:

```text
oracle_inflation = prediction_advantage_oracle - prediction_advantage_belief
```

## 3. Stage 0E work packages

### 0E-1 Model repair

- Belief-based posterior-predictive prediction.
- Oracle benchmark retained only for audit.
- Outcome-only source update.
- Tests that replay the observed outcomes and recover the final posterior exactly.
- Nested posterior PIT calibration check for the assumed generative model.

### 0E-2 Dual-hypothesis prediction

- Predict the outcome under `seen` and `imagined` hypotheses.
- Record hypothesis-specific accuracy, confidence, and prediction error.
- Record `counterfactual_discrepancy = |p_seen - p_imagined|`.
- Compare dual diagnostic, single diagnostic, and dual non-diagnostic prediction on the same fixed
  test sequence.

The dual-prediction gate requires a dual advantage **and** a specificity advantage. If it fails, the
label "counterfactual" is not earned; the construct is renamed **prospective reality testing**.

### 0E-3 Policy competition

Compare `meta_eig`, `eig`, `cost_only`, `positive`, `fixed`, `heuristic`, and `random`. A normative
meta-EIG claim requires meta-EIG to exceed both cost-only and the best competing policy. A failure
downgrades the claim to descriptive.

### 0E-4 Psychometric facets

- Simulated person × occasion × test-facet reliability.
- Relative-reliability floor of 0.70 at two occasions.
- Test-level reporting rather than a single composite.

### 0E-5 Adversarial checks

- Posterior PIT calibration.
- Oracle-inflation quantification.
- Fixed-sequence specificity control.
- Explicit no-double-counting replay test.

### 0E-6 Conditional recovery and SBC

- Recover prediction precision `pi` with `d`, guessing, and response bias fixed.
- Run a conditional SBC rank histogram over a uniform `pi` prior.
- Compare `M0` (no prediction) with `M2` (single belief readout plus prediction bias) by BIC.
- Report relative RMSE, bias, correlation, and the recovery confusion matrix.

This is **conditional** SBC, not full hierarchical SBC. It tests whether the repaired readout is
identifiable under the stated simulation design; it is not human evidence.

## 4. Registered artifacts

| Artifact | Path | Gate | Expected status |
| --- | --- | --- | --- |
| Model repair | [`CRT_STAGE0E_MODEL_REPAIR.json`](../../results/crt/CRT_STAGE0E_MODEL_REPAIR.json) | `ANIMUS_P5_CRT_MODEL_REPAIR` | PASS (audit complete) |
| Specificity audit | [`CRT_STAGE0E_SPECIFICITY_AUDIT.json`](../../results/crt/CRT_STAGE0E_SPECIFICITY_AUDIT.json) | `ANIMUS_P5_CRT_SPECIFICITY` | LIMITED |
| Dual prediction | [`CRT_STAGE0E_COUNTERFACTUAL.json`](../../results/crt/CRT_STAGE0E_COUNTERFACTUAL.json) | `ANIMUS_P5_CRT_COUNTERFACTUAL` | LIMITED |
| Policy competition | [`CRT_STAGE0E_POLICY.json`](../../results/crt/CRT_STAGE0E_POLICY.json) | `ANIMUS_P5_CRT_POLICY` | LIMITED |
| Test facets | [`CRT_STAGE0E_PSYCHOMETRIC.json`](../../results/crt/CRT_STAGE0E_PSYCHOMETRIC.json) | `ANIMUS_P5_CRT_PSYCHOMETRIC` | PASS (simulation only) |
| Conditional recovery | [`CRT_STAGE0E_RECOVERY.json`](../../results/crt/CRT_STAGE0E_RECOVERY.json) | `ANIMUS_P5_CRT_RECOVERY_BELIEF` | PASS (conditional) |

The historical Stage 0D specificity artifact is preserved unmodified and marked historical. The
canonical specificity gate now points to the belief-based audit.

## 5. Results (simulation, seed 20261030)

### 5.1 Model repair

| Quantity | Oracle | Belief |
| --- | ---: | ---: |
| Prediction advantage | 0.127778 | 0.026389 |
| Prediction accuracy | 0.623165 | 0.532993 |
| Specificity decision | PASS | REVIEW |

- `oracle_inflation = 0.101389`.
- Oracle prediction-accuracy gap = `0.090172`.
- Stage 0D specificity is **not** reproduced under belief prediction.
- Posterior PIT: mean 0.499, chi-square 15.92 with 9 df (critical 21.67).

### 5.2 Specificity audit

- Diagnostic prediction accuracy: `0.504861`.
- Nondiagnostic prediction accuracy: `0.493750`.
- Source accuracy gain: `0.026389` (diagnostic 0.400 vs nondiagnostic 0.374).
- Calibration gain: `-0.032138` (worse for diagnostic).
- Decision: `CRT_STAGE0D_SPECIFICITY_REVIEW`.

The Stage 0D gate floor required diagnostic prediction accuracy above 0.55. The belief-based arm is at
chance. The earlier 0.160 source-accuracy gain was an oracle artifact.

### 5.3 Dual prediction

- Mean counterfactual discrepancy: `0.475993`.
- Dual gain over single: `0.000000`.
- Specificity gain over dual nondiagnostic: `0.036806`.
- Decision: `CRT_STAGE0E_COUNTERFACTUAL_REVIEW`.

Participants can represent two different hypotheses, but the dual report does not improve source
accuracy on the fixed sequence. The "counterfactual" label is not yet supported by a behavioural
advantage.

### 5.4 Policy competition

- Meta-EIG minus cost-only: `+0.060416`.
- Meta-EIG minus best alternative: `-0.011806`.
- Best alternative: `0.351389`.
- Decision: `CRT_STAGE0E_POLICY_REVIEW`.

Meta-EIG beats a cheap heuristic but not the best competing policy. The normative claim is downgraded;
the simulation still supports a descriptive analysis of policy fit.

### 5.5 Test facets

- Minimum relative reliability: `0.842731`.
- Mean relative reliability: `0.863290`.
- Decision: `CRT_STAGE0E_PSYCHOMETRIC_PASS`.

The weakest facet is fluency (`0.842731`); this is a simulated design property, not a human estimate.

### 5.6 Conditional recovery and SBC

- Parameter recovery: relative RMSE `0.201650`, bias `0.037556`, correlation `0.776806`.
- Conditional SBC: mean PIT `0.539280`, chi-square `8.50` with 9 df (critical `21.67`).
- Model recovery (`M0` vs `M2`): balanced accuracy `0.937500`; 21/24 `M2` datasets recovered, 24/24
  `M0` datasets recovered.
- Decision: `CRT_STAGE0E_RECOVERY_PASS`.

The repaired readout is identifiable when `d`, guessing, and response bias are fixed and the design
uses 240 trials. Recovery is weaker at the short 60-trial design; the artifact therefore supports a
design check, not a claim that the model is true.

## 6. Decisions

1. **Do not use the Stage 0D oracle specificity result as evidence.** The canonical gate is `LIMITED`.
2. **Use belief-based prediction and outcome-only updating in all future CRT simulations.**
3. **Keep "counterfactual" provisional.** Use **prospective reality testing** in manuscripts until a
   dual-prediction advantage and specificity advantage are demonstrated.
4. **Do not claim meta-EIG is normative.** Report policy fit descriptively; compare with cost-only and
   adaptive baselines.
5. **Do not register a human study on the basis of Stage 0E.** The next step is a human-factors pilot
   with PI, IRB, funding, and registration gates, not a confirmatory claim.
6. **Do not upgrade claims.** Training and clinical claims remain `BLOCKED`.
7. **Treat recovery as conditional.** The `pi` recovery and SBC checks fix `d`, guessing, and response
   bias; they do not establish full hierarchical identifiability or human validity.

## 7. Limitations

- All results are simulation-only and depend on the assumed likelihood table.
- The PIT check is a posterior calibration check, not full hierarchical SBC.
- The recovery check fixes `d`, guessing, and response bias; it is conditional SBC, not a hierarchical
  group-level analysis, and it does not include misspecified likelihoods.
- Model recovery covers `M0` versus `M2` only; `M3` and `M4` are not yet recovered.
- The dual-prediction arm uses the same fixed test sequence; a policy-level dual advantage has not been
  tested.
- The test-facet simulation uses a simple additive model; it is not a human generalizability study.
- No measurement invariance, missing-data, or item-response analysis is included yet.
- The literature search is rapid and non-systematic; it cannot support a priority claim.

## 8. Next experiments

1. Extend model recovery to `M3` (dual counterfactual) and `M4` (dual plus error attribution) and
   compare out-of-sample predictive fit.
2. Run dual-prediction with a **policy-level** manipulation to test whether counterfactual simulation
   changes test selection, not only report content.
3. Add full hierarchical SBC with group-level parameters and misspecified likelihoods.
4. Pre-register a human-factors pilot only after the above pass and after PI/IRB/funding review.
5. Freeze the likelihood table from an independent calibration sample before confirmatory data.

## 9. Commands

From `backend/`:

```powershell
python -m app.cli.crt_stage0e --check
python -m app.cli.crt_stage0e --write --out-dir ..\results\crt
python -m app.cli.crt_stage0e --write --recovery --out-dir ..\results\crt
python -m app.cli.science_ledger --check
python -m app.cli.science_ledger --write
```

From the repository root:

```powershell
python scripts/verify.py --quick
```
