# CRT Stage 1 Preregistration (DRAFT)

## Registration status

- **Status:** DRAFT. Not yet submitted to OSF or a registered-report venue.
- **Version:** 0.1, 2026-10-29.
- **Protocol:** `ANIMUS-CRT-v1`.
- **Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.
- **Canonical claims:** `claim.counterfactual_reality_testing_measurement` (UNVALIDATED);
  `claim.counterfactual_reality_testing_training` and
  `claim.counterfactual_reality_testing_clinical` (BLOCKED).

This draft must be reviewed by the PI, an independent statistician, an adversarial collaborator, and
an ethics board before any human data are collected. Deviations from the registered version will be
logged and reported.

## 1. Study title

**Counterfactual Reality Testing (CRT): a preregistered validation of prospective prediction and
prediction-error attribution in a behavioural source-monitoring task.**

## 2. Background and rationale

Source-monitoring research asks how people attribute an experience to perception or imagination. Most
tasks ask for a post-hoc judgment after the evidence is fixed. ART adds active selection of evidence.
CRT adds a prospective step: before a test outcome is revealed, the participant predicts it and reports
confidence. The test then provides a counterfactual comparison between predicted and observed
consequences.

The rationale is that source attribution may depend not only on the evidence but on the **precision of
the forward model** that generated the prediction. Lower memory precision has been linked to
misattributing self-generated experiences to external sources (Kwon et al., 2022). People track the
epistemic status of real and imagined counterfactual alternatives (Espino & Byrne, 2021), and
counterfactual comparisons inform the sense of agency (Kulakova et al., 2017). Prediction-consistent
imagined experience may inflate seen attributions, especially when prediction confidence is high.

CRT deliberately avoids rich autobiographical counterfactual imagination, which can itself impair
memory for true actions (Dhammapeera et al., 2024) and is sensitive to imagery perspective and decision
criteria (Libby, 2003). The prediction is a sparse test consequence, not a new imagined episode.

The study is **measurement validation**, not an intervention. A training RCT is conditional on the
measurement gates and is specified separately.

## 3. Hypotheses

### Primary hypotheses

- **H1 (prediction advantage):** prospective prediction (`active_predict`) improves source accuracy
  relative to outcome-only active testing (`active_intervene`), with a standardized difference of at
  least 0.20.
- **H2 (meta-EIG policy):** a meta-EIG-cost policy predicts test choices better than outcome-EIG,
  positive-testing, fixed, heuristic, or random policies out of sample (expected log predictive density
  advantage, pre-registered).
- **H3 (reliability):** `CRTE_meta` has a 14-day test-retest ICC(2,1) of at least 0.75, with a lower
  95% confidence bound above 0.60.

### Secondary hypotheses

- **H4 (prediction calibration):** prediction confidence tracks prediction correctness, with
  `prediction_ece <= 0.15`.
- **H5 (imagination inflation):** prediction-consistent imagined trials show a higher seen-attribution
  rate than prediction-inconsistent imagined trials, controlling for source confidence, guessing, and
  response bias.
- **H6 (incremental validity):** `CRTE_meta` predicts source accuracy or calibration beyond `d_prime`
  and `meta_d_prime`.
- **H7 (discriminant):** `CRTE_meta` is more weakly associated with beads-task draws-to-decision than
  with the source measures (absolute r < 0.70 for the discriminant bound).
- **H8 (invariance):** the instrument shows configural, metric, and scalar invariance across device
  class, order, and imagery stratum (Delta CFI < 0.01; Delta RMSEA < 0.015).
- **H9 (exploratory active selection):** active selection improves calibration relative to a
  matched-sequence yoked control. Stage 0C found a near-null under matched yoking; a random-passive
  control matched on the number of tests is required before a superiority claim.

### Exploratory

- Association of `CRTE_meta` with VVIQ-2, SIAQ, and LSHS-E in a non-clinical sample.
- `meta_d_prime` as a secondary measure, only when the trial gate is met.
- Strategy reports, response time, abstention, fatigue.
- Continuous schizotypy associations; no clinical or continuum claim.

## 4. Design

**Type:** prospective, preregistered, two-occasion, within-subject measurement study with a 2x2
prediction-by-agency manipulation and an observational baseline.

