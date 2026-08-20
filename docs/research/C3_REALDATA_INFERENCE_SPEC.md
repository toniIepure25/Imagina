# C3 Real-Data Inference Specification

**Branch:** `research/fmri-imagery-transfer-c3-realdata`
**Date:** 2026-07-24
**Status:** FROZEN BEFORE REAL DATA ANALYSIS

---

## 1. Critical n=4 → n=1 Limitation

### Original Protocol Design (n=4)
The C3 protocol was designed for 4 participants (subj01, subj02, subj05, subj07).
With 4 participants, a group-level sign-flip test has:
- 2^4 = 16 possible configurations
- Minimum exact p-value: 1/16 = 0.0625
- Cannot reject at alpha = 0.05

### Current Execution Constraint (n=1 full pipeline)
Local disk (67.64 GB free) supports full perception decoder training for subj01 only.
Each subject's perception betas require ~40.77 GB.

**Therefore:** The primary inference unit for the initial execution is **subj01 only**.
Group-level inference across 4 participants is deferred pending additional storage.

## 2. Primary Inference Procedure (Within-Subject Randomization)

For subj01, the valid inferential procedure is a **within-subject permutation test**
that shuffles the stimulus-to-target correspondence while preserving participant structure.

### Procedure

1. Train perception decoder on subj01 NSD perception data (split by image identity)
2. Apply frozen decoder to subj01 imagery betas → predict embeddings
3. Compute real MRR against frozen candidate pool (12 imagery targets)
4. For each of N_perm permutations:
   a. Shuffle the 12 target labels randomly among imagery trials
      (respecting the repeat structure: all repeats of stimulus k get label k)
   b. Recompute MRR with shuffled labels
   c. Store null MRR
5. Compute p-value: proportion of null MRR >= observed MRR

### Frozen Parameters

| Parameter | Value |
|-----------|-------|
| N_perm | 100,000 |
| Seed | 20260724 |
| Group statistic | Not applicable (n=1) |
| Alpha | 0.05 |
| Minimum effect of interest | MRR > 1/12 (chance for 12 candidates) |

### What This Tests

The within-subject permutation tests whether subj01's fMRI imagery activations
carry stimulus-specific information that the perception-trained decoder can recover,
above what would be expected from random stimulus-target correspondence.

### What This Does NOT Test

- Population generalizability (requires n > 1)
- Cross-subject transfer
- General imagery decoding capability

## 3. Supplementary Multi-Subject Analysis (If Data Acquired)

If additional subjects' perception data can be acquired (Option C sequential processing):

### Group Randomization Procedure (n=4)

For each of 100,000 joint permutations:
1. Within each participant independently, randomly permute the target-to-stimulus
   correspondence (shuffle which embedding is the correct answer for each trial)
2. Recompute per-participant MRR with shuffled labels
3. Compute per-participant Delta = real_MRR - shuffled_MRR
4. Aggregate using group mean of per-participant Deltas
5. Store group null statistic

p-value = proportion of null group means >= observed group mean

### Supplementary Sign-Flip (n=4)

- 16 configurations
- Minimum p = 0.0625
- Report as supplementary only
- Cannot reject at alpha = 0.05

## 4. Frozen Inference Configuration

### Candidate Pool
- 12 NSD-Imagery target stimuli with valid ground-truth images
- 6 simple (Set A: geometric bars and crosses)
- 6 complex (Set B: natural scenes from NSD shared1000)
- Conceptual (Set C): EXCLUDED from primary MRR (no ground-truth image for embedding)

### Duplicate Policy
- Each trial maps to exactly one target in the candidate pool
- All repeats of the same stimulus target share one embedding
- No duplicate embeddings in the pool

### CLIP Model
- `openai/clip-vit-large-patch14`
- Embedding dimension: 768
- Normalization: L2
- Weight hash: to be computed and frozen before evaluation

### Perception Split
- Split by NSD image identity (10,000 unique images)
- 90% train / 10% held-out perception test
- Repeated presentations stay in one partition
- Normalization fit on train only
- Ridge alpha selected on inner CV within train only

### Imagery Trial Inclusion (corrected 2026-08-21 — see C3_NOVELTY_AND_OVERLAP.md
### changelog and results/c3_nsdimagery_row_mapping.json for provenance)

The official NSD-Imagery subj01 protocol is 12 task runs x 48 trials/run =
576 task trials total (confirmed directly from the 12 official behavioral
log TSVs, cross-checked against the official A/B/C_pair_list.mat cue
tables):

