# ART Stage 2 Preregistration (DRAFT)

## Registration status

- **Status:** DRAFT. Not yet submitted to OSF or a registered-report venue.
- **Version:** 0.1, 2026-10-29.
- **Protocol:** `ANIMUS-ART-v1`.
- **Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.
- **Canonical claims:** `claim.active_reality_testing_measurement` (UNVALIDATED);
  `claim.active_reality_testing_training` and `claim.active_reality_testing_clinical` (BLOCKED).

This draft must be reviewed by the PI, an independent statistician, an adversarial collaborator, and
an ethics board before any human data are collected. Deviations from the registered version will be
logged and reported.

## 1. Study title

**Active Reality Testing (ART): a preregistered validation of a behavioural source-inquiry instrument
for seen, imagined, described, and new content.**

## 2. Background and rationale

Source-monitoring research asks how people attribute an experience to perception or imagination.
Most tasks ask for a post-hoc judgment after the evidence is fixed. They do not measure how a person
**selects** evidence. The information-search literature shows that confidence and metacognitive
sensitivity regulate when and what people sample, but it has not been applied to source attribution.

ART fills that gap. Participants may sample source-diagnostic evidence cards before judging the
source. The primary question is whether the efficiency of that selection is a reliable and valid
individual difference, separable from source discrimination, confidence calibration, and generic
evidence gathering.

The study is **measurement validation**, not an intervention. A training RCT is conditional on the
measurement gates and is specified separately.

## 3. Hypotheses

### Primary hypotheses

- **H1 (active benefit):** active card selection improves source accuracy or calibration relative to
  yoked passive at equal information, with a standardized effect of at least 0.20.
- **H2 (policy):** an EIG-cost policy predicts query choices better than fixed-threshold, heuristic,
  or random policies out of sample (expected log predictive density advantage, pre-registered).
- **H3 (reliability):** `ARTE` has a 14-day test-retest ICC(2,1) of at least 0.75, with a lower 95%
  confidence bound above 0.60.

### Secondary hypotheses

- **H4 (incremental validity):** `ARTE` predicts source accuracy or calibration beyond `d_prime` and
  `meta_d_prime` (incremental R-squared or LOO improvement).
- **H5 (discriminant):** `ARTE` is more weakly associated with beads-task draws-to-decision than with
  the SIM source measures (absolute r < 0.70 for the discriminant bound).
- **H6 (control):** participants sample more cards under low cost than high cost, and choose more
  diagnostic cards under high reliability than low reliability.
- **H7 (invariance):** the instrument shows configural, metric, and scalar invariance across device
  class, order, and imagery stratum (Delta CFI < 0.01; Delta RMSEA < 0.015).

### Exploratory

- Association of `ARTE` with VVIQ-2, SIAQ, and LSHS-E in a non-clinical sample.
- `meta_d_prime` as a secondary measure, only when the trial gate is met.
- Strategy reports, response time, abstention, fatigue.
- Classification-image imagery task in an optional N=60 subsample, as a convergent criterion.
- Continuous schizotypy associations; no clinical or continuum claim.

## 4. Design

**Type:** prospective, preregistered, two-occasion, within-subject measurement study with an embedded
active-versus-yoked crossover.

**Occasions:** day 0 and day 14. Alternate forms A/B counterbalanced across occasions.

**Blocks within occasion:** active and yoked passive, 40 trials each, order counterbalanced, separated
by a filled break.

**Card design:** four cards, at most two samples per trial, without replacement. The four-card menu is
required for identifiability: if every card could be sampled, cumulative EIG would be independent of
order and `ARTE` would be undefined. The pilot will check that the second card is not always the same
conditional on the first.

**Manipulations:** card cost (low/high) and card reliability (high/low) are within-subject, randomized
within blocks. The primary analysis uses the pooled active block; manipulation checks are secondary.

**Blinding:** the analyst is blind to block order and group labels until the primary analysis is
locked. The participant is not told which block is active. The experimenter does not see trial-level
results.

## 5. Participants

### Target

N=180 analysed participants, recruited without extreme-group enrichment for the primary measurement
question.

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
- Prior participation in an ART or source-monitoring experiment with the same stimuli.
- Inability to complete the practice block or comprehension check.

Group labels are recruitment strata, not diagnoses. Participants with aphantasia are not described as
impaired.

### Sample-size rationale

