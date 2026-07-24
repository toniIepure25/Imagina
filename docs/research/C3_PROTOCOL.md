# C3 Protocol — fMRI Perception-to-Imagery Transfer and Reconstruction Readiness

**Branch:** `research/fmri-imagery-transfer-c3`
**Source SHA:** `15ce4a8952927eecc8425b04066049e7a3203807` (corrected C2 final)
**Status:** PROTOCOL LOCKED

---

## 1. Scientific Question

**Primary:**
Does a perception-trained fMRI decoder recover visual-semantic information
from mental imagery strongly and reproducibly enough to justify a later
image-reconstruction experiment?

**Secondary:**
Can a low-capacity imagery-state calibration transform improve transfer on
held-out imagery targets without changing the frozen perception decoder?

## 2. Datasets

### 2.1 NSD Perception Data

| Property | Value |
|----------|-------|
| Dataset | Natural Scenes Dataset (NSD) |
| Reference | Allen et al. (2022), doi:10.1038/s41593-021-00962-x |
| Modality | 7T fMRI |
| Subjects | 8 total; 4 completed 40 sessions (subj01, subj02, subj05, subj07) |
| Role | Large-scale perception decoder training |
| Stimuli | ~73,000 trials; 10,000 unique COCO images per subject |
| Beta variant | func1pt8mm/betas_fithrf (GLMsingle) |
| Resolution | 1.8mm isotropic |
| Access | naturalscenesdataset.org (institutional) |

### 2.2 NSD-Imagery

| Property | Value |
|----------|-------|
| Dataset | NSD-Imagery |
| Reference | Kneeland et al. (CVPR 2025), arXiv:2506.06898 |
| Modality | 7T fMRI (same protocol as NSD) |
| Subjects | 8 scanned; 4 eligible (subj01, subj02, subj05, subj07) |
| Role | Perception-to-imagery transfer evaluation |
| Unique stimuli | 18 (6 simple geometric, 6 complex natural, 6 conceptual) |
| Usable stimuli | 12 (simple + complex; conceptual excluded — no ground truth image) |
| Trials/subject | 576 total (12 runs × 48 trials) |
| Imagery trials | 192 imagery + 192 imagery repeat = 384 (across 6 imagery runs) |
| Vision trials | 144 (across 3 vision runs) |
| Repetitions | 8 per stimulus (vision), 16 per stimulus (imagery) |
| Trial duration | 4s (3s task + 1s rest) |
| Vividness rating | Binary (vivid / not vivid) per imagery trial |
| Beta variant | func1pt8mm/nsdimagerybetas_fithrf (GLMsingle) |
| Access | naturalscenesdataset.org (institutional) |

### 2.3 Eligibility

Only subjects who completed ALL 40 NSD perception sessions are eligible for
C3, because the perception decoder requires the full training set:

| Subject | 40 sessions | Imagery data | C3 eligible |
|---------|-------------|--------------|-------------|
| subj01 | Yes | Yes | **Yes** |
| subj02 | Yes | Yes | **Yes** |
| subj05 | Yes | Yes | **Yes** |
| subj07 | Yes | Yes | **Yes** |
| subj03 | No (30) | Yes | No |
| subj04 | No (30) | Yes | No |
| subj06 | No (30) | Yes | No |
| subj08 | No (30) | Yes | No |

**Eligible participants: 4**

## 3. Stimulus Structure

### 3.1 Simple Stimuli (Set A)
6 geometric shapes: 4 oriented bars (0°, 45°, 90°, 135°) + 2 crosses (+, ×).
Black on gray background. Far out-of-distribution relative to NSD training
(COCO natural images).

### 3.2 Complex Stimuli (Set B)
5 natural scenes from NSD shared1000 + 1 artwork ("The Two Sisters" by
Kehinde Wiley). Most comparable to NSD training distribution.

### 3.3 Conceptual Stimuli (Set C)
6 single-word concepts (abstract visual features/objects). Vision trials show
varying images matching the concept — no single ground truth image exists.
**Excluded from confirmatory analysis.**

### 3.4 Primary Evaluation Subset
Confirmatory analyses use **complex stimuli (Set B) only** as the primary
subset: these are the only stimuli both (a) in-distribution for NSD-trained
decoders and (b) associated with a single ground truth image.

Simple stimuli (Set A) are reported as a secondary, explicitly
out-of-distribution test.

## 4. Target Representation

| Property | Value |
|----------|-------|
| Model | CLIP ViT-L/14 (OpenAI) |
| Weights | openai/clip-vit-large-patch14 |
| Embedding dim | 768 |
| Normalization | L2-normalized |
| Preprocessing | Standard CLIP transform (224×224, normalize) |
| Frozen before | Any imagery evaluation |

The CLIP image embedding is computed for all 12 ground-truth target images
(6 simple + 6 complex) and stored as the frozen candidate pool.

## 5. Primary Metric

**All-candidate visual-embedding retrieval Mean Reciprocal Rank (MRR)**

