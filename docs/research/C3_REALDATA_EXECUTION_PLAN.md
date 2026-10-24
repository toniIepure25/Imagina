# C3 Real-Data Execution Plan

**Branch:** `research/fmri-imagery-transfer-c3-realdata`
**Date:** 2026-07-24
**Source SHA:** `c36768a741fd36ac09906a28a0c96d60b7b69481`

---

## 1. Disk and Feasibility Assessment

| Resource | Value |
|----------|-------|
| D: drive free | 67.64 GB |
| subj01 perception betas (40 sessions × 1043.7 MB) | 40.77 GB |
| subj01 imagery betas (already local) | 0.98 GB |
| subj01 ROI + ncsnr + behavioral (already local) | ~12 MB |
| Remaining after subj01 perception download | ~26.8 GB |
| subj02/05/07 perception betas (each) | ~40.77 GB |
| subj02/05/07 imagery + support (each) | ~1.1 GB |

**Conclusion:** Local disk supports full pipeline execution for **subj01 only**.
Additional subjects require either external storage or sequential process-then-delete workflow.

## 2. Execution Feasibility Decision

### Option A: Single-subject pilot (feasible now)
- Download subj01 perception betas (40.77 GB)
- Run complete perception decoder + zero-shot imagery transfer for subj01
- Report single-subject results as technical validation
- Cannot perform group inference (n=1)

### Option B: Full 4-subject execution (blocked by disk)
- Requires ~163 GB for perception betas alone
- Current free space: 67.64 GB
- **NOT FEASIBLE** without external storage

### Option C: Sequential processing (partially feasible)
- Download subj01 perception betas → train decoder → delete perception betas
- Download subj02 perception betas → train decoder → delete
- Repeat for 05, 07
- Keep imagery betas + trained decoders (~5 GB total)
- Requires imagery data for subj02/05/07 (~3.3 GB)
- **Feasible but risky** (provenance requires hash verification; deleted betas cannot be re-verified)

### Selected Strategy: **Option A + staged expansion**

Execute the complete pipeline for subj01 as a full technical pilot. This establishes:
1. That the perception decoder works on real NSD data
2. That imagery transfer can be evaluated end-to-end
3. Single-subject zero-shot MRR and comparison to null

Then, if subj01 perception passes, download imagery-only data for subj02/05/07 (~3.3 GB)
and apply the subj01-trained decoder cross-subject (exploratory only) OR attempt Option C
for within-subject decoders.

**Critical limitation:** With n=1, the prescribed group-level randomization test is
not meaningful. The primary inference becomes **within-subject permutation** (shuffling
stimulus-to-target correspondence) rather than across-participant sign-flip.

## 3. Acquisition Stages

### Stage 1 — Verify existing subj01 imagery data
- Location: `D:\ComputaCenter\FMRI2images\data\nsd\`
- Files: imagery betas, ROI masks, ncsnr, behavioral TSVs
- Action: Hash verification, schema validation, axis confirmation
- Prior verification: FMRI2images/artifacts/mindcompiler/roy_s1/ (re-verify independently)

### Stage 2 — Download subj01 perception betas
- Source: `s3://natural-scenes-dataset/nsddata_betas/ppdata/subj01/func1pt8mm/betas_fithrf/`
- Files: `betas_session01.hdf5` through `betas_session40.hdf5`
- Size: 40.77 GB
- Protocol: resumable download with .part files, SHA-256 verification, atomic rename
- Estimated time: 3-8 hours depending on bandwidth

### Stage 3 — Download NSD stimulus metadata
- Source: `s3://natural-scenes-dataset/nsddata/experiments/nsd/`
- Required: `nsd_expdesign.mat` or equivalent stimulus mapping
- Purpose: Map session/trial → image_id → CLIP embedding

### Stage 4 — Compute CLIP embeddings for imagery targets
- Source: local rawtargetimages in FMRI2images
- Model: `openai/clip-vit-large-patch14`
- Output: 12 target embeddings (768-d, L2-normalized)
- Freeze before any decoding evaluation

### Stage 5 — (Deferred) Additional subjects
- Download imagery data for subj02/05/07 after subj01 validation passes
- Group inference requires either:
  - External storage for perception betas, OR
  - Sequential download-process-delete workflow (Option C)

## 4. NSD Perception Data Structure (Expected)

Each `betas_sessionXX.hdf5` contains:
- Dataset: `/betas` — shape [n_trials_in_session, 83, 104, 81], dtype int16
- Axes: [trials, Z, Y, X] (reversed vs NIfTI convention)
- Scale: values × 300 = percent signal change
- Sessions have ~750 trials each
- Total subj01: ~30,000 trials across 40 sessions

## 5. NSD Stimulus Mapping

Each trial in each session maps to a specific NSD image (out of 73,000 total).
- 10,000 unique images shown to each subject
- ~1,000 "shared1000" images shown to all 8 subjects (3 presentations each)
- ~9,000 "special" images unique to each subject (various repeat counts)
- Mapping defined in `nsd_expdesign.mat` → `masterordering` variable

## 6. Timeline and Checkpoints

| Checkpoint | Description | Blocker |
|-----------|-------------|---------|
| CP1 | Existing data verification | None |
| CP2 | Perception betas downloaded for subj01 | Network bandwidth |
| CP3 | Stimulus mapping established | nsd_expdesign.mat download |
| CP4 | CLIP embeddings frozen | CLIP model download |
| CP5 | Perception decoder trained and validated | CP2 + CP3 + CP4 |
| CP6 | Zero-shot imagery transfer evaluated | CP5 + CP1 |
| CP7 | State transport evaluated | CP6 |
| CP8 | Uncertainty and controls | CP7 |

## 7. Abort Conditions

Abort and issue `BLOCKED_BY_REAL_DATA_ACCESS` if:
- S3 access fails or requires authentication not available
- Downloaded files fail integrity verification
- Disk space becomes insufficient during download
- NSD stimulus mapping cannot be resolved

Abort and issue `FAILED_BY_PERCEPTION_FOUNDATION` if:
- Real perception decoding MRR does not exceed shuffled null
- After completing the full perception training pipeline

## 8. Environmental Configuration

```
NSD_DATA_ROOT=D:\ComputaCenter\FMRI2images\data\nsd\nsddata
NSD_BETAS_ROOT=D:\ComputaCenter\FMRI2images\data\nsd\nsddata_betas
NSD_STIMULI_ROOT=D:\ComputaCenter\FMRI2images\data\nsd\nsddata\experiments\nsdimagery\rawtargetimages
NSD_CACHE_ROOT=D:\ComputaCenter\FMRI2images\data\nsd\cache
```

These paths are for the local machine only. They must not be committed to Git.
