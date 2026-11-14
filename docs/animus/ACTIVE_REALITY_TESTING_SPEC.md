# Active Reality Testing (ART) v1

## Status

- **Stage:** 0B, specification and simulation. No human data have been collected.
- **Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.
- **Canonical claims:** `claim.active_reality_testing_measurement` (UNVALIDATED),
  `claim.active_reality_testing_training` (BLOCKED), `claim.active_reality_testing_clinical` (BLOCKED).
- **Protocol version:** `ANIMUS-ART-v1`.
- **Stage 0B evidence:**
  [`results/art/ART_STAGE0_SIMULATION.json`](../../results/art/ART_STAGE0_SIMULATION.json),
  [`results/art/ART_STAGE0_POWER.json`](../../results/art/ART_STAGE0_POWER.json), and
  [`results/art/ART_MODEL_RECOVERY.json`](../../results/art/ART_MODEL_RECOVERY.json).
  The simulation uses 120 simulated participants and 120 trials: mean accuracy 0.458, mean ARTE
  0.444, mean queries 1.79, and mean sampling quality 0.875. Recovery (60 participants, 80 trials)
  gives beta bias -0.131, lambda bias -0.035, and tau bias -0.025. The N=180 power check gives 0.961
  power for true ICC 0.75 with a lower bound above 0.60. None of these results is human validation.
- **Preregistration:** draft in [`docs/program/ART_PREREGISTRATION.md`](../program/ART_PREREGISTRATION.md);
  not yet registered.

This document specifies a behavioural instrument for **Active Reality Testing**: how a person selects
and uses evidence to decide whether an experience was seen, imagined, described, or is new. It is not
a decoder, a diagnostic test, a measure of imagery strength, or a clinical instrument.

## Why this construct

The Source and Imagination Monitor (SIM) measures a passive post-hoc source judgment. That is
necessary but incomplete. In everyday life, and in clinical accounts of source confusion, people do
not only receive evidence; they **seek** it. They check perceptual detail, search for a generation
tag, or test whether a context feels familiar. The quality of that search may be a separable ability.

The closest literatures are:

- source monitoring and reality monitoring (Johnson et al., 1993; Dijkstra et al., 2022);
- metacognitive control of information search (Schulz et al., 2023; Hu et al., 2026);
- evidence gathering and jumping-to-conclusions in delusions (Dudley et al., 2016).

A non-exhaustive search found no indexed report that combines source monitoring with active
source-diagnostic evidence selection and scores query choice against an expected-information-gain
policy. This is a design hypothesis, not a priority claim. The word "first" must not be used.

## Construct definition

**Active Reality Testing (ART)** is the accuracy, calibration, and efficiency with which a person
selects and uses evidence to resolve uncertainty about the source of an experience.

The instrument reports four separate axes. It does not combine them into a score.

| Axis | Definition | Primary metric | Status |
| --- | --- | --- | --- |
| Source discrimination | Ability to distinguish seen from imagined content | `d_prime_seen_imagined` | Primary |
| Source calibration | Whether confidence tracks source accuracy | Brier score, ECE | Primary |
| Active efficiency | Quality of selected evidence relative to a computable EIG baseline | `ARTE` | Primary |
| Control sensitivity | Adjustment of sampling to cost and reliability | Cost/reliability contrasts | Secondary |

## Task

### Conditions

Each item has exactly one true source:

1. **seen** - visible in a symbolic scene during encoding;
2. **imagined** - a neutral cue asked the participant to imagine the item;
3. **described** - a verbal description was presented without an imagery instruction;
4. **new** - not presented in any form.

The `described` condition separates "imagined" from "verbal label." The `new` condition provides a
baseline for guessing and false recognition.

### Encoding

- Scenes come from the existing symbolic `SceneGraph`; no generative model is in the loop.
- Seen items are rendered for a fixed exposure.
- Imagined and described items use deterministic text cues.
- No condition label is shown.
- Encoding is incidental: participants study the scene, not source labels.
- A filled delay separates encoding from test.

### Test

On each trial the participant sees a source-neutral probe. Before judging the source, the participant
may sample at most two of four **evidence cards**. Each card costs points from a fixed budget and may
be sampled once. The participant then chooses one of four sources and reports confidence.

