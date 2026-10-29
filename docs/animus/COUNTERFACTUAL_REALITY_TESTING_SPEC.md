# Counterfactual Reality Testing (CRT) v1

## Status

- **Stage:** 0C, specification and simulation. No human data have been collected.
- **Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.
- **Canonical claims:** `claim.counterfactual_reality_testing_measurement` (UNVALIDATED),
  `claim.counterfactual_reality_testing_training` (BLOCKED), and
  `claim.counterfactual_reality_testing_clinical` (BLOCKED).
- **Protocol version:** `ANIMUS-CRT-v1`.
- **Stage 0C evidence:**
  [`results/crt/CRT_STAGE0_SIMULATION.json`](../../results/crt/CRT_STAGE0_SIMULATION.json),
  [`results/crt/CRT_MODEL_RECOVERY.json`](../../results/crt/CRT_MODEL_RECOVERY.json), and
  [`results/crt/CRT_STAGE0_POWER.json`](../../results/crt/CRT_STAGE0_POWER.json).
- **Preregistration:** draft in [`docs/program/CRT_PREREGISTRATION.md`](../program/CRT_PREREGISTRATION.md);
  not yet registered.

This document specifies a behavioural instrument for **Counterfactual Reality Testing**: how a person
predicts the consequence of a source-diagnostic test before seeing it, and uses the resulting
prediction error to revise a source attribution. It is not a decoder, a diagnostic test, a measure of
imagery strength, or a clinical instrument.

## Why this construct

Source-monitoring research asks how people attribute an experience to perception or imagination
(Johnson et al., 1993). Active Reality Testing (ART) adds **selection** of evidence before the source
judgment. CRT adds a further, prospective step: before the test outcome is revealed, the person states
what they expect it to be and how confident they are. The test then provides a **counterfactual**
comparison between the predicted and observed consequence.

The design is deliberately not autobiographical counterfactual imagination. Generating a vivid
counterfactual scenario can itself contaminate source memory (Libby, 2003; Dhammapeera et al., 2024).
CRT uses a sparse, experimenter-defined test consequence, so the prediction is an epistemic probe, not
a new imagined episode.

Relevant evidence:

- Lower memory precision is associated with misattributing self-generated experiences to external
  sources (Kwon et al., 2022).
- People track the epistemic status of real and imagined counterfactual alternatives (Espino & Byrne,
  2021).
- Counterfactual comparisons inform the sense of agency (Kulakova et al., 2017).
- Visual motor imagery recruits forward models, and self-initiated sensory consequences are attenuated
  (Okanou et al., 2026; Mifsud et al., 2018).
- Impaired corollary discharge is associated with reality-monitoring deficits and externalization in
  clinical samples (Samantaray et al., 2025); this motivates measurement, not a clinical claim.

A non-exhaustive search found no indexed report that combines source monitoring with **prospective
counterfactual prediction of a test outcome** and scores prediction-weighted information gain against
a meta-EIG policy. This is a design hypothesis, not a priority claim. The words "first" and
"revolutionary" must not be used.

## Construct definition

**Counterfactual Reality Testing (CRT)** is the accuracy, calibration, and efficiency with which a
person:

1. predicts the consequence of a source-diagnostic test before observing it;
2. uses the prediction and the observed outcome to revise a source attribution;
3. selects further tests according to their expected **meta-information** value; and
4. reports confidence that tracks both source accuracy and prediction accuracy.

The instrument reports separate axes. It does not combine them into a score.

| Axis | Definition | Primary metric | Status |
| --- | --- | --- | --- |
| Source discrimination | Seen versus imagined attribution | `d_prime_seen_imagined` | Primary |
| Prediction accuracy | Whether the predicted test consequence matches the outcome | `prediction_accuracy` | Primary |
| Prediction calibration | Whether prediction confidence tracks prediction correctness | `prediction_ece` | Primary |
| Meta-information efficiency | Quality of selected tests relative to a computable meta-EIG baseline | `CRTE_meta` | Primary |
| Outcome-information efficiency | Quality of selected tests relative to an outcome-EIG baseline | `CRTE_eig` | Secondary |
| Imagination inflation | Externalization after prediction-consistent imagined experience | `imagination_inflation_rate` | Secondary |
| Active selection | Selection benefit relative to a passive control | Calibration/accuracy contrast | Exploratory in Stage 0C |

## Task

### Sources

Each item has exactly one true source:

