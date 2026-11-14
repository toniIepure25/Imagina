# CRT Stage 1 Preregistration (DRAFT)

## Registration status

- **Status:** DRAFT. Not yet submitted to OSF or a registered-report venue.
- **Version:** 1.2-draft, 2026-10-31 (Stage 0H: M0–M7, confirmatory M0/M2/M4/M6/M7; design-optimization REVIEW).
- **Protocol:** `ANIMUS-CRT-v1` v0.6.0.
- **Stage 0H package:** `CRT_STAGE0H_PACKAGE.json` (BLOCKED).
- **Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.
- **Canonical claims:** `claim.counterfactual_reality_testing_measurement` (UNVALIDATED);
  `claim.counterfactual_reality_testing_training` and
  `claim.counterfactual_reality_testing_clinical` (BLOCKED).

This draft must be reviewed by the PI, an independent statistician, an adversarial collaborator, and
an ethics board before any human data are collected. Deviations from the registered version will be
logged and reported.

**Stage 0H stop rule:** the design-optimization gate is currently `REVIEW` (the best candidate did not
reach 0.85 minimum pairwise model discrimination). The full-model SBC/recovery artifacts are screening
checks. Registration remains `BLOCKED`; no human data may be collected or simulated as if observed.

## 1. Study title

**Counterfactual Reality Testing (CRT): a preregistered validation of prospective prediction, test
selection, and source attribution in a behavioural source-monitoring task.**

## 2. Background and rationale

Source-monitoring research asks how people attribute an experience to perception or imagination. Most
tasks ask for a post-hoc judgment after the evidence is fixed. ART adds active selection of evidence.
CRT adds a prospective step: before a test outcome is revealed, the participant predicts it and reports
confidence. The test then provides a comparison between predicted and observed consequences. The
prediction is a **readout of the participant's current source belief** and a policy signal; it is not
treated as independent source evidence. The source is updated from the outcome only. This restriction is
the Stage 0E repair and is fixed before human data collection.

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
measurement gates and is specified separately. The Stage 0E simulation downgraded the specificity,
dual-prediction, and normative-policy claims to `LIMITED`; the human study is not authorized by those
results.

## 3. Hypotheses

### Primary hypotheses

- **H1 (prediction advantage):** prospective prediction improves source accuracy in the **yoked**
  comparison (`yoked_predict` minus `yoked_intervene`), where the test sequence is fixed, with a
  standardized difference of at least 0.20 (the pre-registered SESOI). The active comparison
  (`active_predict` minus `active_intervene`) is a secondary **package effect**, because prediction
  may change test selection as well as source updating.
- **H2 (meta-EIG policy):** a meta-EIG-cost policy predicts test choices better than outcome-EIG,
  positive-testing, fixed, heuristic, cost-only, or random policies out of sample (expected log
  predictive density advantage, pre-registered). Stage 0E simulation does not yet support the
  normative claim (meta-EIG loses to the best competing policy by 0.012); H2 remains a testable
  hypothesis, not a design result.
- **H3 (reliability):** `CRTE_meta` has a 14-day test-retest ICC(2,1) of at least 0.80, with a lower
  95% confidence bound above 0.70 for group-level use. Individual-level use requires ICC >= 0.90 and is
  not planned.

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
- **H9 (exploratory active selection):** active selection improves accuracy relative to a
  random-passive control matched on test count and time. Matched-sequence yoking cannot identify this;
  Stage 0E supplies the control design but no human evidence, and the Stage 0E policy gate is
  `LIMITED`.
- **H10 (counterfactual cost; Stage 1D):** dual diagnostic prediction increases the false-seen rate
  for imagined items relative to single diagnostic prediction, and the dual-nondiagnostic control
  separates response-demand from hypothesis-specific content. A benefit on source accuracy and a cost
  on false-seen attribution may coexist; both are reported.
