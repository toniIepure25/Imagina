# C1 Final Decision — Neural–Behavioral Alignment and Perception–Imagery Transfer

**Status:** Gate decision issued and subsequently AMENDED after real-data
falsification closure (tests 2, 4, 5, 7). Machine-readable version:
[`results/c1_final_decision.json`](../../results/c1_final_decision.json).
Frozen per [`C1_PROTOCOL.md`](C1_PROTOCOL.md) and
[`C1_ANALYSIS_SPEC.md`](C1_ANALYSIS_SPEC.md), which pre-registered the
hypotheses, estimand, validation hierarchy, and decision rules this document
applies to the real result.

**What changed and what did not:** the accepted primary confirmatory number
(`mean_delta_oos = -0.0238`, 95% CI `[-0.0514, -0.0039]`, `p = 0.0250`, 16
participants) is unchanged and was independently reproduced bit-exactly this
session. What changed is the MECHANISM interpretation, after the four
falsification tests originally left `deferred` (temporal shift, channel
permutation, frontal-proxy-only, signal-quality-only) were run against the
real dataset. The original decision (`C1_INCREMENTAL_BEHAVIORAL_VALIDITY =
NULL_SUPPORTED_WITHIN_SENSITIVITY`) is superseded by the decision below.

## Current decision

```
C1_NEURAL_FOUNDATION               = PASS
C1_INCREMENTAL_BEHAVIORAL_VALIDITY = NULL_SUPPORTED_FOR_CURRENT_CLASSICAL_FEATURE_PIPELINE
C1_MECHANISM                       = UNRESOLVED_SIGNAL_QUALITY_OR_ARTIFACT_CONTRIBUTION
C1_PERCEPTION_IMAGERY_TRANSFER     = EXPLORATORY_ONLY_NOT_CONFIRMATORY
C1                                  = COMPLETE_WITH_NULL_RESULT_MECHANISM_UNRESOLVED
```

## Primary confirmatory result (H2) — unchanged, reproduced bit-exactly

Real 16-participant leave-one-subject-out (LOSO) nested validation against
downloaded ds005815 data (`results/c1_incremental_validity.json`):

| Quantity | Value |
|---|---|
| Usable participants | 16 / 20 nominal |
| `mean_delta_oos` | **−0.0238** |
| 95% bootstrap CI | **[−0.0514, −0.0039]** |
| Exact sign-flip p-value | **0.0250** |

This closure re-ran the unmodified `run_c1_confirmatory.py` against the same
real data and compared every field: `mean_delta_oos`, `std_delta_oos`,
`ci_low`, `ci_high`, `exact_sign_flip_p_value`, and all 16 per-participant
deltas matched with **zero absolute difference**. The primary result is not
a fluke of one run — it is exactly reproducible.

## Why the mechanism interpretation changed

The original decision treated the negative Delta_OOS as a reasonably clean
"classical EEG features hurt cross-subject prediction" finding, because the
six falsification tests run at the time (leakage, hyperparameter-blindness,
participant-ID nullity, label-shuffle nullity, pre-cue-vs-postcue, and
behavior-plus-random-noise) all passed. Four tests remained undone. Running
them against real data changed the picture:

**Test 2 — temporal shift.** Two frozen temporal controls (pre-cue, before
the stimulus was shown; late-shift, displaced past the imagery-locked
window) were built from the SAME retained epochs, trials, behavior-only
covariates, and LOSO folds as the primary analysis — only the neural
window differs.

| Window | `mean_delta_oos` | p-value |
|---|---|---|
| Aligned (primary) | −0.0238 | 0.025 |
| Pre-cue | −0.0197 | **0.0002** |
| Late-shift | −0.0247 | 0.0046 |

Both temporal controls independently show a significant negative effect of
comparable magnitude, and neither differs significantly from the aligned
result (paired sign-flip p = 0.71 for aligned-vs-precue, p = 0.89 for
aligned-vs-late-shift; both CIs include zero). **The negative effect is not
temporally specific — it reproduces even before the stimulus was shown.**

**Test 4 — channel-label permutation.** Five deterministic permutations
(fixed seed registry: 101, 202, 303, 404, 505, committed before any result
was inspected) recomputed the frozen frontal/central/posterior features from
the identical epochs with scrambled channel-to-group mapping.

| Seed | `mean_delta_oos` | p-value |
|---|---|---|
| 101 | −0.0208 | 0.004 |
| 202 | −0.0201 | 0.078 |
| 303 | +0.0156 | 0.382 |
| 404 | −0.0337 | 0.014 |
| 505 | −0.0003 | 0.982 |
| Aligned (correct mapping) | −0.0238 | 0.025 |

The correctly-mapped result falls **within** the empirical range of the five
permuted results (+0.0156 to −0.0337), not as an outlier. Scrambling the
anatomical mapping did not reliably change or destroy the effect. **The
negative effect is not spatially specific.**

**Test 5 — frontal/ocular-proxy-only.** Features recomputed from only the 7
frozen frontal-proxy channels (YOTO has no dedicated EOG channel):
`mean_delta_oos = -0.0035` (p = 0.024, significant on its own, but ~15% of
the full magnitude). The aligned-vs-frontal paired difference is borderline
(mean diff −0.0203, bootstrap CI `[−0.0477, −0.0008]` narrowly excludes
zero, but sign-flip p = 0.088 does not reach conventional significance).
**Frontal/ocular activity partially reproduces the effect** — real but
smaller, and not conventionally distinguishable from the full result.

**Test 7 — signal-quality-only.** Strictly non-content features (peak-to-
peak amplitude, broadband/channel variance, spectral flatness, artifact-
threshold proximity, missing-channel count, neighboring-trial rejection
rate, retained-trial fraction) show `mean_delta_oos = -0.0046`, CI
`[-0.0255, 0.0141]` (includes zero), p = 0.663 — **not significant, does
not reproduce the effect.** Generic signal-quality heterogeneity alone does
not explain the result.

