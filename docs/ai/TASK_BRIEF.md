# TASK_BRIEF.md — Merge Gate B: Persistent Synthetic Experiment Runtime

---

## Goal

Build a transport-independent, persistent, deterministic runtime on `research/scientific-platform`
capable of executing a complete synthetic-only three-condition crossover experiment (adaptive,
fixed, frozen yoked). The runtime must produce provenance-complete synthetic records, support
deterministic replay, preserve safety behavior, and expose one working synthetic end-to-end
flow through backend APIs, CLI, and frontend.

## Why This Matters

Merge Gate A established structural integrity (migrations, governance, balanced allocation,
API blinding, honest documentation). Merge Gate B proves the engineering runtime works
end-to-end with synthetic data, which is the prerequisite for later human-participant
studies, objective behavioral validation, and real EEG integration.

## Scope

- B0: Residual Merge Gate A integrity corrections
- B1: Migration v003 — persistent runtime tables (sessions, trials, feedback, safety, yoked libraries, manifests, exports)
- B2: Persistent session and trial state machines with CAS concurrency
- B3: Transport-independent ResearchSessionRuntime with injectable clock, IDs, event sinks
- B4: Unified feedback policy contract (adaptive, fixed, frozen yoked adapters)
- B5: Frozen yoked trajectory library (generation, freezing, validation, assignment)
- B6: Synthetic study orchestration, run records, and versioned export
- B7: Canonical deterministic replay validation
- B8: Synthetic API endpoints and frontend operator workflow
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
