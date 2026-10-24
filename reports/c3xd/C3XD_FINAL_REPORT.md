# C3XD — Cue-Deconfounded Semantic/Event Imagery Qualification (raw BIDS) — Final Report

**NOT C3XR / C3XR-CAT / C4. No reconstruction, captioning, semantic decoding, or geometry.**

## Decision
**`C3XD_BLOCKED_RAW_PIPELINE_INFEASIBLE`** — the confirmatory raw cue-deconfounded reliability could
not be executed in this environment. The event-timing contract was certified and the design-
identifiability question was answered in full: **per-trial imagery IS separably estimable, and a
properly separated GLM/LSS removes cue/video leakage to a non-false-positive level provided the
video-specific cue response in VC is ≤ ~0.5× the imagery response — but that ratio can only be
measured from the raw BOLD, which is infeasible here (139 GB vs 37 GB; no reproducible preprocessing/
registration/ROI-provenance stack).** This is a documented fail-closed stop, **not** a FAIL and
**not** a workaround. **C3XE preparation is NOT authorized.** C3XC remains valid for its declared
(preprocessed-release) scope and is unchanged.

## Provenance / lineage
- Starting SHA (C3XC final): `fce7a04ebe0a0b5767eb600d30f5c78520680b8b`; branch
  `research/d2-cue-deconfounded-imagery-c3xd` from that SHA.
- C3XC lineage verified: decision `C3XC_D2_SEMANTIC_IMAGERY_QUALIFIED`, seal `e3c2ac56…`, CI run
  34343018957 (SUCCESS). C3XA/C3XB/C3XC artifacts preserved unchanged.
- Seal `reports/c3xd/c3xd_protocol_seal.json` (self_hash `1a680c1b`), committed BEFORE any
  neural/design outcome.

## Raw data (selective, no bulk download)
- OpenNeuro **ds005191 v1.0.2**, public S3 mirror. Inventory `results/c3xd/raw_acquisition_plan.json`.
- Selected scope: testImagery + testPerception (+ events/sidecars) for S1–S6; **trainPerception
  EXCLUDED** (verified). Raw BOLD: testImagery 98.3 GB + testPerception 41.2 GB = **139.4 GB** (peak
  ≈ 223 GB with preprocessing) vs **37.1 GB** free → **storage insufficient**.
- Only tiny events.tsv/sidecars were downloaded (timing audit); no BOLD; no raw neural data in git.

## Event-timing contract (certified; TR = 1 s; `C3XD_TEMPORAL_CONTRACT.md`)
Per imagery trial: **cue (-2, variable 4–17 s) → imagery (2, 12–23 s, 0 s gap) → [2 s] → target video
(3, 10–21 s) → evaluation (-5, 6 s)**. All 6 subjects: imagery **360 trials = 72 videos × 5 sessions**,
exactly 5 reps/video, session-balanced; perception 72 videos; 72/72 correspondence.
- cue → imagery separation: **0 s gap** (adjacent), but cue and imagery **durations are jittered**.
- imagery → video separation: **2 s gap** (≈14–25 s onset separation).

## Candidate GLM designs, conditioning, synthetic recovery
Design family (frozen): **A** = LSA separate per-trial cue/imagery/video + eval; **B** = LSS per-trial
imagery; **C** = naive HRF-shifted late-imagery window (negative baseline). Selection used **design +
synthetic recovery ONLY**, never real reliability (`c3xd_glm_design_selection.json`).
- **Conditioning:** imagery-submatrix condition number **1.16**, imagery VIF mean **1.67**, imagery-vs-
  own-cue correlation **0.06** → per-trial imagery is well-conditioned and separable. (The full-design
  condition number is inflated by drift/eval collinearity in the nuisance subspace and does not affect
  imagery estimability.)
- **Synthetic injected-signal recovery** (real S1 timing; 4 HRF/noise/AR perturbations;
  `c3xd_design_simulation.json`): imagery recovery r 0.61–0.81 (min ≥ 0.6 for all models).