1. **seen** - visible in a symbolic scene during encoding;
2. **imagined** - a neutral cue asked the participant to imagine the item;
3. **described** - a verbal description was presented without an imagery instruction;
4. **new** - not presented in any form.

The `described` condition separates imagination from a verbal label. The `new` condition provides a
guessing and false-recognition baseline.

### Tests

On each trial the participant sees a source-neutral probe. Before judging the source, the participant
may select at most two of six **tests**. Each test costs points from a fixed budget and may be used
once. For every selected test, the participant first predicts the test outcome (yes/no) and reports
prediction confidence. The outcome is then revealed. The participant may select a second test, predict
again, and finally choose one of the four sources and report source confidence.

| Test | Seen | Imagined | Described | New | Cost | Complexity | Agency | What it probes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Viewpoint shift | 0.80 | 0.40 | 0.25 | 0.20 | 1.5 | 2 | 0.30 | Does the content survive a viewpoint change? |
| Generation check | 0.30 | 0.75 | 0.55 | 0.20 | 1.0 | 1 | 0.40 | Was it self-generated? |
| Context check | 0.70 | 0.65 | 0.60 | 0.20 | 1.0 | 1 | 0.30 | Was it encoded in the study context? |
| Intention check | 0.20 | 0.70 | 0.25 | 0.20 | 2.0 | 3 | 0.70 | Was there an intention to imagine? |
| Description check | 0.25 | 0.50 | 0.80 | 0.20 | 1.0 | 1 | 0.30 | Was it verbally described? |
| Fluency check | 0.55 | 0.55 | 0.55 | 0.55 | 0.5 | 1 | 0.30 | Does it feel fluent? |

The values are the probability of a positive test signal conditional on the true source. They are
**initial design values**, to be calibrated in the pilot. The fluency test is a **zero-diagnosticity
trap**: it has no counterfactual discrimination, so a rational meta-EIG policy should avoid it. The
proportion of fluency choices is a manipulation check, not a primary outcome.

### Conditions

The Stage 1 design is a 2x2 plus an observational baseline:

| Condition | Test selection | Prediction required |
| --- | --- | --- |
| `observe` | none | no |
| `active_intervene` | participant chooses | no |
| `active_predict` | participant chooses | yes |
| `yoked_intervene` | donor sequence | no |
| `yoked_predict` | donor sequence | yes |

- 120 trials per occasion: 4 cells x 30 trials, plus 20 `observe` trials.
- Two occasions: day 0 and day 14; 60 trials per occasion, 15 per cell plus 10 observe.
- The order of cells is counterbalanced.
- The donor sequence is taken from a matched participant and a matched item position; the yoked
  participant sees the same test identities but generates their own outcomes and predictions.
- `active_predict` uses a meta-EIG policy. `active_intervene` uses an outcome-EIG policy. The primary
  prediction contrast is `active_predict` minus `active_intervene`.

Stage 0C found that **matched-sequence yoking cannot identify an active-selection superiority effect**
on accuracy or calibration: both arms receive the same test distribution. The active-selection
contrast is therefore exploratory in this protocol. A random-passive control matched on the number of
tests is required before any active-selection claim.

### Encoding

- Scenes come from the existing symbolic `SceneGraph`; no generative model is in the loop.
- Seen items are rendered for a fixed exposure.
- Imagined and described items use deterministic text cues.
- No condition label is shown.
- Encoding is incidental: participants study the scene, not source labels.
- A filled delay separates encoding from test.

### Test flow

1. Source-neutral probe.
2. Select a test or stop.
3. Predict the test outcome and report prediction confidence.
4. Observe the outcome.
5. Optionally select a second test and repeat steps 3-4.
6. Choose one of four sources and report source confidence.
7. Optional abstention and strategy report.

The client never receives `true_source`, correctness, or the model posterior for the current trial.
The response payload contains only test choices, predictions, prediction confidence, source choice,
source confidence, latency, and an optional abstention flag.

## Generative model

For person `i`, source `s` in `(seen, imagined, described, new)`, test `a`, prior `pi_s`, test
likelihood `p_as`, and outcome `O` in `{0,1}`:

```text
O | S=s, A=a ~ Bernoulli(sigmoid(d_i * logit(p_as)))
P | S=s, A=a ~ Bernoulli(sigmoid(pi_i * logit(p_as)))
```

`d_i` is evidence gain; `pi_i` is prediction precision. When `pi_i = 0`, the prediction is independent
of the source and CRT reduces to ART/AgRT. This nested relation is a testable model constraint, not a
claim that people literally compute logits.

