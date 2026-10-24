# C3XDR — Infrastructure-Enabled Execution Rerun of the C3XD Question

**Execution rerun, NOT a new hypothesis. NOT C3XE / C3XR / C3XR-CAT / C4.** No geometry, no captioning,
no semantic decoding, no reconstruction. Same scientific question as the already-sealed C3XD; the only
difference is that C3XDR attempts the raw-BIDS execution that C3XD proved well-posed but could not run.

## 0. Lineage (frozen)
- C3XC final `fce7a04ebe0a0b5767eb600d30f5c78520680b8b` — decision `C3XC_D2_SEMANTIC_IMAGERY_QUALIFIED`.
- C3XD final `d60cbfde4cab53270298f4b0df59e3beb8cfddab` — decision `C3XD_BLOCKED_RAW_PIPELINE_INFEASIBLE`,
  seal `1a680c1b1d2e3f0c015bae41088f3a5a97642ff119e9a52b995e1f3c66a723fb`, CI 34368467455.
- Branch `research/d2-cue-deconfounded-imagery-c3xdr` from the C3XD final SHA.
- C3XC/C3XD artifacts are IMMUTABLE. Historical reading preserved: C3XD = BLOCKED (no execution
  infrastructure); C3XDR = execution attempt of the SAME question under adequate infrastructure.

## 1. Infrastructure gate (Section 1 — hard, FIRST)
Requires an execution location with ≥300 GB usable persistent storage (prefer ≥500) AND a reproducible
preprocessing/registration stack (containerized). Audited in `results/c3xdr/infrastructure_audit.json`.
If unmet → `C3XDR_BLOCKED_STORAGE` and STOP; download nothing large. **This gate is the operative
determinant of the C3XDR outcome in the present environment (see decision).**

## 2. Selective acquisition (frozen; inherited from C3XD)
ds005191 v1.0.2 raw BIDS: testImagery + testPerception functional runs + events/sidecars (+ anat/fmap
only if required by preprocessing) for S1–S6. **trainPerception EXCLUDED** (~139.4 GB relevant subset).
Tests enforce the exclusion. SHA-256 recorded for every selected input.

## 3. Primary raw estimator — MODEL A (LSA), FROZEN before any raw outcome
Justified EXCLUSIVELY by the completed C3XD design/synthetic analysis (`results/c3xd/
c3xd_design_simulation.json`, `c3xd_glm_design_selection.json`): Model A = separated LSA GLM with
per-trial cue / imagery / post-imagery video regressors + grouped evaluation + nuisance. C3XD synthetic
recovery for A: imagery recovery r min≈0.61/mean≈0.76; false-positive reliability 0 at cue-gain 0.25×
and 0.5×, 0.25 at 1.0×. **A/B/C are NOT re-compared on real BOLD; the primary GLM is never tuned on
C3XDR outcomes; no switch to LSS if LSA is weaker.**

## 4. Reliability estimator (frozen, inherited)
`c3xb_reliability.reliability_with_inference_pairs` with unit := imagery SESSION (accelerator
`c3xc_fast`, bit-identical). SB-corrected session-disjoint split-half reliability; within-session
video-label permutation null (1000); non-straddling hierarchical bootstrap over sessions (1000); split
seeds 20260909/+100/+200; N_REP_POINT=200. Estimator-hash change → fail-closed. Subject gate: R_I>0 AND
perm p<0.05 AND bootstrap CI lower>0 AND min-over-seeds>0 → PASS, else MARGINAL / NOISE_FLOOR. Matched
raw perception R_P via the frozen run-disjoint estimator; report R_I/R_P (non-gating unless already
sealed).

## 5. Preprocessing provenance (frozen ONE pipeline; container-pinned)
Reproduce the published/KamitaniLab Mind Captioning preprocessing/space as closely as practical so the
released localizer ROI definition is reusable. Record container image+digest, software versions,
command line, parameters, input hashes, output-space definition. No outcome-based preprocessing search;
no smoothing chosen to inflate reliability. Spec: `results/c3xdr/c3xdr_preprocessing_spec.json`,
`reports/c3xdr/C3XDR_PREPROCESSING_PROVENANCE.md`.

## 6. ROI provenance (hard gate) — VC primary; V1/LVC/HVC secondary
Map the released `metainf.roiname` localizer ROIs into the raw-derived functional space via a certified
transform chain (reproduce the KamitaniLab localizer→functional mapping, or transform the authoritative
released mask through certified registration, or reproduce the official space exactly). Record per
subject: space, source, transform chain+hashes, affines, voxel count, orientation, mask hash, overlap
with the released representation. Status `C3XDR_ROI_CERTIFIED`, else `C3XDR_BLOCKED_ROI_PROVENANCE`. No
approximation of VC.

## 7. Two-stage execution
Stage 1 = S1 technical qualification (acquisition/events/preprocessing/registration/ROI/GLM/beta
extraction validated on technical properties ONLY — never using S1 R_I/decoding/geometry to tune the
pipeline); freeze the full pipeline; then Stage 2 = S2–S6 + frozen inference.

## 8. Beta / unit / correspondence contracts
Imagery Model-A betas (cue / imagery / post-video) map uniquely to subject/session/run/trial/video_id;
360 imagery trials = 72 videos × 5 reps × 5 sessions, no silent drops (else
`C3XDR_BLOCKED_UNIT_CONTRACT`). Perception through the same stack (72×5). 72/72 imagery↔perception
correspondence by video identity per subject.

## 9. Cue-contamination controls (mandatory)
(a) Empirical `cue_gain_empirical = G_cue/G_img` and `video_gain_empirical` (frozen magnitude estimator;
diagnostic, NOT a model selector). (b) **Falsification** `R_I_cuevideo_predicted`: propagate the
estimated cue+video (+nuisance) prediction through the exact Model-A imagery-beta operator and compute
its imagery reliability; `Delta_I = R_I_observed − R_I_cuevideo_predicted` with a valid within-session
randomization test (sealed before outcomes). Secondary early-vs-late FIR and current/previous/next-video
controls.

## 10. Deconfounding success + dataset decision
Subject PASS requires: raw Model-A imagery reliability PASS AND matched perception PASS AND ROI certified
AND unit contract certified AND the cue+video-only propagated null CANNOT explain the observed imagery
reliability (Delta_I>0, randomization p<0.05, where exchangeability valid; else B is a sealed sensitivity
criterion with a conservative pre-set decision). Dataset ≥2/6 → `C3XDR_D2_CUE_DECONFOUNDED_IMAGERY_
QUALIFIED`; exactly 1 → `…_LIMITED`; 0 (genuinely unreliable) → `…_FAIL`; execution incomplete →
`C3XDR_BLOCKED_*`. BLOCKED ≠ FAIL.

## 11. Authorization
Only `C3XDR_D2_CUE_DECONFOUNDED_IMAGERY_QUALIFIED` may authorize preparation of a separately-sealed C3XE
gate. It executes no geometry/reconstruction/C4. Behaviour non-gating; no semantic features; no geometry
imports (test-enforced). No raw/derived neural arrays in git.

## STOP after C3XDR.
