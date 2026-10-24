# ANIMUS — Measurement Model (experimental)

**Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`  
**Status:** experimental behavioural instrument; not a diagnosis, not a neural decoder, not a measure of
imagery strength.

ANIMUS records what a person can do with a scene they just inspected, and how well their confidence tracks
their accuracy. It deliberately does **not** infer a hidden mental image. The scene is symbolic and
inspectable; every task answer is rebuilt on the server from that scene.

## Why multiple dimensions

Mental imagery is not one quantity. Vividness, spatial manipulation, control, and metacognition dissociate,
and self-report correlates only weakly with objective performance (Pearson, 2019; 2024 mental comparison
work). A single composite would erase exactly the information that makes practice useful. ANIMUS therefore
keeps five observable dimensions separate:

| Dimension | Task family | What a high estimate means | What it does not mean |
|---|---|---|---|
| `stability` | Object reconstruction, attribute recall | The inspected object content survives a short delay | The image was vivid or durable in daily life |
| `discrimination` | Candidate comparison | The person can reject a subtly changed scene | The person has a generally accurate visual memory |
| `spatial` | Spatial layout, view inference | The person can rebuild or infer the layout | The person has strong mental rotation ability |
| `control` | Directed change | The person can choose a requested scene change | The person can control spontaneous imagery |
| `calibration` | Confidence on any trial | Confidence tracks correctness | The person is a good or poor imaginer |

The first four are ability estimates; `calibration` is a Brier score, not an ability. They are never summed.

## Ability estimate

For each ability dimension, trials are Bernoulli outcomes. With a uniform Beta prior and `s` successes in
`n` trials:

```
alpha = 1 + s
beta  = 1 + (n - s)
mean  = alpha / (alpha + beta)
var   = alpha * beta / ((alpha + beta)^2 * (alpha + beta + 1))
```

The displayed estimate is the posterior mean; the displayed uncertainty is the posterior standard
deviation. An estimate is withheld until `n >= 3`, and is labelled `collecting`, `provisional`, or
`moderate_evidence` by trial count. The prior is deliberately weak: with three successes the estimate is
0.80, not 1.00.

This is a descriptive posterior, not a validated psychometric model. It assumes exchangeable trials and
does not model practice, fatigue, or task-specific difficulty. Those are open validation questions, not
features hidden behind a score.

## Calibration

For a trial with stated confidence `c ∈ [0, 1]` and outcome `y ∈ {0, 1}`, the Brier contribution is
`(c - y)^2`. The reported Brier score is the mean over trials and is withheld until three trials; lower is
better. Calibration is shown only
alongside ability, because a well-calibrated person can still be inaccurate. A person who always says 50%
is not "well calibrated" in a useful sense; the profile must be read with the ability dimensions.
The calibration dimension deliberately has `estimate = null`; its scalar readout is `brier_score`. Showing
`1 - Brier` as an "accuracy estimate" would relabel a calibration measure as an ability.

## Task generation and scoring

`build_task(scene, task_type, seed, difficulty)` is deterministic. The task payload contains a `task_id`
fingerprint, prompt, options, preview duration, difficulty, seed, and task type, but **not**
`correct_option_id`. The server
reconstructs the same task on submission and scores the option. A task is rejected if its type, seed,
difficulty, or source version no longer matches, or if the option is unknown.

| Task | Construction | Answer |
|---|---|---|
| `attribute_recall` | Pick an attribute; distractors are plausible alternatives | The actual value |
| `style_recall` | Ask for the scene style | The actual style |
| `candidate_discrimination` | Present the source and one changed candidate | The candidate that changed |
| `spatial_view` | Ask which position opposes the current camera | The opposite view |
| `control_choice` | Ask for a requested change; options are scene values | The requested value |
| `object_reconstruction` | Token bank with targets and decoys; select remembered objects | F1 against target tokens |
| `spatial_layout` | Place target tokens on a normalized 2D grid | Mean position score |

Phase A simplifications are explicit: `spatial_view` is a multiple-choice view inference, not a
continuous mental-rotation task; `control_choice` is a selection task, not a direct manipulation task;
`candidate_discrimination` changes one visible attribute at low difficulty and several at high difficulty.
`spatial_layout` uses a discrete grid, not free-hand drawing. These are **not** validated measures of the
corresponding construct and must not be reported as such. `RECONSTRUCTION_SPEC.md` has the exact scoring
rules.

## Adaptive policy

The first two trials are warmups: object reconstruction, then attribute recall. Calibration is updated on
every trial but is not a selectable dimension. After warmup, a coverage floor selects any dimension with
`n < 2`; otherwise the policy selects the dimension with the highest expected information gain over the Beta
posterior. See `ADAPTIVE_POLICY.md` for the formula and guardrails.

Difficulty moves by at most `0.08` after a short rolling window: success raises it, failure lowers it;
it is clamped to `[0.1, 0.9]`. The heuristic follows the Challenge Point idea that learning is best at an
intermediate challenge, but ANIMUS does **not** claim that its step size is optimal or that practice
produces far transfer. The 2025 Challenge Point scoping review reports heterogeneous evidence, not a
universal recipe.

## Error signature

Reconstruction trials also produce descriptive error counts: object omissions, decoy intrusions, precision,
recall, and mean normalized spatial error. The trial outcome keeps all of them; the profile aggregates
omissions, intrusions, and mean spatial error over recent reconstruction trials and shows them separately.
They are a description of how reconstruction failed, not a symptom, a diagnosis, or a weighted component of
an ability score. The aggregation is intentionally simple and will change if validation shows that it is
unstable.

## Epistemic interview

The interview is a second, separate behavioural surface. Each binary probe has a `Beta(1, 1)` posterior
over the positive state (`present` for objects, `left` for relations). An answer with confidence `c`
contributes `c` to the hidden state and `1 - c` to the alternative, then that mass is mapped to the positive
or negative side; a correct `absent` or `right` answer therefore lowers the positive-state probability. The
first object and first spatial probe are forced for coverage when available, then the next probe maximises
expected binary entropy reduction. The final summary reports object and spatial accuracy, mean Brier, coverage, abstention,
overconfidence, and mean realised information gain.

These are not additional profile dimensions and are not summed with the five ability dimensions. A
posterior near `0.5` is an explicit statement of uncertainty, not a failed answer. The model is a design
choice; its fit to human confidence is an open validation question. See `EPISTEMIC_INTERVIEW_SPEC.md`.

## Scene Threshold

Scene Threshold is a contrastive 2-AFC task on the same symbolic scene. One option is the encoded scene; the
other differs only in object presence, x-position, or hue. The target side is counterbalanced and withheld
until scoring. A 2-down/1-up staircase sets the next delta, but the reported threshold comes from a fitted
psychometric function:

```text
p_correct(delta) = 0.5 + 0.5 × (1 - lapse) × sigmoid((delta - threshold) / slope)
```

d′ is `sqrt(2) × z(p_correct)` with a log-linear correction. The summary also reports signed A-side bias,
Brier, overconfidence, type-2 AUC when sparse classes allow it, and coverage. Because 2-AFC is used, a
yes/no criterion is not identified; only side bias is reported. Thresholds are normalized to the scene and
are not comparable across scenes. They are not imagery-strength scores, and the task has no neural or
clinical claim. See `CONTRAST_SPEC.md` and `OBSERVATORY_SPEC.md`.

## What the profile is not

- Not a diagnosis of aphantasia, hypophantasia, prosopagnosia, or any clinical condition.
- Not a measure of imagery strength, vividness, intelligence, creativity, or neural content.
- Not a treatment, cure, brain-training programme, or evidence of far transfer.
- Not comparable across people without norms, invariance testing, and a validated administration protocol.
- Not a substitute for the VVIQ, MIQ-RS, or a laboratory task; those have their own validity limits.

Aphantasia is a variation in experience, not a deficit. The UI must not frame a low ability estimate as a
failure or a high estimate as superiority.

## Research anchors

- Bainbridge, W. A., Hall, E. H., & Baker, C. I. (2019). Drawings of real-world scenes during free recall
  reveal detailed object and spatial information in memory. *Nature Communications*.
  https://doi.org/10.1038/s41467-018-07830-6
- Bainbridge, W. A., Pounder, Z., Eardley, A. F., & Baker, C. I. (2021). Quantifying aphantasia through
  drawing: Those without visual imagery show deficits in object but not spatial memory. *Cortex*.
  https://doi.org/10.1016/j.cortex.2020.11.014
- Fink, A., König, C., & Frey, A. (2026). Multidimensional Bayesian adaptive testing. *Behavior Research
  Methods*. https://doi.org/10.3758/s13428-026-03123-9
- Pearson, J. (2019). The human imagination: the cognitive neuroscience of visual mental imagery.
  *Nature Reviews Neuroscience*. https://doi.org/10.1038/s41583-019-0202-9
- Dance, C. J., et al. (2021). Aphantasia and congenital lack of visual imagery. *Consciousness and
  Cognition*. https://doi.org/10.1016/j.concog.2021.103243
- Rademaker, R. L., & Pearson, J. (2012). Training visual imagery: improvements in metacognition but not
  imagery strength. *Frontiers in Psychology*. https://doi.org/10.3389/fpsyg.2012.00224
- Melby-Lervåg, M., Redick, T. S., & Hulme, C. (2016). Working memory training does not improve
  performance on measures of intelligence or other measures of "far transfer". *Perspectives on
  Psychological Science*. https://doi.org/10.1177/1745691616635612
- Challenge Point scoping review (2025). *Journal of Motor Behavior*.
  https://doi.org/10.1080/00222895.2025.2508283
