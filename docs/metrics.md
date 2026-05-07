# Metrics Reference

All metrics in IMAGINA V1 are **experimental proxy metrics**. They require validation before any scientific or clinical claims can be made.

## IQI — Imagery Quality Index

**Formula:**

```
IQI = (0.35 * attention_stability
     + 0.30 * imagery_engagement
     + 0.20 * behavioral_consistency
     + 0.15 * relaxation) * confidence
```

**Range:** 0–1 (higher is better)

**Components:**
- `attention_stability`: derived from theta/beta ratio, self-reported focus, distraction, signal quality
- `imagery_engagement`: derived from vividness, stability, alpha stability, simulated imagery strength
- `behavioral_consistency`: derived from behavioral stability, reaction time, self-report consistency
- `relaxation`: derived from alpha power ratio, self-reported relaxation, effort level
- `confidence`: inverse of uncertainty (higher when data is reliable)

## PID — Perception-Imagination Distance

**Formula:**

```
PID = 0.45 * neural_proxy_distance
    + 0.35 * behavioral_distance
    + 0.20 * uncertainty
```

**Range:** 0–1 (lower is better)

**Components:**
- `neural_proxy_distance`: `1 - f(simulated_imagery_strength, alpha_stability, imagery_engagement)` — in V1 this is simulated, not real neural data
- `behavioral_distance`: `1 - f(behavioral_consistency, fatigue)` — how far behavioral signals are from stable target
- `uncertainty`: increases with low signal quality, contradictory signals, sparse data

## Fatigue

Derived from self-reported fatigue, theta/beta ratio, effort, decreasing focus, and session duration.

## Uncertainty

Increases when signal quality is low, self-report and behavioral proxies conflict, fatigue is high, or insufficient data is available.

## Interpretation Mapping

| Condition | Interpretation |
|-----------|---------------|
| PID < 0.25 and IQI > 0.75 | excellent |
| PID < 0.40 and IQI > 0.60 | good |
| PID > 0.65 | unstable |
| fatigue > 0.75 | fatigue_risk |
| confidence < 0.30 | unknown |

## Limitations

- V1 simulates EEG features — no real neural data is used.
- Self-report is subjective and can be inconsistent.
- Component weights are hand-tuned, not empirically optimized.
- No cross-individual normalization has been performed.
- Metrics should not be used for diagnosis or clinical decisions.
