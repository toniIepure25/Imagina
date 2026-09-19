# ANIMUS-P2 Neural Decoder — Model Card

> **Status: NOT VALIDATED (confirmatory pending).** The sealed pipeline is proven correct on synthetic data;
> the real perception decoder is trained/validated only when the confirmatory cluster run completes. Until
> then no perception-content claim is authorized.

## Intended use
Estimate a frozen visual-content embedding from fMRI acquired **while a participant perceives a visual
stimulus**, for consumption by the ANIMUS closed loop as an observation source. Offline/replay only.

## Validated domain
Visual **perception** content only (once VALIDATED). **Not** imagery, **not** dreams, **not** image
reconstruction, **not** mental-state/thought decoding.

## Dataset / subjects
Independent perception dataset (primary NOD ds004496; fallback BOLD5000 ds001499), prospectively-fixed
subject subset; grouped-by-identity train/val/test. Exact subjects/counts recorded in the confirmatory
results and `model_manifest.json` at run time.

## Stimulus space / ROI / target
Natural-image identities with exact labels; primary ROI Wang25 topographic visual network; target = frozen
open vision-language embedding of the actual stimulus image (not captions).

## Model
Regularized linear (ridge) multi-output regression; alpha by nested validation. Bootstrap-ensemble
uncertainty; calibrated reject option.

## Evaluation
Held-out unseen identities: content margin M (+ permutation p, identity-bootstrap CI, multi-seed), 2AFC,
retrieval (Top-k/MRR/rank), category-matched and low-level-baseline controls, label-permutation collapse.

## Uncertainty
First-class per-observation uncertainty (ensemble spread), calibrated on validation; monotone error↔
uncertainty checked; conformal-style coverage reported at run time.

## Known failure modes
Category-only recovery (checked via category-matched decoys), low-level-only structure (checked via low-
level baseline), session/run fingerprints (checked via shuffles), OOD stimuli/categories (degradation
reported), high-motion/low-coverage trials (rejected).

## OOD behaviour
Reject option returns `valid=false` above the validation-calibrated uncertainty threshold or on QC/ROI
failure. The decoder can say "no valid neural-content estimate."

## Privacy
Raw neural arrays and identifiers never leave the decoder toward any generator; only sanitized content
latents flow into ANIMUS. No raw neural data committed to Git.

## Claims allowed (only when VALIDATED)
"Experimental validated perception-content neural adapter: visual-content representations can be estimated
from fMRI during visual perception under the validated P2 protocol."

## Claims forbidden
Imagery neural content; thought/mind reading; dream decoding; mental-image reconstruction; real-time brain
reading.
