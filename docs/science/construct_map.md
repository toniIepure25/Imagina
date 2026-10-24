# Construct Map — IMAGINA Objective Imagery Measurement

> **Status:** Synthetic validation only. No human construct validity established.

## Primary Construct: Imagery Precision

How accurately imagined visual features can be reconstructed from memory after a mask/interference interval.

**Endpoint:** `composite_reconstruction_error` (standardized multi-feature error, lower is better)

**Components:**
- Orientation error: circular distance / 90 degrees
- Hue error: circular hue distance / 180 degrees
- Position error: Euclidean distance / display diagonal
- Spatial frequency error: absolute log-ratio
- Size error: absolute log-ratio

**Weights (frozen):** orientation=0.25, hue=0.20, spatial_frequency=0.20, position=0.20, size=0.15

## Secondary Constructs

### Imagery Control
How accurately a person can intentionally manipulate a mental representation.

**Task:** Imagery Manipulation (Task B)
**Endpoint:** `imagery_manipulation_accuracy` (lower is better)

### Imagery Stability
How consistently the representation is maintained across a retention delay.

**Task:** Delayed Imagery (Task C)
**Endpoint:** `delayed_stability_degradation` (lower is better)

### Metacognitive Calibration
Correspondence between subjective confidence and objective reconstruction accuracy.

**Endpoint:** `metacognitive_calibration` (higher is better)

### Subjective Vividness (Secondary Only)
Self-reported imagery quality. **Never treated as an objective outcome.**

**Endpoint:** `subjective_vividness` (subjective_secondary role)

### Perceptual/Motor Control (Negative Control)
Perceptual matching with target visible, isolating motor/perceptual skill from imagery.

**Task:** Perceptual Control (Task D)
**Endpoint:** `perceptual_matching_error` (negative_control role)

## Construct Separation Rules

1. Vividness, confidence, and effort are always labeled subjective.
2. Perceptual control improvement alone does not indicate imagery improvement.
3. The primary endpoint is always objective reconstruction error.
4. Subjective-objective dissociation is a testable hypothesis, not an assumption.
