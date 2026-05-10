# IMAGINA V3 — Real EEG-Enabled Mental Imagery Research Platform

**Status: V3.0-final-candidate — FIRST_REAL_EEG_EVALUATION_COMPLETE**

A local-first, closed-loop mental imagery training prototype with real OpenMIIR EEG integration.

> **Real EEG Achieved**: OpenMIIR dataset (10 FIF files, 69 channels, 512 Hz) imported and evaluated. Real-mode evaluation passes. This remains an engineering evaluation — scientific validation is not complete.

> **Disclaimer:** IMAGINA is a research prototype. It estimates proxy metrics related to attention, self-reported vividness, behavioral stability, and simulated EEG-like signal patterns. It does NOT decode thoughts or dreams, diagnose conditions, or provide medical advice. PID and IQI are experimental proxy metrics that require validation.

## Features

- Guided mental imagery sessions with adaptive feedback
- Procedural 3D Dream Corridor (React Three Fiber) that responds to 10 scene parameters
- Real-time WebSocket streaming of metrics, curriculum state, and feedback
- Composite proxy metrics: IQI (Imagery Quality Index) and PID (Perception-Imagination Distance)
- 8-level adaptive curriculum with staircase progression
- Safety monitor (fatigue, overeffort, session time limits, dissociation keywords)
- Signal provider abstraction for simulated, replay, manual, and future LSL streams
- Calibration profiles with quality scores and normalization metadata
- Local-only user profiles and lightweight experiment protocols
- JSONL/CSV research exports and offline evaluation harness
- Deterministic demo replay with seeded signal simulation
- JSON and HTML session reports
- SQLite event store for persistence and replay
- Scientific disclaimers visible throughout the UI

## Architecture

```
backend/   — FastAPI + Python
frontend/  — Next.js + TypeScript + Tailwind + React Three Fiber
docs/      — Documentation (architecture, metrics, ethics, claims, demo script)
data/      — Local SQLite database and exports
research/  — Config files and notebook placeholders
```

See [docs/architecture.md](docs/architecture.md) for the full system diagram.

## Quick Start

IMAGINA runs as two local services: a FastAPI backend on port 8000 and a Next.js frontend on port 3000.

### Backend

