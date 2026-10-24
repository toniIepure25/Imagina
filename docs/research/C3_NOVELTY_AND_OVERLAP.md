# C3 Novelty and Overlap Audit

**Date:** 2026-07-24 (original); updated 2026-08-21 before H4
**Branch:** `research/fmri-imagery-transfer-c3-realdata`
**Status:** AUDIT COMPLETE — UPDATED WITH SPERA ET AL. 2026 METHODOLOGICAL DETAIL

---

## 1. Summary

C3 proposes provenance-locked, ROI-resolved, uncertainty-calibrated
perception-to-imagery transfer analysis using NSD/NSD-Imagery.

Multiple prior works have already addressed parts of this question.
The zero-shot transfer component (C3-H2) is **very likely to produce a null
result** based on published evidence. The potential novel contribution lies in:
(a) rigorous low-capacity state transport with proper leakage-safe validation,
(b) calibrated uncertainty, and (c) honest reporting with deterministic provenance.

## 2. Overlap Matrix

| # | Paper/System | Dataset | Split | Model | Metric | Reported result | Code | Overlap with C3 | Gap | Classification |
|---|-------------|---------|-------|-------|--------|-----------------|------|-----------------|-----|----------------|
| 1 | NSD-Imagery (Kneeland 2025) | NSD + NSD-Imagery | Perception-trained, imagery-tested | MindEye1, MindEye2, Brain Diffuser, iCNN, Takagi | PixCorr, SSIM, 2WC (CLIP, Alex) | CLIP 2WC: 46-53% (chance=50%) for imagery | Yes (model repos) | **HIGH** — same dataset, same zero-shot question | C3 uses ridge (simpler); adds transport, uncertainty, provenance | Extension |
| 2 | Spera et al. (2026) | NSD + NSD-Imagery | Perception-trained, imagery-tested | DynaDiff (frozen zero-shot) | CLIP, Alex(2/5) 2AFC | CLIP 48.94% at chance; Alex ~50% | Not public | **HIGH** — same question, same dataset | C3 uses ridge; adds transport layer | Extension |
| 3 | MindEye1 (Scotti 2024) | NSD | Perception only (982 test) | Contrastive+diffusion | R@1, PixCorr, FID | 93.8% R@1 (perception) | Yes | **LOW** — perception only, no imagery | — | Excluded |
| 4 | MindEye2 (Scotti 2024) | NSD | Perception only (982 test) | Shared-subj+finetuning | R@1, PixCorr | 93.0% R@1 (perception) | Yes | **LOW** — perception only, complex arch | — | Excluded |
| 5 | Brain Diffuser (Ozcelik 2023) | NSD | Perception only (982 test) | VDVAE+diffusion | PixCorr, SSIM | Best low-level metrics | Yes | **LOW** — perception only | — | Excluded |
| 6 | iCNN (Shen 2019) | DeepImage | Perception+imagery | CNN decoder | PixCorr | Demonstrated imagery recon (simple) | Yes | **MEDIUM** — imagery decoding, different dataset | Different data, different approach | Excluded |
| 7 | Takagi 2023 | NSD | Perception | Stable Diffusion guided | Semantic metrics | Good semantic, poor structural | Yes | **LOW** | — | Excluded |
| 8 | Linear feature decoders (Naselaris 2011, Kay 2008) | Various | Perception (some imagery) | Ridge/Bayesian linear | Voxel-prediction, retrieval | Above-chance for perception | Partially | **MEDIUM** — same model class (ridge) | Different dataset, different target embedding | Extension |

## 3. Critical Published Evidence for C3-H2

### 3.1 NSD-Imagery Paper (Kneeland et al., CVPR 2025)

Table 1 (Mental Imagery Trials, CLIP 2-Way Comparison):
| Model | CLIP 2WC | Interpretation |
|-------|----------|----------------|
| MindEye1 | 52.03% | Barely above 50% chance |
| Brain Diffuser | 52.73% | Barely above 50% chance |
| iCNN | 49.39% | At/below chance |
| MindEye2 | 46.02% | Below chance |
| Takagi et al. | 43.26% | Below chance |

Key quote: "architectural choices significantly impact cross-decoding
performance: models employing simple linear decoding architectures and
multimodal feature decoding generalize better to mental imagery"

### 3.2 Spera et al. (2026)

