# CRT Registered Report Package

**Status:** draft; not submitted and not accepted.
**Stage:** 0H package for Stage 1/Stage 2.
**Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.

## 1. Stage 1 (in-principle acceptance) content

1. **Introduction and theory:** three accounts, M0–M7, explicit falsifiers, and the non-systematic
   literature search caveat.
2. **Design:** N=480 main (432 analysed at 10% attrition), 120 trials per occasion, two occasions,
   four cells plus observe; N=160 dual-cost assay; N=80 calibration.
3. **Primary endpoint:** model-based source sensitivity for `yoked_predict − yoked_intervene`.
4. **Primary model comparison:** pre-specified M0/M2/M4/M6/M7; M1/M3/M5 exploratory.
5. **Adjustment set:** trial vividness and pre-outcome prediction confidence, with condition
   interactions; no source confidence as a predictor of the same judgment.
6. **Design-optimization gate:** the current artifact is `REVIEW`, so Stage 1 cannot be submitted as
   confirmatory until the design is revised or the claim is narrowed.
7. **Analysis code:** frozen hash, simulation configs, SBC/recovery thresholds, and multiverse rules.
8. **Adversarial collaboration:** roles, red-team tests, independent statistician, deviation log.
9. **Ethics and data management:** local-first, no external neural data, consent, withdrawal.
10. **Optional neural extension:** separate Stage 1E, not required for the behavioural report.

## 2. Stage 2 (full acceptance) content

- Registered report with the Stage 1 methods unchanged unless a signed amendment is published.
- Primary result with calibrated uncertainty and the pre-specified model comparison.
- All exclusions, deviations, and red-team tests.
- A null-result appendix that is publishable without reframing.

## 3. Decision rules

| Outcome | Interpretation |
|---|---|
| Primary effect present; M2/M4 beat M6/M7 with margin | Active-prospective account supported within the task |
| Primary effect absent | CRT's simplest active claim rejected; source-monitoring description remains |
| Effect explained by vividness | M6 retained; active claim rejected |
| Effect explained by precision | M7 retained; active claim rejected |
| Model comparison indeterminate | No theory adjudication; report the bound |

No outcome is called “revolutionary”, “first”, “validated”, “decoded”, or clinical.

## 4. Stop rules before submission

- Design optimization `REVIEW`.
- Full-model SBC or recovery `REVIEW`.
- Unresolved adversarial disagreement on a falsifier.
- No independent statistician or no ethics approval.
- Any unregistered change to the primary endpoint or model set.

## 5. Artifact checklist

- [ ] `CRT_STAGE0H_MODEL_SPACE.json`
- [ ] `CRT_STAGE0H_DESIGN_OPTIMIZATION.json` (currently `REVIEW`)
- [ ] `CRT_STAGE0H_FULL_MODEL_SBC.json`
- [ ] `CRT_STAGE0H_FULL_MODEL_RECOVERY.json`
- [ ] `CRT_STAGE0H_PACKAGE.json`
- [ ] Calibration protocol and likelihood table
- [ ] Frozen analysis hash
- [ ] Signed adversarial-collaboration agreement
- [ ] Ethics approval
- [ ] Registration receipt

## 6. Current blockers

The package remains `BLOCKED`. The design-optimization gate is `REVIEW`; full-model SBC/recovery are
screening checks; no independent review, calibration, registration, or ethics approval exists. The
correct action is revision, not a claim upgrade.