```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

The API docs are at http://localhost:8000/docs.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

### Docker

```bash
docker-compose up --build
```

Backend: http://localhost:8000 | Frontend: http://localhost:3000

## Running Tests

```bash
cd backend
timeout 40s python3 -m pytest app/tests/ -q
python3 -m ruff check .
```

If `aiosqlite` hangs inside a restricted sandbox, rerun the pytest command outside the sandbox. The app itself remains local-first.

```bash
cd frontend
npm run lint
npm run build
```

If a previous Next build was interrupted and `npm run build` reports another build is already running, remove the stale generated lock file:

```bash
rm -f frontend/.next/lock
```

## V2 Research Workflow Runbook

1. Open http://localhost:3000/profile and create a local-only profile, or continue anonymously.
2. Open http://localhost:3000/experiments, choose a protocol, and create an experiment run when you want a research-mode flow.
3. Click **Create Next Session** in the experiment page, then open the linked session. For a normal run, open http://localhost:3000/session directly.
4. In session setup, select profile mode, signal provider, simulated scenario, task, and acknowledge the scientific/safety disclaimer.
5. Complete calibration and review the calibration quality score and warnings.
6. Start the session, stream metrics over WebSocket, submit self-report sliders, and watch the corridor adapt.
7. Stop the session and open the session report.
8. Download JSON report, HTML report, event JSONL, timeline CSV, self-report CSV, summary CSV, and the data dictionary.
9. Return to `/profile` to view longitudinal progress and recommendations.
10. Return to `/experiments` for experiment progress, linked reports, aggregate summary, and experiment summary export.
11. Run the offline evaluation CLIs before changing metric formulas or provider behavior.

The corridor is not a decoded mental image. It is an adaptive scaffold driven by experimental proxy metrics.

## Demo Runbook

1. Open http://localhost:3000
2. Start with **Watch Replay** for the most reliable 3-minute cinematic demo
3. Narrate the visual mapping: clarity follows IQI proxy, fog follows uncertainty/fatigue, wall distortion follows instability, doors follow curriculum progression, and the pulse is a reset cue
4. Then use **Start Session** for a live guided session
5. Complete calibration (30s), submit self-report sliders, and watch the corridor adapt
6. End the session and view the report
7. Open `/reports/{session_id}` for the JSON-backed report page, or click the HTML report link

See [docs/demo_script.md](docs/demo_script.md) for a full 3-5 minute demo walkthrough.

## V1.5 Visual Mapping

The corridor is not a decoded mental image. It is an adaptive scaffold driven by experimental proxy metrics.

- Clearer corridor: stronger IQI proxy
- Lower fog: lower uncertainty/fatigue proxy
- Calmer wall motion: better estimated stability
- Steadier lights: stronger attention/relaxation proxy
- More coherent particles: lower uncertainty proxy
- Doors/details: curriculum progression
- Breathing pulse: reset cue when fatigue or attention requires simplification

## Running A Simulated Session

1. Start the backend and frontend with the commands above.
2. Create a session from the UI, complete baseline calibration, and start the guided corridor.
3. Submit self-report sliders during the run. These influence later proxy estimates together with the simulated EEG-like feature stream.
4. Use **End Session** to stop the loop and generate the summary/report.

## Running Replay Demo

The replay page calls `POST /api/replay/demo`, creates a deterministic seeded session, then streams stored events through the same WebSocket envelope used by live sessions.

```bash
curl -X POST http://localhost:8000/api/replay/demo
```

## Metrics

| Metric | Formula | Range | Meaning |
|--------|---------|-------|---------|
| IQI | 0.35*attention + 0.30*engagement + 0.20*behavioral + 0.15*relaxation | 0-1 (higher=better) | Estimated imagery quality |
| PID | 0.45*neural_dist + 0.35*behavioral_dist + 0.20*uncertainty | 0-1 (lower=better) | Perception-imagination distance |

See [docs/metrics.md](docs/metrics.md) for full details.

## Documentation

- [Architecture](docs/architecture.md)
- [Scientific Claims Policy](docs/scientific_claims.md)
- [Ethics and Safety](docs/ethics.md)
- [Metrics Reference](docs/metrics.md)
- [Demo Script](docs/demo_script.md)
- [Experiment Plan](docs/experiment_plan.md)
- [Experiment Mode](docs/experiments.md)
- [Data Dictionary](docs/data_dictionary.md)
- [Reproducibility](docs/reproducibility.md)
- [Offline Evaluation](docs/evaluation.md)
- [Roadmap](docs/roadmap.md)
- [Implementation Notes](docs/implementation_notes.md)

## What It Does NOT Do

- Does not read your mind or decode dreams
- Does not show what you are imagining
- Does not diagnose conditions or provide medical advice
- Does not cure aphantasia or guarantee lucid dreaming
- Does not measure consciousness objectively

## Limitations

- V2 uses simulated/manual/replay providers; LSL remains a documented stub, not real EEG hardware integration
- Self-report metrics are subjective
- Metric weights are hand-tuned, not empirically optimized
- No cross-user normalization
- Safety monitoring is basic keyword/threshold-based
- V2 workflow integration improves reproducibility and research operations, not scientific validity by itself

## Roadmap

### V2.1
- Real optional LSL EEG stream (Muse, OpenBCI)
- MNE preprocessing and artifact detection
- EEG bandpower extraction
- Public or controlled validation datasets

### V3
- EEG/fMRI representation learning
- CLIP alignment for imagery assessment
- Generative post-session visual summaries
- Longitudinal user model
- Formal psychophysical validation

## License

Research prototype. Not for clinical use.