- **H11 (theory adjudication; Stage 0H):** among the pre-specified confirmatory models
  M0/M2/M4/M6/M7, the active-prospective model must beat the best signal-strength (M6) and
  higher-order precision (M7) model out of sample by the pre-registered margin, after adjustment for
  vividness and pre-outcome confidence. If it does not, the rival account is retained and the active
  claim is rejected. M1/M3/M5 are exploratory and cannot carry a confirmatory claim.

### Exploratory

- Association of `CRTE_meta` with VVIQ-2, SIAQ, and LSHS-E in a non-clinical sample.
- `meta_d_prime` as a secondary measure, only when the trial gate is met.
- Strategy reports, response time, abstention, fatigue.
- Continuous schizotypy associations; no clinical or continuum claim.

## 4. Design

**Type:** prospective, preregistered, two-occasion, within-subject measurement study with a 2x2
prediction-by-agency manipulation and an observational baseline.

**Occasions:** day 0 and day 14. Alternate forms A/B counterbalanced across occasions.

**Trials:** 120 per occasion: 25 in each of the four cells plus 20 `observe` trials. Two occasions
provide 240 trials total. The `observe` baseline is not included in the primary prediction contrast.
The earlier draft's 30-per-cell/120-total text was arithmetically inconsistent; Stage 0F fixes it to
25 per cell and records the audit in `results/crt/CRT_STAGE0F_PROTOCOL_AUDIT.json`.

**Cells:**

- `active_intervene`: participant selects tests; no prediction.
- `active_predict`: participant selects tests; predicts each test outcome before reveal.
- `yoked_intervene`: donor test sequence; no prediction.
- `yoked_predict`: donor test sequence; predicts each test outcome before reveal.

The primary prediction contrast is `yoked_predict` minus `yoked_intervene`. The active contrast is a
package effect and cannot isolate prediction from self-selected testing.

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

### Model restriction (Stage 0E repair)

The participant's source posterior is `m_i(s)`. The predicted positive-outcome probability for test `a`
is the belief-based readout

```text
q_i(a) = sum_s m_i(s) * p_as
P(P = 1 | a, m_i; pi_i) = sigmoid(pi_i * logit(q_i(a)))
```

and the source update is outcome-only:

```text
p(s | O, a) proportional to prior_s * P(O | s, a; d_i)
```

The prediction is not an independent likelihood and is not counted twice. The oracle variant is a
benchmark only. This restriction is fixed before human data collection; changing it requires a
protocol amendment and a new registration.

### Specificity sub-study (Stage 1C)

A separate within-subject sample (N=160) completes `active_predict_diagnostic` and
`active_predict_nondiagnostic` blocks in counterbalanced order. Both blocks use the same fixed test
sequence, prediction format, confidence report, cost, and time. Only the prediction content differs.
The primary outcome is source accuracy; Brier score and ECE are descriptive. A null or negative
diagnostic contrast rejects the counterfactual-prediction interpretation even if the generic prediction
arm beats outcome-only testing.

### Dual-prediction sub-study (Stage 1D)

A separate within-subject sample (N=160) completes `active_predict_single`,
`active_predict_dual`, and `active_predict_dual_nondiagnostic` blocks in counterbalanced order. All
three blocks use the same fixed test sequence, prediction confidence report, cost, and time. The
primary outcome is the **false-seen rate for imagined items**; source accuracy and criterion bias are
secondary. The dual-nondiagnostic arm controls for the extra response demand of the dual format.
This is the human test of whether counterfactual prediction is a benefit, a cost, or both. A null
result is reported as equivalence, not as support for a benefit claim.

### Selection sub-study (Stage 1B)

A separate within-subject sample (N=160) completes `active_predict`, `random_passive`, and
`algorithm_adaptive` blocks. The random-passive arm receives experimenter-selected tests matched on
count and time. The algorithm arm receives the maximum-meta-EIG test. The primary selection contrast is
active minus random-passive; algorithm minus random-passive estimates adaptive-design value. If the
algorithm outperforms active choice, that is a benchmark result, not a failed control.

