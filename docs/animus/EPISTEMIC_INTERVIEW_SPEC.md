# Epistemic Reconstruction Interview — `eri-v1`

**Status:** experimental, local-only, code complete but unexecuted on the current host.
**Claim level:** `L1_BEHAVIORAL_ASSISTED`. This is not a diagnosis, a neural decoder, an image of
imagined content, or a validated psychometric test.

## Purpose

`recon-v1` asks a person to rebuild a scene and then scores the reconstruction. The interview asks a
different question: *which binary observation would most reduce uncertainty about the scene, and what
does the resulting belief state look like?* It is a behavioural elicitation method, not a measurement of
neural content.

The output is a set of calibrated posterior probabilities over symbolic object presence and spatial
relations. It is deliberately reported with entropy, coverage, abstention, and calibration rather than a
single "imagination score".

## What the interview does

1. The server snapshots the active symbolic `SceneGraph` version.
2. The UI shows that scene once for `preview_seconds` from a fixed view, then hides it for the rest of the
   interview.
3. It builds a deterministic probe pool from `(scene.content_hash(), seed, form_id, difficulty)`.
4. The first two probes use a coverage floor when both families are available: one object-presence probe
   and one spatial-relation probe.
5. Later probes are selected by expected information gain over the current mean-field Beta belief.
6. The person answers a binary question, gives confidence in `[0.5, 1.0]`, or abstains.
7. The posterior updates from the answer and confidence; an abstention updates coverage only.
8. The interview ends at `max_probes` or when no probes remain.
9. The reconstruction reports probabilities, entropy, and descriptive scores. It does not reveal the
   hidden answer for unanswered probes.

## Probe families

### `object_presence`

> Was the `<label>` present in the hidden scene?

Options: `present`, `absent`.

Target probes are generated for entities in the scene. Decoy probes use object kinds that are absent from
the entire scene and are marked absent in the hidden answer. If every known kind is already present, the
pool omits decoys rather than asking a factually false question. The public payload never carries `answer`,
`target`, `is_target`, or the entity id. Per-probe responses also withhold correctness and Brier feedback
until the reconstruction summary, so the interview does not become a trial-by-trial learning task.

### `spatial_relation`

> Was the `<subject>` to the left or right of the `<object>`?

Options: `left`, `right`.

Only pairs with a normalized x-separation of at least `0.15` are eligible. Positions are normalized to
`[-1, 1]` using the scene's own bounding box; no camera, renderer, or screen coordinates are used.

## Belief model

Each probe is a Bernoulli variable with a `Beta(alpha, beta)` posterior, initialised at `Beta(1, 1)`.

Let the positive option be `present` for an object probe and `left` for a spatial probe; `alpha` is the
posterior mass for that positive state. Let `support_truth = c` for a correct answer and `1 - c` for an
incorrect answer. If the hidden answer is the positive option, add `support_truth` to `alpha`; if the
hidden answer is the negative option, add `support_truth` to `beta`:

```text
truth = hidden answer
support = c if choice == truth else 1 - c
if truth == positive_option:
    alpha' = alpha + support; beta' = beta + (1 - support)
else:
    alpha' = alpha + (1 - support); beta' = beta + support
```

For example, a correct `absent` answer with `c = 0.9` adds `0.1` to `alpha` and `0.9` to `beta`, lowering
the probability of presence. The posterior mean is `alpha / (alpha + beta)`. The update is intentionally
simple and transparent. It is a stated response model, not a fitted model of a person.

An abstention records the probe as asked but leaves the posterior unchanged.

## Probe selection

Expected information gain for a variable with prior `p` and selection sensitivity `s`:

```text
p_yes = p * s + (1 - p) * (1 - s)
post_yes = (alpha + s) / (alpha + beta + 1)
post_no  = (alpha + 1 - s) / (alpha + beta + 1)
EIG = H(p) - [p_yes * H(post_yes) + (1 - p_yes) * H(post_no)]
```

`H` is binary entropy in nats. `s = 0.8` is a design parameter used only to rank probes; it is not an
ability estimate and is not used in scoring. Ties are broken by `probe_id` so selection is deterministic.

The coverage floor runs first. Without it, a high-uncertainty object probe could crowd out the spatial
measurement entirely.

## Scoring and summary

Every answered probe produces:

```text
correct = (choice == hidden answer)
accuracy = 1 if correct else 0
Brier = (confidence - accuracy)^2
realised_gain = H(p_before) - H(p_after)
```

An abstention produces `correct = null`, `accuracy = null`, `Brier = null`, and is included in coverage
and abstention rate. The interview summary reports:

| Field | Meaning |
|---|---|
| `object_accuracy` | mean accuracy on answered object probes |
| `spatial_accuracy` | mean accuracy on answered spatial probes |
| `mean_brier` | mean Brier score on answered probes; lower is better |
| `coverage` | answered probes / total probes |
| `abstention_rate` | abstained probes / total probes |
| `overconfidence` | mean confidence on answered probes minus accuracy |
| `mean_information_gain` | mean realised entropy reduction per probe |

There is no composite score. Object accuracy, spatial accuracy, calibration, coverage, and entropy answer
different questions and are not collapsed.

`probability` is the posterior mean for the positive state (`left` for spatial probes; `present` for object
probes). The relation label is derived from that posterior (`left_of` when `probability >= 0.5`, otherwise
`right_of`); it never copies the hidden relation. Object entries include decoys so absent candidates remain
visible.

## Reconstruction payload