- **False-positive imagery reliability under a cue+video-only null**, by video-specific cue:imagery
  magnitude (the decisive metric):

  | model | 0.25× | 0.5× | 1.0× |
  |---|---|---|---|
  | A (LSA) | 0% | 0% | 25% |
  | B (LSS) | 0% | 0% | 50% |
  | C (naive) | 25% | 75% | 75% |

  Interpretation: a video-specific cue response is consistent across repetitions, so residual leakage
  is picked up by the reliability estimator as spurious "imagery" reliability. Model A controls this
  fully when cue magnitude ≤ 0.5× imagery, but not at comparable magnitude; the naive window (C) leaks
  even at 0.25×. **Selection status: `NO_IDENTIFIABLE_MODEL_AT_EQUAL_MAGNITUDE`** — no model is
  certifiably cue-safe at the conservative equal-magnitude assumption; sufficiency is CONDITIONAL on
  the (unmeasured) VC cue-response magnitude.

## Raw preprocessing / ROI provenance
- Raw preprocessing/registration was **not executed** (storage + no reproducible fMRIPrep/FSL/SPM/
  FreeSurfer stack in-environment).
- **ROI provenance: `BLOCKED_C3XD_ROI_PROVENANCE`** (`c3xd_roi_provenance.json`): the C3XC VC (and
  V1/LVC/HVC) are localizer voxel indices in the KamitaniLab **preprocessed** release space; mapping
  them to raw-BIDS functional space needs their localizer GLMs + registration derivatives, which are
  not distributed as raw-space masks and are not reproducible here. No "close-enough" mapping (sealed).

## Per-subject raw reliability
Not produced — raw betas could not be generated (see blockers). `c3xd_raw_imagery_manifest.json` /
`c3xd_raw_perception_manifest.json` record status `NOT_PRODUCED_BLOCKED` with the certified event
contract; no trials silently dropped. The `>=2/6` raw reliability gate was therefore **not evaluated**.

## Cue diagnostics (synthetic; `c3xd_cue_diagnostics.json`)
Per-trial imagery is estimable (VIF 1.67, cond 1.16); the cue-magnitude false-positive curve above is
the substitute for the raw cue/imagery/post-video component diagnostics (which need BOLD). The
early-vs-late and previous-/next-trial controls are defined in the event manifest (prev/next video ids
recorded) and are deferred to the raw execution.

## Decision / authorization
`C3XD_BLOCKED_RAW_PIPELINE_INFEASIBLE`. Authorizes **nothing**; **C3XE preparation NOT authorized**;
never C3XR/C3XR-CAT/reconstruction/captioning/semantic-decoding/geometry/C4. What would unblock:
≥250 GB working storage + a reproducible preprocessing/registration stack + raw-space VC/localizer
masks (or KamitaniLab derivatives); then freeze Model A, extract cue-deconfounded imagery+perception
betas, measure the actual VC cue-response magnitude, and run the frozen session-disjoint reliability
gate with the cue+video-only false-positive control.

## Integrity / verification
- Seal committed before outcomes; frozen reliability estimator unchanged (hashes pinned); model
  selection used design/synthetic ONLY (never real reliability/geometry/decoding/ROI/behaviour); no
  semantic features; no geometry; no raw neural data in git; C3XA/C3XB/C3XC untouched.
- Tests: `test_c3xd_qualification.py` 9/9 (synthetic + artifact integrity). Ruff clean.
- CI job `c3xd-d2-cue-deconfounded-imagery` (C3XD + inherited C3XC/C3XB/C3XA/C3X/C3R/C3G + backend-core
  + Ruff); CI-tested SHA / run recorded at closeout.

## Next candidate (record only; not executed)
Resolve C3XD on adequate infrastructure (raw pipeline) as above; a C3XD PASS would then authorize a
separately-sealed C3XE semantic/event state-geometry gate (scope documented in
`results/c3xd/c3xd_scope_registry.json`; not computed). **STOP after C3XD.**
