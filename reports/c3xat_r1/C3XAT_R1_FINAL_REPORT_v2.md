# C3XAT-R1 — Final Report v2 (Execution Attempt 2)

**Successor to the atlas-provenance report; preserves all prior history. Seals `bb0d07ac…` /
`23a6f92d…` unchanged; execution_attempt = 2; no C3XAT-R2.** Measurement-only — no geometry, decoding,
reconstruction, or semantic features. **No neural outcome was computed or inspected.**

## Decision
**`C3XAT_R1_BLOCKED_PERCEPTION_ESTIMAND`** (BLOCKED ≠ FAIL). A pre-outcome code audit + metadata-only
event audit found that the sealed matched-perception control R_P cannot be validly computed for this
dataset under the frozen run-disjoint contract. **Dataset gate not evaluated; C3XAG not authorized.**

## Supersession chain (all preserved, none rewritten)
1. `C3XAT_R1_BLOCKED_EXECUTION_INCOMPLETE` — interim checkpoint.
2. `C3XAT_R1_BLOCKED_ATLAS_SPACE_PROVENANCE` — **resolved** via authoritative ProbAtlas_v4 recovery.
3. `C3XAT_R1_BLOCKED_PERCEPTION_ESTIMAND` — **current terminal for attempt 2**.

## Pre-outcome perception audit (no BOLD, no R_P inspected)
An independent code audit found two perception-path driver defects (from source + the ds005191/C3XD
event contract + task semantics, **not** from any result):
1. The generic parser reads `trial_type==2` as `imageryID`/imagery — correct for testImagery, but in
   testPerception `trial_type==2` is a **video presentation** whose identity is `stimID`.
2. The driver sent perception through the imagery cue/imagery/post-video/eval Model A, whereas the sealed
   R_P intent is reliability of **raw perception betas**, same ROI, run-disjoint.

The running confirmatory jobs were **stopped before any outcome**; **0 result files existed** at stop
(the campaign was ~11 min in, before the reliability step wrote anything); nothing was read or
quarantined-with-contents (`confirmatory_driver_perception_bug_preoutcome.json`).

**Perception event contract** (`perception_event_contract_preoutcome.json`, from events only): each
subject has 10 perception runs, **360 target trials, 72 distinct videos**; global `trial_type` counts
`{-1:60, 2:2160, -2:2040, 3:240, -3:60}` (target = `trial_type==2 & stimID>0`).

## The blocker: run-disjoint 72-video estimand is ill-defined
`perception_run_split_coverage_preoutcome.json` enumerated all **C(10,5)/2 = 126** 5-vs-5 run partitions
per subject:

| subject | min common | median | max | all splits = 72? |
|---|---|---|---|---|
| S1–S6 | **64** | 72 | 72 | **No** |

Because the frozen estimator uses only videos **common to both halves**, some run-disjoint splits would
evaluate as few as 64 of the 72 videos — a **split-dependent estimand**. Per the sealed R_P authorization
rule, **any** split `< 72` common ⇒ `R_P_authorized = false` and **stop**. No workaround was applied
(no split selection, no video/run dropping, no session-disjoint or run-pair switch, nothing
outcome-guided).

Since the primary subject PASS **requires** Wang25 R_P PASS, no subject can be validly certified, so the
dataset gate cannot be evaluated with valid measurements.

## What succeeded and remains frozen/reusable
- ds005191 acquisition complete (1063 files, 139,957,018,247 bytes, `749ded7b…`).
- fMRIPrep 24.1.1 (`9aec0b83…`) succeeded for all 6 subjects; S1 technical qualification PASS.
- **Wang2015 volumetric provenance recovered** (ProbAtlas_v4, `3743ac34…`) and **primary ROI certified**
  (7604-voxel binary Wang25 union, mask `19b681ec…`, grid/affine match, 100% finite BOLD coverage).
- Imagery Model A bit-identical to C3XD (real `-5` grouped eval), frozen estimator, paired-Δ sensitivity,
  and the first implementation freeze — all intact.

## Per subject (S1–S6)
R_I / R_P / Δ_I / passes: **not computed** (blocked at the R_P estimand gate, pre-outcome). No values
fabricated. PASS count: not evaluable. Primary dataset decision: not evaluated.

## Resume path (execution_attempt stays 2; no C3XAT-R2)
A **separately justified, prospective** clarification of the matched-perception estimand would be needed
before any R_P — e.g., a sealed perception unit that guarantees a fixed 72-video estimand (run-pair or
session-aware), or an explicitly sealed common-video restriction — chosen with **no** reference to
outcomes. The imagery pipeline, atlas, and derivatives remain frozen and reusable.

## Integrity
No neural outcome computed or inspected; invalid campaign products quarantined (none existed); imagery
pipeline/atlas/estimator/thresholds/gates unchanged; both seals immutable; all prior gates immutable;
no kubeconfig/license/token committed. Tests hermetic; ruff clean.

## STOP
Genuine fail-closed perception-estimand blocker reached, pre-outcome. No C3XAG, no geometry, no decoding,
no reconstruction, no C4. execution_attempt = 2 remains open on the resume path above.
