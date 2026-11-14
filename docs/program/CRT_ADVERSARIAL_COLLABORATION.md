# CRT Adversarial Collaboration Protocol

**Status:** draft for independent review; no collaborators have agreed and no venue has accepted.
**Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.

## 1. Purpose

The program is designed so that proponents of the three accounts can agree on what would count
against them. Adversarial collaboration is not a courtesy review after the result; it fixes the
falsifiers, the analysis, and the authorship/data-access rules before human data.

## 2. Roles

| Role | Responsibility | Independence |
|---|---|---|
| CRT proponent | Owns the active-prospective model and predictions | May not unblind primary outcomes |
| Signal-strength advocate | Owns M6/vividness account and the adjustment set | Signs the M6 falsifier |
| Precision advocate | Owns M7/higher-order precision account | Signs the M7 falsifier |
| Red team | Attempts to produce the same pattern with demand, fluency, or strategy artifacts | No analysis veto, writes a signed report |
| Independent statistician | Runs the primary model comparison from frozen code and masked data | No stake in the result |
| Data manager | Holds the randomization code and deviation log | Separate from analysts |

## 3. Frozen disagreements

1. **What counts as prediction?** The active package must change the consequence the participant
   predicts, not just arousal or effort. The yoked arm controls for stimulation and time.
2. **What counts as a vividness explanation?** M6 is rejected if the yoked prediction effect on
   model-based source sensitivity survives adjustment for trial vividness and the vividness ×
   condition interaction is not the whole effect. The adjustment is pre-specified, not chosen after
   looking at the result.
3. **What counts as a precision explanation?** M7 is rejected if the prediction effect survives
   adjustment for pre-outcome prediction confidence/source precision and the confidence × condition
   interaction is not the whole effect. Source confidence is never a predictor of the same judgment.
4. **What counts as a dual cost?** The dual diagnostic condition must increase false-seen for imagined
   items relative to the single diagnostic condition; the nondiagnostic-demand arm separates demand
   from content-specific counterfactual simulation.
5. **What is a failed replication?** The pre-specified primary contrast is null or reversed, or the
   model comparison does not clear its margin with calibrated uncertainty.

## 4. Red-team tests

- **Demand/strategy:** ask participants what they think the study tests; test whether explicit
  awareness predicts the effect.
- **Fluency:** control for test fluency and response time; the fluency trap must stay at chance.
- **Effort/time:** yoked arms equate exposure; test residual time-on-task.
- **Output editing:** test whether source reports are edited after feedback; no feedback in the main
  phase.
- **Analysis flexibility:** multiverse of reasonable exclusion rules, reported in full; the primary
  result must survive the pre-specified set.
- **Model flexibility:** recovery and SBC must use the same likelihood and priors as the analysis;
  no post hoc model additions.

## 5. Data and code access

- All code, likelihoods, priors, and simulation configs are frozen before unblinding.
- The independent statistician receives masked condition labels and a hash of the analysis code.
- The randomization key is released only after the primary analysis is signed.
- Deviations are logged with time, reason, and sign-off; the log is published with the report.
- No participant data or neural data leave the local environment.

## 6. Authorship and reporting

Authorship follows substantive contribution, not position on the result. A signed disagreement
appendix is published even if the main result is null. The red-team report is published whether or not
it changes the interpretation.

## 7. What this document does not claim

It does not claim that any collaborator has agreed, that the design is accepted, that the result is
known, or that the program is a systematic review. Those are separate facts with separate evidence.
