# Architecture

## System Overview

IMAGINA is a monorepo with a Python/FastAPI backend and a Next.js/TypeScript frontend.

### Backend (FastAPI, port 8000)

| Module | Purpose |
|--------|---------|
| `api/` | REST endpoints for sessions, tasks, state, feedback, replay, reports, health |
| `websocket/` | WebSocket manager + session stream loop |
| `services/signal_simulator.py` | Deterministic simulated EEG-like signal generator (6 scenarios) |
| `services/feature_engine.py` | Feature normalization (V1 pass-through; V2 plug-in for real preprocessing) |
| `services/state_estimator.py` | Rule-based mapping from features + self-report to StateEstimate |
| `signals/` | Signal provider abstraction for simulated, replay, manual, and future LSL streams |
| `evaluation/` | Offline scenario and cohort simulation tools |
| `services/pid_iqi_engine.py` | Computes PID and IQI composite proxy metrics |
| `services/curriculum_manager.py` | 8-level adaptive staircase curriculum |
| `services/feedback_policy_engine.py` | Maps state to 10 scene feedback parameters + prompt text |
| `services/safety_monitor.py` | Fatigue, overeffort, dissociation, session-length checks |
| `services/report_service.py` | Aggregates events into SessionSummary |
| `storage/` | SQLite via aiosqlite — sessions table + events table (event sourcing) |
| `schemas/` | Pydantic v2 models for all domain types |

### Frontend (Next.js, port 3000)

| Module | Purpose |
|--------|---------|
| `app/page.tsx` | Landing page with disclaimers |
| `app/session/page.tsx` | Full session flow: setup → calibration → guided imagery → summary |
| `app/replay/page.tsx` | Deterministic demo replay |
| `app/reports/[sessionId]/page.tsx` | Session report viewer |
| `app/science/page.tsx` | Scientific notes and limitations |
| `components/scene/` | React Three Fiber 3D Dream Corridor with feedback-driven visuals |
| `components/metrics/` | MetricsDashboard, TimelineChart (Recharts), CurriculumTimeline |
| `components/session/` | SessionSetup, BaselineCalibration, SelfReportPanel, SessionControls |
| `lib/websocket.ts` | Typed WebSocket client with reconnect |

### Data Flow (per 2s window)

1. **SignalSimulator** generates an EEGSampleWindow + FeatureVector (seeded, deterministic)
2. **FeatureEngine** normalizes features (V1: pass-through)
3. **StateEstimator** produces a StateEstimate from features + latest self-report + baseline
4. **PIDIQIEngine** computes PID and IQI from state + features
5. **CurriculumManager** evaluates level progression/regression
6. **FeedbackPolicyEngine** produces a FeedbackAction (10 scene params + prompt)
7. **SafetyMonitor** checks for fatigue, overeffort, etc.
8. All events are persisted to SQLite event store and streamed via WebSocket

## V2 Extension Points

- Signal providers isolate data source concerns from the metric loop.
- Calibration profiles provide per-session normalization metadata.
- Local profiles summarize user progress without authentication or cloud sync.
- Experiment protocols support adaptive/fixed/control research modes.
- Export endpoints provide JSONL/CSV data for reproducible analysis.
9. Frontend applies FeedbackAction to the 3D scene and updates metrics charts

### Event Sourcing

All computations are stored as EventEnvelope records in SQLite. This enables:
- Deterministic replay of demo sessions
- Post-session report generation
- Future offline analysis
