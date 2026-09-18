# ANIMUS — Claims Boundary

ANIMUS-P1 makes **no** neural-content-decoding claim. This document is the contract; the code enforces it.

## Claim levels (machine-readable, `claims.py`)
| Level | Meaning | Allowed in P1 |
|---|---|---|
| `L0_SIMULATED` | Simulated loop; no biosignals, no decoded thoughts | ✅ |
| `L1_BEHAVIORAL_ASSISTED` | Behavioral-assisted amplifier; no decoded neural content | ✅ |
| `L2_BIOSIGNAL_ASSISTED_EXPERIMENTAL` | Experimental biosignal-assisted; research only | ❌ (future gate) |
| `L3_NEURAL_CONTENT_INFORMED_VALIDATED` | Validated neural-content-informed | ❌ (future gate) |

The operating ceiling is **L1**. `ClaimAuthorization.enforce` fails closed above it; there is **no manual
bypass**. UI labels and exports derive strings from the claim level only.

## What ANIMUS-P1 may say
- "Behavioral-assisted imagination amplifier (no decoded neural content)."
- "Your representation became more stable and clarified across this session." (based on allowed metrics)
- "Simulated neural observation" — clearly labeled as synthetic.

## What ANIMUS-P1 must never say
- "We read your thought" / "mind reading" / "neural reconstruction of your image" / "we know what you
  imagined." These phrases are enumerated and auditable (`audit_text_for_forbidden_claims`).

## Benchmark-only vs real-user metrics
Ground-truth similarity, attribute/object accuracy, scene-graph edit distance and `loop_gain` require a
hidden target and are **evaluator-only** (MODE B / benchmark). They must never surface in real-user mode
(MODE A amplifier), where the imagined target is unknown. Real-user metrics are uncertainty reduction,
self-reported clarity/confidence progression, candidate change magnitude, controller action entropy, and
stability across re-imagination.

## Scientific status (mirrors `evidence_registry.py`)
- Imagery reliability: **LIMITED** cohort evidence (C3XAT-R1).
- Independent replication: **not yet executed** (C3XRA acquisition-ready; C3XRP human replication not run).
- Content decoder: **not validated**. Geometry (C3XAG): **not authorized**. Neural reconstruction:
  **not validated**.

No frozen C3XAT/C3XRP/C3XRA result is modified or reinterpreted by ANIMUS. C3XAT reliability values are
measurement evidence only and are never converted into content information.