The source posterior after a prediction-outcome pair is:

```text
log p(S | P, O, A) proportional to log prior
  + log P(P | S, A; pi_i)
  + log P(O | S, A; d_i)
  + b_pi * I(P = O) * m_i * I(S = seen)
```

`b_pi` is the **imagination-inflation bias**: a prediction-consistent outcome receives extra weight
for the `seen` source. `m_i` is prediction confidence. The bias is a measurement parameter, not a
clinical process claim.

### Meta-information gain

Outcome EIG is:

```text
EIG(a) = H(S) - E_{O|a}[H(S | O, a)]
```

Meta-EIG includes the prediction as a second signal:

```text
EIG_meta(a) = H(S) - E_{P,O|a}[H(S | P, O, a)]
```

Counterfactual discrimination is the mutual information between prediction and source:

```text
CD(a) = I(P; S | A=a)
```

For the fluency test, `CD(a) = 0` and `EIG_meta(a) = EIG(a)`. The Stage 0C policy assigns a large
negative utility to zero-CD tests, so a rational meta-EIG agent avoids the trap.

### Policy

At each step the available tests have meta-EIG, cost, complexity, and agency value. The model uses:

```text
u(a) = beta_i * (EIG_meta(a) / max(EIG_meta) - lambda_i * cost(a) - gamma_i * complexity(a))
       + alpha_i * agency_value(a)
P(a) = mixture of softmax(u) and positive-testing softmax
P(stop) = softmax([u(available), ..., tau_i])
```

Parameters:

- `d_i` - evidence gain / source discriminability;
- `pi_i` - prediction precision;
- `b_pi` - imagination-inflation bias;
- `beta_i` - sensitivity to relative meta-EIG;
- `lambda_i` - cost sensitivity;
- `gamma_i` - complexity sensitivity;
- `tau_i` - stopping threshold;
- `guess_i` - source guessing;
- `bias_i` - externalization bias;
- `mix_i` - mixture weight for meta-EIG versus positive testing;
- `alpha_i` - agency-value weight;
- `lapse_i` - lapse rate.

The normalization by `max(EIG_meta)` is fixed before human data: raw meta-EIG in bits is small relative
to a one-point cost and makes the policy weakly identified. A sensitivity analysis will use raw
meta-EIG.

### Source choice

```text
P(choice = j | S=s) = (1 - g_i) * I(j = MAP) + g_i * q_j
q_j = (1 - b_i) * uniform_j + b_i * I(j = seen)
```

The source posterior is first adjusted by `b_pi`; the choice model then adds guessing and
externalization. This separation is required because a seen bias can arise from source guessing,
response bias, or prediction-consistent imagination inflation.

### Ideal-observer baselines

- `greedy_meta_eig`: one-step-greedy cumulative meta-EIG without replacement. Strong computable
  baseline, not a claim of global optimality over the finite horizon.
- `random_meta_eig`: expected cumulative meta-EIG under uniform test sampling without replacement.
- `greedy_eig` and `random_eig`: outcome-only analogues.
- `CRTE_meta = (human_meta_eig - random_meta_eig) / (greedy_meta_eig - random_meta_eig)`, bounded to
  `[0, 1]`, with the raw value retained. When the denominator is near zero, `CRTE_meta` is `null` with
  `insufficient_tests`.
- `CRTE_eig` is defined analogously with outcome EIG.

The model is a design and simulation model. It is not a fit to human data and does not establish that
people use meta-EIG.

## Estimands and reporting

### Primary

- `prediction_advantage`: `active_predict` minus `active_intervene` in source accuracy.
- `CRTE_meta`: meta-information efficiency.
- `prediction_ece`: calibration of prediction correctness.
- `d_prime_seen_imagined`: 2x2 discrimination between seen and imagined trials.
- Brier score for source correctness.
- Test-retest ICC(2,1) for `CRTE_meta` and `prediction_advantage`, with 95% CI.

### Secondary

- `CRTE_eig`, `active_calibration_advantage`, `active_accuracy_advantage`.
- Criterion `c`, externalization rate, full 4x4 confusion matrix.
- `imagination_inflation_rate`: seen attribution after a high-confidence, prediction-consistent
  imagined experience.
