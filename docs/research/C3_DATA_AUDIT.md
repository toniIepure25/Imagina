# C3 Data Audit — NSD and NSD-Imagery

**Date:** 2026-07-24
**Branch:** `research/fmri-imagery-transfer-c3`
**Status:** AUDIT COMPLETE — confirms 4 eligible participants, partial local data

---

## 1. NSD-Imagery Participants

| Participant | 40 NSD sessions | Imagery data | Perception betas local | Imagery betas local | ROI masks local | Behavioral local | Eligible | Exclusion |
|-------------|-----------------|--------------|----------------------|--------------------|-----------------|--------------------|----------|-----------|
| subj01 | Yes | Yes | No | Yes (1003.7 MB) | Yes | Yes | **Yes** | — |
| subj02 | Yes | Yes | No | No | No | No | **Yes** | Data not yet downloaded |
| subj05 | Yes | Yes | No | No | No | No | **Yes** | Data not yet downloaded |
| subj07 | Yes | Yes | No | No | No | No | **Yes** | Data not yet downloaded |
| subj03 | No (30 sessions) | Yes | — | — | — | — | No | Insufficient perception training data |
| subj04 | No (30 sessions) | Yes | — | — | — | — | No | Insufficient perception training data |
| subj06 | No (30 sessions) | Yes | — | — | — | — | No | Insufficient perception training data |
| subj08 | No (30 sessions) | Yes | — | — | — | — | No | Insufficient perception training data |

**Eligible participants: 4** (subj01, subj02, subj05, subj07)

## 2. Data Inventory — subj01 (confirmed local)

### 2.1 Imagery Betas
- **Path:** `nsddata_betas/ppdata/subj01/func1pt8mm/nsdimagerybetas_fithrf/betas_nsdimagery.hdf5`
- **Size:** 1003.74 MB
- **Variant:** fithrf (GLMsingle)
- **Space:** func1pt8mm (1.8mm isotropic)
- **Status:** Downloaded ✓

### 2.2 Signal Quality (ncsnr)
- **Path:** `nsddata_betas/ppdata/subj01/func1pt8mm/betas_fithrf/ncsnr.nii.gz`
- **Size:** 1.09 MB
- **Status:** Downloaded ✓

### 2.3 ROI Masks
| File | Size | Status |
|------|------|--------|
| `roi/prf-visualrois.nii.gz` | 65.6 KB | ✓ |
| `roi/streams.nii.gz` | 68.1 KB | ✓ |
| `roi/nsdgeneral.nii.gz` | 65.1 KB | ✓ |
| `mean_nsdimagery.nii.gz` | 809.7 KB | ✓ |
| `valid_nsdimagery.nii.gz` | 2.4 KB | ✓ |

### 2.4 Behavioral Data (12 TSV files)
| File | Description |
|------|-------------|
| `nsdimagery_subj01_visA.tsv` | Vision trials, Set A (simple) |
| `nsdimagery_subj01_visB.tsv` | Vision trials, Set B (complex) |
| `nsdimagery_subj01_visC.tsv` | Vision trials, Set C (conceptual) |
| `nsdimagery_subj01_imgA_1.tsv` | Imagery trials, Set A, rep 1 |
| `nsdimagery_subj01_imgA_2.tsv` | Imagery trials, Set A, rep 2 |
| `nsdimagery_subj01_imgB_1.tsv` | Imagery trials, Set B, rep 1 |
| `nsdimagery_subj01_imgB_2.tsv` | Imagery trials, Set B, rep 2 |
| `nsdimagery_subj01_imgC_1.tsv` | Imagery trials, Set C, rep 1 |
| `nsdimagery_subj01_imgC_2.tsv` | Imagery trials, Set C, rep 2 |
| `nsdimagery_subj01_attA.tsv` | Attention trials, Set A |
| `nsdimagery_subj01_attB.tsv` | Attention trials, Set B |
| `nsdimagery_subj01_attC.tsv` | Attention trials, Set C |

### 2.5 Experiment Metadata
| File | Status |
|------|--------|
| `designmatrixGLMsingle.mat` | ✓ |
| `A_pair_list.mat` | ✓ |
| `B_pair_list.mat` | ✓ |
| `C_pair_list.mat` | ✓ |
| `cue_pair_list.xlsx` | ✓ |
| `attA_dm.mat` / `attB_dm.mat` / `attC_dm.mat` | ✓ |
| `visA_dm.mat` / `visB_dm.mat` / `visC_dm.mat` | ✓ |
| `imgA_1_dm.mat` through `imgC_2_dm.mat` | ✓ |
| `rawtargetimages/setA/` | 13 files |
| `rawtargetimages/setB/` | Present |