```json
{
  "objects": [
    {"label": "lantern", "kind": "lantern", "probability": 0.82, "status": "likely_present"}
  ],
  "relations": [
    {
      "subject": "castle",
      "relation": "left_of",
      "object": "moon",
      "probability": 0.71,
      "status": "likely_left"
    }
  ],
  "uncertainty": {"object_entropy": 0.41, "relation_entropy": 0.39},
  "scores": {
    "n_probes": 12,
    "n_answered": 10,
    "object_accuracy": 0.7,
    "spatial_accuracy": 0.6,
    "mean_brier": 0.18,
    "coverage": 0.833,
    "abstention_rate": 0.167,
    "overconfidence": 0.05,
    "mean_information_gain": 0.04
  },
  "protocol_version": "eri-v1",
  "scoring_version": "eri-v1"
}
```

For objects, `status` is a display band (`likely_present`, `likely_absent`, `uncertain`); for relations it
is `likely_left`, `likely_right`, or `uncertain`. It is not a decision rule or a diagnosis. Probabilities
near `0.5` mean the evidence did not separate the states.

## Determinism and persistence

- `ERI_PROTOCOL_VERSION = "eri-v1"`, `ERI_SCORING_VERSION = "eri-v1"`.
- Probe ids are `pr_` + a SHA-256 prefix; task ids are `eri_` + a SHA-256 prefix.
- `form_id` is one of `A`, `B`, `C`; forms change the deterministic probe order/pool, not the scoring rule.
- `max_probes` defaults to `12` and must be within `[6, 20]`.
- `expected_version_id` is optional; if supplied and the scene head has moved, the request fails with
  `409 stale_version` instead of silently interviewing a different scene.
- Difficulty is rounded to three decimals and is part of the task fingerprint.
- Migration **v020** is additive:
  - table `animus_studio_interviews`;
  - trial columns `interview_id`, `probe_index`, `probe_type`, `belief_json`, `information_gain`.
- Existing v019 practice rows remain readable. `belief_json` defaults to `{}`.
- Every probe is written to the existing trial ledger with a unique `(session_id, client_trial_id)`.
  Idempotent retries are checked before the scene-version guard.
- `expected_version_id` rejects an interview whose source scene has changed.

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/animus/studio/sessions/{session_id}/interviews/start` | create an interview and return the first probe |
| `POST` | `/animus/studio/sessions/{session_id}/interviews/{interview_id}/probes` | record one probe answer |
| `GET` | `/animus/studio/interviews/{interview_id}` | summary and reconstruction |
| `GET` | `/animus/studio/sessions/{session_id}/interviews` | local interview index |

Start body:

```json
{"max_probes": 12, "form_id": "A", "difficulty": 0.45, "expected_version_id": "ver_..."}
```

Probe body:

```json
{
  "probe_id": "pr_...",
  "task_id": "eri_...",
  "choice": "present",
  "confidence": 0.8,
  "abstained": false,
  "latency_ms": 1200,
  "client_trial_id": "ei_...",
  "expected_version_id": "ver_..."
}
```

Confidence below `0.5` is rejected: a forced choice with no evidence maps to `0.5`, not to a false
certainty. `choice` is empty only when `abstained` is true.

## Simulation, not validation

`backend/app/evaluation/animus_epistemic_sim.py` compares random, fixed-coverage, and information-gain
selection on a synthetic scene with a stated response model. It is deterministic and labelled
`simulation_only`. It can show that the selector behaves as implemented; it cannot show that the interview
is valid for people.

## Boundaries

- The hidden scene still exists in the local session snapshot. The UI shows it only during the timed
  encoding preview and does not display it during the
  interview, but this is not a secure assessment; a local user can inspect client state.
- The Beta model is a design choice. A different response model, sensitivity, prior, or confidence scale
  would change the posterior.
- Decoy kinds and relation pairs are design choices and can change difficulty.
- Interview length, display, fatigue, and prior knowledge are not modelled as covariates in `eri-v1`.
- The output is not an imagery-strength score, an IQ, a memory diagnosis, a measure of consciousness, or a
  neural reconstruction.
- Aphantasia and hypophantasia are variations. Lower accuracy or higher abstention is not framed as a
  deficit.
- No clinical, diagnostic, treatment, or "brain training" claim is authorised.

## Research anchors

These papers inform the design of behavioural scene reconstruction and confidence elicitation. They do not
validate this implementation.

- Bainbridge, W. A., Hall, E. H., & Baker, C. I. (2019). Drawings of real-world scenes during free recall
  reveal detailed object and spatial information in memory. *Nature Communications*.
  https://doi.org/10.1038/s41467-018-07830-6
- Bainbridge, W. A., Pounder, Z., Eardley, A. F., & Baker, C. I. (2021). Quantifying aphantasia through
  drawing: Those without visual imagery show deficits in object but not spatial memory. *Cortex*.
  https://doi.org/10.1016/j.cortex.2020.11.014
- Rademaker, R. L., & Pearson, J. (2012). Training visual imagery: Improvements of metacognition, but not
  imagery strength. *Frontiers in Psychology*. https://doi.org/10.3389/fpsyg.2012.00224
- Melby-Lervåg, M., Redick, T. S., & Hulme, C. (2016). Working memory training does not improve
  performance on measures of intelligence or other measures of "far transfer". *Perspectives on
  Psychological Science*. https://doi.org/10.1177/1745691616635612

## Validation required

A separate preregistered study must test:

1. test–retest reliability of posterior reconstruction and calibration;
2. convergent/discriminant validity against established imagery and scene-memory measures;
3. sensitivity to probe budget, preview exposure, and scene complexity;
4. whether adaptive selection improves precision over coverage-first selection in humans;
5. whether abstention is used strategically or as a difficulty response;
6. whether the Beta response model is adequate, or whether a different calibration model is needed;
7. whether interview performance predicts anything outside the interview (it is not assumed to).

Until then, `eri-v1` is an experimental behavioural interview.
