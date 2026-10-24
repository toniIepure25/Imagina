# C3 H2 / Vision-Validation Correction — Prediction Collapse

## What this corrects

Commit `11a8d54` recorded a vision cross-session validation **PASS** (Set B
exact permutation p=0.026), and an initial (uncommitted) H2 run reported
`SUBJ01_ZERO_SHOT_IMAGERY_TRANSFER_PASS` (Set B exact p=0.0014). Both were
decided by an insufficient rule: "primary Set B exact permutation p < 0.05."
Deeper diagnosis shows **both of those "significant" results are artifacts of
a degenerate single-candidate prediction collapse, not genuine transfer.**
This document and the collapse-guarded re-runs correct the interpretation. The
prior commit is preserved as the record of the flawed-decision-rule state; it
is not rewritten.

## The diagnosis

Applying the frozen H1 perception decoder to the NSD-Imagery betas (both
vision and imagery, using strictly frozen perception preprocessing as the
zero-shot protocol requires) produces **near-constant predictions that collapse
onto a single candidate**, regardless of the true stimulus:

| Run | Within-Set-B argmax concentration |
|---|---|
| visB (seen Set B) | candidate 6 for **45/48** trials (94%) |
| visA (seen Set A) | candidate 2 for **48/48** trials (100%) |
| imgB_1+imgB_2 (imagined Set B) | candidate 6 for **96/96** trials (100%) |

Uniform/chance concentration for 6 candidates is ~17%. The observed 94–100%
concentration is a gross collapse.

**Why the permutation test fired anyway.** The exact 6! target-label null
permutes which physical stimulus maps to which of the 6 pool labels. Under the
true labeling, the ~16 trials of the one stimulus that happens to coincide with
the collapse target (shared0385_nsd28752 → candidate 6) all rank #1, inflating
MRR; permutations that move that stimulus away from candidate 6 tank the MRR.
So the test detects the (stimulus shared0385 ↔ candidate 6) coincidence — which
is a **decoder collapse target, not imagery content.** Per-target MRR makes this
explicit for imagery: target 6 = 0.969, every other target = 0.08–0.11 (at/below
chance). And **2AFC = 0.424 (below chance)** confirms there is no genuine
broad transfer — on average the true target is farther from the prediction than
a random foil.

## The mechanism (why the collapse happens)

The imagery-session betas carry a systematic per-voxel offset relative to the
perception session: when z-scored with the frozen perception voxel mean/std,
the imagery ROI values have mean ≈ −0.86 (not 0) and std ≈ 1.56. Raw int16
scales are otherwise compatible (perception and imagery samples both ~±600).
A linear decoder maps this consistent offset to a consistent CLIP-space
location, so predictions cluster in one small region → collapse to one nearest
candidate. This is genuine **cross-session nonstationarity**, exactly the
failure mode the mission's vision-validation step is designed to catch.

Critically, this is **not** a mapping or pipeline bug — the mapping was proven
independently of any decoding:
- beta row k == behavioral trial k (design-matrix onset order == behavioral
  trial order, column→CONDITION a consistent function);
- vision seen-image target = CONDITION, 96/96 agreement with the official
  pair_list FRAMEFILE ground truth;
- candidate pool in the identical CLIP space (Set B shared1000 candidates match
  their perception embeddings at cosine = 1.000000).

## The corrected decision rule

A permutation-significant exact-p is accepted as genuine transfer **only if**
all three hold: exact p < 0.05 **AND** predictions are not a degenerate
single-candidate collapse (`prediction_collapse_diagnostic`, dominant fraction
≤ 0.5) **AND** 2AFC > 0.5. This guard is added to both
`run_nsdimagery_vision_validation.py` and `run_h2_zero_shot_transfer.py`.

## Corrected outcomes

- **Vision cross-session validation:** `BLOCKED_CROSS_SESSION_VISION_VALIDATION_DEGENERATE_COLLAPSE`.
  The mapping is certified correct; the frozen zero-shot decoder does not
  transfer across sessions — it collapses.
- **H2 zero-shot imagery transfer:** `SUBJ01_ZERO_SHOT_IMAGERY_TRANSFER_NULL_DEGENERATE_COLLAPSE`.
  No genuine stimulus-specific imagery information is recovered zero-shot; the
  apparent exact-p significance is a collapse artifact, decisively refuted by
  the 94–100% single-candidate concentration and below-chance 2AFC.

This is consistent with the published prior expectation (Kneeland 2025, Spera
2026) that zero-shot imagery transfer is essentially null for this setting, and
it motivates H4 (a low-capacity calibration/transport layer fit inside imagery
folds, held-out-target), which is the appropriate next step given a zero-shot
null.