## 5. Participants

### Target

N=480 enrolled participants, with approximately 432 analysed at 10% attrition.

Recruitment strata for exploratory invariance:

- 160 with self-reported aphantasia or hypophantasia (VVIQ-2 lower extreme);
- 160 typical imagery;
- 160 hyperphantasia (upper extreme).

The primary analysis is the full sample; stratum contrasts are secondary. Recruitment will screen
approximately 4,000-6,000 adults to identify the extreme strata if enrichment is used.

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

The Stage 0F design check estimates only about 0.61-0.65 power for a standardized prediction effect of
0.20 at N=240 with 50 trials per condition and 10% attrition. The approved Stage 0G design decision is
therefore N=480 and d=0.20 as the smallest effect of interest; the current paired approximation gives
approximately 0.925 power at N=480 (0.938 at N=520, 0.80 at N=360). N=360 is acceptable only if d=0.25
is pre-registered as the SESOI before data collection. Do not retain d=0.20 with N=240. The design
decision must be rechecked against the trial-level model-based endpoint before registration. The
Stage 0F artifact is
[`results/crt/CRT_STAGE0F_DESIGN_POWER.json`](../../results/crt/CRT_STAGE0F_DESIGN_POWER.json).
This is a planning result, not human evidence.

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

1. `prediction_advantage`: `yoked_predict` minus `yoked_intervene` in source accuracy.
2. `CRTE_meta` at day 14, ICC(2,1) with 95% CI.
3. Out-of-sample predictive advantage of the meta-EIG-cost policy over alternatives.
4. Stage 1D `false_seen_inflation`: dual diagnostic minus single diagnostic in the imagined-item
   false-seen rate, with the dual-nondiagnostic arm as the demand control.

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
| Stage 0F protocol | `CRT_STAGE0F_PROTOCOL_PASS` | Fix arithmetic/contrast before registration |
| Stage 0F power | >=0.90 for the chosen SESOI; >=0.80 for the false-seen assay | Revise N/trials/SESOI; do not register as confirmatory |
| Full hierarchical SBC | 95% coverage 0.93-0.97; no rank skew | Revise model/priors; no human data |
| M3/M4 recovery | Balanced accuracy >=0.85 | Drop the dual claim; retain single prediction |
| Feasibility | >=80% completion; >=90% comprehension; no serious adverse events | Revise task; do not proceed |
| Reliability | ICC >=0.80; lower 95% CI >=0.70 for `CRTE_meta` | Publish psychometric null; stop training RCT |
| Prediction advantage | Yoked standardized difference >=0.20 or calibration advantage with CI excluding 0 | Drop prediction-specific claim; retain descriptive |
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
- Stage 0F status: protocol audit passes; design power is **REVIEW** at d=0.20/N=240; the distortion
  assay is validated against an injected effect and separates a `b_pi=0` null from a `b_pi>0` bias
  channel; endpoint-level hierarchical SBC and M0/M2/M3/M4 recovery pass. A trial-level CRT
  hierarchical SBC is still outstanding. Stage 0G raises the main design to N=480/d=0.20 and adds the
  three-account theory adjudication. Registration remains **BLOCKED** until trial-level SBC/recovery,
  calibration, and independent review pass.
- The analysis code will be frozen and hashed before the primary analysis.
- The pilot (N=40) is feasibility-only and will be reported separately; it is not used to support
  confirmatory claims. An independent calibration sample (N=80) freezes the test-likelihood table
  before confirmatory analysis.
- Any deviation from this draft will be recorded with date, reason, and whether it was blinded.
- The final registered version supersedes this draft.

## 13. What this study will not establish

- That CRT measures "reality" outside the experimental sources.
- That CRT diagnoses or predicts psychosis.
- That CRT improves imagery or clinical outcomes.
- That the task is a neural decoder.
- That the instrument is "first" or "revolutionary."
- That a matched-sequence yoked contrast identifies active-selection superiority.