- `confounded_test_rate`: proportion of fluency choices.
- ECE and overconfidence for source confidence.
- Sampling quality, termination quality, number of tests.
- Cost sensitivity: change in sampling under high versus low cost.
- Model-free test diagnosticity: mutual information between chosen test and true source.
- `meta_d_prime`, only when the trial gate is met.
- Response time, abstention, strategy report, fatigue.

### Explicitly not reported

- A composite "reality score."
- A diagnosis, risk category, or clinical prediction.
- An imagery-strength estimate.
- A neural or physiological inference.
- A claim that the task measures "reality" outside the experimental sources.
- A priority or "first" claim.

## Hypotheses

- **H1 (prediction advantage):** prospective prediction improves source accuracy relative to
  outcome-only active testing, with a standardized difference of at least 0.20 in the human study.
- **H2 (meta-EIG policy):** a meta-EIG-cost policy predicts test choices better than outcome-EIG,
  positive-testing, fixed, heuristic, or random policies out of sample.
- **H3 (reliability):** `CRTE_meta` has a 14-day ICC(2,1) of at least 0.75, with a lower 95% bound
  above 0.60.
- **H4 (prediction calibration):** prediction confidence tracks prediction correctness, with
  `prediction_ece <= 0.15`.
- **H5 (imagination inflation):** prediction-consistent imagined trials show a higher seen-attribution
  rate than prediction-inconsistent imagined trials, controlling for source confidence and response
  bias.
- **H6 (incremental validity):** `CRTE_meta` predicts source accuracy or calibration beyond `d_prime`
  and `meta_d_prime`.
- **H7 (discriminant):** `CRTE_meta` is distinct from beads-task draws-to-decision (r < 0.70).
- **H8 (exploratory):** `CRTE_meta` relates to imagery vividness and schizotypy in a non-clinical
  sample. No clinical or continuum claim.
- **H9 (exploratory active selection):** active selection improves calibration relative to a
  matched-sequence yoked control. Stage 0C predicts a near-null; a random-passive control is required
  before a superiority claim.

## Reliability and validity plan

The full protocol is in [`docs/program/CRT_PREREGISTRATION.md`](../program/CRT_PREREGISTRATION.md)
and the analysis plan in [`docs/program/CRT_ANALYSIS_PLAN.md`](../program/CRT_ANALYSIS_PLAN.md).

| Domain | Evidence required |
| --- | --- |
| Content validity | Cognitive interviews (N=24), expert review, accessibility review |
| Structural validity | Model comparison and posterior predictive checks |
| Reliability | ICC(2,1), SEM, MDC95 at 14 days |
| Measurement error | Bland-Altman and MDC95 |
| Hypotheses testing | Convergent with SIM/ART, VVIQ-2, SIAQ; discriminant with beads task and working memory |
| Known-groups | Imagery strata and schizotypy (exploratory) |
| Responsiveness | No-intervention interval; training RCT only after measurement passes |
| Measurement invariance | Device class, order, imagery stratum, age, gender |

## Stage 0C findings

The Stage 0C simulator is in [`backend/app/research/crt/`](../../backend/app/research/crt/). It uses
120 simulated participants and 120 trials in the full run. The recovery run fixes `alpha`, `d`, `guess`,
and `bias`. The artifacts report:

- The prediction contrast is positive and large in simulation: `active_predict` exceeds
  `active_intervene` in source accuracy by about 0.14, and `active_predict` accuracy is about 0.48.
- `CRTE_meta` is about 0.54 for the meta-EIG policy, and prediction calibration is about 0.03 ECE,
  within the design gate.
- The fluency trap rate is 0.00 for the rational meta-EIG policy.
- The active-versus-yoked **calibration** contrast is about -0.004 under matched-sequence yoking. This
  is a structural identification result, not a human null: the yoked arm receives the same test
  distribution.
- Recovery passes for the policy parameters and prediction precision: beta bias -0.016, lambda bias
  -0.033, gamma bias -0.009, tau bias 0.227, pi bias -0.010, and `b_pi` bias 0.010. The `b_pi` RMSE is
  0.105, so the imagination-inflation parameter is retained as a secondary parameter and must be
  estimated hierarchically in the human analysis.

The Stage 0C simulation decision is `CRT_STAGE0_SIMULATION_REVIEW` because the active-selection
calibration gate is not met under matched yoking. The recovery and power decisions are
`CRT_STAGE0_RECOVERY_PASS` and `CRT_STAGE0_POWER_PASS`. A REVIEW is a design result, not a failed
implementation and not human evidence.

## Boundaries

- **Not a diagnostic test.** No clinical sample is recruited in Stage 1. Aphantasia is treated as
  variation, not deficit.
