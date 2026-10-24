# Scene Threshold — `contrast-v1` / `sdt-v1`

**Status:** experimental, local-only, code complete but unexecuted on the current host.
**Claim level:** `L1_BEHAVIORAL_ASSISTED`. This is not an imagery-strength score, a diagnosis, a neural
decoder, or a validated psychometric instrument.

## Purpose

The epistemic interview asks what the person believes about a scene. Scene Threshold asks a narrower
perceptual question: after a single encoding view, how large must a change be before the person can tell
the changed scene from the original? The task is a two-alternative forced-choice (2-AFC) contrast
discrimination task over the symbolic scene graph.

The pair is rendered from two symbolic scenes. No image model is used. The target side and the changed
feature are stored server-side and never sent before the answer is recorded.

## Session flow

1. The server snapshots an immutable source scene version.
2. The client shows that scene once, from a fixed non-interactive camera, for the trial preview duration.
3. The client receives a pair of options with the same camera, lighting, atmosphere, style, and layout.
   Exactly one option is the original; the other is a minimally changed variant.
4. The person chooses A or B, gives confidence in `[0.5, 1.0]`, or abstains.
5. The server scores the answer and chooses the next pair. No correctness feedback is shown during the
   session.
6. The session ends after `max_trials` or when no valid feature remains.
7. The summary reports d′, side bias, per-feature thresholds, calibration, coverage, and notes.

Default `max_trials = 16`; allowed range `12–24`. Forms A/B/C counterbalance the feature rotation. The
target side is not a predictable alternation: each block of two trials contains one A and one B in a
seeded order, so the design stays balanced without letting a participant infer the answer from the trial
index. The contrast seed is generated on the server and stored with the session; it is not returned to the
client, so a retry rebuilds the same pair without exposing the side schedule.

## Pair construction

Available feature types depend on the scene:

| Feature | Change | Publicly withheld |
|---|---|---|
| `object_presence` | Remove one leaf entity and relations that reference it | Target side, changed entity, delta |
| `spatial_position` | Shift one leaf entity on x by `delta × scene span`, choosing a direction with room and recording the realized delta | Target side, changed entity, delta, direction |
| `object_color` | Rotate the entity colour hue by `delta × 0.5` in HSL | Target side, changed entity, delta |

The presence pair is shown first and again at trial index 6 when the scene has more than two entities.
Spatial position is forced at trial index 1 if available. Later trials alternate spatial and colour
features with a form-dependent offset. Presence can be used as a fallback if neither continuous feature is
available.

The original and the variant differ only in the intended feature. The variant keeps the same scene id,
version metadata, renderer settings, and all unrelated entities. The public payload contains only option
ids, labels, scenes, prompt, trial id, task id, trial index, and preview duration.

## Adaptive staircase

For continuous features the initial deltas are `0.35` (spatial) and `0.45` (colour). The staircase is
2-down/1-up:

- Two consecutive correct answers lower the delta.
- One incorrect answer raises it.
- The step is `0.08` for the first two reversals, then `0.04`.
- Delta is clamped to `[0.05, 0.95]`.
- Abstentions do not move the staircase.

The staircase is a design rule for concentrating trials near the person's threshold. It is not itself the
threshold estimate. The estimate comes from the fitted psychometric function, so the adaptive schedule does
not directly determine the reported number.

## Scoring

### Sensitivity

Under the equal-variance Gaussian model for 2-AFC:

```text
d′ = sqrt(2) × z(p_correct)
```

A log-linear correction is used:

```text
p_correct = (correct + 0.5) / (n + 1)
```

`d′` is `null` with no answered trials.

### Side bias

The public bias readout is the signed proportion of A choices:

```text
side_bias = (#A / answered) - 0.5
```

This is a response-side bias, not a signal-detection criterion. Because the target side is
counterbalanced, a yes/no criterion is not identified in 2-AFC; the product therefore does not report
`criterion`.

### Threshold

For each continuous feature, the fitted model is:

```text
p_correct(delta) = 0.5 + 0.5 × (1 - lapse) × sigmoid((delta - threshold) / slope)
```

The lower asymptote is fixed at `0.5` because this is 2-AFC. The default lapse is `0.02`. The fit is a
deterministic grid search over threshold `0.02–0.98` and slope `0.02–0.60`, in steps of `0.01`. A
threshold is withheld with fewer than six usable trials. If almost every answer is correct (or almost every
answer is incorrect), the fit is marked `censored` at the low or high search boundary instead of pretending
the threshold was identified. A bootstrap interval is reported when enough resamples fit; `censored` marks
a threshold at the search boundary.

The threshold is in normalized within-scene change units. It is **not comparable across scenes**, and a
lower value is not an "imagery strength" score.

### Calibration

For answered trials:

```text
Brier = mean((confidence - accuracy)^2)
overconfidence = mean(confidence) - accuracy
```

Type-2 AUC is withheld unless there are at least three correct and three incorrect trials. It is a
descriptive confidence-separation statistic, not a meta-d′ model.

### Coverage and abstention

Abstentions are recorded with `correct = null`, are included in `n_trials`, and are excluded from
`n_answered`, d′, thresholds, and calibration. Coverage is `n_answered / n_trials`. Abstention is treated
as a valid response, not a failure.

## Reflection

After completion the person may optionally record strategies (`visual`, `spatial`, `verbal`, `semantic`,
`sensorimotor`, `guessing`) and a short note. Reflection is descriptive only and does not change any score.
It is stored locally with the session.

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/animus/studio/sessions/{session_id}/contrast/start` | Start a session and receive the first pair |
| `POST` | `/animus/studio/sessions/{session_id}/contrast/{contrast_id}/trials` | Score one trial and receive the next pair |
| `GET` | `/animus/studio/contrast/{contrast_id}` | Summary and result |
| `GET` | `/animus/studio/sessions/{session_id}/contrast` | List sessions |
| `POST` | `/animus/studio/contrast/{contrast_id}/reflection` | Add optional strategy reflection |
| `GET` | `/animus/studio/sessions/{session_id}/observatory` | Merge belief, discrimination, and reliability |

`client_trial_id` is unique per contrast and makes retries idempotent. `expected_version_id` and the
`X-Expected-Version` header guard against stale scene state. Starting a session does not persist a trial;
the first trial is stored only when it is submitted.

## What the task does not establish

- It does not measure neural imagery, dream content, or hidden visual experience.
- It does not produce a diagnosis, a clinical score, or a treatment effect.
- It does not support "imagery training", "brain training", or far-transfer claims.
- It does not make thresholds comparable between different scenes, forms, displays, or people.
- It has not been validated against an independent human sample in this repository.

## Research anchors

The design is informed by, but not validated by, work on scene memory, aphantasia heterogeneity,
confidence–performance dissociations, change detection, and adaptive psychophysics:

- Bainbridge, Hall & Baker (2019), `10.1038/s41467-018-07830-6`.
- Bainbridge et al. (2021), `10.1016/j.cortex.2020.11.014`.
- Bainbridge & Baker (2020), `10.1016/j.cub.2019.12.004`.
- Siena & Simons (2024), `10.1162/jocn_a_02120`.
- Reeder et al. (2024), `10.1016/j.cognition.2024.105907`.
- Lin & Oberauer (2022), `10.1016/j.cogpsych.2022.101463`.
- Teng (2025), `10.1016/j.neuropsychologia.2025.109331`.
- Rainforth et al. (2024), `10.1214/23-sts915`.
- Fink, König & Frey (2026), `10.3758/s13428-026-03123-9`.
