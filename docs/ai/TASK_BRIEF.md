# TASK_BRIEF.md

## Current task — ANIMUS 5.0 Scene Threshold observatory (2026-10-24)

**Goal:** add a contrastive 2-AFC scene-discrimination task and a provenance-aware longitudinal observatory,
without adding neural input, an image model, a diagnosis, a composite score, or a new dependency.

**Scope**
- Additive SQLite v021 contrast session and trial tables.
- Deterministic presence/position/colour pairs with hidden target, feature, and delta.
- 2-down/1-up staircase and fitted 75%-correct threshold; d′, signed side bias, Brier, coverage.
- Evidence provenance, leave-one-out sensitivity, and feature-level test–retest reliability.
- Contrast start/submit/summary/list/reflection and observatory API.
- Observatory UI, profile card, and Studio entry point.
- Deterministic simulation and honest validation/claims documentation.

**Non-goals**
- Neural decoding, neural reconstruction, dream content, image generation.
- Clinical diagnosis, treatment, cure, imagery-strength, or far-transfer claims.
- Cross-scene norms, leaderboards, composite scores, or person comparison.
- A criterion estimate from 2-AFC, which is not identified.

**Constraints**
- No new runtime dependency; local-only; no external calls.
- No execution or local install during this session; static verification only.
- Preserve existing Studio/P1 behavior and claim ceiling.

**Acceptance**
- Start returns a pair without target side, feature, delta, or answer.
- Submit is idempotent, rejects a stale scene, and returns the next pair or result.
- Abstention is excluded from d′/thresholds and included in coverage.
- Thresholds are withheld when sparse and marked when censored.
- Observatory reports `insufficient` reliability below three aligned features.
- Capability envelope keeps neural/clinical/image-generation boundaries.
- Tests and docs are present; runtime verification remains explicitly pending.

---

## Historical brief — ANIMUS 4.0 epistemic reconstruction interview (2026-10-23)

**Goal:** add a separate behavioural interview that asks binary questions about a hidden symbolic scene,
updates a transparent posterior, and reports uncertainty/calibration/coverage without adding neural input,
an image model, a diagnosis, or a composite score.

**Scope**
- Additive SQLite v020 interview header and probe metadata.
- `eri-v1` object-presence and spatial-relation probes with hidden answers.
- Mean-field Beta belief, coverage floor, then expected-information-gain selection.
- Binary choice, confidence in `[0.5, 1.0]`, and abstention.
- Posterior reconstruction with object/relation entropy and separate scores.
- Interview start/submit/summary/list API and local profile summary.
- Interview UI, profile card, and Studio entry point.
- Deterministic policy simulation and honest validation/claims documentation.

**Non-goals**
- Neural decoding, neural reconstruction, dream content, image generation.
- Clinical diagnosis, treatment, cure, imagery-strength, or far-transfer claims.
- A single "imagination score", norms, leaderboards, or cross-person comparison.
- Participant recruitment or data collection.

**Constraints**
- No new runtime dependency; local-only; no external calls.
- No execution or local install during this session; static verification only.
- Preserve existing Studio/P1 behavior and claim ceiling.

**Acceptance**
- Start returns a probe without the hidden answer or target flag.
- Submit is idempotent, rejects a stale scene, and returns the next probe or reconstruction.
- Abstention is excluded from Brier and included in coverage.
- Profile exposes five dimensions, error signature, and epistemic summary; no composite.
- Capability envelope keeps neural/clinical/image-generation boundaries.
- Tests and docs are present; runtime verification remains explicitly pending.

---

## Historical brief — Merge Gate B.1: Runtime Completion and Evidence Hardening

---

## Goal

Close all persistence, replay, export, outbox, manifest, API, Playwright, and CI gaps
identified during Merge Gate B audit, producing a fully hardened synthetic-only experiment
runtime on `research/scientific-platform`.

## Why This Matters

Merge Gate B established the core runtime architecture but left critical gaps: run state was
ephemeral (in-memory dict), outbox table was unpopulated, manifests were never created,
export lacked atomicity and validation, and Playwright tests only checked page loads.
Gate B.1 closes these gaps to produce a runtime that can serve as the foundation for
human-participant studies (after further validation work).

## Scope

- B1-1: Persistent run lifecycle with idempotent commands (v004 migration, RunService)
- B1-2: Injectable pipeline adapters (SignalProvider, FeatureProcessor, etc.)
- B1-3: Transactional outbox pattern (PersistentOutboxWriter, OutboxDispatcher)
- B1-4: Session manifest creation and completion sealing
- B1-5: Canonical normalization (recursive normalize()) and replay-from-manifest
- B1-6: Atomic export service with validator (checksums, data classification)
- B1-7: Orchestrator correctness (no INSERT OR REPLACE, typed errors, manifest integration)
- B1-8: API semantics (sessions, failures, export validation endpoints)
- B1-9: Full Playwright E2E workflow (create → poll → verify)
- B1-10: CI jobs (backend-runtime, playwright, docker-smoke)
- B1-11: Documentation and final verification

## Non-Goals

- Human participant readiness
- Real EEG/LSL integration
- Statistical fitting or analysis
- Authentication or user tracking
- Publication-ready scientific claims

## Starting HEAD

`67802f3` on `research/scientific-platform`

## Results

- **384 backend tests** passing (core + research markers)
- **0 ruff errors**
- **Frontend build clean** (18 routes)
- **7 new backend modules**: run_service, pipeline_adapters, outbox, manifest,
  export_service, v004 migration, pipeline_adapters
- **7 new test files**: test_run_service, test_outbox, test_manifest,
  test_export_service (plus updates to existing test files)
- **11 commits** on `research/scientific-platform`
- B9: Playwright E2E, Docker smoke, regression coverage
- B10: Documentation reconciliation

## Non-Goals

- Human data collection
- Real EEG acquisition (LSL, MNE, BrainFlow)
- Objective behavioral tasks (binocular rivalry, psychophysics)
- Statistical model fitting (LMM execution)
- Publication claims
- Authentication infrastructure
- Cloud services or telemetry
- Generative AI
- Clinical claims
- Mind-reading or dream-decoding language

## Constraints

- [x] No prohibited scientific claims
- [x] No raw EEG/neural data sent to external APIs
- [x] No hardcoded secrets
- [x] No bypassing safety monitors
- [x] Follow existing code conventions
- [x] Small, focused diffs
- [x] Do not modify V8–V44 product/demo behavior
- [x] All synthetic records clearly classified

## Starting HEAD

`6bcd39b050f1cbd06f5f4a4115abda9372efbb28`

## Actual Starting HEAD (this session)

`ce40448` (continuation from prior Merge Gate B session)

## Commit Sequence

1. fix(research): close Merge Gate A integrity gaps
2. feat(storage): add persistent synthetic runtime schema
3. feat(runtime): add persistent session and trial state machines
4. feat(runtime): implement transport-independent research runtime
5. feat(runtime): unify adaptive fixed and yoked policy contracts
6. feat(runtime): add frozen yoked trajectory libraries
7. feat(runtime): add synthetic study orchestration and export
8. feat(runtime): add deterministic replay validation
9. feat(research-ui): add synthetic runtime operator workflow
10. test(runtime): add synthetic E2E and release smoke coverage
11. docs: document persistent synthetic runtime boundaries

---

*Created: 2026-07-10*
