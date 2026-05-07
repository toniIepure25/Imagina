# IMAGINA Implementation Status

## Current Capabilities

- FastAPI backend with REST and WebSocket session streaming.
- Next.js frontend with live session, replay, report, profile-ready layout, and science pages.
- SQLite event store for local-first session persistence.
- Deterministic simulated EEG-like feature generation.
- PID/IQI proxy metric engine, adaptive curriculum, feedback policy, and safety monitor.
- Deterministic replay and JSON/HTML reports.
- Signal provider, calibration, profile, experiment, export, and report modules are now linked into one V2 research workflow.
- Experiment runs can create or attach linked sessions, track progress, aggregate summaries, and export experiment JSON.
- Local profiles update idempotently from completed session summaries and expose a longitudinal progress report.

## Simulated

- EEG-like bandpower features.
- Signal quality.
- Imagery strength proxy.
- Behavioral stability proxy.
- Replay demo participants and scenarios.

## Real

- Local event logging.
- User self-report input.
- Session/replay/report workflows.
- Session setup metadata for profile, task, signal provider, simulated scenario, experiment run, and consent.
- Calibration quality profiles stored per session and surfaced in reports.
- Deterministic simulation and evaluation hooks.
- Safety thresholding over proxy metrics and notes.

## Future Work

- Real LSL/Muse/OpenBCI provider implementation.
- Empirical metric validation against questionnaires or controlled tasks.
- Real participant studies using the existing experiment protocol scaffolding.
- Optional learned models after validation.

## Known Limitations

- IMAGINA does not decode thoughts or dreams.
- PID/IQI are experimental proxy metrics.
- V1/V2 simulated signals are not clinical measurements.
- Reports are research summaries, not medical evaluation.
- LSL is still a stub; V2.1 should add optional real provider implementation without changing the current simulated workflow.
- Profile progress is local-only and depends on sessions completed in the same workspace/database.
