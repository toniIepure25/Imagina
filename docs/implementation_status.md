# IMAGINA Implementation Status

## Software Version

`0.5.0.dev1` (backend) / `0.5.0-research` (frontend) — research platform pivot. See `docs/roadmap.md` for the research direction.

## Current Capabilities

### Closed-Loop Pipeline (WebSocket-driven)
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

### Product/Demo Stack (REST-driven, parallel)
- ~100 REST endpoints in `api/imagina/routes.py` for guided sessions, skill tree, protocol studio, benchmark SDK, policy lab, and capstone demo.
- 80+ frontend components including `/imagina/live` control room and `/imagina/showcase`.
- File-based JSON storage under `data/imagina/` (separate from SQLite event store).
- 99 CLI modules for research, benchmarking, OpenMIIR analysis.

### Testing
- 34 backend test files with ~400 tests (pytest).
- Integration tests using TestClient and temp SQLite databases.
- CLI verification scripts (standalone, not pytest-discoverable).
- Zero frontend automated tests.

## Simulated (not experimental evidence)

- EEG-like bandpower features (deterministic mathematical functions).
- Signal quality proxies.
- Imagery strength proxies.
- Behavioral stability proxies.
- Replay demo participants and scenarios.

## Not Implemented (required for scientific validation)

- Controlled experiment infrastructure (randomization, condition assignment, counterbalancing).
- Fixed-feedback and yoked/sham-feedback control conditions.
- Study-mode separation (demo vs. research data).
- Consent and ethics gating.
- Validated outcome measures (VVIQ-2, behavioral imagery tasks).
- Trial-level data capture with timing and provenance.
- Schema migrations and versioned research tables.
- Frontend automated tests.
- Preregistered analysis pipeline.
- Power analysis tooling.

## Known Limitations

- IMAGINA does not decode thoughts or dreams.
- PID and IQI are experimental proxy metrics with no empirical validation.
- All default signals are simulated — not biological data.
- Reports are engineering summaries, not medical or scientific evaluation.
- The LSL real provider is gated behind `IMAGINA_ENABLE_EXPERIMENTAL_LSL` and requires `pylsl`.
- Profile progress is local-only.
- `numpy` and `scipy` are optional runtime dependencies (not in core `pyproject.toml`).
- The V8-V44 product stack and the WebSocket pipeline are architecturally separate.
