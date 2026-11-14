# PRM Stage 1 Preregistration (DRAFT)

## Registration status

- **Status:** DRAFT. Not yet submitted to OSF or a registered-report venue.
- **Version:** 0.1, 2026-10-29.
- **Protocol:** `ANIMUS-SIM-v1`.
- **Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.
- **Canonical claims:** `claim.source_monitoring_measurement` (UNVALIDATED);
  `claim.source_monitoring_training` and `claim.source_monitoring_clinical` (BLOCKED).

This draft must be reviewed by the PI, an independent statistician, and an ethics board before any
human data are collected. Deviations from the registered version will be logged and reported.

## 1. Study title

**Source and Imagination Monitor (SIM): a preregistered validation of a behavioural
source-monitoring instrument for seen, imagined, described, and new content.**

## 2. Background and rationale

Mental imagery questionnaires are widely used but have incomplete psychometric evidence, contested
cutoffs, and weak convergence with objective performance. The platform's existing instruments
measure discrimination thresholds, reconstruction beliefs, and confidence, but not the process by
which a person attributes an experience to perception or imagination. Source-monitoring research
provides a behavioural operationalization of that process, with evidence for individual differences
and clinical relevance. The present study asks whether a controlled, adaptive source-monitoring
instrument can measure that process reliably and validly in a non-clinical sample.

The study is **measurement validation**, not an intervention. A training RCT is conditional on the
measurement gates and is specified separately.

## 3. Hypotheses

### Primary hypotheses

- **H1 (reliability):** `d_prime_seen_imagined` has a 7-day test-retest ICC(2,1) of at least 0.75,
  with a lower 95% confidence bound above 0.60.
- **H2 (reliability):** Brier score has a 7-day test-retest ICC(2,1) of at least 0.75, with a lower
  95% confidence bound above 0.60.

### Secondary hypotheses

- **H3 (convergent):** `d_prime_seen_imagined` and source bias show small-to-moderate associations
  with VVIQ-2 and SIAQ (absolute r between 0.15 and 0.50). A near-zero association would challenge
  the imagery interpretation; a near-unity association would make the task redundant.
- **H4 (discriminant):** the source measures are more weakly associated with a working-memory
  composite than with the imagery questionnaires.
- **H5 (known groups):** imagery-extreme groups differ on source bias or source discrimination, with
  a continuous VVIQ-2 association reported as the primary analysis.
- **H6 (invariance):** the instrument shows configural, metric, and scalar invariance across imagery
  groups and device classes (Delta CFI < 0.01; Delta RMSEA < 0.015).
- **H7 (adaptive efficiency):** adaptive EIG yields at least 20% lower posterior SD per minute than
  a yoked fixed schedule after 60 trials, with final `d_prime` equivalent within +/-0.20.

### Exploratory

- Calibration error and overconfidence by source condition.
- `meta_d_prime` as a secondary measure, only when the trial gate is met.
- Response time and abstention.
- Strategy reports and reported imagery use.
- Association with the Launay-Slade Hallucination Scale (LSHS-E) in a non-clinical sample.

## 4. Design

**Type:** prospective, preregistered, multi-occasion, within-subject measurement study with an
embedded adaptive-versus-yoked crossover.

**Occasions:** day 0, day 7, day 28. Two alternate forms (A/B) counterbalanced across occasions.

**Arms within occasion:** adaptive and yoked fixed, order counterbalanced, separated by a filled
break. The adaptive arm is the index measure; the yoked arm is the efficiency control.

**Blinding:** the analyst is blind to arm and group labels until the primary analysis is locked. The
participant is not told which arm is adaptive. The experimenter does not see trial-level results.

## 5. Participants

### Target

N=180 analysed participants:

- 60 with self-reported aphantasia or hypophantasia (VVIQ-2 lower extreme);
- 60 typical imagery (middle range);
- 60 hyperphantasia (upper extreme).

Recruitment will screen approximately 2,000-3,000 adults to identify the extreme strata, given an
aphantasia prevalence of roughly 4%.

### Inclusion

- Age 18-65.
- Normal or corrected-to-normal vision.
- Able to complete a 60-minute online session.
- Provides informed consent.

### Exclusion

- Self-reported current neurological or psychiatric treatment.
- Current substance intoxication or acute illness.
- Prior participation in a source-monitoring experiment with the same stimuli.
- Inability to complete the practice block.

Group labels are recruitment strata, not diagnoses. Participants with aphantasia are not described
as impaired.

### Sample-size rationale

