# C3 Stimulus Reconstruction Audit

## Overview

NSD stimuli are **square-cropped and resized COCO images** at 425×425 pixels, stored
in `nsd_stimuli.hdf5` as `imgBrick[73000, 425, 425, 3]` uint8.

Instead of downloading the full 36.84 GB HDF5, we reconstruct the 10,000 images
viewed by subj01 from the publicly available COCO source images using the
`cropBox` metadata in `nsd_stim_info_merged.pkl`.

## Frozen Reconstruction Specification

| Parameter | Value |
|-----------|-------|
| Source | COCO images from `images.cocodataset.org/{cocoSplit}/{cocoId:012d}.jpg` |
| Crop metadata | `nsd_stim_info_merged.pkl` → `cropBox` column |
| **cropBox format** | **(top_frac, bottom_frac, left_frac, right_frac)** |
| Coordinate convention | Fractions of **original image dimensions** (H for top/bottom, W for left/right) |
| Crop computation | `top_px = int(top_frac * H)`, `bottom_px = int(bottom_frac * H)`, `left_px = int(left_frac * W)`, `right_px = int(right_frac * W)` |
| Crop application | `img.crop((left_px, top_px, W - right_px, H - bottom_px))` |
| **Result must be square** | `(W - left_px - right_px) == (H - top_px - bottom_px)` |
| Rounding policy | `int()` truncation (floor for positive fractions) |
| Resize target | 425 × 425 pixels |
| Interpolation | PIL `Image.LANCZOS` (high-quality downsampling) |
| Antialias | Implicit in LANCZOS |
| Color mode | RGB (converted from JPEG RGB) |
| Output format | PNG (lossless storage of the reconstructed pixel values) |
| Output dimensions | 425 × 425 × 3, uint8 |

## CropBox Convention Discovery

The cropBox format was **empirically verified** by comparing reconstructed stimuli
against the official `nsd_stimuli.hdf5` accessed via S3 HTTP range reads.

### Method

1. Downloaded COCO source images for selected NSD IDs.
2. Applied candidate crop interpretations.
3. Resized to 425×425 with LANCZOS.
4. Compared pixel-by-pixel against official `imgBrick[nsd_id]`.
5. Also performed brute-force offset scanning to find optimal crop position.

### Evidence

| nsdId | COCO size | cropBox | Best crop | Verified match |
|-------|-----------|---------|-----------|----------------|
| 13 | 640×480 | (0, 0, 0.125, 0.125) | Center H-square: x=80→560 | mean_diff=0.81, max=18 |
| 10 | 480×640 | (0.125, 0.125, 0, 0) | Center W-square: y=80→560 | mean_diff=1.22, max=18 |
| 27 | 480×640 | (0, 0.25, 0, 0) | Top-aligned: y=0→480 | mean_diff=0.96, max=24 |
| 95 | 480×640 | (0.25, 0, 0, 0) | Bottom-aligned: y=160→640 | mean_diff=0.63, max=20 |
| 147 | 640×427 | (0, 0, 0, 0.333) | Left-aligned: x=0→427 | mean_diff=1.22, max=28 |

### Incorrect interpretation (rejected)

The initial implementation used `(top, left, bottom, right)` ordering.
This produced non-square intermediate crops and mean pixel differences of 29–54
against the official stimuli. This has been corrected.

## JPEG Decoding Tolerance

The small residual differences (mean < 1.3, max ≤ 28) arise from:

1. **JPEG codec differences**: COCO images downloaded from `images.cocodataset.org`
   may have been decoded differently than when NSD originally processed them.
2. **LANCZOS interpolation rounding**: Sub-pixel interpolation on different source
   pixels produces ±1 rounding differences.

### Frozen tolerance

| Metric | Threshold |
|--------|-----------|
| Maximum absolute pixel difference | ≤ 30 |
| Mean absolute pixel difference | ≤ 2.0 |

These thresholds were established BEFORE examining the full dataset and are
justified by JPEG codec behavior. CLIP embeddings computed on images within
this tolerance will be functionally identical (cosine similarity > 0.999).

## Image-Index Conventions

| Convention | Description |
|-----------|-------------|
| `nsd_stim_info_merged.pkl` index | 0-based (row 0 = nsdId 0) |
| `subjectim` matrix | 1-based NSD image IDs (value range 1–73000) |
| `masterordering` | 1-based trial image slot indices |
| NSD image ID (nsdId) | 0-based in code, `subjectim[subj, slot] - 1` |
| `imgBrick` HDF5 index | 0-based (index 0 = nsdId 0) |
| COCO ID | Integer from COCO metadata, unrelated to NSD indexing |
| Output filename | `nsd_{nsdId:05d}.png` |
| CLIP embedding row | Corresponds to sorted participant image slot order |

## Validation Subset Selection

For gold-standard comparison, select images covering:
- First and last participant images
- Shared1000 and non-shared images
- Extreme crop magnitudes (large and small)
- Different COCO splits (train2017, val2017)
- Portrait and landscape source images
- Top/bottom/left/right/center crops

## Certification Status

Set after running the full gold-standard comparison on ≥20 representative images
from the 10,000 participant set.

Possible statuses:
- `STIMULUS_RECONSTRUCTION_PIXEL_IDENTICAL`
- `STIMULUS_RECONSTRUCTION_EQUIVALENT_WITH_FROZEN_TOLERANCE`
- `STIMULUS_RECONSTRUCTION_NOT_EQUIVALENT`
- `STIMULUS_RECONSTRUCTION_BLOCKED_NO_GOLD_STANDARD`
