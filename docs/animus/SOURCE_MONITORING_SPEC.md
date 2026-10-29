# Source and Imagination Monitor (SIM) v1

## Status

- **Stage:** 0, specification and simulation. No human data have been collected.
- **Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.
- **Canonical claims:** `claim.source_monitoring_measurement` (UNVALIDATED),
  `claim.source_monitoring_training` (BLOCKED), `claim.source_monitoring_clinical` (BLOCKED).
- **Protocol version:** `ANIMUS-SIM-v1`.
- **Stage 0 evidence:** [`results/prm/PRM_STAGE0_SIMULATION.json`](../../results/prm/PRM_STAGE0_SIMULATION.json).
  Simulation-only: 120 simulated participants, 120 trials, recovery bias +0.051, RMSE 0.197, and a
  28.9% final-entropy reduction versus the fixed stratified schedule. This is not human validation.
- **Preregistration:** draft in [`docs/program/PRM_PREREGISTRATION.md`](../program/PRM_PREREGISTRATION.md);
  not yet registered.

This document specifies a behavioural instrument for **epistemic source monitoring**: how a person
decides whether an experience was seen, imagined, described, or is new. It is not a decoder, a
diagnostic test, or a measure of imagery strength.

## Why this construct

The platform already measures discrimination thresholds, reconstruction beliefs, and confidence.
Those surfaces answer "what is the scene?" and "how uncertain is the belief?" They do not answer the
prior question that makes imagination scientifically interesting: **how does a person know whether
the evidence in front of them came from the world or from their own mind?**

Source-monitoring research provides a mature behavioural operationalization of that question. The
literature is summarized in [`docs/animus/EVIDENCE_MAP.md`](EVIDENCE_MAP.md) and in the Stage 0
research record. The key design hypothesis is that source discrimination, source bias, and source
calibration are separable individual differences that can be measured without neural decoding.

## Construct definition

**Epistemic source monitoring (ESM)** is the accuracy, calibration, and efficiency with which a person
attributes a remembered or imagined experience to its source under uncertainty.

The instrument reports four separate axes. It does not combine them into a score.

| Axis | Definition | Primary metric | Status |
| --- | --- | --- | --- |
| Source discrimination | Ability to distinguish seen from imagined content | `d_prime` from a 2x2 seen/imagined confusion matrix | Primary |
| Source bias | Tendency to call imagined content "seen" | Criterion `c`; positive = externalizing | Primary |
| Source metacognition | Whether confidence tracks source accuracy | Brier score, expected calibration error, overconfidence | Primary |
| Epistemic efficiency | Person-parameter uncertainty removed per unit burden | Posterior entropy reduction per minute | Exploratory |

## Task

### Conditions

Each item has exactly one true source:

1. **seen** - the object or feature was visible in the scene during encoding;
2. **imagined** - the object or feature was not visible; a neutral cue asked the participant to
   imagine it;
3. **described** - the object or feature was not visible; a verbal description was presented without
   an imagery instruction;
4. **new** - the object or feature was not presented in any form.

The `described` condition is essential. Without it, "imagined versus seen" is confounded with
"verbal label versus visual experience." The `new` condition provides a baseline for guessing and
for false recognition.

### Encoding

- Scenes are generated from the existing symbolic `SceneGraph`. The server holds the scene version,
  item table, and truth labels.
- Seen items are rendered for a fixed exposure. Imagined and described items are presented as
  deterministic text cues. No condition label is shown to the participant.
- Encoding is incidental: participants are asked to study the scene, not to memorize source labels.
- A filled delay separates encoding from test.

### Test

On each trial the participant sees a single probe and chooses one of four sources, then reports
confidence in `[0.5, 1.0]`. Abstention is allowed and analysed as a separate response category.

The client never receives `truth`, `condition`, correctness, or expected information gain for the
current trial. The response payload contains only the choice, confidence, latency, and an optional
abstention flag.

### Trial count

- 120 trials per occasion for `d_prime` and Brier.
- At least 200 trials per person across occasions before `meta_d_prime` is reported.
- A session is stopped at 60 minutes. Partial data are reported with an explicit `insufficient`
  status rather than silently imputed.

## Generative model

For person `i` and item `j` with true source `s_j` in the ordered set
`(new, imagined, described, seen)`:

```text
x_ij ~ Normal(mu_s, sigma^2)
response = interval(x_ij; c_1, c_2, c_3)
```

The means are parameterized so that evidence increases from `new` to `seen`:

```text
mu_seen       =  d / 2
mu_imagined   = -d / 2
mu_described  = -d / 2 - described_gap
mu_new        = -d / 2 - described_gap - new_gap
```

`d = mu_seen - mu_imagined` is the primary source-discrimination parameter. The criteria are
monotone and share a bias shift:

```text
c_k = c_k^0 + bias,   k = 1, 2, 3
```

