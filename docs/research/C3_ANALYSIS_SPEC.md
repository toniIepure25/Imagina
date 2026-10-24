# C3 Analysis Specification

**Branch:** `research/fmri-imagery-transfer-c3`
**Locked before confirmatory imagery evaluation**

---

## 1. Frozen Specification (must not change after seeing imagery results)

### 1.1 Target Embedding
```
model: openai/clip-vit-large-patch14
framework: transformers or open_clip
embedding_dim: 768
normalization: L2
preprocessing: Resize(224) → CenterCrop(224) → ToTensor → Normalize(mean=[0.48145466, 0.4578275, 0.40821073], std=[0.26862954, 0.26130258, 0.27577711])
```

### 1.2 Primary ROI
```
primary: nsdgeneral (all visually responsive voxels per NSD definition)
secondary: prf-visualrois (V1=1, V2=2, V3=3, hV4=4)
tertiary: streams (ventral=1, lateral=2, parietal=3)
```

### 1.3 Primary Decoder
```
type: ridge regression
target: CLIP-ViT-L/14 image embedding (768-d)
input: z-scored voxel betas within nsdgeneral mask
regularization: alpha selected via inner CV on perception data
normalization: per-voxel z-score fit on training sessions only
voxel_selection: ncsnr > 0 within ROI mask (no performance-based selection)
```

### 1.4 Candidate Pool
```
pool_size: 12 (6 simple + 6 complex stimuli with ground truth)
pool_construction: precompute CLIP embedding for each ground truth image
duplicate_policy: not applicable (all 12 stimuli are unique)
```

### 1.5 Primary Metric
```
metric: MRR (Mean Reciprocal Rank)
aggregation: mean across trials → participant-level → population
chance: H(12)/12 ≈ 0.259
alpha: 0.05 (one-sided)
test: exact sign-flip permutation (2^4 = 16 permutations)
minimum_effect: 0.10 above chance (MRR ≥ 0.359)
```

### 1.6 Permutation Null
```
type: shuffled fMRI-target pairing
method: for each permutation, randomly reassign target labels
n_permutations: exhaustive (all possible for n=4 sign-flips)
```

## 2. Perception Decoder Training (C3-H1)

### 2.1 Data
- Subject-specific: one decoder per subject
- Training: NSD perception betas (sessions 1-37), test: sessions 38-40
  (or official NSD train/test split by image_id)
- Use official NSD shared1000 as held-out test set
- All repetitions of the same image averaged before training

### 2.2 Procedure
```
for each subject:
    1. Load betas for nsdgeneral voxels
    2. Z-score voxels (fit on training images only)
    3. Average repeated presentations of same image
    4. Compute CLIP embedding for each stimulus image
    5. Fit ridge regression: voxels → CLIP embedding
    6. Select alpha via 5-fold inner CV (by image_id)
    7. Evaluate on held-out NSD test images
    8. Report: correlation, MRR on test set
```

### 2.3 Success Criterion
```
Perception MRR on NSD shared1000 (982 test images):
    must be > shuffled null with p < 0.001
Expected: MRR >> 0.5 for subject-specific ridge (well-established)
```

## 3. Zero-Shot Imagery Transfer (C3-H2)

### 3.1 Procedure
```
for each subject:
    1. Freeze the trained perception decoder (from H1)
    2. Load imagery betas for nsdgeneral voxels
    3. Z-score imagery voxels using TRAINING-FIT normalization
    4. Apply frozen decoder → predicted CLIP embeddings
    5. For each imagery trial:
        a. Compute cosine similarity to all 12 candidate embeddings
        b. Rank candidates
        c. Record rank of correct target
        d. Compute reciprocal rank
    6. Report: trial-level RR, stimulus-level MRR, participant-level MRR
```

### 3.2 Null Control
```
For shuffled null:
    Randomly permute the mapping between fMRI trials and target labels
    Repeat 10000 times → null distribution of participant-level MRR
```

### 3.3 Subgroup Analysis (prespecified)
```
Primary: all 12 stimuli
Secondary: complex only (6 stimuli, in-distribution)
Exploratory: simple only (6 stimuli, out-of-distribution)
```

## 4. ROI Analysis (C3-H3)

### 4.1 ROI Definitions
```
nsdgeneral: all visually responsive voxels (primary)
V1: prf-visualrois == 1
V2: prf-visualrois == 2
V3: prf-visualrois == 3
hV4: prf-visualrois == 4
ventral: streams == 1
lateral: streams == 2
parietal: streams == 3
```

### 4.2 Procedure
Train separate ridge decoders per ROI (same procedure as H1).
Apply each to imagery. Report MRR per ROI per subject.
Do NOT select "best ROI" after seeing imagery results.

## 5. State Transport (C3-H4)

### 5.1 Transport Models
```
identity: y_calibrated = y_predicted (no change)
mean_correction: y_calibrated = y_predicted + (mean_imagery_train - mean_perception_train)
affine_ridge: y_calibrated = A @ y_predicted + b, fitted with ridge regularization
low_rank_linear: y_calibrated = U @ V^T @ y_predicted, rank ≤ 10
```

### 5.2 Split
```
Leave-one-stimulus-out cross-validation within imagery:
    - For each of 12 target stimuli:
        - Train transport on remaining 11 stimuli's imagery trials
        - Evaluate on held-out stimulus's imagery trials
    - Report: held-out-target MRR per subject
```

### 5.3 Controls
```
random_low_rank: same structure as low_rank_linear but with random weights
permuted_target: transport fitted on shuffled imagery labels
```

## 6. Uncertainty (C3-H5)

### 6.1 Uncertainty Sources
```
repeat_variance: variance of predicted embedding across imagery repetitions
decoder_variance: bootstrap variance of ridge coefficients
distribution_distance: Mahalanobis distance from perception training distribution
roi_disagreement: variance of predictions across ROI-specific decoders
```

### 6.2 Evaluation
```
calibration: reliability diagram (predicted confidence vs actual accuracy)
error_correlation: Spearman(uncertainty, |error|)
risk_coverage: selective MRR at various abstention thresholds
```

## 7. Secondary Metrics

| Metric | Definition |
|--------|-----------|
| Top-1 accuracy | Fraction of trials where correct target is rank 1 |
| Top-3 accuracy | Fraction of trials where correct target is rank ≤ 3 |
| Median rank | Median rank of correct target |
| Cosine similarity | Mean cosine(predicted_embedding, true_embedding) |
| Two-way identification | 2AFC accuracy against random foil |

## 8. Provenance Requirements

Every result artifact contains:
```json
{
    "dataset_id": "nsd_imagery",
    "dataset_version": "1.0",
    "participant_set": ["subj01", "subj02", "subj05", "subj07"],
    "beta_variant": "func1pt8mm/betas_fithrf",
    "roi_mask": "nsdgeneral",
    "embedding_model": "openai/clip-vit-large-patch14",
    "split_hash": "<sha256 of split assignment>",
    "decoder_spec_hash": "<sha256 of decoder config>",
    "random_seed_registry": {"numpy": 42, "split": 42},
    "code_sha": "<git commit>",
    "confirmatory_or_exploratory": "confirmatory",
    "created_at": "<ISO-8601>"
}
```
