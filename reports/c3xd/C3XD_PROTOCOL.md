# C3XD — Cue-Deconfounded Semantic/Event Imagery Qualification (Mind Captioning, raw BIDS)

**Prospective protocol, sealed BEFORE inspecting any raw neural / design outcome.**
**NOT C3XR. NOT C3XR-CAT. NOT C4.** No reconstruction, no captioning, no semantic decoding, no
perception↔imagery geometry.

## 0. Question
Does the reliable semantic/event imagery signal qualified in C3XC (preprocessed Figshare release)
remain reproducible when imagery-period activity is re-estimated from **RAW BIDS** with a prospectively
frozen model that explicitly separates the preparation **cue**, the **imagery** interval, the
subsequent **target-video** presentation, and **evaluation**? Only a PASS may authorize a future,
separately-sealed C3XE semantic/event state-geometry gate. C3XD does NOT test geometry.

## 1. Lineage (frozen)
- Scientific parent: **C3XC** final SHA `fce7a04ebe0a0b5767eb600d30f5c78520680b8b`; decision
  `C3XC_D2_SEMANTIC_IMAGERY_QUALIFIED`; C3XC seal self_hash
  `e3c2ac5686edda077ad0fbbe575c0deaffe69d4567e09397cf30081eacf762b6`; C3XC CI run 34343018957
  (c3xc + backend-core + inherited gates SUCCESS).
- Branch: `research/d2-cue-deconfounded-imagery-c3xd` from `fce7a04…`.
- C3XC remains VALID for its declared scope (preprocessed-release reliability). C3XD is a STRONGER
  follow-up; it does not revise or delete `results/c3xc/*` or `reports/c3xc/*`, nor C3XA/C3XB.

## 2. Data (frozen)
- **OpenNeuro ds005191 v1.0.2**, RAW BIDS = operative source for the C3XD primary outcome.
- Figshare preprocessed arrays may serve ONLY as reproducibility/alignment anchors AFTER the raw
  pipeline is frozen; raw-derived and Figshare-derived neural samples are NEVER mixed in one estimator.
- **Selective acquisition only:** testImagery + testPerception (+ anat/fmap/events/sidecars) for
  S1–S6. **trainPerception EXCLUDED.** No full-snapshot download. Plan:
  `results/c3xd/raw_acquisition_plan.json`; storage preflight before any download.

## 3. Trial / repetition contract (to certify from BIDS events)
- Subjects 6; imagery **72 videos × 5 independent sessions = 5 reps/video**; perception 72 videos × 5
  reps. Independent unit = **imagery SESSION** (as C3XC). 72/72 exact imagery↔perception correspondence
  by video identity. Required 72/72 and 5 balanced session-reps unless missing data explicitly
  documented; no silent trial dropping.

## 4. Frozen reliability estimator (inherited, unchanged)
- Normative: `c3xb_reliability.reliability_with_inference_pairs` (sha `33d483a1…`) with **unit :=
  imagery SESSION** — Spearman-Brown-corrected session-disjoint split-half reliability; within-session
  video-label permutation null (1000); non-straddling hierarchical bootstrap over sessions (1000);
  split seeds **20260909 / +100 / +200**; N_REP_POINT=200. Accelerators `c3xb_fast` (`f5a19a7f…`) /
  `c3xc_fast` (`dc2b9be3…`), proven bit-identical (tests). Frozen estimator hash change → fail-closed.
- Inherited estimator family hashes: c3g `a289a915…`, c3x `623c9236…`.
- Subject gate: R_I>0 AND perm p<0.05 AND bootstrap CI lower>0 AND min-over-seeds>0 → PASS; else
  MARGINAL / NOISE_FLOOR. Statuses: RAW_IMAGERY_RELIABILITY_{PASS,MARGINAL,NOISE_FLOOR}.
- Perception positive control R_P (same estimator/ROI on raw perception betas); attenuation R_I/R_P.

## 5. Cue-deconfounding — design family (frozen BEFORE outcomes)
Candidate models, all built from the ACTUAL BIDS event timings (TR, onsets, durations):
- **Model A** — separated canonical-HRF GLM: distinct regressors for cue / imagery / post-imagery
  video / evaluation + nuisance.
- **Model B** — imagery LSS/LS-S: per-imagery-trial target regressor; other imagery trials grouped;
  cue / video / eval modelled; nuisance. Grouping frozen before outcomes.