**Occasions:** day 0 and day 14. Alternate forms A/B counterbalanced across occasions.

**Trials:** 120 per occasion: 30 in each of the four cells plus 20 `observe` trials. Two occasions
provide 240 trials total. The `observe` baseline is not included in the primary prediction contrast.

**Cells:**

- `active_intervene`: participant selects tests; no prediction.
- `active_predict`: participant selects tests; predicts each test outcome before reveal.
- `yoked_intervene`: donor test sequence; no prediction.
- `yoked_predict`: donor test sequence; predicts each test outcome before reveal.

**Test menu:** six tests, at most two per trial, without replacement. Viewpoint, generation, context,
intention, description, and fluency. The fluency test is a zero-diagnosticity trap with equal
likelihoods for all sources. Costs and complexity values are fixed in the protocol.

**Manipulations:** test cost (low/high) and test reliability (high/low) are within-subject, randomized
within blocks. The primary analysis uses the pooled active-predict and active-intervene cells;
manipulation checks are secondary.

**Blinding:** the analyst is blind to cell order and group labels until the primary analysis is locked.
The participant is not told which condition is active. The experimenter does not see trial-level
results.

**Yoking:** a donor sequence is taken from a matched participant and item position. The yoked
participant sees the same test identities but generates their own outcomes and predictions. The
matched-sequence design controls information quantity and time on task. It cannot identify an
active-selection superiority effect; that question requires a random-passive control.

## 5. Participants

### Target

N=180 analysed participants.

Recruitment strata for exploratory invariance:

- 60 with self-reported aphantasia or hypophantasia (VVIQ-2 lower extreme);
- 60 typical imagery;
- 60 hyperphantasia (upper extreme).

The primary analysis is the full sample; stratum contrasts are secondary. Recruitment will screen
approximately 2,000-3,000 adults to identify the extreme strata if enrichment is used.

### Inclusion

- Age 18-65.
- Normal or corrected-to-normal vision.
- Able to complete a 75-minute online session.
- Provides informed consent.

### Exclusion

- Self-reported current neurological or psychiatric treatment.
- Current substance intoxication or acute illness.
- Prior participation in a CRT, ART, or source-monitoring experiment with the same stimuli.
- Inability to complete the practice block or comprehension check.

Group labels are recruitment strata, not diagnoses. Participants with aphantasia are not described as
impaired.

### Sample-size rationale

N=180 is a planning target. Under the Stage 0C power approximation
([`results/crt/CRT_STAGE0_POWER.json`](../../results/crt/CRT_STAGE0_POWER.json)), true ICC 0.75 with
N=180 gives 0.961 power for a lower 95% bound above 0.60. This is a planning result, not human
evidence. The study is powered for the reliability hypothesis; group differences are secondary and
will be reported with confidence intervals, not as confirmatory tests.

## 6. Materials

- Symbolic scenes generated by the existing ANIMUS scene engine; no generative AI in the loop.
- Deterministic text cues for imagined and described conditions.
- Six tests with the likelihood table in the CRT specification; at most two per trial, without
  replacement.
- VVIQ-2 (imagery vividness).
- SIAQ (spatial imagery).
- OSIVQ (exploratory comparator).
- Beads task (draws-to-decision) as a discriminant measure.
- Working-memory composite (operation span or digit span; fixed before registration).
- LSHS-E (exploratory, non-clinical).
- Usability, fatigue, strategy, and adverse-experience items.

## 7. Procedure

1. Consent and eligibility screen.
2. Practice block with feedback on the test interface and prediction format; comprehension check.
3. Occasion 1: form A; cells in counterbalanced order.
4. Questionnaires and demographics.
5. Occasion 2 (day 14): form B; cells in reversed order.
6. Debrief: explains the four sources, the test likelihoods, and the zero-diagnosticity fluency trap;
   offers withdrawal of data.

Each occasion is capped at 75 minutes. Participants may stop at any time. A fatigue check occurs every
20 trials.

## 8. Outcomes

### Primary