| Card | Seen | Imagined | Described | New | What it probes |
| --- | ---: | ---: | ---: | ---: | --- |
| Perceptual detail | 0.80 | 0.35 | 0.25 | 0.20 | Was there a visual trace? |
| Generation tag | 0.30 | 0.75 | 0.55 | 0.20 | Was it self-generated? |
| Context tag | 0.70 | 0.65 | 0.60 | 0.20 | Was it encoded at all? |
| Novelty tag | 0.20 | 0.25 | 0.30 | 0.80 | Does it feel new? |

The values are the probability of a positive card signal conditional on the true source. They are
**initial design values**, to be calibrated in the pilot. The participant is trained on the card
meaning; the model uses the same likelihood table.

Two cards are sampled at most, from a four-card menu. This is deliberate: if every available card
were sampled, cumulative EIG would not depend on the order or subset, and `ARTE` would be undefined.
The four-card/two-query design ensures that the second choice is a genuine selection problem.

### Active and yoked passive blocks

- 80 test trials: 40 active and 40 yoked passive, order counterbalanced.
- Active trials: the participant chooses cards; each card costs points; the budget is 60 points.
- Yoked passive trials: replay a matched active participant's card sequence. The participant sees the
  same evidence in the same order but does not choose it.
- The yoked condition controls information quantity, time on task, and motor engagement. It isolates
  the value of **selection**, not the value of more information.
- Training: 10 trials with feedback and a comprehension check.
- Main blocks: no trial-level feedback.
- Two occasions: day 0 and day 14; 60-75 minutes per occasion.

The client never receives `true_source`, correctness, or the model posterior for the current trial.
The response payload contains only card choices, source choice, confidence, latency, and an optional
abstention flag.

### Trial count

- 80 trials per occasion for the primary estimates.
- At least 40 active trials per occasion for ARTE.
- `meta_d_prime` is reported only when the trial gate is met or a hierarchical model with partial
  pooling is used.
- A session stops at 75 minutes. Partial data are reported with an explicit `insufficient` status.

## Generative model

For person `i`, source `s` in `(seen, imagined, described, new)`, prior `pi_s`, and evidence cards
`q`:

```text
p(s | e_1..e_k) proportional to pi_s * product_q P(e_q | s, q)
EIG(q) = H(p(s)) - E_{e_q}[H(p(s | e_q))]
```

The person-level evidence gain `d_i` sharpens or flattens the card likelihoods through a logit scale:

```text
p_eff(q, s; d_i) = sigmoid(d_i * logit(p(q, s)))
```

This is a measurement parameter, not a claim that people literally compute logits.

### Query policy

At each step the available cards have expected information gains `EIG_q` and costs `c_q`. The model
uses a normalized utility:

```text
u_q = beta_i * (EIG_q / max(EIG) - lambda_i * c_q)
P(q) proportional to exp(u_q)
P(stop) proportional to exp(tau_i)
```

Parameters:

- `d_i` - evidence gain / source discriminability;
- `bias_i` - source-response bias;
- `meta_d_i` - confidence efficiency;
- `beta_i` - sensitivity to relative expected information gain;
- `lambda_i` - cost sensitivity;
- `tau_i` - stopping threshold;
- `lapse_i` - lapse rate.

The normalization by `max(EIG)` is deliberate: raw EIG in bits is small relative to a one-point cost,
so an unnormalized utility would make the policy nearly random and weakly identified. The normalized
utility is the Stage 0B implementation; the preregistration fixes it before human data.

### Ideal-observer baselines

- `greedy_eig`: one-step-greedy cumulative EIG without replacement. This is a strong computable
  baseline, not a claim of global optimality over the finite horizon.
- `random_eig`: expected cumulative EIG when cards are sampled uniformly without replacement.
- `ARTE`: `(human_eig - random_eig) / (greedy_eig - random_eig)`, bounded to `[0, 1]`, with the raw
  value retained. When the denominator is near zero - including no query, or sampling the full card
  set - `ARTE` is `null` with `insufficient_queries`.

The model is a design and simulation model. It is not a fit to human data and does not establish that
people use EIG.

## Estimands and reporting

### Primary

- `d_prime_seen_imagined`: 2x2 discrimination between seen and imagined trials.
- Brier score for source correctness.
- `ARTE`: active evidence-selection efficiency.
- Test-retest ICC(2,1) for `ARTE`, with 95% CI.

