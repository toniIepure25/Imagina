# CRT Stage 0H: Theory-Discriminating Models and Adversarial Review Package

**Status:** computational and documentation stage; no human data.
**Protocol:** `ANIMUS-CRT-v1`, version 0.6.0.
**Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.
**Registration:** `BLOCKED`.

## 1. Purpose

Stage 0G made CRT falsifiable on paper but did not make the competing accounts empirically
distinguishable. The trial model was a readout approximation, M6/M7 were unimplemented, the full-set
recovery was 0.733, and the 0.90 recovery result came from a post hoc M0/M2/M4 subset.

Stage 0H adds:

1. a formal M0–M7 model space with M0/M2/M4/M6/M7 confirmatory;
2. a trial-level readout for the signal-strength (M6) and higher-order precision (M7) rivals;
3. an offline design-optimization screen for model discrimination;
4. a full joint latent-source model with observed test choice;
5. pre-specified SBC and recovery gates;
6. an adversarial-collaboration and Registered Report package.

It does **not** collect human data, authorize an API/DB/UI change, upgrade a claim, or support a
priority or “revolutionary” statement.

## 2. Model space

| Model | Account | Confirmatory? |
|---|---|---|
| M0 | baseline source SDT | yes |
| M1 | prediction precision only | no |
| M2 | active prospective single prediction | yes |
| M3 | dual counterfactual plus direct effect | no |
| M4 | dual counterfactual plus consistency bias | yes |
| M5 | prediction-induced bias | no |
| M6 | signal strength / vividness | yes |
| M7 | higher-order precision / confidence | yes |

M6: source judgment is mediated by trial vividness; a direct prediction effect after controlling
vividness rejects M6. M7: source judgment and source confidence are joint functions of precision; a
direct prediction effect beyond precision rejects M7. Source confidence is never used as a predictor
of the same source judgment.

## 3. Readout implementation

`analysis/crt/trial_model.py` now implements M0–M7. The readout remains
`trial_level_hierarchical_readout_not_full_crt_pomdp`. M6 uses trial vividness; M7 uses pre-outcome
prediction confidence as a precision proxy. These are screening approximations, not the final joint
model.

## 4. Design optimization

`analysis/crt/design_optimization.py` simulates candidate trial compositions and evaluates pairwise
BIC discrimination among M0/M2/M4/M6/M7. The objective is maximin pairwise balanced accuracy subject
to a power floor. The classifier used to rank candidates is a design heuristic, not a hypothesis test.

The current artifact is `REVIEW`: the best candidate (`combined_manipulation`) reached 0.625 minimum
pairwise accuracy, below the pre-specified 0.85 threshold. This is a stop rule, not a reason to relabel
the result. The design must be revised before registration.

## 5. Full joint model

`analysis/crt/full_model.py` implements a latent-source model with observed test choice, joint
prediction/outcome/source-report/confidence likelihood, participant random effects, numerical Laplace
posterior draws, SBC, and BIC recovery.

Scope string: `full_joint_source_monitoring_latent_state_not_policy_pomdp`. It is not the policy POMDP;
the policy that selected the test is compared separately out of sample.

The generated SBC and recovery artifacts are screening checks. The recorded run used four SBC draws
and one recovery replicate at N=6/T=20 (a deliberately small screening run, not the planned 1,000
draws). Both are `REVIEW`: M6 coverage was 0.75 and recovery balanced accuracy was 0.60, with M6
confused with M0/M4. A `REVIEW` means the model or design needs revision; it is not human evidence.

## 6. Artifacts and gates

- `results/crt/CRT_STAGE0H_MODEL_SPACE.json`
- `results/crt/CRT_STAGE0H_DESIGN_OPTIMIZATION.json`
- `results/crt/CRT_STAGE0H_FULL_MODEL_SBC.json`
- `results/crt/CRT_STAGE0H_FULL_MODEL_RECOVERY.json`
- `results/crt/CRT_STAGE0H_PACKAGE.json`

| Artifact | Decision | Gate |
|---|---|---|
| `CRT_STAGE0H_MODEL_SPACE.json` | `CRT_STAGE0H_MODEL_SPACE_PASS` | `PASS` |
| `CRT_STAGE0H_DESIGN_OPTIMIZATION.json` | `CRT_STAGE0H_DESIGN_OPTIMIZATION_REVIEW` | `LIMITED` |
| `CRT_STAGE0H_FULL_MODEL_SBC.json` | `CRT_STAGE0H_FULL_MODEL_SBC_REVIEW` | `LIMITED` |
| `CRT_STAGE0H_FULL_MODEL_RECOVERY.json` | `CRT_STAGE0H_FULL_MODEL_RECOVERY_REVIEW` | `LIMITED` |
| `CRT_STAGE0H_PACKAGE.json` | `BLOCKED` | `BLOCKED` |

Readiness remains `BLOCKED` until the computational gates, adversarial review, calibration,
registration, and ethics are complete.

## 7. Adversarial and registered-report package

The package is in
[`CRT_ADVERSARIAL_COLLABORATION.md`](CRT_ADVERSARIAL_COLLABORATION.md) and
[`CRT_REGISTERED_REPORT_PACKAGE.md`](CRT_REGISTERED_REPORT_PACKAGE.md). It specifies rival roles,
frozen predictions, an independent analyst, masked preprocessing, a deviation log, and a Stage 1/Stage 2
Registered Report path. It does not claim that collaborators have agreed or that a venue has accepted.

## 8. Optional neural extension

[`CRT_NEURAL_EXTENSION.md`](CRT_NEURAL_EXTENSION.md) is a separate, optional Stage 1E. It uses EEG to
test prediction-error and source-retrieval components. It makes no decoding, clinical, or diagnostic
claim and is not required for the behavioural program.

## 9. Boundaries

No human data, clinical sample, neural decoding, training claim, or measurement upgrade. No “first”,
“revolutionary”, priority, “proves”, “validated”, “diagnoses”, or “decodes” language. The current
design-optimization `REVIEW` is reported as a limitation, not hidden.

## 10. Next steps

1. Revise the model/design until the pre-specified discrimination and recovery gates pass, or narrow
   the confirmatory claim.
2. Run the independent N=80 calibration after ethics and registration.
3. Complete adversarial review and Stage 1 Registered Report submission.
4. Only then consider the N=480 main study and the N=160 Stage 1D dual-cost assay.