### 2.6 Perception Betas (NOT available locally)
The main NSD perception betas (betas_session01.hdf5 through betas_session40.hdf5)
are NOT downloaded for any subject. Each session file is approximately 400-700 MB.
Total per subject: ~16-28 GB.

**These are required for training the perception decoder (C3-H1).**

## 3. NSD-Imagery Trial Structure

### 3.1 TSV Column Schema
From behavioral TSV inspection:
```
SUBJECT, SESSION, RUN, TRIAL, CONDITION, CUE, FRAMEFILE, IMAGEFILE,
GROUNDTRUTH, ISCORRECT, CHANGEMIND, TOTAL1, TOTAL2, BUTTON,
TRIALONSET, TRIALEND, IMAGEONSET, IMAGESERIESENDS, FINALDECISIONTIME, RT
```

### 3.2 Trial Counts (per subject, per run type)
- Vision runs (3): 48 trials each = 144 vision trials
- Imagery runs (6): 48 trials each = 288 imagery trials (2 reps × 3 sets × 48)
- Attention runs (3): 48 trials each = 144 attention trials (excluded)
- **Total per subject:** 576 trials
- **Usable imagery trials (simple + complex):** 192 (4 sets × 48)
- **Usable imagery trials per stimulus:** 16 (2 reps × 8 within-run reps)

### 3.3 Stimulus Conditions (per set)
| Set | Stimuli | Cue letters |
|-----|---------|-------------|
| A (simple) | 4 bars + 2 crosses | L, V, H, + others |
| B (complex) | 5 scenes + 1 artwork | Unique letters |
| C (conceptual) | 6 word concepts | Unique letters |

## 4. Required Downloads (Not Yet Acquired)

### Priority 1 — Minimum for C3-H1 perception foundation (subj01)
| File | Approx size | Source |
|------|-------------|--------|
| `betas_session01.hdf5` ... `betas_session40.hdf5` | ~16-28 GB total | naturalscenesdataset.org (S3) |

### Priority 2 — Full C3 dataset (subj02, 05, 07)
| Item | Per subject |
|------|-------------|
| Perception betas (40 sessions) | ~16-28 GB |
| Imagery betas (HDF5) | ~1 GB |
| ROI masks (3 files) | ~200 KB |
| Behavioral TSVs (12 files) | ~100 KB |
| ncsnr map | ~1 MB |

### Priority 3 — Stimulus embeddings
| Item | Notes |
|------|-------|
| 12 target images (CLIP embeddings) | Compute locally from rawtargetimages |
| NSD shared1000 image IDs for Set B | Cross-reference pair_list.mat |

## 5. Data Location Configuration

C3 uses environment variables for data roots (never hardcoded paths):
```
NSD_DATA_ROOT — root of nsddata (ROIs, behavioral, ppdata)
NSD_BETAS_ROOT — root of nsddata_betas
NSD_STIMULI_ROOT — root of target stimulus images
```

Local machine paths (gitignored):
```
NSD_DATA_ROOT=D:\ComputaCenter\FMRI2images\data\nsd\nsddata
NSD_BETAS_ROOT=D:\ComputaCenter\FMRI2images\data\nsd\nsddata_betas
NSD_STIMULI_ROOT=D:\ComputaCenter\FMRI2images\data\nsd\nsddata\experiments\nsdimagery\rawtargetimages
```

## 6. Data Quality Considerations

1. **SNR gap:** Imagery betas have fundamentally lower SNR than perception betas
   (documented in Allen et al. 2022 and Kneeland et al. 2025)
2. **Spatial resolution:** Imagery representations in early visual cortex have
   broader receptive fields (Breedlove et al.)
3. **Distribution shift:** Simple geometric stimuli are far OOD relative to
   COCO-trained NSD decoders. Complex stimuli (Set B) are the closest to
   in-distribution.
4. **Small candidate pool:** 12 stimuli with ground truth → coarse MRR scale.
   At 12 items, MRR only takes values k/12 where k divides into rank positions.

## 7. Risks and Limitations

- **n=4 subjects** → minimal statistical power, only large effects detectable
- **18 stimuli (12 usable)** → coarse retrieval metric, low ceiling for MRR
- **Published zero-shot baseline at chance** → H2 null is the most likely outcome
- **Perception betas not yet downloaded** → compute/storage bottleneck (~100 GB total)
- **Institutional access** required for NSD data