### Secondary

- Criterion `c`, externalization rate, full 4x4 confusion matrix.
- ECE and overconfidence.
- Sampling quality, termination quality, number of cards sampled.
- Cost sensitivity: change in sampling under high versus low cost.
- Model-free query diagnosticity: mutual information between chosen card and source.
- `meta_d_prime`, only when the trial gate is met.
- Response time, abstention, strategy report, fatigue.

### Explicitly not reported

- A composite "reality score."
- A diagnosis, risk category, or clinical prediction.
- An imagery-strength estimate.
- A neural or physiological inference.
- A claim that the task measures "reality" outside the experimental sources.

## Hypotheses

- **H1 (active benefit):** active selection improves source accuracy or calibration relative to yoked
  passive at equal information.
- **H2 (policy):** an EIG-cost policy predicts query choices better than fixed-threshold, heuristic,
  or random policies out of sample.
- **H3 (reliability):** `ARTE` has a 14-day ICC(2,1) of at least 0.75, with a lower 95% bound above
  0.60.
- **H4 (incremental validity):** `ARTE` predicts source accuracy or calibration beyond `d_prime` and
  `meta_d_prime`.
- **H5 (discriminant):** `ARTE` is distinct from beads-task draws-to-decision (r < 0.70).
- **H6 (control):** participants adapt sampling to card cost and reliability.
- **H7 (exploratory):** `ARTE` relates to imagery vividness and schizotypy in a non-clinical sample.
  No clinical or continuum claim.

## Reliability and validity plan

The full protocol is in [`docs/program/ART_PREREGISTRATION.md`](../program/ART_PREREGISTRATION.md)
and the analysis plan in [`docs/program/ART_ANALYSIS_PLAN.md`](../program/ART_ANALYSIS_PLAN.md).

| Domain | Evidence required |
| --- | --- |
| Content validity | Cognitive interviews (N=24), expert review, accessibility review |
| Structural validity | Model comparison and posterior predictive checks |
| Reliability | ICC(2,1), SEM, MDC95 at 14 days |
| Measurement error | Bland-Altman and MDC95 |
| Hypotheses testing | Convergent with SIM, VVIQ-2, SIAQ; discriminant with beads task and working memory |
| Known-groups | Imagery strata and schizotypy (exploratory) |
| Responsiveness | No-intervention interval; training RCT only after measurement passes |
| Measurement invariance | Device class, order, imagery stratum, age, gender |

## Boundaries

- **Not a diagnostic test.** No clinical sample is recruited in Stage 1B/2B. Aphantasia is treated as
  variation, not deficit.
- **Not a neural decoder.** No EEG, fMRI, or other neural data are used.
- **Not a measure of imagery strength.** Source attribution and active evidence selection may
  dissociate from vividness.
- **Not validated.** All claims remain `UNVALIDATED` or `BLOCKED` until the registered gates pass.
- **Not a priority claim.** The search is non-exhaustive; "first" and "revolutionary" are prohibited.

## Failure modes

| Failure | Response |
| --- | --- |
| Participants ignore card probabilities | Training, comprehension check, simplify the card menu |
| Cards too diagnostic (ceiling) | Calibrate likelihoods in the pilot; adaptive difficulty |
| Cards too weak (floor) | Increase trials or reliability; stop if uninformative |
| Active versus passive confound | Yoked passive at equal information; counterbalance order |
| Working-memory confound | WM composite covariate; optional low-WM variant |
| Model non-identifiability | SBC, parameter recovery, simpler model fallback |
| ARTE circularity | Model-free mutual-information metric alongside ARTE |
| Yoked partner unavailable | Precomputed stratified sequence, logged |
| Client retries | Idempotency keys; server state |
| Truth leakage | Server-only `true_source`; contract tests |
| Clinical overreach | Claims blocked; no clinical sample |

## Open questions

1. Are the card likelihoods learnable without explicit probability instruction?
2. Does active selection improve calibration, accuracy, or both?
3. Is `ARTE` separable from working memory and generic evidence gathering?
4. Does the 14-day interval capture state or trait variance?
5. Which model comparison is decisive: EIG-cost versus confidence-in-control?
6. Can the task be shortened without losing reliability?
7. Does the task show measurement invariance across device classes?
8. Is there a defensible non-clinical bridge to source-monitoring research without a continuum claim?