N=180 is a planning target. Under a Fisher-z approximation, true ICC 0.75 with N=180 gives a lower
95% bound near 0.61, which is close to the target. The Stage 0 power simulation
([`results/prm/PRM_STAGE0_POWER.json`](../../results/prm/PRM_STAGE0_POWER.json)) gives 0.961 power
for true ICC 0.75 with a lower bound above 0.60 under the stated normal approximation. This is a
planning result, not human evidence. The study is powered for the reliability hypothesis, not for
small group differences; group comparisons are secondary and will be reported with confidence
intervals, not as confirmatory tests.

## 6. Materials

- Symbolic scenes generated by the existing ANIMUS scene engine; no generative AI in the loop.
- Deterministic text cues for imagined and described conditions.
- VVIQ-2 (imagery vividness).
- SIAQ (spatial imagery).
- OSIVQ (object/spatial imagery) as an exploratory comparator.
- Working-memory composite (operation span or digit span; fixed before registration).
- LSHS-E (exploratory, non-clinical).
- Usability, fatigue, strategy, and adverse-experience items.

## 7. Procedure

1. Consent and eligibility screen.
2. Practice block with feedback on the response interface only, not on source accuracy.
3. Occasion 1: form A, adaptive and yoked arms, counterbalanced.
4. Questionnaires and demographics.
5. Occasion 2 (day 7): form B, adaptive and yoked arms, reversed order.
6. Occasion 3 (day 28): form A, adaptive only, for longitudinal stability.
7. Debrief: explains the four sources and the purpose; offers withdrawal of data.

Each occasion is capped at 60 minutes. Participants may stop at any time. A fatigue check occurs
every 20 trials.

## 8. Outcomes

### Primary

1. `d_prime_seen_imagined` at day 7, ICC(2,1) with 95% CI.
2. Brier score at day 7, ICC(2,1) with 95% CI.

### Secondary

- Criterion `c`, externalization rate, full confusion matrix.
- Calibration error, overconfidence.
- `meta_d_prime` (gated).
- Adaptive vs yoked posterior SD per minute; trials to posterior SD <= 0.25.
- Convergent/discriminant correlations.
- Known-groups contrasts.
- Measurement invariance.
- Usability, fatigue, adverse events.

## 9. Analysis plan

The full plan is in [`docs/program/PRM_ANALYSIS_PLAN.md`](PRM_ANALYSIS_PLAN.md). In brief:

- Hierarchical Bayesian generative model with weakly informative priors.
- Simulation-based calibration before fitting human data.
- ICC(2,1), SEM, and MDC95 for reliability.
- Multigroup CFA for questionnaire parcels; hierarchical model with group-specific parameters and
  ROPE for behavioural parameters.
- Mixed-effects model for adaptive efficiency; equivalence test on final `d_prime`.
- FIML or multiple imputation for missing data.
- One primary endpoint per hypothesis; secondary endpoints labelled exploratory.
- Blinded primary analysis; preregistered multiverse; all deviations logged.

## 10. Decision gates

| Gate | Criterion | If failed |
| --- | --- | --- |
| Feasibility | >=80% completion; >=90% comprehension; no serious adverse events | Revise task; do not proceed |
| Reliability | ICC >=0.75; lower 95% CI >=0.60 for both primary endpoints | Publish psychometric null; stop training RCT |
| Invariance | Delta CFI <0.01; Delta RMSEA <0.015 | Restrict to lab or revise; no group comparison |
| Adaptive efficiency | >=20% precision-per-minute advantage; final `d_prime` equivalent | Drop adaptive claim; keep fixed instrument |
| Construct | Source measures not redundant with generic source memory (r < 0.70) | Reframe as source memory, not imagery |

## 11. Ethics and data management

- IRB/ethics approval is required before recruitment.
- Informed consent; no deception beyond ordinary task framing; debrief.
- No clinical diagnosis; no clinical sample; aphantasia as variation.
- Local-first data collection; de-identified exports; no raw neural data.
- Data and code availability statement prepared before registration.
- Adverse events recorded and reported.
- Compensation is set by the PI and disclosed.

## 12. Registration and reporting

- OSF preregistration before data collection.
- Stage 1 registered report submitted to a methods or consciousness journal.
- STROBE for the observational validation; GRRAS for reliability reporting.
- Stage 2 report regardless of outcome.
- Any deviation from this plan is listed in a dated deviation log.

## 13. Open decisions before registration

1. Final working-memory measure and scoring.
2. Exact VVIQ-2 strata cutoffs, informed by the screening distribution.
3. Whether the day-28 occasion uses both arms or adaptive only.
4. Site/device stratification and the minimum device class for inclusion.
5. Target registered-report venue.
6. Independent statistician and adversarial collaborator.
