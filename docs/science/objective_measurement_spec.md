# Objective Measurement Specification — IMAGINA

> **Status:** Synthetic engineering validation. No human psychometric properties established.

## Task Battery

### Task A: Multi-Feature Imagery Reconstruction
- **Phases:** fixation → target → mask → imagery → reconstruction → confidence
- **Dimensions:** orientation, hue, spatial frequency, position, size
- **Scoring:** Feature-space error normalized by perceptual range

### Task B: Imagery Manipulation
- **Phases:** fixation → base stimulus → transformation cue → imagery → reconstruction → confidence
- **Transforms:** rotate, shift, scale frequency, change hue, enlarge/shrink
- **Scoring:** Distance from mathematically expected transformed target

### Task C: Delayed Imagery Stability
- **Phases:** fixation → target → variable delay → reconstruction → confidence
- **Delays:** 1s, 3s, 6s, 10s
- **Scoring:** Immediate vs. delayed error; stability slope

### Task D: Perceptual Negative Control
- **Phases:** fixation → target (visible) → matching → confidence
- **Purpose:** Isolates motor/perceptual skill from imagery
- **Interpretation:** Improvement here alone ≠ imagery improvement

## Scoring Functions

All scoring uses `backend/app/research/psychophysics/scoring.py` (version 1.0).

| Feature | Error Function | Normalization |
|---------|---------------|---------------|
| Orientation | Circular distance | / 90 degrees |
| Hue | Circular hue distance | / 180 degrees |
| Position | Euclidean distance | / display diagonal |
| Spatial Frequency | abs(log(response/target)) | / log(max/min) |
| Size | abs(log(response/target)) | / log(max/min) |

## Composite Weights (Frozen)

```python
DEFAULT_COMPOSITE_WEIGHTS = {
    "orientation": 0.25,
    "hue": 0.20,
    "spatial_frequency": 0.20,
    "position": 0.20,
    "size": 0.15,
}
```

## Calibration

- 3-down/1-up transformed staircase
- Condition-independent (frozen before experimental sessions)
- Stored with protocol version, threshold, uncertainty, and hash

## Determinism

- Trial schedules are seed-controlled, balanced, frozen, and hashable
- Scoring code is versioned and included in session manifests
- Replay reconstructs and rescores exact trials