The criterion `c` for the seen/imagined contrast is computed from the observed hit and false-alarm
rates, with a log-linear correction for extreme rates. Positive `c` means a conservative bias
(fewer "seen" reports); the externalization sign convention is documented in the scoring module.

Confidence is modelled as a monotone function of the posterior probability that the chosen source is
correct, with a metacognitive noise parameter. The ideal-observer confidence is a diagnostic
baseline, not a claim that participants are ideal observers.

## Adaptive selection

The adaptive engine chooses the next item to maximize the expected reduction in entropy of the
person-level posterior:

```text
j* = argmax_j E_{r ~ p(r | theta, item_j)} [ H(p(theta | D)) - H(p(theta | D, item_j, r)) ]
```

subject to:

- a global coverage floor of at least 15% of trials per source;
- no more than 40% of trials from one item family;
- the production protocol adds block-level coverage (both seen and imagined in every block of 20
  trials); the Stage 0 simulator enforces the global floor and the 40% cap.

`theta` contains `d`, `bias`, and optionally `meta_d_prime`. This is deliberately different from the
current ANIMUS adaptive policy, which reduces entropy over scene variables. The Stage 0 simulator
uses a discrete grid over `theta` so the calculation is deterministic and dependency-free. The
production estimator may use Laplace or particle approximations, but must pass the same recovery
tests.

## Yoked control

The adaptive arm is compared with a **yoked fixed schedule** that preserves:

- item content and order;
- condition counts per block;
- total trials and time-on-task;
- confidence elicitation.

The yoked schedule is generated from a matched participant's adaptive sequence. If no match is
available, a stratified random schedule with the same block constraints is used and the fallback is
logged. The comparison isolates the effect of selection, not the effect of practice or stimulus
content.

## Estimands and reporting

### Primary

- `d_prime_seen_imagined`: 2x2 discrimination between seen and imagined trials.
- `brier_score`: mean squared error of confidence for source correctness.
- Test-retest ICC(2,1) for both, with 95% confidence intervals.

### Secondary

- Criterion `c` and externalization rate.
- Expected calibration error (10 equal-width bins).
- Overconfidence (mean confidence minus accuracy).
- Full 4x4 confusion matrix.
- `meta_d_prime`, only when the trial gate is met; otherwise `null` with a reason.
- Posterior entropy reduction per minute.
- Response time, abstention rate, and strategy report.

### Explicitly not reported

- A composite "source monitoring score."
- A diagnosis or risk category.
- An imagery-strength estimate.
- A neural or physiological inference.

## Reliability and validity plan

The full protocol is in [`docs/program/PRM_PREREGISTRATION.md`](../program/PRM_PREREGISTRATION.md)
and the analysis plan in [`docs/program/PRM_ANALYSIS_PLAN.md`](../program/PRM_ANALYSIS_PLAN.md).

The validation matrix follows COSMIN domains:

| Domain | Evidence required |
| --- | --- |
| Content validity | Cognitive interviews (N=24), expert review, accessibility review |
| Structural validity | Generative-model comparison and posterior predictive checks |
| Internal consistency | Not applicable to a generative behavioural model; reported for questionnaire comparators only |
| Reliability | ICC(2,1), SEM, MDC95 at 7 days |
| Measurement error | Bland-Altman and MDC95 |
| Hypotheses testing | Convergent/discriminant patterns with VVIQ-2, SIAQ, working memory |
| Known-groups | Aphantasia/hypophantasia, typical, hyperphantasia strata |
| Responsiveness | No-intervention interval; training RCT only after measurement passes |
| Measurement invariance | Group and device-class invariance |

## Boundaries

- **Not a diagnostic test.** Aphantasia is treated as variation, not deficit. No clinical sample is
  recruited in Stage 1.
- **Not a neural decoder.** No EEG, fMRI, or other neural data are used.
- **Not a measure of imagery strength.** The task measures source attribution, which may dissociate
  from vividness.
- **Not validated.** All claims remain `UNVALIDATED` or `BLOCKED` until the registered validation
  gates pass.

## Failure modes

| Failure | Response |
| --- | --- |
| All items exhausted before the trial target | Report `insufficient`; no d_prime |
| Posterior degenerates to one condition | Coverage constraint; log and resample |
| Yoked schedule unavailable | Stratified random fallback, logged |
| Client retries a submission | Idempotent by `client_trial_id` |
| Scene version mismatch | 409; restart the session |
| Participant reports no imagery | Allowed; analysed as strategy, not failure |
| Fatigue or distress | Stop rule; partial data; adverse-event log |
| Device class differs | Record browser/GPU; test invariance; restrict to lab if needed |

## Open questions

1. Are source discrimination and source bias separable in a hierarchical model, or does a single
   latent factor explain both?
2. Does adaptive EIG over person parameters improve precision per minute relative to a yoked fixed
   schedule by at least 20%?
3. Is source monitoring stable enough to be a trait, or is it state-like?
4. Do imagery extremes differ on source bias, source discrimination, or both?
5. Does the task survive device and renderer variation without measurement non-invariance?