**Taken together:** the effect survives being non-content controls (not
temporally locked, not spatially locked, partially present in frontal-only)
but is not explained by pure signal quality alone. This pattern is not
consistent with "classical EEG content actively and specifically hurts
prediction." It is more consistent with an unresolved, non-specific
contribution — plausibly frontal/ocular contamination interacting with
cross-participant feature collinearity in the current classical construction
— that the data cannot presently disambiguate further. Per the task's own
override rule ("if quality-only or frontal-only reproduces the negative
effect, use `NULL_SUPPORTED_FOR_CURRENT_CLASSICAL_FEATURE_PIPELINE` /
`C1_MECHANISM = UNRESOLVED_SIGNAL_QUALITY_OR_ARTIFACT_CONTRIBUTION`"), this
closure applies that override given frontal-only's partial reproduction
combined with the temporal/spatial non-specificity findings.

## Why this is still a supported null, not an inconclusive non-result

The fixed-sample sensitivity analysis is unaffected by this closure (it
depends only on the unchanged `observed_std_delta_oos` and participant
count): power at the pre-registered minimum effect of interest (Δ = 0.05)
remains **0.9665**, above the 0.80 adequacy threshold. The design would have
detected a real effect of the minimum pre-registered size with high
probability — the negative finding (whatever its exact mechanism) is not a
symptom of low power.

## Ruling out a leakage/reliability failure

All ten falsification/negative-control tests now have real, non-deferred
outcomes (`results/c1_negative_controls.json`) — 7 pass, 3 (temporal shift,
channel permutation, frontal-proxy) surface the mechanism concerns above.
Critically, **none of the ten exposed train/test leakage**:

- No train/test leakage across LOSO folds (test 8, structural check, PASS).
- Hyperparameter selection and model fitting are provably blind to
  outer-test targets (test 9, PASS).
- A participant-ID-only surrogate feature collapses to near zero (test 6,
  PASS).
- Within-participant label shuffling collapses the effect (test 3, PASS).
- Behavior-plus-random-noise does not reproduce the effect (test 10, PASS).
- Signal-quality-only does not reproduce the effect (test 7, PASS).

This rules out `C1 = FAILED_BY_RELIABILITY`: the pipeline itself is sound
and leakage-free. The concern this closure raises is about the scientific
*mechanism* behind a real, reproducible, well-powered negative effect — not
about a broken or leaking pipeline.

## Honest limitations

- **Negative control 10 remains the anchoring caveat**, now corroborated by
  tests 2, 4, and 5: behavior-plus-random-noise (`−0.0023`) sits closer to
  zero than the real result (`−0.0238`), and the real effect turns out to be
  neither temporally nor spatially specific. Multiple independent lines of
  evidence now converge on the same interpretation: the current classical
  feature pipeline's negative contribution is more likely an artifact of the
  feature construction (collinearity, frontal/ocular contamination) than a
  genuine content/timing-locked neural signal actively hurting prediction.
- **Test 1 vs. test 2 precue discrepancy.** Test 1's original precue result
  (`−0.0006`, Commit 7) used precue records that never received
  `add_lagged_prior_vividness()` (all `has_prior=0`), unlike every other
  analysis in this project. Test 2's independently-recomputed precue result
  (`−0.0197`, this closure) applies it consistently with the primary
  pipeline and is treated as the more methodologically consistent number.
  Test 1's original result is preserved unmodified as historical record
  (see `results/c1_negative_controls.json`'s `honest_note_on_precue_discrepancy`),
  not retroactively corrected.
- The frontal-proxy-only feature vector (test 5) inherits two structurally
  constant ratio features (posterior-to-frontal alpha/beta ratio, both
  trivially 0 with no posterior channel present) from unmodified reuse of
  the shared feature-extraction code. Inert, but worth noting rather than
  silently omitting.
- 4/20 nominal participants excluded before the primary analysis was run,
  for reasons fixed independent of outcome: sub-05 (too few trials survived
  artifact rejection), sub-10 and sub-14 (genuine MNE PCA/ICA degeneracy),
  sub-07 (session-1 raw file absent from the public S3 mirror, HTTP 404).
  This closure did not revisit or alter these exclusions.
- H1 (neural reliability) and H3/H4 (perception-imagery transfer) remain
  small-sample (1–2 participant) machinery demonstrations, explicitly
  exploratory, outside this gate's confirmatory evidence base — hence
  `C1_PERCEPTION_IMAGERY_TRANSFER = EXPLORATORY_ONLY_NOT_CONFIRMATORY`.
- The ds005815 checksum manifest remains incomplete for files recovered
  mid-session; this closure did not attempt to regenerate it.

## Claim boundaries upheld

No thought-reading, real-time BCI, or clinical efficacy claim is made. No
missing paired behavioral target was replaced with a stimulus label. The
perception-only alignment demonstration is never described as
"neural-behavioral alignment" in the confirmatory sense. The negative result
is never reinterpreted as proof that EEG contains no useful information —
only that this specific tested pipeline shows an unresolved, non-content-
specific negative contribution. Image generation and closed-loop
neurofeedback were not started.

## What this decision does and does not authorize

This closes Scientific Gate C1 with a real, honestly-reported, adequately-
powered null/negative result for the primary hypothesis, with an explicit
mechanism caveat. It does **not** authorize image generation, real-time BCI,
or closed-loop neurofeedback work. It does authorize proceeding to
Scientific Gate C2 (neural content–state disentanglement), a materially
different scientific question from C1's incremental-validity test, per
separate explicit instruction.