- **Model C** — FIR / prospectively-defined late-imagery window minimising cue-HRF contamination
  (window fixed before outcomes, not chosen from reliability).

## 6. Primary model selection (design-only; NEVER neural)
Select ONE primary model using ONLY: event timings, design-matrix conditioning, regressor
correlations / VIF, synthetic injected-signal recovery, estimator bias/variance, cue→imagery and
video→imagery cross-talk. NEVER using imagery reliability, geometry, decoding, ROI effect size, or
behaviour. Recorded in `results/c3xd/c3xd_glm_design_selection.json`, committed BEFORE confirmatory
imagery betas.

## 7. Synthetic deconfounding simulation (mandatory, frozen thresholds)
Generate synthetic BOLD from the actual event timings; inject cue-only / imagery-only / post-video-
only / cue+imagery / imagery+postvideo / all / null, across HRF shifts, HRF width, noise levels,
motion nuisance, AR(1) noise. For each candidate model measure imagery recovery correlation,
cue→imagery leakage, post-video→imagery leakage, bias, variance, false-positive imagery recovery.
**Acceptance thresholds (frozen here, before any real BOLD):**
- imagery recovery r ≥ 0.6 (imagery-only injection);
- cue→imagery leakage: correlation of recovered imagery beta with an injected cue-only signal ≤ 0.2;
- post-video→imagery leakage ≤ 0.2;
- false-positive imagery recovery under null ≤ 0.05 (at the permutation α).
A model is "accepted" only if it meets all four. If NO candidate meets them given the real timing →
`C3XD_BLOCKED_BY_CUE_DECONFOUNDING` and STOP.

## 8. Nuisance / preprocessing provenance (frozen policy)
Nuisance: motion parameters, run intercepts, drift/high-pass, session effects (audit availability;
freeze prospectively). NEVER regress video identity, semantic features, vividness, or accuracy from
the primary neural samples. Reproduce the published/official spatial preprocessing as closely as
possible; record raw SHA-256, snapshot, slice-timing, motion/distortion correction, registration,
smoothing, detrending, standardization, GLM/HRF, ROI mapping. No outcome-based preprocessing search;
no aggressive smoothing to inflate reliability.

## 9. ROI contract
Primary ROI = **VC** (same released/localizer-defined visual-cortex scope as C3XC, where spatially
reproducible); secondary V1 / LVC / HVC (frozen localizer composites). Raw-space ROI mapping must be
cross-validated against the C3XC release (voxel count, affine/space, mask hash, overlap, orientation,
per-subject). Ambiguous mapping → `BLOCKED_C3XD_ROI_PROVENANCE` (no silent approximation).

## 10. Dataset gate
≥2/6 subjects with raw imagery PASS AND raw matched perception reliable AND deconfounding model
accepted AND ROI provenance certified → `C3XD_D2_CUE_DECONFOUNDED_IMAGERY_QUALIFIED`; exactly 1 →
`…_LIMITED`; 0 → `C3XD_D2_RAW_IMAGERY_RELIABILITY_FAIL`; temporal design not identifiable →
`C3XD_BLOCKED_BY_CUE_DECONFOUNDING`; ROI unmappable → `BLOCKED_C3XD_ROI_PROVENANCE`; storage/pipeline
infeasible → `C3XD_BLOCKED_RAW_PIPELINE_INFEASIBLE` (documented; NOT a fail, NOT a workaround).

## 11. Descriptive-only analyses (never gating)
C3XC-vs-C3XD per-subject R_I delta/ratio/rank; cue/imagery/post-video component reliabilities +
cross-component RSA; early-vs-late imagery control; previous-/next-trial contamination control.
Behaviour (accuracy/vividness) descriptive only, never used to select trials/subjects.

## 12. Forbidden
No DeBERTa/TimeSformer/captions/decoded-feature/LLM/CLIP/DINO features; no captioning; no
reconstruction; no semantic decoding; no state geometry (G3/G4/G6/G8/Procrustes/transport/SNR-matched
geometry). No raw neural data committed to git. C3XA/C3XB/C3XC artifacts never modified.

## 13. Authorization if PASS
A C3XD PASS authorizes ONLY preparation of a future, separately-sealed **C3XE — D2 Semantic/Event
State-Geometry** gate. C3XD itself performs none of it. C3XE scope is recorded (documentation only) in
`results/c3xd/c3xd_scope_registry.json`.

## STOP after C3XD.