For each held-out imagery trial:
1. Predict CLIP embedding from fMRI via the frozen perception decoder
2. Compute cosine similarity against all 12 candidates (simple + complex)
3. Rank the correct target
4. Compute reciprocal rank = 1/rank

Aggregate: mean across trials within participant → participant-level MRR →
population inference across 4 participants.

**Chance MRR:** For uniform random ranking in a 12-item pool:
H(12)/12 = (1 + 1/2 + ... + 1/12)/12 ≈ 3.103/12 ≈ 0.259

**Minimum effect of interest:** MRR > 0.35 (participant-level mean)
representing ~35% above chance in relative terms.

## 6. Primary Estimands

### 6.1 Zero-shot transfer
```
Delta_zero_shot = participant_MRR(real_decoder_on_imagery) - participant_MRR(shuffled_pairing_null)
```
Participant is the inferential unit (n=4).

### 6.2 State transport
```
Delta_transport = participant_MRR(calibrated_transport) - participant_MRR(identity_transport)
```

## 7. Hypotheses

### C3-H1: Perception Decoding Foundation
A ridge decoder trained on NSD perception fMRI predicts CLIP embeddings for
held-out perceived images above a shuffled-pairing null.

### C3-H2: Zero-Shot Perception-to-Imagery Transfer
The perception-trained decoder applied to imagery fMRI predicts the correct
target embedding above a matched null.

**Prior expectation (based on published evidence):** Kneeland et al. (2025)
showed CLIP 2WC of 46-53% (chance=50%) for existing models on imagery.
Spera et al. (2026) showed CLIP 48.94% for a frozen DynaDiff baseline.
**A null result is the most likely outcome.**

### C3-H3: ROI Dependence
Primary ROI: combined visual cortex (nsdgeneral mask).
Secondary ROIs: V1, V2, V3, hV4, ventral stream, lateral, parietal.

### C3-H4: Low-Capacity State Transport
A mean-correction or affine ridge applied to the frozen decoder output improves
imagery MRR above identity on held-out imagery trials.

### C3-H5: Uncertainty and Abstention
Decoder uncertainty predicts trial-level errors.

## 8. Model Hierarchy

| Model | Description | Role |
|-------|-------------|------|
| M0 | Null/metadata baselines | Controls |
| M1 | Ridge regression (primary) | Perception decoder |
| M2 | ROI-factorized ridge | Secondary decoder |
| M3 | Multimodal target (CLIP + lower-level) | Exploratory |
| M4 | Low-rank state transport | Calibration |
| M5 | Published benchmark comparison | Optional |

## 9. Split Policy

### Perception (training)
- Split by stimulus identity (image_id)
- All repetitions of the same image stay in one fold
- 5-fold cross-validation, stratified by session

### Imagery (zero-shot test)
- **No imagery trial enters any perception-side fitting**
- Entire imagery dataset is a sealed evaluation set

### Transport (H4)
- Nested leave-one-stimulus-out within imagery
- Held-out-target is the primary transport evaluation

## 10. Mandatory Controls

1. Shuffled fMRI-target pairing (null)
2. Mean-target prediction
3. Trial-order-only model
4. Run/session-only model
5. ROI signal-quality-only model (ncsnr)
6. Random ROI-matched voxels
7. Voxel-order permutation
8. Low-ncsnr voxel control
9. Cue and target metadata leakage audit
10. Duplicate-image leakage audit
11. Perception train/test image-identity separation
12. Imagery calibration/test target separation
13. Outer-test-blind hyperparameter selection
14. State transport vs identity
15. State transport vs random low-rank mapping
16. Generator-free success requirement

## 11. Statistical Inference

- Participant is the inferential unit (n=4)
- Primary test: exact permutation test (2^4 = 16 permutations for sign-flip)
- Alpha = 0.05 (one-sided: MRR > chance)
- Minimum detectable effect constrained by n=4
- Sensitivity analysis with actual participant-level variance

**Power limitation:** With n=4, only LARGE effects are detectable. Any null
must be reported with an explicit sensitivity bound. An honest power
statement is mandatory.

## 12. Decision Rules

| Outcome | Condition |
|---------|-----------|
| C3_RECONSTRUCTION_READINESS = PASS | H1 pass AND H2 pass |
| C3_RECONSTRUCTION_READINESS = PASS_CALIBRATION_REQUIRED | H1 pass AND H2 null AND H4 pass |
| C3_RECONSTRUCTION_READINESS = BLOCKED | H1 pass AND H2 null AND H4 null |
| C3 = FAILED_BY_PERCEPTION_FOUNDATION | H1 fails |
| C3 = FAILED_BY_LEAKAGE | Any control fails |

## 13. Claim Boundaries

**Allowed:**
- Perception embeddings transferred/failed to transfer to imagery
- Low-capacity calibration improved/failed to improve
- Specific ROIs carried/failed to carry information
- The tested pipeline is/is not reconstruction-ready

**Forbidden:**
- Thought reading / mind decoding
- Exact recovery of private mental imagery
- Real-time BCI claims
- Clinical efficacy
- Causal imagery enhancement
