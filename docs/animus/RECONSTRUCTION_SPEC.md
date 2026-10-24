# Reconstruction Instrument — `recon-v1`

**Status:** experimental, local-only, code complete but unexecuted on the current host.
**Claim level:** `L1_BEHAVIORAL_ASSISTED`. Not a diagnosis, not neural decoding, not a validated
psychometric test.

## Why reconstruction

A multiple-choice probe can test recognition without showing how much of a scene survived. Reconstruction
asks the user to rebuild the object set or spatial layout from memory, which creates a richer behavioural
record and an interpretable error profile. The source scene is symbolic; the instrument never reads imagery
and never generates an image.

The design is informed by drawing-from-memory work (Bainbridge, Hall & Baker, 2019) and the object/spatial
dissociation reported in aphantasia (Bainbridge et al., 2021). Those studies validate drawing as a research
method, not this implementation. Construct validity for `recon-v1` remains open.

## Task families

### `object_reconstruction`

- Preview the scene, then hide it.
- The server returns a shuffled token bank containing target tokens and deterministic decoys.
- The user selects every object they remember.
- Tokens carry `token_id`, `kind`, `label`, `role`, and an optional colour. No token carries `is_target`.
- The answer (`target_token_ids`) never leaves the server before scoring.

Selection score (F1):

```text
TP = selected target tokens
FP = selected decoy tokens
FN = unselected target tokens
score = 2TP / (2TP + FP + FN)
precision = TP / (TP + FP)
recall = TP / (TP + FN)
omissions = FN
intrusions = FP
```

The task updates the `stability` dimension, labelled **Object detail** in the profile.

### `spatial_layout`

- Preview the scene, then hide it.
- The server returns the target object tokens but not their positions.
- The user places each token on a normalized top-down grid.
- The UI uses a 7×7 grid by default; coordinates are normalized to `[-1, 1]`.
- The answer (`target_positions`) never leaves the server before scoring.

Position score:

```text
d_i = euclidean distance between user position and target position for token i
tolerance = clamp(0.55 - 0.35 * difficulty, 0.12, 0.55)
score_i = max(0, 1 - d_i / (2 * tolerance))
score = mean(score_i)
mean_spatial_error = mean(d_i)
```

A missing placement counts as an omission and receives the maximum distance. The task updates the `spatial`
dimension, labelled **Spatial structure** in the profile.

## Generation and determinism

Both tasks are generated from `(scene.content_hash(), task_type, seed, difficulty)`:

- target count is `2 + round(difficulty * 3)`, clamped by the number of eligible entities;
- decoy count for objects is `1 + round(difficulty * 3)`;
- target selection, decoy kinds, and token order use a seeded `random.Random`;
- the difficulty sent to the API is rounded to three decimals, and the same rounded value is used in
  `task_id`;
- reconstruction `task_id` includes `recon-v1`; legacy task fingerprints are unchanged.

If a scene has fewer than two entities, or no spatial variation, the server falls back to the matching
legacy task (`attribute_recall` or `spatial_view`) rather than inventing an invalid reconstruction. The
fallback task carries its own legacy `task_id` and actual task type.

## Error profile

Every reconstruction outcome includes:

```json
{
  "omissions": 0,
  "intrusions": 0,
  "object_precision": 1.0,
  "object_recall": 1.0,
  "mean_spatial_error": null,
  "spatial_n": 0
}
```

`object_precision` and `object_recall` are null for spatial trials. `mean_spatial_error` is null for object
trials. The profile aggregates these values descriptively; it does not convert them into a composite score
or a clinical category.

## Persistence

Migration **v019** adds to `animus_studio_trials`:

- `task_family` (`legacy` or `reconstruction`),
- `response_kind` (`option`, `token_selection`, `spatial_placement`),
- `scoring_version` (`v1` or `recon-v1`),
- `error_profile_json`.

All columns are additive with defaults; v018 rows remain readable and old clients ignore the new fields.

## Boundaries

- The target scene is still present in the local session snapshot. The UI hides it during the question, but
  this is not a secure assessment; a local user can inspect client state.
- Preview duration, display size, input device, and renderer can affect scores. These are not measured as
  covariates in `recon-v1`.
- Object tokens and decoys are our design choice. A different token bank could change difficulty and
  construct coverage.
- The score is not an imagery-strength score, an IQ, a memory diagnosis, or a measure of consciousness.
- Aphantasia and hypophantasia are variations. Lower object detail is not framed as a deficit.

## Validation required

A separate preregistered study must test:

1. test–retest reliability of object and spatial scores;
2. convergent and discriminant validity against established imagery and scene-memory measures;
3. sensitivity to preview duration and scene complexity;
4. whether object and spatial scores separate as predicted;
5. whether the error profile is stable enough to interpret;
6. whether information-gain selection improves precision over coverage-first selection in humans, not only
   in simulation.

Until then, `recon-v1` is an experimental behavioural probe.

## References

- Bainbridge, W. A., Hall, E. H., & Baker, C. I. (2019). Drawings of real-world scenes during free recall
  reveal detailed object and spatial information in memory. *Nature Communications*.
  https://doi.org/10.1038/s41467-018-07830-6
- Bainbridge, W. A., Pounder, Z., Eardley, A. F., & Baker, C. I. (2021). Quantifying aphantasia through
  drawing: Those without visual imagery show deficits in object but not spatial memory. *Cortex*.
  https://doi.org/10.1016/j.cortex.2020.11.014
