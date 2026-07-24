# C3 Final Decision — fMRI Perception-to-Imagery Transfer and Reconstruction Readiness

**Status:** INFRASTRUCTURE COMPLETE — AWAITING REAL DATA

Machine-readable: [`results/c3_final_decision.json`](../../results/c3_final_decision.json)

---

## Current State

The C3 scientific pipeline is fully implemented and smoke-tested on synthetic
data (61 tests passing). The gate decision cannot be issued until NSD perception
betas are downloaded and the full pipeline is executed on real data.

## What Is Complete

| Component | Status | Tests |
|-----------|--------|-------|
| Dataset registry (NSD + NSD-Imagery) | ✓ | 7 |
| Provenance manifests (6 types) | ✓ | 6 |
| Data ingestion (HDF5, NIfTI, TSV) | ✓ | 8 |
| Ridge perception decoder | ✓ | 13 |
| Zero-shot transfer evaluation | ✓ | 6 |
| State transport (5 methods + LOSO) | ✓ | 7 |
| Uncertainty calibration (4 sources) | ✓ | 4 |
| Negative controls (9 checks) | ✓ | 10 |
| CI workflow jobs (4 C3 jobs) | ✓ | — |

**Total: 61 tests, 0 failures**

## What Is Blocked

1. **NSD perception betas** (~16-28 GB per subject × 4 subjects = 80-120 GB)
   - Required for training the perception decoder (C3-H1)
   - Must be downloaded from naturalscenesdataset.org

2. **Remaining NSD-Imagery data** for subjects 02, 05, 07
   - Imagery betas, ROI masks, behavioral data

3. **CLIP embedding computation** for the 12 target stimulus images

## Prior Expectation

Based on published evidence:
- **Kneeland et al. (CVPR 2025):** CLIP 2WC on imagery = 46-53% (chance = 50%)
- **Spera et al. (2026):** Frozen DynaDiff zero-shot = 48.94% CLIP (chance)

**The most likely outcome is:**
```
C3_PERCEPTION_DECODING = PASS
C3_ZERO_SHOT_IMAGERY_TRANSFER = NULL_SUPPORTED_WITHIN_SENSITIVITY
C3_STATE_TRANSPORT = NULL_OR_INCONCLUSIVE (n=4 underpowered)
C3_RECONSTRUCTION_READINESS = BLOCKED
C3 = COMPLETE_WITH_IMAGERY_TRANSFER_NULL
```

## Honest Limitations

1. **n=4 participants** — only large effects detectable
2. **18 stimuli** (12 usable) — coarse retrieval metric
3. **Published zero-shot null** — C3-H2 is very likely confirmatory of known result
4. **No novel positive expected** — scientific value is in rigorous replication and calibration
5. **State transport (H4)** — the only hypothesis without a published negative, but
   underpowered for subtle effects

## Decision Rules (When Real Data Available)

| Outcome | Condition |
|---------|-----------|
| PASS | H1 pass AND H2 pass |
| PASS_CALIBRATION_REQUIRED | H1 pass AND H2 null AND H4 pass |
| BLOCKED | H1 pass AND H2 null AND H4 null |
| FAILED_BY_PERCEPTION_FOUNDATION | H1 fails |
| FAILED_BY_LEAKAGE | Any control fails |

## Next Steps

1. Download NSD perception betas for subj01 (minimum viable: ~16 GB)
2. Train perception decoder on NSD data → verify H1
3. If H1 passes: apply to imagery → evaluate H2
4. If H2 null (expected): evaluate H4 (state transport)
5. Run full negative control battery on real data
6. Issue final decision
