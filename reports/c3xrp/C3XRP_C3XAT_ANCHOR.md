# C3XRP — Immutable C3XAT-R1 Historical Anchor

**C3XRP (Independent Replication & Precision Gate) is NOT C3XAT-R2 / C3XAG / C3XE / C3XR / C4.** C3XAT-R1
is CLOSED and immutable; C3XRP must not alter or reinterpret any C3XAT artifact, and must not attempt to
promote sub-02 or target sub-02/sub-03.

## Anchored decision (may_be_changed = false)
- Base SHA: `f25282b670797daf05e1ed9fcc9245840cb05d1b`
- C3XAT-R1 final decision: **`C3XAT_D2_ATLAS_IMAGERY_LIMITED`**, PASS **1/6** (sub-03 only), threshold ≥2/6.
- **C3XAG remains NOT AUTHORIZED.**

## Historical evidence (reference only — not re-analyzable here)
| subject | R_I | R_P | Δ | primary |
|---|---|---|---|---|
| sub-03 | PASS | PASS | PASS | **PASS** |
| sub-02 | PASS | PASS | **FAIL** | FAIL |

sub-02 is a formal PRIMARY FAIL (reliable imagery+perception, failed the conservative Δ contamination
criterion). C3XRP must not convert it to a PASS.

## Immutable references (`results/c3xrp/c3xat_anchor.json` carries exact hashes)
`C3XAT_R1_FINAL_DECISION_COMPLETE.json`, `C3XAT_R1_PRIMARY_DATASET_DECISION.json`,
`implementation_freeze_manifest_v2.json`, `C3XAT_R1_SECONDARY_RESULTS.json`, Wang25 primary mask
(`19b681ec…`), Wang2015 ProbAtlas_v4 archive (`3743ac34…`); C3XAT seal `bb0d07ac…`, C3XAT-R1 exec seal
`23a6f92d…`.

## Independence rule for C3XRP
A PRIMARY replication dataset must contain neural imagery measurements NOT used in C3XC / C3XD / C3XDR /
C3XDR-R1 / C3XAT / C3XAT-R1. **ds005191 (Mind Captioning, Horikawa) cannot be the replication outcome**
(may be used only for method validation / replay / synthetic calibration / power planning). Any candidate
sharing participants or imagery measurements with prior gates is `NOT_INDEPENDENT_REPLICATION`.

## What this gate may authorize
Nothing is executed here. Only a *future actual* `C3XRP_REPLICATION_QUALIFIED` outcome could later be
considered as evidence for authorizing preparation of a geometry gate — **not now**.
