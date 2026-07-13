# TASK_BRIEF.md — Merge Gate B.1: Runtime Completion and Evidence Hardening

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