- Vision: 3 runs (visA, visB, visC) x 48 = 144 trials
- Attention: 3 runs (attA, attB, attC) x 48 = 144 trials
- Imagery: 6 runs (imgA_1, imgA_2, imgB_1, imgB_2, imgC_1, imgC_2) x 48 = 288 trials
  - Set A (simple): imgA_1 + imgA_2 = 96 trials = 6 stimuli x 16 repeats
  - Set B (complex): imgB_1 + imgB_2 = 96 trials = 6 stimuli x 16 repeats
  - Set C (conceptual): imgC_1 + imgC_2 = 96 trials = 6 concepts x 16 repeats,
    EXCLUDED from primary image-ground-truth analysis (no single fixed
    ground-truth image target)
- Attention runs: EXCLUDED from H2 (not an imagery condition)

Total imagery trials available for H2 is **288**, not a larger figure that
would result from mis-counting only one of each pair's two repeat-runs.

**This section describes the task-trial structure only.** The raw NSD-Imagery
beta file (`betas_nsdimagery.hdf5`) for subj01 contains 720 rows, not 576 —
see `results/c3_nsdimagery_row_mapping.json` for the (currently
`BLOCKED_IMAGERY_ROW_PROVENANCE`) investigation into the extra 144 rows and
the exact beta-row-to-trial alignment. H2 may not proceed until that mapping
is authoritatively resolved.

### Primary ROI
- `nsdgeneral` (combined visual cortex mask)
- Voxel selection: ROI membership AND ncsnr > 0

### Decoder
- Ridge regression
- Alpha candidates: [0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0, 100000.0]
- Inner CV folds: 5
- Target normalization: Yes (subtract mean, fit on train)
- Voxel z-scoring: Yes (fit on train)

## 5. Gate Decision Rules (Single-Subject Execution)

### Perception Foundation (subj01)
- PASS: Held-out perception MRR significantly above shuffled null (p < 0.05)
- FAIL: Perception MRR not above shuffled null

### Zero-Shot Imagery Transfer (subj01)
- PASS: Imagery MRR significantly above within-subject permutation null (p < 0.05)
- NULL_SUPPORTED: Imagery MRR not above null AND adequate power demonstrated
- INCONCLUSIVE: Not enough imagery targets/repeats for adequate power

### State Transport (subj01)
- PASS: Calibrated MRR on held-out imagery targets > identity transport MRR
- NULL: No improvement above identity

### Reconstruction Readiness
With n=1, reconstruction readiness requires BOTH:
1. Single-subject evidence (perception PASS + imagery transfer PASS)
2. Explicit acknowledgment that population generalization is NOT established

Possible decisions:
- `SINGLE_SUBJECT_PASS_AWAITING_POPULATION_EVIDENCE`
- `NULL_SUPPORTED_SINGLE_SUBJECT`
- `FAILED_BY_PERCEPTION_FOUNDATION`
- `BLOCKED_BY_REAL_DATA_ACCESS`

## 6. Sensitivity Analysis

### Within-Subject Power
With 12 target stimuli and multiple repeats:
- Candidate pool size: 12
- Chance MRR: 1/12 ≈ 0.083
- Maximum possible MRR: 1.0
- A good decoder should achieve MRR > 0.3 (rank 1 for ~30% of trials, rank 2-3 for others)

Simulate frozen permutation test using:
- Actual trial counts
- Actual candidate pool size
- Fixed seed
- Report minimum detectable effect

### Power Estimation
Run power simulation before real evaluation:
- Generate synthetic "positive" data at various effect sizes
- Run the same permutation procedure
- Report power curve as function of true MRR

## 7. Provenance Requirements

Every real-data artifact must contain:
```
dataset_id: NSD / NSD-Imagery
dataset_version: 1.0
participant_set: [subj01] (or expanded)
beta_variant: func1pt8mm/betas_fithrf
beta_file_hashes: {session -> SHA-256}
roi_file_hash: SHA-256 of nsdgeneral.nii.gz
ncsnr_hash: SHA-256 of ncsnr.nii.gz
clip_model: openai/clip-vit-large-patch14
clip_weight_hash: SHA-256 of model weights
candidate_pool_hash: SHA-256 of frozen embeddings
split_hash: SHA-256 of train/test partition
decoder_spec_hash: SHA-256 of DecoderConfig
randomization_seed: 20260724
n_permutations: 100000
code_sha: git rev-parse HEAD
created_at: ISO timestamp
confirmatory_or_exploratory: confirmatory
```

## 8. Replay Requirements

Replay must fail closed if any of the following change:
- Beta file hashes
- ROI file hash
- CLIP weight hash
- Split hash
- Decoder config hash
- Randomization seed
- Code SHA (for deterministic operations)
