# IMAGINA Implementation Status

## Software Version

`0.5.0.dev1` (backend) / `0.5.0-research` (frontend) — research platform development.

## Current Capabilities

### Closed-Loop Pipeline (WebSocket-driven) — Integrated
- FastAPI backend with REST and WebSocket session streaming.
- Next.js 16 frontend with live session, replay, report, profile, and science pages.
- SQLite event store for local-first session persistence (event sourcing).
- Deterministic simulated EEG-like feature generation (6 scenarios).
- PID/IQI proxy metric engine (hand-tuned weighted composites, unvalidated).
- 8-level adaptive staircase curriculum (3-up/1-down).
- Feedback policy engine mapping state to 10 scene parameters + prompt text.
- Safety monitor (fatigue >0.80, overeffort, dissociation keywords, 20-min limit).
- React Three Fiber 3D Dream Corridor with param-driven feedback visuals.
- Signal provider abstraction (simulated, manual, replay, dataset.replay, lsl.stub, lsl.real).
- Calibration profiles, local user profiles, experiment protocol scaffolding.
- Deterministic replay and JSON/HTML reports.
- DSP fallback chain: scipy Welch -> numpy FFT -> stdlib heuristic.

### Product/Demo Stack (REST-driven, parallel) — Integrated
- ~100 REST endpoints in `api/imagina/routes.py`.
- 80+ frontend components including `/imagina/live` and `/imagina/showcase`.
- File-based JSON storage under `data/imagina/`.
- 99 CLI modules for research, benchmarking, OpenMIIR analysis.

### Research Platform Governance — Implemented (isolated from session runtime)
- Versioned database migrations (v001 legacy, v002 research governance).
- PRAGMA foreign_keys = ON enforced on every connection.
- Normalized research tables: studies, protocol_versions, ethics_reviews, consent_document_versions, participants (UNIQUE pseudonym per study), consents, sequence_allocations, condition_assignments, audit_events.
- Collection readiness gate (evaluate_collection_readiness): default-deny for human data.
- Separate public and operator API views (condition blinding in public API).
- Balanced Williams crossover sequence allocator (6 sequences, transactional).
- Consent gate with participant-study membership validation and withdrawal support.
- System capability endpoint returning machine-verifiable status.

### Research Module Scaffolding — Implemented but isolated
- Feedback condition definitions (adaptive, fixed, yoked).
- Trial scheduler (in-memory, not persisted).
- Stimulus registry with content hashing.
- Provenance tracking (git SHA, versions).
- Instrument registry (VVIQ-2 metadata, Likert scales).
- Imagery self-report task component (renamed from BehavioralTask).

### Research Frontend — Implemented but not wired to live sessions
- Research route structure: /research, /research/operator, /research/participant, /research/eeg-validation, /research/synthetic-demo.
- Operator dashboard with API-derived safeguard status (no static checkmarks).
- Consent gate component (ConsentGate).
- Imagery self-report task (ImagerySelfReportTask).
- Historical EEG/OpenMIIR validation dashboard preserved at /research/eeg-validation.

### Statistical Scaffolding — Specification only
- Power analysis utility (within-subjects approximation).
- Synthetic data generator (deterministic, seeded).
- LMM specification string (not an executable fitted analysis).
- IQI/PID validation analysis helpers (descriptive, not confirmatory).
- Cohen's d implementation (independent samples formula).

### Biosignal Acquisition Foundations — Utility only
- EEG ring buffer with signal quality estimation.
- Marker synchronizer for event/EEG alignment.
- Drop rate and flat channel detection.
- No real acquisition worker, no real LSL lifecycle, no spectral validation.

### Testing
- 43 backend test files, 266 core+research tests passing.
- 280 additional tests (legacy/artifact/hardware/external) in separate markers.
- 5 frontend test files, 11 Vitest tests passing.
- CI classified: backend-core (hermetic), backend-legacy-validation (manual), frontend, docker-config.

## Simulated (not experimental evidence)

- EEG-like bandpower features (deterministic mathematical functions).
- Signal quality proxies.
- Imagery strength proxies.
- Behavioral stability proxies.
- Replay demo participants and scenarios.

## Not Yet Implemented (required for scientific study)

- **Runtime integration**: Feedback conditions not wired into the live session loop.
- **Synthetic end-to-end workflow**: No complete study-to-export synthetic run.
- **Objective behavioral endpoint**: Imagery self-report is subjective, not behavioral.
- **Persistent trial engine**: TrialScheduler is in-memory only.
- **Real EEG acquisition**: No real acquisition worker, clock correction, or spectral validation.
- **Confirmatory statistics**: LMM is a specification, not a fitted analysis.
- **Human data collection**: Not authorized; no ethics approval on file.
- **Preregistration**: Incomplete draft; primary outcome not finalized.
- **Yoked trajectory source**: Provenance-aware yoked source not implemented.

## Known Limitations

- IMAGINA does not decode thoughts or dreams.
- PID and IQI are experimental proxy metrics with no empirical validation.
- All default signals are simulated — not biological data.
- Reports are engineering summaries, not medical or scientific evaluation.
- The sample size in the preregistration is provisional.
- Block randomization was not previously used in participant enrollment (now replaced by balanced Williams allocator in Merge Gate A).
- The V8-V44 product stack and the WebSocket pipeline are architecturally separate.
