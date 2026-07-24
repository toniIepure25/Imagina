# C3 Novelty and Overlap Audit

**Date:** 2026-07-24
**Branch:** `research/fmri-imagery-transfer-c3`
**Status:** AUDIT COMPLETE

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

## 4. Remaining Gaps (What C3 Adds)

### 4.1 What is NOT covered by prior work:

1. **Low-capacity state transport with proper leakage-safe validation**
   - Spera et al. used full imagery fitting (matched supervision)
   - No prior work tests a strictly low-capacity (mean-correction, affine ridge)
     transport applied AFTER a frozen perception decoder
   - Key distinction: transport capacity << imagery sample size

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
