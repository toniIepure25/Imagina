# C3G — State-Specific Neural Geometry — Final Report

**Gate:** C3G (NOT C4). **Subject:** subj01 only — no population claim.
**Branched from C3M final SHA** `11445aa90486865ae1fcb33b4e3699e6e501f419`; C3/C3M untouched.
**Decision:** `C3G_SIMPLE_ATTENUATION_SUPPORTED`.

## Question
After correcting cross-session nonstationarity (here by construction — perception and imagery are
the SAME-session, same-content Set-B **vision** vs **imagery** trials), is the residual
perception→imagery degradation explained by simple signal attenuation/reliability loss, or by a
reproducible state-specific transformation of representational geometry?

---

## Directly established (what the data and tests show)

1. **Imagery single-trial patterns are at the noise floor.** Split-half reliability of Set-B
   imagery content patterns is ≈ 0 in nsdgeneral (**0.011**) and negative in early visual cortex
   (V1 −0.076, V2 −0.092); perception (vision) reliability is moderate (nsdgeneral 0.434, V1 0.688).
   Robust across seeds and subspace dimensions (imagery reliability < 0.05 in all 9 robustness
   settings). This corroborates the C3M imagery NULL.

2. **No content-level perception↔imagery geometry survives permutation.** In nsdgeneral, linear
   CKA on the 6 content-averaged patterns p = 0.31; crossnobis 6×6 RDM correlation r = 0.218,
   p = 0.33. Across the 7 ROIs the RDM correlations are mixed and none survive (a ventral-stream
   trend r = 0.514, p = 0.098, is **not** significant).

3. **Effective dimensionality is not reliably different** (participation-ratio state difference
   p = 0.25 in nsdgeneral).

4. **The one FDR-significant primary metric is a reliability artifact.** The top-10 principal
   subspaces of perception and imagery overlap less than the state-relabel null
   (observed 0.179 vs null 0.424, permutation p = 0.001). But the relabel null is inflated because
   pooling+relabeling mixes perception's reliable signal into both pseudo-states. The preregistered
   **SNR-matched-perception control** settles it: degrading perception with isotropic noise to
   imagery's reliability collapses the perception-vs-imagery overlap to the noise floor
   (**0.179 → 0.015**), and at matched reliability there is **no reorientation beyond chance**
   (degP-vs-I overlap permutation p = 1.0). This holds in **every** robustness setting
   (k ∈ {5,10,20} × 3 seeds: raw reorientation p ≈ 0.003 always; degP-vs-I overlap ≈ 0.01–0.025
   always).

5. **Supervised transforms are uninformative (underpowered, K = 6).** Leave-one-content-out
   held-out cosine: identity ≈ −0.017; the best learned transform (gain) −0.070, beating neither
   identity nor capacity-matched random. Pre-registered as SECONDARY; cannot drive the decision.

## Core findings table

| Question | Result (nsdgeneral) |
|---|---|
| SNR/attenuation explanation | **Sufficient** — degraded perception reproduces the imagery phenotype |
| Mean displacement (G1) | present but uninformative given reliability gap |
| Amplitude gain (G2) | imagery amplitude differs (noise-dominated) |
| Dimensionality (G3 participation ratio) | not reliably different (p = 0.25) |
| Subspace orientation (G4) | raw p = 0.001 **but collapses to noise floor under SNR control** |
| Geometry preservation (G6 CKA / G8 RDM) | not significant (p = 0.31 / 0.33) |
| Best low-capacity transform | gain; **does not beat identity or random** (K = 6, underpowered) |
| Held-out improvement | none |
| Controls | SNR-matched, state-/content-permutation, capacity-matched random, gain-only |
| Robustness | reorientation collapses under SNR match in all k×seed settings; imagery reliability ≈ 0 in all |

---

## Supported interpretation

After removing the cross-session confound (same-session vision vs imagery) and controlling for
reliability, **the residual perception→imagery difference in subj01 is explained by signal
attenuation: imagery single-trial patterns carry essentially no reliable stimulus-specific
information (reliability ≈ 0).** No reproducible state-specific representational-geometry
transformation is detectable beyond this reliability loss. In the sealed language:

