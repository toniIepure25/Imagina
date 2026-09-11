# C3XAT — Atlas-defined Cue-Deconfounded Raw Imagery Qualification (prospective protocol)

**NEW prospectively-sealed measurement-qualification family. NOT a continuation, relaxation, or exact
replication of the released KamitaniLab ROI analysis (that is C3XDR, still provenance-blocked).
Measurement qualification ONLY — NO geometry, NO decoding, NO reconstruction, NO semantic features.**
C3XC / C3XD / C3XDR / C3XDR-R1 / C3XPR / C3XPA preserved unchanged.

## Why C3XAT exists
C3XPR/C3XPA established that exact released ROI membership is known in the released 2 mm frame, but the
public release lacks the authoritative released↔raw spatial link required for exact C3XDR replay, and no
author artifact is assumed to become available. Rather than substitute an approximate ROI inside the
frozen C3XDR seal, C3XAT defines a **new** analysis whose spatial definitions are completely reproducible
from public data (published atlases). See `results/c3xat/c3xat_scope_registry.json`.

## Core scientific question
When visual ROIs are defined prospectively using independently published, fully reproducible atlases
rather than the unrecoverable original Mind Captioning localizer ROIs, does cue-deconfounded
naturalistic video imagery exhibit reproducible stimulus-specific multivoxel activity across independent
imagery sessions?

## Phase 0 — prospective seal (`c3xat_protocol_seal.json`, committed before confirmatory processing)
Freezes: dataset, subjects, preprocessing, output space, primary ROI, secondary ROIs, whole-cortex
control, GLM (Model A), nuisance, reliability estimator, null, bootstrap, split seeds, cue/video
falsification, subject PASS rule, and the dataset decision rule.

## Dataset
OpenNeuro **ds005191 v1.0.2**, subjects **S1–S6**. Include: testImagery, testPerception, anat,
fieldmaps, events, sidecars. **Exclude trainPerception** (used for no neural/outcome/parameter-tuning
purpose even if technically required). Trial contract: imagery = 72 videos × 5 reps = 360 trials over 5
imagery sessions; perception = 72 videos × 5 reps; **72/72** exact video-identity correspondence
required; fail-closed on violation (verified against BIDS events only; no BOLD).

## Preprocessing space
Primary space **MNI152NLin2009cAsym, 2 mm isotropic**, one pinned fMRIPrep workflow. Frozen: fMRIPrep
version, container digest, FreeSurfer / TemplateFlow / ANTs / AFNI versions+hashes, all CLI and
output-space parameters. **Smoothing = NONE** for the primary multivoxel reliability. No post-outcome
preprocessing modification.

## Primary ROI — `WANG25_TOPOGRAPHIC_VISUAL_NETWORK`
Wang et al. 2015 probabilistic maps of visual topography, **volume-based MNI maximum-probability map
(MPM)**, using the **complete** atlas (25 maps / 22 regions). Pinned: source URL/repo, file version,
download date, SHA-256, MD5 (if supplied), space, resolution, label table. **No performance-based
subselection**; terminology is *atlas-defined topographic visual network* — **never** the Kamitani "VC".
Using the full MPM removes post-hoc choices (early vs high, ventral vs dorsal, occipital vs temporal),
minimizing researcher degrees of freedom.

## Secondary ROI — `BENSON_V1V2V3`
Benson14 anatomy-predicted retinotopy via pinned Neuropythy template; union of predicted V1+V2+V3 both
hemispheres. **Secondary**: cannot rescue a failed primary gate and cannot change primary PASS status.

## Whole-cortex control — `CORTICAL_GRAY_MATTER`
From preprocessing segmentation only; a descriptive enrichment control, **not** a qualification ROI.

## ROI QC (before any outcome)
Per subject: Wang25 count; Benson V1/V2/V3 and V1–V3 union counts; cortical-gray-matter count; affine,
shape, orientation, brain-mask overlap, left/right balance, finite coverage. Masks frozen and hashed
**before** computing R_I. No manual editing; no subject-specific ROI modification.

## GLM — `MODEL_A_LSA` (frozen, reused unchanged from C3XD/C3XDR)
per-trial cue + per-trial imagery + per-trial post-video + grouped evaluation + nuisance. Model A/B/C is
**not** reopened; no LSS switch on results.

## Nuisance (frozen before outcomes)
motion, run/session intercepts, drift/high-pass, justified physiological/tissue nuisance. **Never**
regress video identity, semantic embeddings, captions, vividness, or accuracy from the imagery signal.

## Primary reliability
`c3xb_reliability.reliability_with_inference_pairs`, independent unit = **imagery session**. Statistic
**R_I_ATLAS** = Spearman-Brown corrected session-disjoint split-half reliability of concatenated 72-video
mean multivoxel patterns in WANG25. Inference: `n_rep_point=200`, `n_perm=1000`, `n_boot=1000`. Split
seeds base **20260909**, offsets **0/100/200**; no seed selection. Null: within-imagery-session
video-label permutation (session/trial-count/video-count/ROI-data/temporal structure preserved; no
cross-session exchange). Bootstrap: non-straddling hierarchical (no session/trial in both halves;
C3R/C3XB safeguards retained).

## Cue/video contamination falsification (mandatory; identical concept to C3XDR)
Diagnose G_cue, G_imagery, G_video; cue_gain=G_cue/G_imagery, video_gain=G_video/G_imagery. Propagate
cue+post-video+nuisance through the exact Model-A imagery-beta operator → `R_I_cuevideo_predicted`;
`Delta_I = R_I_observed − R_I_cuevideo_predicted`. A subject does **not** pass on raw R_I alone; observed
reliability must survive the sealed criterion (Delta_I>0 AND randomization p<0.05 where exchangeable,
else sealed conservative sensitivity).

## Subject & dataset decision
**Subject PASS requires all:** WANG25 R_I PASS, WANG25 R_P PASS, cue/video criterion PASS, unit contract
PASS, atlas mask QC PASS. Statuses PASS / MARGINAL / NOISE_FLOOR. Benson V1–V3 is secondary and cannot
change primary PASS.
**Dataset gate:** ≥2/6 → `C3XAT_D2_ATLAS_IMAGERY_QUALIFIED`; exactly 1/6 → `…_LIMITED`; 0/6 valid →
`…_FAIL`; execution/provenance incomplete → `C3XAT_BLOCKED_*`. Independent of C3XDR.

## Secondary / descriptive (after primary is frozen)
Benson V1–V3 reliability + falsification reported separately (cannot change the decision); spatial
enrichment comparison WANG25 vs Benson vs whole-cortex vs ROI-size-matched random masks; optional purely
descriptive cross-pipeline comparison to released-preprocessed C3XC R_I (**not** an equivalence/
replication test — different spatial definitions).

## Authorization
ONLY `C3XAT_D2_ATLAS_IMAGERY_QUALIFIED` authorizes **preparing** (not executing) a new separately-sealed
gate **C3XAG** (Atlas-defined Perception↔Imagery State Geometry). C3XAG is not C3XE / C3XR / C3XR-CAT /
C3XDR-R2 and is not executed here.

## Forbidden
Features: CLIP, DINO, TimeSformer, DeBERTa, LLMs, captions, video embeddings, semantic labels, decoded
features, Stable Diffusion, reconstruction models. Geometry: G3/G4/G6/G8, CKA, RDM geometry, subspace
overlap, state transform/transport.

## STOP after C3XAT
Do not execute geometry, do not start C3XAG, do not decode, do not reconstruct, do not start C4.
