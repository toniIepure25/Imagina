# C3G — State-Specific Neural Geometry — Protocol

**NOT C4.** Subject subj01 only. Branched from C3M final SHA
`11445aa90486865ae1fcb33b4e3699e6e501f419`. C3/C3M are immutable.

## Central question
After correcting ordinary cross-session nonstationarity, is the residual perception→imagery
degradation explained by **simple signal attenuation / noise**, or does imagery exhibit a
**reproducible state-specific transformation of representational geometry**? NULL and
SIMPLE_ATTENUATION are valid, valuable outcomes.

## States, content, spaces
- **State P (perception):** NSD-Imagery-session **Set-B VISION** betas — 48 trials (6 content × 8
  reps), rows visB 192:240.
- **State I (imagery):** NSD-Imagery-session **Set-B IMAGERY** betas — 96 trials (6 content × 16
  reps), rows imgB 336:384 ∪ 624:672.
- **Content:** the 6 Set-B natural images (candidate pool indices 6–11; nsdIds 28752, 30857, 53882,
  61178, 65873, and nsd00000).
- **Anchor perception distribution:** core-NSD X_p (6000 trials, betas_fithrf, decoder voxel order)
  — reference for perception covariance / dimensionality / reliability and for the frozen C3M
  alignment. Core-NSD perception patterns of the 5 resolvable Set-B images are also available.
- **Set A (simple bars):** VISION 48 + IMAGERY 96 — **OOD secondary** only.

**Why within-session vision is "perception":** P and I are in the SAME NSD-Imagery session with the
SAME 6 stimuli, so the cross-session shift (relative to core-NSD / the decoder) is shared and
**cancels in the P↔I contrast by construction** — this is the operational "cross-session
correction." The frozen C3M M3-CORAL alignment is used only to relate representations to core
perception / the decoder read-out (secondary).

**Representational spaces:** (i) **native voxel space, nsdgeneral 15587** (PRIMARY); (ii)
ROI-restricted voxel spaces V1,V2,V3,hV4 (prf-visualrois) and ventral,lateral,parietal (streams)
(Phase 6, hierarchical); (iii) decoder-embedding 768-dim (secondary read-out space).

## Sample-size posture (pre-committed)
Content items with paired perception+imagery = 6 → content-level supervised transforms are severely
sample-limited. Therefore the **primary confirmatory evidence is trial-level distributional
geometry** (covariance, dimensionality, subspace angles, CKA/Procrustes/RSA, crossnobis) with
permutation and bootstrap inference (hundreds of trials — well powered). Learned transforms
(Phases 4–5) are **secondary/corroborative**, evaluated with nested CV + permutation and
capacity-matched controls; content-level transforms use leave-one-content-out (6-fold) and are
explicitly flagged as underpowered.

## Metrics (per space; computed identically for P, I, and all controls)
- **G1 centroid displacement:** ‖mean_I − mean_P‖ normalized by pooled within-state scatter.
- **G2 scalar gain α:** best global (and ROI) α in I ≈ α·P amplitude; also per-voxel std ratio.
- **G3 covariance eigenspectrum:** eigenvalue profiles; log-spectrum divergence; **participation
  ratio / effective dimensionality**.
- **G4 principal subspace angle:** angles between top-k P and I covariance subspaces.
- **G5 eigenvector alignment:** |Uk_P^T Uk_I| summary.
- **G6 linear CKA** between P and I trial-pattern second moments.
- **G7 Procrustes disparity** (orthogonal) between state geometries.
- **G8 crossnobis RDM (6×6 content)** in each state; **RDM correlation P↔I** (content-rank
  preservation), cross-validated across reps/runs.
- **G9 reliability/SNR:** split-half pattern reliability and per-state amplitude SNR.

## Controls (Phase 7; run for every primary comparison)
1. shuffled P↔I trial pairing; 2. random orthogonal transforms; 3. capacity-matched random maps;
4. **SNR-matched degraded perception** (critical); 5. session-matched perception; 6. label
permutation; 7. random low-rank maps; 8. identity; 9. gain-only model.

## Critical SNR control (Phase 2D) — decides SIMPLE_ATTENUATION
Degrade perception (P and/or core X_p) to imagery-like reliability by (a) adding calibrated
isotropic Gaussian noise to match split-half reliability, and (b) rep-subsampling — WITHOUT using
imagery labels. Test whether degraded perception reproduces the imagery phenotype on G3
(eigenspectrum + participation ratio), decoder collapse (dominant_fraction), and G8 (RDM). If
degraded perception reproduces imagery within bootstrap CI on the primary metrics →
**SIMPLE_ATTENUATION**.

## Transform hierarchy (Phase 4; secondary)
T0 identity · T1 scalar gain · T2 diagonal (regularized) · T3 orthogonal Procrustes · T4 low-rank
linear (rank/λ controlled) · T5 covariance-domain (only if distinct from frozen C3M correction) ·
T6 tiny bottleneck nonlinear (only if all linear fail). Evaluated on held-out content/trials vs
identity and capacity-matched random.

## Sealed decision rules (fixed before confirmatory inspection)
- **C3G_STATE_GEOMETRY_SUPPORTED** iff ALL: (A) SNR-matched perception does NOT reproduce the
  imagery phenotype (differs on ≥1 primary geometry metric beyond bootstrap CI); (B) ≥1 primary
  geometry metric shows a reliable P↔I difference after Benjamini-Hochberg FDR (q=0.05) across the
  confirmatory metric×space family; (C) the qualitative result is not driven by a single ROI /
  content / trial subset; (D) robust across the Phase-9 perturbations.
- **C3G_SIMPLE_ATTENUATION_SUPPORTED** iff SNR/gain/reliability degradation of perception
  reproduces the imagery phenotype within CI on the primary metrics (G3 spectrum + participation
  ratio + decoder collapse + G8 RDM) — i.e. (A) fails.
- **C3G_STATE_GEOMETRY_NULL** otherwise (no reliable geometry difference survives).
- **BLOCKED** if provenance, event/content correspondence, leakage-free evaluation, or sample size
  invalidate the intended inference.

## Multiplicity, seeds, determinism
- Confirmatory family = primary metrics {G1,G2,G3,G4,G6,G7,G8} × spaces {nsdgeneral} for the
  primary decision; ROI spaces and decoder space are hierarchical/secondary. FDR (Benjamini-
  Hochberg, q=0.05) within the confirmatory family; ROI families corrected separately.
- Permutations ≥1000; bootstrap ≥1000 (trial resampling). Seed **20260826**. crossnobis via
  leave-one-run-out / split-half. All runners emit input hashes + result self-hash.

## Exclusions
Set C conceptual imagery (no ground-truth image) and attention runs excluded. nsd00000 excluded
from any core-NSD perception content match (absent in subj01 core NSD); retained for within-session
Set-B analyses (its imagery/vision rows exist).

## Preregistration
`reports/c3g/c3g_protocol_seal.json` (self-hashed) fixes all of the above BEFORE confirmatory
outcomes are inspected. Any later unplanned analysis is labelled `EXPLORATORY_POST_HOC` and cannot
change the primary decision.