Frozen zero-shot DynaDiff (strong perception decoder, no imagery fitting):
| Metric | Score | Chance |
|--------|-------|--------|
| CLIP 2AFC | 48.94% | 50% |
| Alex(5) 2AFC | 50.21% | 50% |
| Alex(2) 2AFC | 51.03% | 50% |

**Conclusion:** A strong frozen perception decoder at chance on imagery.

### 3.3 Implications for C3

The published evidence strongly predicts:
- **C3-H2 will produce a null result** (zero-shot transfer at chance)
- **C3-H1 should pass** (perception decoding is well-established for NSD)
- **C3-H4 is the only potentially novel positive finding** (state transport)

## 3.4 Updated methodological comparison against Spera et al. 2026 (before H4)

Re-read at abstract/arXiv level before executing C3-H4
(arXiv:2604.15374, "Seeing the imagined: a latent functional alignment in
visual imagery decoding from fMRI data"). This is a direct, axis-by-axis
comparison against what C3-H4 (low-capacity state transport) was originally
scoped to test, per the governing protocol's explicit requirement not to
claim novelty where prior work materially overlaps.

| Axis | Spera et al. 2026 | C3-H4 (this work) | Overlap |
|---|---|---|---|
| Space being transformed | **Decoder-output / latent space** — maps imagery-evoked activity into the pretrained DynaDiff model's *conditioning* space, backbone frozen | **Decoder-output space** — identity/mean-correction/affine-ridge/low-rank transport applied to the frozen ridge decoder's *predicted CLIP embedding*, not to raw voxels | **HIGH — same space.** C3-H4 cannot claim "decoder-output-space calibration" as a novel idea; Spera's primary method already does this, with a stronger (diffusion-conditioning) target representation. |
| Voxel-space vs decoder-output-space | Spera explicitly report a **voxel-space ridge alignment baseline** as a comparison point, distinct from their primary latent-space method | C3-H4 does not separately test a voxel-space transform; the frozen perception decoder itself is the only voxel→embedding mapping, fit once on perception data only | C3 does not add a new voxel-space technique either — this axis is fully covered by Spera's baseline already. |
| Rank / capacity | Not specified at abstract level; full-paper capacity of the latent alignment is unknown to this audit | Explicit ladder: identity (rank 0) → mean correction (rank 0, offset only) → affine ridge (full-rank + bias) → strict low-rank linear (rank ≤ 10) → matched random low-rank (falsification control) | Cannot claim capacity is *lower* than Spera's without the full paper's parameter count; the explicit ladder + random-matched-rank falsification control is a genuine methodological addition regardless. |
| Supervision | Matched imagery-perception pairs, **augmented with a retrieval strategy** that pulls in additional semantically-related NSD perception trials as pseudo-supervision | Only the true paired imagery data actually collected for the subject; no augmentation, no additional perception trials borrowed in | **Real, defensible difference.** C3-H4 is a strictly more conservative test — no augmentation ingredient that could inflate apparent transfer. |
| Retrieval augmentation | Yes — core ingredient of their method | No — deliberately excluded per the frozen C3-H4 protocol (perception decoder and its training data must stay untouched by any imagery-informed step) | Real difference, in C3's favor for interpretability, not necessarily for raw performance. |
| Held-out-target protocol | Not described in the abstract/arXiv-page-level review conducted here; unconfirmed whether their evaluation holds out entire target identities vs. only held-out trials of already-seen targets | Explicit **nested leave-one-target-out**: a target present in transport calibration may never appear in the held-out-target test fold (see `evaluate_transport_loso` in `transport.py`) | Plausible real difference, but not confirmed absent in Spera's full paper — reported as "not evident from abstract-level review," not as a confirmed gap. |
| Identity baseline | Implied by their "frozen pretrained baseline" comparison | Explicit `identity_transport()` control | Equivalent in spirit. |
| Random low-rank baseline | Not mentioned | Explicit `random_low_rank_transport()` falsification control (same rank, random weights) | Real addition — a dedicated null-capacity control distinguishing "any linear transform helps" from "this specific fitted transform helps." |
| Uncertainty analysis | Not mentioned in the abstract or the methodological summary reviewed | Explicit C3-H5 (repeat-variance, distribution-distance, ROI-disagreement uncertainty scores; risk-coverage curves) | Plausible real gap, same caveat as held-out-target above — full paper not reviewed line-by-line. |
| Primary estimand | High-level semantic reconstruction metrics (their decoder still produces images/captions via DynaDiff) | `Delta_transport` = held-out-target MRR(calibrated) − held-out-target MRR(identity), a pure retrieval statistic with no generative step | Different by construction — C3 never reconstructs images (protocol prohibition), so the estimands are not directly comparable in magnitude, only in direction (does calibration help at all). |

**Honest determination:** C3-H4's core idea — calibrating a frozen decoder's
*output* to bridge perception→imagery — is **not novel**; Spera et al. 2026
already do this, with a richer supervision signal (retrieval augmentation)
and a stronger backbone (DynaDiff vs. ridge regression). C3-H4's remaining,
actually-defensible contribution is narrower than originally scoped:

1. A **strictly conservative** transport evaluation using only true paired
   data, no retrieval augmentation — answering "does calibration help
   *without* borrowing information from other trials," not "can calibration
   be made to work with enough auxiliary supervision."
2. An explicit **capacity ladder with a random-matched-rank control**,
   isolating whether any specific fitted transform beats a same-shaped
   random one.
3. (Pending full-paper confirmation) possibly the first **nested
   held-out-target** evaluation and **calibrated uncertainty** analysis for
   this exact zero-shot-imagery-transfer setting.

If C3-H4 is executed, its write-up must state this overlap explicitly and
must not describe decoder-output-space transport itself as a novel idea.

## 4. Remaining Gaps (What C3 Adds)

### 4.1 What is NOT covered by prior work:

1. **Low-capacity state transport with proper leakage-safe validation**
   - **Revised 2026-08-21 (see §3.4):** Spera et al. 2026's primary method
     already performs decoder-output/latent-space calibration of a frozen
     perception decoder for imagery — the core idea is NOT novel to C3.
   - What remains defensible: C3-H4 uses no retrieval augmentation (only
     true paired imagery data), and adds an explicit random-matched-rank
     falsification control and nested held-out-target evaluation.
   - This must be reported as a stricter/narrower conservative test, not as
     a novel transport concept.

2. **Calibrated uncertainty for perception-to-imagery transfer**
   - No prior work reports calibrated uncertainty metrics
   - No selective transfer / risk-coverage analysis exists

3. **ROI-resolved transfer analysis with preregistered ROI**
   - Spera et al. report per-region contribution but WITH imagery fitting
   - No frozen zero-shot ROI comparison exists

4. **Deterministic provenance and exact reproducibility**
   - Prior works do not provide hash-locked provenance chains
   - C3 adds fail-closed replay

5. **Rigorous null reporting with sensitivity analysis**
   - Prior works simply report numbers without formal null inference
   - C3 provides permutation tests, power analysis, equivalence bounds

### 4.2 What C3 is NOT:
- Not a new reconstruction method
- Not imagery fitting / adaptation (that's Spera et al.'s contribution)
- Not a claim of novelty for the zero-shot question itself
- Not an attempt to beat MindEye/Brain Diffuser on any metric

## 5. Honest Framing

C3's scientific value lies in:
1. **Replicating** the published zero-shot null with a well-regularized linear
   decoder and proper statistical inference
2. **Testing** whether minimal calibration (low-capacity transport) provides
   any improvement without full imagery fitting
3. **Quantifying** what information, if any, is recoverable from imagery fMRI
   using the simplest possible frozen pipeline
4. **Establishing** whether the null is adequately powered or merely underpowered
5. **Providing** deterministic, provenance-locked evidence for/against
   reconstruction readiness

If the zero-shot null is confirmed AND transport fails, the honest conclusion is:
**Reconstruction is NOT justified without imagery-specific fitting** — consistent
with Spera et al.'s finding that adaptation is required.

## 6. Risk of Non-Contribution

The highest-probability outcome is:
```
C3-H1: PASS (perception decoding works — trivially expected)
C3-H2: NULL (zero-shot at chance — predicted by prior work)
C3-H4: NULL or INCONCLUSIVE (transport underpowered at n=4)
C3: COMPLETE_WITH_IMAGERY_TRANSFER_NULL
```

This outcome is still scientifically valuable because:
- It provides independent replication with a different method family (ridge)
- It adds formal statistical inference (not just reporting numbers)
- It establishes an honest, provenance-locked negative result
- It clearly delineates what IS vs IS NOT achievable without imagery data

But it is honest to acknowledge: **this is most likely a well-conducted
replication of a known null, not a novel positive discovery.**