- **Not a neural decoder.** No EEG, fMRI, or other neural data are used.
- **Not a measure of imagery strength.** Source attribution and prediction may dissociate from
  vividness.
- **Not validated.** All claims remain `UNVALIDATED` or `BLOCKED` until registered gates pass.
- **Not a priority claim.** The search is non-exhaustive; "first" and "revolutionary" are prohibited.
- **Not autobiographical counterfactual imagination.** The prediction is a sparse test consequence,
  not a rich imagined episode.

## Failure modes

| Failure | Response |
| --- | --- |
| Prediction is trivially easy | Calibrate likelihoods; increase test uncertainty; use prediction error |
| Prediction is independent of source (`pi=0`) | CRT reduces to ART/AgRT; report the nested result |
| Prediction contaminates source memory | Keep prediction sparse; randomize test order; compare with ART |
| Meta-EIG and EIG are indistinguishable | Increase test heterogeneity; report both; do not claim meta-specificity |
| Active versus yoked is unidentifiable | Add random-passive control; do not claim selection superiority |
| Fluency trap is ignored | Report confounded-test rate; train the test meanings |
| `b_pi` is weakly identified | Hierarchical model; SBC; report as secondary; do not diagnose |
| Model non-identifiability | SBC, parameter recovery, simpler model fallback |
| Working-memory confound | WM composite covariate; optional low-WM variant |
| Truth leakage | Server-only `true_source`; contract tests |
| Clinical overreach | Claims blocked; no clinical sample |

## Open questions

1. Are the test likelihoods learnable without explicit probability instruction?
2. Does prospective prediction improve accuracy, calibration, or both?
3. Is `CRTE_meta` separable from outcome EIG and working memory?
4. Does prediction-consistent imagination inflation survive controls for source guessing and response
   bias?
5. Does the 14-day interval capture state or trait variance?
6. Which model comparison is decisive: meta-EIG versus positive testing?
7. Can the task be shortened without losing reliability?
8. Does the task show measurement invariance across device classes?
9. Does a random-passive control reveal an active-selection benefit that matched yoking cannot?
10. Is there a defensible non-clinical bridge to source-monitoring research without a continuum claim?

## References

- Dhammapeera, P., et al. (2024). Counterfactual imagination and memory for true actions.
  DOI: [10.1080/17588928.2024.2315814](https://doi.org/10.1080/17588928.2024.2315814).
- Dijkstra, N., et al. (2024). Confidence does not distinguish imagination from reality.
  DOI: [10.1167/jov.24.5.13](https://doi.org/10.1167/jov.24.5.13).
- Espino, O., & Byrne, R. M. J. (2021). The epistemic status of counterfactual alternatives.
  DOI: [10.1037/xlm0000965](https://doi.org/10.1037/xlm0000965).
- Johnson, M. K., Hashtroudi, S., & Lindsay, D. S. (1993). Source monitoring.
  DOI: [10.1037/0033-2909.114.1.3](https://doi.org/10.1037/0033-2909.114.1.3).
- Kulakova, E., et al. (2017). Counterfactual comparison and sense of agency.
  DOI: [10.1016/j.concog.2017.01.013](https://doi.org/10.1016/j.concog.2017.01.013).
- Kwon, M., et al. (2022). Memory precision and reality monitoring.
  DOI: [10.1162/jocn_a_01814](https://doi.org/10.1162/jocn_a_01814).
- Libby, L. K. (2003). Imagination inflation and imagery perspective.
  DOI: [10.3758/bf03196128](https://doi.org/10.3758/bf03196128).
- Mifsud, N. G., et al. (2018). Visual sensory attenuation for self-initiated stimuli.
  DOI: [10.1016/j.cognition.2018.06.005](https://doi.org/10.1016/j.cognition.2018.06.005).
- Okanou, T., et al. (2026). Visual motor imagery and forward models.
  DOI: [10.1016/j.neuroscience.2026.07.015](https://doi.org/10.1016/j.neuroscience.2026.07.015).
- Samantaray, S., et al. (2025). Corollary discharge and reality monitoring.
  DOI: [10.1016/j.schres.2025.07.003](https://doi.org/10.1016/j.schres.2025.07.003).
- Tian, X., & Poeppel, D. (2010). Mental imagery as internal forward models.
  DOI: [10.3389/fpsyg.2010.00166](https://doi.org/10.3389/fpsyg.2010.00166).