1. `prediction_advantage`: `active_predict` minus `active_intervene` in source accuracy.
2. `CRTE_meta` at day 14, ICC(2,1) with 95% CI.
3. Out-of-sample predictive advantage of the meta-EIG-cost policy over alternatives.

### Secondary

- `prediction_ece`, `prediction_accuracy`.
- `CRTE_eig`, `active_calibration_advantage`, `active_accuracy_advantage`.
- `d_prime_seen_imagined`, criterion `c`, full confusion matrix.
- Brier score, ECE, overconfidence for source confidence.
- `imagination_inflation_rate`, controlling for guessing and response bias.
- `confounded_test_rate` (fluency choices).
- Sampling quality, termination quality, number of tests.
- Cost and reliability sensitivity.
- Model-free test diagnosticity.
- `meta_d_prime` (gated).
- Convergent/discriminant correlations.
- Measurement invariance.
- Usability, fatigue, adverse events.

## 9. Analysis plan

The full plan is in [`docs/program/CRT_ANALYSIS_PLAN.md`](CRT_ANALYSIS_PLAN.md). In brief:

- Hierarchical Bayesian model with weakly informative priors.
- Simulation-based calibration before fitting human data.
- ICC(2,1), SEM, and MDC95 for reliability.
- Model comparison with LOO/WAIC and posterior predictive checks.
- Mixed-effects models for prediction, agency, and cost/reliability contrasts.
- Multigroup CFA for questionnaire comparators; hierarchical model with group-specific parameters.
- FIML or multiple imputation for missing data.
- One primary endpoint per hypothesis; secondary endpoints labelled exploratory.
- Blinded primary analysis; preregistered multiverse; all deviations logged.

The nested model test checks whether `pi = 0`, which would make CRT equivalent to ART/AgRT. A
non-zero `pi` is necessary but not sufficient for a prediction-specific claim.

## 10. Decision gates

| Gate | Criterion | If failed |
| --- | --- | --- |
| Feasibility | >=80% completion; >=90% comprehension; no serious adverse events | Revise task; do not proceed |
| Reliability | ICC >=0.75; lower 95% CI >=0.60 for `CRTE_meta` | Publish psychometric null; stop training RCT |
| Prediction advantage | Standardized difference >=0.20 or calibration advantage with CI excluding 0 | Drop prediction-specific claim; retain descriptive |
| Prediction calibration | `prediction_ece <= 0.15` | Revise prediction format; do not claim calibration |
| Policy | Meta-EIG model beats alternatives out of sample | Report descriptive only; no normative claim |
| Incremental validity | `CRTE_meta` adds prediction beyond `d_prime`/`meta_d_prime` | Narrow the construct claim |
| Discriminant | `CRTE_meta`-beads r <0.70 | Revise task or drop distinctness claim |
| Invariance | Delta CFI <0.01; Delta RMSEA <0.015 | Restrict to lab/device; no group comparison |
| Active selection | Random-passive control required for superiority | Keep active-selection claim exploratory |
| Training | Measurement gates pass; separate RCT registration | Remain blocked |
| Clinical | Separate IRB, clinical sample, registration | Remain blocked |

## 11. Ethics and data management

- Local-first: no cloud, no telemetry, no external API.
- Pseudonymous participant IDs; raw data in local SQLite; de-identified export.
- No neural data; no clinical sample; no diagnosis.
- Participants may withdraw; data are deleted on request before aggregation.
- Adverse events are logged; the session stops on request or fatigue threshold.
- The study is not a treatment and makes no clinical claim.

## 12. Registration and deviations

- Target: Registered Report Stage 1 at a general-interest human behaviour journal; fallback *Cortex*
  or *eLife*.
- The analysis code will be frozen and hashed before the primary analysis.
- The pilot (N=40) is feasibility-only and will be reported separately; it is not used to support
  confirmatory claims.
- Any deviation from this draft will be recorded with date, reason, and whether it was blinded.
- The final registered version supersedes this draft.

## 13. What this study will not establish

- That CRT measures "reality" outside the experimental sources.
- That CRT diagnoses or predicts psychosis.
- That CRT improves imagery or clinical outcomes.
- That the task is a neural decoder.
- That the instrument is "first" or "revolutionary."
- That a matched-sequence yoked contrast identifies active-selection superiority.
