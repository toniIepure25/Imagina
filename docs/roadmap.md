# Roadmap

## Current State (0.5.0-research)

- Local FastAPI/Next.js app with WebSocket closed-loop pipeline.
- Simulated EEG-like features (deterministic, not biological data).
- PID/IQI proxy metrics (hand-tuned, unvalidated).
- Dream Corridor 3D feedback scene.
- Replay, reports, safety monitor.
- Signal provider abstraction (simulated, manual, replay, LSL gated).
- Product/demo stack with guided sessions, skill tree, protocol studio, benchmarks.

## Research Platform Development

### Merge Gate A — Research Platform Integrity Foundation (current)

Status: **In progress**

- CI truth: strict markers, classified test suite, honest reporting.
- Versioned database migrations with FK enforcement.
- Normalized research governance tables.
- Collection readiness gate (default-deny for human data).
- Balanced Williams crossover sequence allocator.
- Public/operator API separation (condition blinding).
- Imagery self-report task (renamed from BehavioralTask).
- Restored EEG validation dashboard.
- Documentation reconciled with actual capabilities.

### Merge Gate B — Synthetic End-to-End Workflow (planned)

Status: **Not started**

- Wire feedback conditions into the live session loop.
- Persistent research session and trial state machine.
- Provenance-aware yoked feedback source.
- Complete synthetic study-to-export workflow.
- Playwright end-to-end smoke test.
- Synthetic export with complete provenance metadata.
- Deterministic replay from seed and manifest.

### Gate C0 — Scientific Measurement and Causal Validation (completed)

Status: **Complete (synthetic validation)**

- Objective imagery reconstruction error as primary endpoint (frozen, versioned).
- Four-family psychophysics task battery (reconstruction, manipulation, delayed, perceptual control).
- Psychometric calibration (3-down/1-up staircase, condition-independent).
- Hierarchical cognitive agent model for scientific simulation.
- Causal estimands and identification assumptions formalized.
- Confirmatory hierarchical analysis executable (statsmodels MixedLM).
- Simulation-based power/Type-I error validation across 9+ scenarios.
- Measurement reliability and construct-validity diagnostics.
- Objective tasks integrated into persistent runtime with leakage prevention.
- Falsification test suite (null, subjective-only, practice-only, carryover, leakage).
- Scientific workbench UI (measurement, simulation, analysis pages).
- Preregistration-ready synthetic protocol frozen.
- **All validation is synthetic-only. No human construct validity established.**

### Phase C.1 — Objective Behavioral Validation (future work)

Status: **Not started**

- Validate psychophysics task battery with human participants.
- Establish human psychometric properties (reliability, validity).
- Pilot test with N=3-5 before full study.

### Phase D — Real Biosignal Integration (future work)

Status: **Not started**

- Real LSL acquisition worker with clock correction.
- Spectral feature validation against known datasets.
- MNE preprocessing pipeline.
- Signal quality validation.

### Phase E — Confirmatory Statistics and Publication (future work)

Status: **Blocked** (requires objective outcome, human data, ethics approval)

- Executable LMM analysis pipeline.
- Power analysis with finalized primary outcome.
- Preregistration completion and submission.
- Methods section finalization.
- Usability pilot.
- Ethics submission.

## Scientific Non-Negotiables

- Simulated EEG is never experimental evidence.
- IQI/PID are exploratory proxies, not validated outcomes.
- No human data collection without ethics approval metadata.
- No claims of mind reading, dream decoding, or clinical neurofeedback.
- Primary outcome is not yet finalized.
- Sample size is provisional.