> after correcting measured cross-session covariance nonstationarity and controlling for simple
> signal degradation, a residual state-dependent representational transformation was **not**
> detectable under the preregistered model family.

## Not established (limitations — stated explicitly)

- **Single subject; no population claim.**
- **This is a power-limited negative, not proof of geometric equivalence.** Because imagery
  reliability ≈ 0, imagery's representational geometry cannot be characterized; the absence of a
  detectable distinct geometry may reflect insufficient reliable imagery signal rather than true
  perception≈imagery geometry. We therefore claim "explained by attenuation / not detectable,"
  **not** "imagery has the same neural representation."
- We cannot rule out that a subset of trials/voxels, a different imagery paradigm, or another
  subject carries reliable imagery signal with a distinct geometry.
- Content-level analyses are limited to K = 6 items; nonlinear transformations were not exhaustively
  ruled out (the linear supervised stage is already underpowered, so T6 was not invoked).
- Observational representational analysis; **no neural-mechanism claim**.
- Results depend on the frozen ROI/ncsnr definitions and the split-half reliability estimator.
- We do **not** claim imagery has a fundamentally different neural representation.

---

## Scientific decision — the exact sealed rule and which criteria passed

Primary family (nsdgeneral), BH-FDR q = 0.05: **G4 significant** (p = 0.001); G3 (0.25), G6 (0.31),
G8 (0.33) not significant.

- **(B)** ≥ 1 primary metric reliable after FDR → **TRUE** (G4).
- **(A)** SNR-matched degraded perception does **not** reproduce the imagery phenotype → **FALSE**
  (degP-vs-I shows no reorientation beyond chance, p = 1.0; participation ratio not reproduced is
  moot because it was not reliably different to begin with).

Sealed mapping: (B) TRUE and (A) FALSE ⇒ **`C3G_SIMPLE_ATTENUATION_SUPPORTED`** (a perm-significant
raw difference exists, but reliability-matched degraded perception reproduces the imagery
phenotype). Not `STATE_GEOMETRY_SUPPORTED` (requires A). Not `NULL` (B holds).

## Integrity

- **C3/C3M untouched**; started from the C3M final SHA; all frozen inputs re-verified bit-identical
  (decoder df2dfd89, imagery 31485ff0, ROI c1662087, ncsnr 39217f54); C3M M3 vision gate reproduced
  logically identical.
- **Seal committed BEFORE any confirmatory inspection** (`reports/c3g/c3g_protocol_seal.json`,
  self_hash 9fd2f7ea). One amendment is documented: a correctness bug fix to the paired-metric
  (G4) handler, made **before any confirmatory output existed** (the prior run crashed on the bug);
  sealed criteria unchanged. A later clarity rename of a non-criterion robustness helper is noted in
  git history and did not change the decision.
- **No post-result threshold manipulation.** The decision rule was applied mechanically.
- Analysis code hashes recorded in the seal (c3g_geometry a289a915, run_c3g_analysis 588fa292).

## Interpretation (one paragraph)

In subj01, once the perception vs imagery comparison is made within the same session on the same
six images and reliability is controlled, imagery single-trial activity is statistically
indistinguishable from noise-degraded perception: it has near-zero stimulus reliability, no
significant content-level similarity structure, and the single "reorientation" signal is an
artifact of the reliability asymmetry that vanishes under a reliability-matched control. The honest
reading is that subj01's imagery representation is dominated by signal attenuation, and any distinct
state geometry — if it exists — is below what this dataset can measure; this is a limitation of
imagery signal quality, not evidence that perception and imagery share a representation.

## Next step (NOT auto-started)

Because C3G is not a positive state-geometry result and imagery reliability is the limiting factor,
the scientifically defensible next step is **prospective replication on a subject whose imagery
carries measurable reliability** — i.e. build a full C3-scale foundation for subj02/05/07 and, as a
gating pre-check, verify imagery split-half reliability exceeds the noise floor **before** any
geometry analysis. Further tuning on subj01 is not warranted. If no subject shows reliable imagery
signal, the perception→imagery geometry question is bounded by measurement, not by geometry.
