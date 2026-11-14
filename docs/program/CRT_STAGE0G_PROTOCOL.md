# CRT Stage 0G: Theory Adjudication, Trial-Level Model, and Calibration Planning

**Status:** computational and documentation stage; no human data.
**Protocol:** `ANIMUS-CRT-v1`, version 0.5.0.
**Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.
**Registration:** `BLOCKED`.

## 1. Purpose

Stage 0G turns CRT from a single design hypothesis into a falsifiable adjudication among three
accounts:

1. signal-strength threshold;
2. higher-order precision inference;
3. active prospective inference.

It also raises the main design to **N=480, d=0.20** (approximately 0.925 power in the paired
approximation), adds a trial-level hierarchical readout model with SBC and recovery, and specifies an
independent calibration sample. It does **not** collect human data, authorize an API/DB/UI change, or
upgrade any claim.

## 2. Design decision

- Main study: 2×2 prediction-by-agency design, two occasions, 120 trials/occasion, 240 trials total.
- N=480 enrolled; approximately 432 analysed at 10% attrition.
- SESOI d=0.20; N=360 only if d=0.25 is pre-registered.
- Primary contrast remains `yoked_predict − yoked_intervene`.
- Primary endpoint is model-based source sensitivity; raw accuracy is secondary.
- Stage 1D dual-prediction cost assay remains N=160; independent calibration N=80; pilot N=40.
- Human collection remains blocked until registration, ethics, trial-level SBC/recovery, and
  calibration planning are independently reviewed.

## 3. Theory adjudication

The decision table, six predictions, and falsification rules are in
[`CRT_THEORY_ADJUDICATION.md`](CRT_THEORY_ADJUDICATION.md). The rapid search record and review
protocol are in [`CRT_STAGE0G_SCOPING_PROTOCOL.md`](../research/CRT_STAGE0G_SCOPING_PROTOCOL.md).
The review is **not systematic** and does not support a priority claim.

## 4. Trial-level model

`analysis/crt/trial_model.py` implements a trial-level hierarchical **readout** model with:

- participant random effects for source sensitivity, consistency bias, prediction precision, and
  prediction bias;
- condition effects for prediction, dual format, and their interaction proxies;
- models M0–M5 mapped to no effect, precision-only, single belief, dual counterfactual, dual plus
  consistency bias, and prediction-induced bias;
- Laplace posterior draws from a numerical Hessian, with the group covariance obtained by Schur
  complement;
- SBC ranks/coverage and BIC-based model recovery.

Scope string: `trial_level_hierarchical_readout_not_full_crt_pomdp`. This is **not** the full CRT
source-monitoring POMDP or meta-EIG policy model. It is a trial-level validation step that must be
followed by a full joint model before registration.

SBC result (M2, 1,000 draws, N=20, 60 trials): target `delta_d` mean rank 0.5025, coverage 0.955,
chi-square 21.66, convergence 0.99; decision `CRT_STAGE0G_TRIAL_SBC_PASS`. The intercept `alpha_d`
coverage is 0.838 and is reported as diagnostic only. This is an algorithm/readout calibration, not a
design-power estimate and not evidence for the full CRT model.

Model recovery is reported in two steps. A prior-averaged M0–M5 run gave balanced accuracy **0.375**
(`REVIEW`): the models are nested, and a null effect is often the correct generating model. An
effect-conditioned full-set run (each active effect |δ|≥0.25, N=24, 120 trials) gave **0.733**
(`REVIEW`). A post hoc reduction to the confirmatory **M0/M2/M4** set, with N=32, 160 trials, gave
**0.90** (`CONDITIONAL_PASS`). The artifact records `selection_status` as
`post_hoc_after_full_set_review`; the gate is therefore `LIMITED`, not `PASS`. This is a sensitivity
analysis, not a pre-specified full-set recovery success. M1/M3/M5 remain exploratory; M6/M7 are not
implemented.

## 5. Calibration plan

Independent N=80, ground-truth source induction, hierarchical beta-binomial estimation of
`p(test|source)`, measurement invariance, test–retest ICC, and a non-diagnostic fluency check. The
likelihood table is frozen only if precision and invariance pass; otherwise the model-based endpoint
falls back to raw accuracy. Human calibration is gated by ethics and registration. Full rules are in
[`CRT_CALIBRATION_PROTOCOL.md`](CRT_CALIBRATION_PROTOCOL.md).

## 6. Artifacts and gates

- `results/crt/CRT_STAGE0G_DESIGN_POWER.json`
- `results/crt/CRT_STAGE0G_TRIAL_SBC.json`
- `results/crt/CRT_STAGE0G_TRIAL_RECOVERY.json`
- `results/crt/CRT_STAGE0G_CALIBRATION_PROTOCOL.json` (protocol only; no human data)
- `results/crt/CRT_STAGE0G_REGISTRATION_PACKAGE.json`
- Planned but not generated: `CRT_STAGE0G_CALIBRATION_SIM.json` (simulation only; human calibration
  remains gated).
- Gates: Stage 0G design power, trial-level SBC, trial-level recovery, calibration plan, registration
  readiness.

Until those artifacts exist and pass independent review, the registration package remains `BLOCKED`.

## 7. Boundaries

No clinical, diagnostic, training, neural-decoding, or measurement-upgrade claim. No “first”,
“revolutionary”, or priority language. The model is a readout validation, not evidence that CRT
improves human reality monitoring.