N=180 is a planning target. Under the Stage 0B power approximation
([`results/art/ART_STAGE0_POWER.json`](../../results/art/ART_STAGE0_POWER.json)), true ICC 0.75 with
N=180 gives 0.961 power for a lower 95% bound above 0.60. This is a planning result, not human
evidence. The study is powered for the reliability hypothesis; group differences are secondary and
will be reported with confidence intervals, not as confirmatory tests.

## 6. Materials

- Symbolic scenes generated by the existing ANIMUS scene engine; no generative AI in the loop.
- Deterministic text cues for imagined and described conditions.
- Four evidence cards with the likelihood table in the ART specification; at most two samples per
  trial, without replacement.
- VVIQ-2 (imagery vividness).
- SIAQ (spatial imagery).
- OSIVQ (exploratory comparator).
- Beads task (draws-to-decision) as a discriminant measure.
- Working-memory composite (operation span or digit span; fixed before registration).
- LSHS-E (exploratory, non-clinical).
- Usability, fatigue, strategy, and adverse-experience items.
- Optional classification-image task for a convergent subsample.

## 7. Procedure

1. Consent and eligibility screen.
2. Practice block with feedback on the card interface and a comprehension check.
3. Occasion 1: form A; active and yoked blocks in counterbalanced order.
4. Questionnaires and demographics.
5. Occasion 2 (day 14): form B; blocks in reversed order.
6. Debrief: explains the four sources and the card probabilities; offers withdrawal of data.

Each occasion is capped at 75 minutes. Participants may stop at any time. A fatigue check occurs every
20 trials. The optional classification-image subsample completes an additional 20-minute session.

## 8. Outcomes

### Primary

1. `ARTE` at day 14, ICC(2,1) with 95% CI.
2. Active-versus-yoked difference in source accuracy or Brier score at equal information.
3. Out-of-sample predictive advantage of the EIG-cost policy over alternatives.

### Secondary

- `d_prime_seen_imagined`, criterion `c`, full confusion matrix.
- Brier score, ECE, overconfidence.
- Sampling quality, termination quality, number of cards sampled.
- Cost and reliability sensitivity.
- Model-free query diagnosticity.
- `meta_d_prime` (gated).
- Convergent/discriminant correlations.
- Measurement invariance.
- Usability, fatigue, adverse events.

## 9. Analysis plan

The full plan is in [`docs/program/ART_ANALYSIS_PLAN.md`](ART_ANALYSIS_PLAN.md). In brief:

- Hierarchical Bayesian model with weakly informative priors.
- Simulation-based calibration before fitting human data.
- ICC(2,1), SEM, and MDC95 for reliability.
- Model comparison with LOO/WAIC and posterior predictive checks.
- Mixed-effects models for active-versus-yoked and cost/reliability contrasts.
- Multigroup CFA for questionnaire comparators; hierarchical model with group-specific parameters.
- FIML or multiple imputation for missing data.
- One primary endpoint per hypothesis; secondary endpoints labelled exploratory.
- Blinded primary analysis; preregistered multiverse; all deviations logged.

## 10. Decision gates

| Gate | Criterion | If failed |
| --- | --- | --- |
| Feasibility | >=80% completion; >=90% comprehension; no serious adverse events | Revise task; do not proceed |
| Reliability | ICC >=0.75; lower 95% CI >=0.60 for `ARTE` | Publish psychometric null; stop training RCT |
| Active benefit | Standardized difference >=0.20 or calibration advantage with CI excluding 0 | Drop active-benefit claim; keep descriptive |
| Policy | EIG-cost model beats alternatives out of sample | Report descriptive only; no normative claim |
| Incremental validity | `ARTE` adds prediction beyond `d_prime`/`meta_d_prime` | Narrow the construct claim |
| Discriminant | `ARTE`-beads r <0.70 | Revise task or drop distinctness claim |
| Invariance | Delta CFI <0.01; Delta RMSEA <0.015 | Restrict to lab/device; no group comparison |
| Training | Measurement gates pass; separate RCT registration | Remain blocked |
| Clinical | Separate IRB, clinical sample, registration | Remain blocked |

## 11. Ethics and data management

- Local-first: no cloud, no telemetry, no external API.
- Pseudonymous participant IDs; raw data in local SQLite; de-identified export.
- No neural data; no clinical sample; no diagnosis.
- Participants may withdraw; data are deleted on request before aggregation.
- The optional classification-image task is separate and consent-gated.
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

- That ART measures "reality" outside the experimental sources.
- That ART diagnoses or predicts psychosis.
- That ART improves imagery or clinical outcomes.
- That the task is a neural decoder.
- That the instrument is "first" or "revolutionary."
