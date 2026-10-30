# CRT Stage 0D Protocol: Theory and Design Controls

## Status

- **Stage:** 0D, simulation only. Historical protocol; the specificity result is superseded by Stage 0E.
- **Protocol:** `ANIMUS-CRT-v1`.
- **Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.
- **Human data:** none.
- **Canonical artifacts:**
  [`CRT_STAGE0D_MODEL_TOURNAMENT.json`](../../results/crt/CRT_STAGE0D_MODEL_TOURNAMENT.json),
  [`CRT_STAGE0D_SPECIFICITY_POWER.json`](../../results/crt/CRT_STAGE0D_SPECIFICITY_POWER.json),
  [`CRT_STAGE0D_GTHEORY.json`](../../results/crt/CRT_STAGE0D_GTHEORY.json), and
  [`CRT_STAGE0D_CALIBRATION.json`](../../results/crt/CRT_STAGE0D_CALIBRATION.json).
- **Superseding audit:** [`CRT_STAGE0E_PROTOCOL.md`](CRT_STAGE0E_PROTOCOL.md). The specificity artifact is
  retained as historical; its oracle prediction path is not a human model.

## 1. Purpose

Stage 0C showed a positive prospective-prediction contrast but an unresolved active-selection contrast.
Stage 0D asks four design questions before any human study:

1. Are the competing theories separable under measurement noise?
2. Is the prediction advantage specific to diagnostic prediction?
3. Does active choice add value beyond random-passive exposure and algorithm-adaptive selection?
4. Are the test likelihoods and reliability design adequate for a confirmatory study?

## 2. Design

### 2.1 Model-signature tournament

Five models:

- `crt_meta_eig`
- `eig_only`
- `higher_order_precision`
- `sdt_confidence`
- `heuristic_source`

Each model predicts a five-dimensional signature (prediction advantage, meta-EIG efficiency, active
selection gain, specificity gain, prediction-error update). The simulation adds Gaussian noise and
classifies each observation by nearest signature. The gate is balanced accuracy >= 0.80.

This is a **signature separability** analysis. It is not a fit to human data and not a claim that the
models are true.

### 2.2 Specificity control

- `active_predict_diagnostic`: predict a source-diagnostic test outcome.
- `active_predict_nondiagnostic`: predict a matched but source-independent consequence.
- Both arms use the same participants, fixed test sequence, tests, confidence report, cost, and time.
  The fixed sequence isolates prediction content from test-selection differences.
- The non-diagnostic prediction has `pi = 0`, so it cannot update the source posterior by construction.
- Gate: diagnostic accuracy gain >= 0.02 and diagnostic prediction accuracy > 0.55.

The simulation result is a sanity check, not evidence that people show the same pattern.

### 2.3 Active-selection control

- `active`: participant chooses tests with the meta-EIG policy.
- `algorithm`: algorithm chooses the maximum-meta-EIG test; participant predicts.
- `random_passive`: experimenter selects tests uniformly; participant predicts.
- Gate: active choice gain >= 0.01 and adaptive design gain >= 0.01.

Algorithm-adaptive selection is allowed to outperform active choice. That would show that human choice
is not optimal, not that the control failed.

### 2.4 Test-likelihood calibration

A simulated calibration sample (40 participants, 20 trials per source-test cell) estimates the six test
likelihoods with a Beta-Binomial model. Gate: at least four tests have a seen-versus-imagined likelihood
ratio outside `[0.75, 1.33]`, and the fluency trap remains within `[0.80, 1.25]`.

The human calibration sample must freeze the likelihood table before confirmatory data collection.

### 2.5 Generalizability theory

A person-by-occasion variance-component analysis and a four-point decision study. Gate: relative
reliability at two occasions >= 0.70 in the simulation. The simulation is a planning illustration, not a
human reliability estimate.

## 3. Results

| Check | Decision | Key result |
| --- | --- | --- |
| Model signatures | PASS (provisional) | Balanced accuracy 0.90; weakest diagonal 0.775 (heuristic). |
| Specificity | HISTORICAL PASS; CURRENT LIMITED | Oracle diagnostic accuracy gain 0.160; belief-based source accuracy gain 0.026 and diagnostic prediction accuracy 0.505 (Stage 0E). |
| Active selection | PASS (historical oracle path) | Active-choice gain 0.037; adaptive-design gain 0.128; active is 0.092 below algorithm. |
| Calibration | PASS | Four strong tests; fluency likelihood ratio 1.005. |
| G-theory | PASS | Relative reliability 0.938 at two occasions; occasion component zero in this draw. |

The specificity report's Brier and calibration gains are near zero or negative. The gate uses accuracy
because the non-diagnostic prediction is constructed to be source-neutral, not to match the confidence
distribution. Brier and ECE remain descriptive secondary checks.

**Stage 0E correction.** The specificity row above was generated with oracle prediction and
prediction/outcome double counting. Under belief-based prediction and outcome-only updating, the
diagnostic-specificity advantage does not reproduce. The canonical specificity gate now points to
[`CRT_STAGE0E_SPECIFICITY_AUDIT.json`](../../results/crt/CRT_STAGE0E_SPECIFICITY_AUDIT.json) and is
`LIMITED`. The historical artifact is preserved unmodified.

## 4. What Stage 0D does not establish

- That any model is true in humans.
- That people use meta-EIG.
- That active choice improves outcomes.
- That the test likelihoods are correct in humans.
- That the instrument is reliable.
- That CRT is ready for training, clinical use, or neural decoding.

## 5. Gates and kill criteria

| Gate | Pass | Fail action |
| --- | --- | --- |
| Theory separability | Balanced accuracy >= 0.80 | Redesign contrasts; do not run a decisive human test |
| Specificity | Diagnostic gain >= 0.02 | Reclassify CRT as generic prediction |
| Active selection | Active > random-passive | No active-selection claim |
| Calibration | >= 4 strong tests; fluency null | Drop or redesign weak tests |
| G-theory | Relative reliability >= 0.70 | Revise trial/occasion design |

## 6. Next stage

Stage 1A is a human measurement validation with N=240, two occasions, a pilot N=40, and a registered
report. Stage 1B (selection controls, N=160) and Stage 1C (specificity control, N=160) are separate
preregistered sub-studies. None is authorized by Stage 0D or Stage 0E. They require PI approval, IRB,
funding, a second screener, and an adversarial collaborator, plus the Stage 0E model-fitting and
hierarchical-SBC follow-up.

## 7. Reproduction

```powershell
cd backend
python -m app.cli.crt_stage0d --check
python -m app.cli.crt_stage0d --write --out-dir ..\results\crt
python -m app.cli.science_ledger --check
```
