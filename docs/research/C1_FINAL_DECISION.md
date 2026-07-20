# C1 Final Decision — Neural–Behavioral Alignment and Perception–Imagery Transfer

**Status:** Gate decision issued. Machine-readable version:
[`results/c1_final_decision.json`](../../results/c1_final_decision.json).
Frozen per [`C1_PROTOCOL.md`](C1_PROTOCOL.md) and
[`C1_ANALYSIS_SPEC.md`](C1_ANALYSIS_SPEC.md), which pre-registered the
hypotheses, estimand, validation hierarchy, and decision rules this document
applies to the real result.

## Decision

```
C1_NEURAL_FOUNDATION              = PASS
C1_INCREMENTAL_BEHAVIORAL_VALIDITY = NULL_SUPPORTED_WITHIN_SENSITIVITY
C1_PERCEPTION_IMAGERY_TRANSFER     = EXPLORATORY_ONLY_NOT_CONFIRMATORY
C1                                 = COMPLETE_WITH_NULL_RESULT
```

## Primary confirmatory result (H2)

Real 16-participant leave-one-subject-out (LOSO) nested validation against
downloaded ds005815 data (`results/c1_incremental_validity.json`):

| Quantity | Value |
|---|---|
| Usable participants | 16 / 20 nominal |
| `mean_delta_oos` | **−0.0238** |
| 95% bootstrap CI | **[−0.0514, −0.0039]** |
| Exact sign-flip p-value | **0.0250** |

The primary estimand is negative and its confidence interval excludes zero:
**adding classical EEG features to the behavior-only model measurably hurt
out-of-sample prediction of trial-level imagery vividness**, not merely
failed to help.

## Why this is a supported null, not an inconclusive non-result

A negative or null point estimate is not by itself evidence of "no effect" —
it could simply mean the study was underpowered to detect a real, smaller
effect. `C1_ANALYSIS_SPEC.md` Section 9 requires a fixed-sample sensitivity
analysis before a null result can be reported as *supported* rather than
*inconclusive*.

`results/c1_sensitivity.json`, run against the observed 16-participant sample
and the observed outer-fold variance (`std_delta_oos = 0.0493`), estimates
power at the pre-registered minimum effect of interest (Δ = 0.05):

| Effect size (Delta_OOS) | Estimated power |
|---|---|
| 0.00 | 0.048 (≈ nominal alpha, as expected under the null) |
| 0.03 | 0.631 |
| 0.05 (minimum effect of interest) | **0.9665** |
| 0.08 | 1.000 |

Power at the minimum effect of interest (0.9665) clears the 0.80 adequacy
threshold. The design *would* have detected a real effect of the
pre-registered minimum size with high probability — so its absence (and the
observed direction reversal) is informative, not simply a symptom of a small
sample.

## Ruling out a leakage/reliability failure instead

All negative-control and falsification checks that could structurally
invalidate the result instead passed against real data
(`results/c1_negative_controls.json`):

- No train/test leakage across LOSO folds (test 8).
- Hyperparameter selection and model fitting are provably blind to outer-test
  targets — corrupting only the held-out fold's test targets left the chosen
  L2 and trained-model checkpoint hash unchanged (test 9).
- A participant-ID-only surrogate feature collapses to near zero, ruling out
  ID leakage explaining the (negative) effect (test 6).
- Within-participant label shuffling collapses the effect, confirming the
  primary analysis isn't picking up some structural artifact independent of
  the actual targets (test 3).
- Pre-cue EEG (same trials, features from before the stimulus) does not
  reproduce the post-cue result (test 1).

This rules out `C1 = FAILED_BY_RELIABILITY`: the pipeline's negative controls
behave exactly as a sound pipeline should, even though the substantive
finding is unfavorable to the neural-increment hypothesis.

## Honest limitations

- **Negative control 10 is the most important caveat.** Behavior-plus-
  random-noise (`−0.0023`) sits *closer to zero* than the real
  behavior-plus-classical-features result (`−0.0238`) — the real features
  underperform random noise, not merely fail to add value. This is
  consistent with the negative primary finding, and is flagged honestly as
  suggestive of overfitting or collinearity within the classical feature set
  (many correlated band-power/spectral-entropy features across three frozen
  channel groups, fit with L2-only regularization on a modest per-fold
  training set), rather than proof that no EEG feature representation could
  ever help. A different, lower-dimensional feature representation might
  behave differently — that is future work, not resolved by this decision.
- 4/20 nominal participants excluded before the primary analysis was run, for
  reasons fixed independent of outcome: sub-05 (too few trials survived
  artifact rejection), sub-10 and sub-14 (genuine MNE PCA/ICA degeneracy —
  one component captured >99% of variance), sub-07 (session-1 raw file
  absent from the public S3 mirror, HTTP 404).
- Falsification tests 2 (temporal shift), 4 (channel permutation), 5
  (ocular-only), and 7 (signal-quality-only) were not run against real data
  this session; each requires an additional feature-extraction pass not yet
  built into `run_c1_confirmatory.py`. They remain explicitly deferred
  (`results/c1_negative_controls.json`'s `not_run_this_session`), not
  silently dropped.
- H1 (neural reliability) and H3/H4 (perception-imagery transfer) were run
  only as small-sample (1–2 participant) machinery demonstrations
  (`results/c1_reliability.json`, `results/c1_alignment.json`), explicitly
  labeled exploratory. They are not part of this gate decision's confirmatory
  evidence and make no population-level claim in either direction — hence
  `C1_PERCEPTION_IMAGERY_TRANSFER = EXPLORATORY_ONLY_NOT_CONFIRMATORY` rather
  than a PASS/FAIL verdict.
- The ds005815 checksum manifest is incomplete for files recovered mid-session;
  those files are marked `not_in_manifest`, never falsely marked valid.

## Claim boundaries upheld

No thought-reading, real-time BCI, or clinical efficacy claim is made. No
missing paired behavioral target was replaced with a stimulus label. The
perception-only alignment demonstration is never described as
"neural-behavioral alignment" in the confirmatory sense. Image generation and
closed-loop neurofeedback were not started.

## What this decision does and does not authorize

This closes Scientific Gate C1 with a real, honestly-reported, adequately-
powered null/negative result for the primary hypothesis. It does **not**
authorize starting C1.1, C2, image generation, or closed-loop neurofeedback
work — per the task's explicit stop condition, work stops here pending
separate authorization to proceed.
