# PROJECT_CONTEXT.md — IMAGINA for AI Agents

## What IMAGINA Is

IMAGINA is a **closed-loop mental imagery amplification system** — a research prototype that estimates and trains the quality, stability, attention, and sensory engagement of visual mental imagery. It is NOT a "mind reading" system.

The system asks: **"How well is the user imagining?"** — not "What exactly is the user thinking?"

It estimates proxies: Attention Stability, Relaxation, Imagery Engagement, Fatigue, Imagery Quality Index (IQI), and Perception-Imagination Distance (PID). It uses adaptive visual/audio/generative feedback as a scaffold for mental imagery practice.

Scientific framing: Mental imagery overlaps with perception but is noisier, less stable, and driven by top-down reactivation. IMAGINA remains defensible by using language such as "estimated proxy", "research prototype", "simulated/replay signal", "self-report", "calibration", "training support".

## Current Repository Architecture

```
Imagina/
├── backend/                   # Python 3.10+ / FastAPI
│   ├── app/
│   │   ├── api/               # REST endpoints (11 routers)
│   │   ├── core/              # Config, constants, time, errors
│   │   ├── evaluation/        # Cohort simulator, replay validator, metric sanity
│   │   ├── reports/           # JSON and HTML report generators
│   │   ├── schemas/           # Pydantic v2 models
│   │   ├── services/          # Business logic (pid_iqi, curriculum, safety, etc.)
│   │   ├── signals/           # Signal provider abstraction
│   │   ├── storage/           # SQLite/aiosqlite event store
│   │   ├── tests/             # pytest test suite (11 test files)
│   │   └── websocket/         # WebSocket manager + session stream
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/                  # Next.js 16 + TypeScript + Tailwind 4
│   ├── app/                   # Pages (session, replay, reports, profile, experiments, science, landing)
│   ├── components/
│   │   ├── scene/             # React Three Fiber 3D corridor (CorridorGeometry, DreamDoor, ParticleField, etc.)
│   │   ├── session/           # SessionSetup, BaselineCalibration, SelfReportPanel, SessionControls
│   │   ├── metrics/           # MetricsDashboard, TimelineChart, CurriculumTimeline, SafetyBanner
│   │   ├── layout/            # AppShell, Header, Footer
│   │   └── common/            # Button, Card, Badge, DisclaimerBox, Slider
│   ├── lib/                   # API client, WebSocket client, formatters, feedback mapping, types
│   ├── Dockerfile
│   ├── package.json
│   └── tsconfig.json
├── docs/                      # Architecture, metrics, ethics, claims, demo, experiments, evaluation
│   └── ai/                    # AI agent context files
├── data/                      # Local SQLite DB, session data, exports
├── research/                  # Config files (curriculum_v1.yaml, demo_session.yaml), notebooks
├── scripts/                   # Verification and utility scripts
├── .github/workflows/ci.yml   # GitHub Actions CI
├── docker-compose.yml
├── .env.example
└── README.md
```

## Intended Target Architecture

Planned evolution (aligned with `docs/roadmap.md`):

| Version | Stage | Key Changes |
|---------|-------|-------------|
| V1 | Behavioral/simulated MVP (current) | Simulated EEG-like signals, rule-based state estimator, behavioral self-report |
| V2 | Learned EEG feature prototype | Real EEG bandpower (Muse/OpenBCI via LSL), MNE preprocessing, artifact detection, learned feature transforms |
| V3 | Semantic neuro-AI system | EEG/fMRI representation learning, CLIP alignment for imagery assessment, generative post-session summaries, longitudinal user model, formal psychophysical validation |

## Main Modules and Responsibilities

| Module | Location | Responsibility |
|--------|----------|---------------|
| Signal Provider | `backend/app/signals/` | Abstract data sources (simulated, replay, manual, LSL stub) |
| Feature Engine | `backend/app/services/feature_engine.py` | Normalize/transform features (V1 pass-through) |
| State Estimator | `backend/app/services/state_estimator.py` | Rule-based mapping from features + self-report to StateEstimate |
| PID/IQI Engine | `backend/app/services/pid_iqi_engine.py` | Compute PID and IQI composite proxy metrics |
| Curriculum Manager | `backend/app/services/curriculum_manager.py` | 8-level adaptive staircase (3-up/1-down) |
| Feedback Policy Engine | `backend/app/services/feedback_policy_engine.py` | Map state to 10 scene feedback parameters + guided prompts |
| Safety Monitor | `backend/app/services/safety_monitor.py` | Fatigue, overeffort, dissociation keywords, session time limit |
| Session Service | `backend/app/services/session_service.py` | Session lifecycle management |
| Report Service | `backend/app/services/report_service.py` | Aggregate events into session summary |
| Calibration Service | `backend/app/services/calibration_service.py` | Baseline calibration with quality scores |
| Task Service | `backend/app/services/task_service.py` | Task definitions and management |
| Export Service | `backend/app/services/export_service.py` | JSONL/CSV research exports |
| Replay Service | `backend/app/services/replay_service.py` | Deterministic seeded demo replay |
| Multimodal platform | `backend/app/multimodal/` | 7-modality acquisition, sync, physiology/neural pipelines, fusion, evidence-labelled estimator, shadow-first controller, Dream Corridor bridge (see `docs/multimodal_platform.md`, ADR-040) |
| Multimodal API / UI | `backend/app/api/multimodal.py`, `frontend/app/multimodal/` | `/api/multimodal/*` and the Research Command Center |
| Personalization | `backend/app/services/personalization_service.py` | Local user profiles and progress tracking |
| Experiment Service | `backend/app/services/experiment_service.py` | Experiment protocol management |
| Storage | `backend/app/storage/` | SQLite event store (sessions + events tables) |
| WebSocket | `backend/app/websocket/` | Real-time session stream |
| Dream Corridor | `frontend/components/scene/` | 3D scene responding to 10 feedback parameters |
| Metrics UI | `frontend/components/metrics/` | Live dashboard, timeline charts, curriculum timeline |
| Session UI | `frontend/components/session/` | Setup, calibration, self-report, controls |

## Data Flow (per 2-second window)

```
Signal Source (simulated/replay/manual/LSL)
  → Signal Simulator → EEGSampleWindow + FeatureVector
  → Feature Engine → normalized features
  → State Estimator → StateEstimate (features + self-report + baseline)
  → PID/IQI Engine → PIDEstimate, IQIEstimate
  → Curriculum Manager → level progression/regression decision
  → Feedback Policy Engine → FeedbackAction (10 scene params + prompt text)
  → Safety Monitor → SafetyEvent checks (fatigue, effort, dissociation, time)
  → WebSocket → stream to frontend
  → Frontend Scene → Three.js corridor adapts in real-time
  → Event Store (SQLite) → all events persisted
  → Session Report → aggregate summary on session end
```

## V1/V2/V3 Roadmap

### V1 (Current — Behavioral/Simulated MVP)
- Simulated EEG-like features (6 scenarios)
- Rule-based state estimator
- Self-report sliders for imagery quality proxy
- Three.js Dream Corridor with 10 scene params
- 8-level staircase curriculum
- Basic safety monitor
- Session reports (JSON/HTML)
- Offline evaluation harness
- Experiment protocol framework
- Local user profiles

### V2 (Planned — Learned EEG Feature Prototype)
- Optional real LSL EEG stream (Muse, OpenBCI)
- MNE preprocessing and artifact detection
- Bandpower extraction (alpha, theta, beta, gamma)
- Learned feature transforms
- Updated PID/IQI weights from data
- Public or controlled validation datasets

### V3 (Planned — Semantic Neuro-AI)
- EEG/fMRI representation learning
- CLIP alignment for imagery assessment
- Generative post-session visual summaries
- Longitudinal user model
- Formal psychophysical validation

## Dream Corridor MVP

The Dream Corridor is a 3D procedural scene (React Three Fiber) whose visual properties respond to 10 scene parameters driven by the feedback policy engine:

- **Clarity/fog**: follows IQI proxy (clearer = better quality)
- **Wall stability/distortion**: follows attention stability (steadier = more stable)
- **Lighting steadiness**: follows attention/relaxation (steadier = better attention)
- **Particle coherence**: follows uncertainty (more coherent = lower uncertainty)
- **Doors/details**: follow curriculum progression (more doors = higher level)
- **Breathing pulse**: reset cue when fatigue or attention requires simplification

The corridor is explicitly **NOT** a decoded mental image — it is an adaptive scaffold driven by experimental proxy metrics.

## Core Metrics

| Metric | Formula | Range |
|--------|---------|-------|
| IQI | 0.35*attention + 0.30*engagement + 0.20*behavioral + 0.15*relaxation, × confidence | 0–1 (higher=better) |
| PID | 0.45*neural_dist + 0.35*behavioral_dist + 0.20*uncertainty | 0–1 (lower=better) |
| Attention Stability | Inverse theta/beta proxy from features + self-report | 0–1 |
| Relaxation | Relative alpha-band proxy from features + self-report | 0–1 |
| Imagery Engagement | Task-related parietal/gamma proxy + vividness/self-report | 0–1 |
| Fatigue | Trend-based theta/lower-alpha + self-report + session duration | 0–1 |

Interpretation thresholds:
- PID < 0.25 and IQI > 0.75 → "excellent"
- PID < 0.40 and IQI > 0.60 → "good"
- PID > 0.65 → "unstable"
- Fatigue > 0.75 → "fatigue_risk"
- Confidence < 0.30 → "unknown"

## Scientific Limitations

1. V1 uses simulated EEG features — no real neural data.
2. Self-report components are inherently subjective.
3. Metric weights are hand-tuned, not empirically optimized.
4. No cross-user normalization.
5. Metrics have not been validated in controlled experiments.
6. Simulated data is not equivalent to real EEG.
7. Safety monitoring is basic keyword/threshold-based.
8. The corridor is a scaffold, not a reconstruction.

## Privacy and Safety Constraints

1. **Local-first**: All data stays in SQLite on the user's machine.
2. **No external AI APIs**: Raw neural/session data must never be sent to external services.
3. **No cloud accounts**: No authentication, no tracking, no telemetry.
4. **Safety overrides**: Fatigue >0.80 triggers warnings; session >20min triggers stop; dissociation keywords trigger stop.
5. **Cooldowns and grounding**: The system includes breathing cues and simplification feedback for high-fatigue states.
6. **No dissociation-inducing UX**: No strobe effects, isolation depths, or altered state suggestions.

## Important Files and Folders

| Path | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app entry point |
| `backend/app/services/pid_iqi_engine.py` | PID/IQI computation |
| `backend/app/services/safety_monitor.py` | Safety checks |
| `backend/app/services/curriculum_manager.py` | Adaptive staircase |
| `backend/app/services/feedback_policy_engine.py` | State → scene params |
| `backend/app/services/signal_simulator.py` | Simulated EEG generator |
| `backend/app/signals/base.py` | Signal provider interface |
| `backend/app/storage/database.py` | SQLite init |
| `backend/app/storage/event_store.py` | Event sourcing store |
| `backend/app/tests/` | Test suite (11 files) |
| `frontend/app/session/page.tsx` | Session flow page |
| `frontend/components/scene/DreamCorridorScene.tsx` | 3D corridor |
| `frontend/components/metrics/MetricsDashboard.tsx` | Live metrics dashboard |
| `docs/architecture.md` | System architecture |
| `docs/metrics.md` | Metric formulas |
| `docs/scientific_claims.md` | Claims policy |
| `docs/ethics.md` | Ethics and safety |
| `docs/roadmap.md` | Version roadmap |
| `research/configs/curriculum_v1.yaml` | Curriculum level config |
| `.github/workflows/ci.yml` | CI pipeline |
| `docker-compose.yml` | Docker services |

---

*Last updated: 2026-05-07 — AI development context system initialization.*

---

## ANIMUS Studio product layer (2026-10-23)

| Path | Responsibility |
|------|----------------|
| `backend/app/core/animus/scene/` | ANIMUS-SG-v1 scene graph, library, compose, intent parser, typed commands, diff, revisions, regeneration |
| `backend/app/core/animus/studio/` | Atomic SQLite repository, serialized async Studio service, typed records/errors/locks, event bus, claim/capability guard |
| `backend/app/core/animus/studio/types.py` | Runtime-free typed records for sessions, branches, versions, candidates, worlds, summaries, and events |
| `backend/app/api/animus_studio.py` | `/animus/studio/*` snapshot API with response models, OpenAPI errors, optimistic concurrency, and stable error codes |
| `backend/app/api/animus_studio_ws.py` | Live channel with Origin validation, subscribe-before-snapshot, typed errors, and intent |
| `backend/app/storage/migrations/v014_animus_studio.py` | Additive Studio tables (sessions, versions, branches, events, candidates, commands, worlds) |
| `backend/app/storage/migrations/v015_animus_studio_branch_scope.py` | Session-scoped branch key + lost-branch repair |
| `backend/app/storage/migrations/v016_animus_studio_integrity.py` | Index-only candidate/list integrity support |
| `backend/app/storage/migrations/v017_animus_studio_branch_redo.py` | Additive branch redo-stack column |
| `backend/app/storage/migrations/v018_animus_studio_measurement.py` | Additive profile, estimates, protocols, runs, and trials tables |
| `backend/app/storage/migrations/v019_animus_studio_reconstruction.py` | Additive reconstruction metadata and error-profile columns |
| `backend/app/storage/migrations/v020_animus_epistemic_interview.py` | Additive interview header and probe metadata |
| `backend/app/storage/migrations/v021_animus_contrast_observatory.py` | Additive contrast session and trial tables |
| `backend/app/core/animus/studio/profile.py` | Beta-Binomial ability estimates, Brier calibration, limitations, no composite |
| `backend/app/core/animus/studio/tasks.py` | Deterministic scene/reconstruction tasks; answer stays server-side |
| `backend/app/core/animus/studio/reconstruction.py` | Token banks, spatial scoring, `recon-v1` error profiles |
| `backend/app/core/animus/studio/adaptive.py` | Coverage floor plus information-gain selection and bounded difficulty |
| `backend/app/core/animus/studio/epistemic.py` | Binary probes, mean-field Beta belief, `eri-v1` posterior reconstruction |
| `backend/app/core/animus/studio/sdt.py` | 2-AFC d′, threshold fit, Brier/type-2, test–retest helpers |
| `backend/app/core/animus/studio/contrast.py` | Contrast pairs, adaptive staircase, `contrast-v1` scoring |
| `backend/app/core/animus/studio/observatory.py` | Evidence provenance, leave-one-out, longitudinal reliability |
| `backend/app/core/animus/studio/protocols.py` | Versioned practice protocols and validation |
| `backend/app/evaluation/animus_instrument_sim.py` | Deterministic synthetic policy comparison; not human validation |
| `backend/app/evaluation/animus_epistemic_sim.py` | Deterministic interview policy simulation; `simulation_only` |
| `backend/app/evaluation/animus_contrast_sim.py` | Deterministic 2-AFC respondent and threshold-recovery simulation; `simulation_only` |
| `backend/app/schemas/animus_studio.py` | Strict bounded request schemas for the Studio API |
| `backend/app/schemas/animus_studio_responses.py` | Typed response contract for every successful Studio route |
| `frontend/app/animus/` | Product routes: landing, studio, practice, interview, observatory, profile, worlds, about |
| `frontend/components/animus/` | Procedural R3F scene, candidate strip, prompt bar, inspector, history, studio shell, reconstruction board, epistemic probe, contrast pair, atlas, evidence trail, reliability panel |
| `frontend/lib/animusStudioApi.ts`, `useAnimusStudio.ts` | Typed client, response/command/WS types, and product state hook |
| `frontend/scripts/verify-animus-ui.cjs` | Playwright end-to-end loop + screenshots |
| `docs/animus/` | Vision, architecture, API contract, claims boundary, roadmap, demo, README |

The Studio is additive: it does not replace the IMAGINA session stack or the P1 ANIMUS research API. The claim
ceiling remains L1; image generation, uploads, neural content, dream content, and neural reconstruction are
disabled/unauthorized.

Schema v018 adds the experimental measurement layer: a local profile, five separate behavioural estimates,
Brier calibration, versioned protocols, and idempotent trial records. Schema v019 adds reconstruction task
metadata and error profiles; schema v020 adds epistemic interview headers and probe metadata; schema v021 adds
contrast sessions and trials. Practice tasks
are deterministic and server-scored; the client never receives the answer, target flags, or target positions
before submission. Object reconstruction uses token F1; spatial layout uses normalized position error;
calibration is cross-cutting. The profile has no composite and is labelled `EXPERIMENTAL` with
`clinical_use = DISABLED`. The epistemic interview is a separate surface: binary probes, Beta posterior,
coverage/calibration/abstention/entropy, no composite, and no neural claim. Scene Threshold is a contrastive
2-AFC surface: hidden target side, adaptive staircase, fitted within-scene threshold, d′, side bias, Brier,
and coverage; the observatory adds evidence provenance and feature-level test–retest. See
`docs/animus/MEASUREMENT_MODEL.md`, `RECONSTRUCTION_SPEC.md`, `ADAPTIVE_POLICY.md`,
`EPISTEMIC_INTERVIEW_SPEC.md`, `CONTRAST_SPEC.md`, `OBSERVATORY_SPEC.md`, and
`docs/animus/VALIDATION_PROTOCOL.md`.

Schema v017 persists branch redo stacks; Studio connections use `synchronous=FULL`, strict stored-JSON
decoding, deep health diagnostics, and a durable event cursor. Before a non-empty database is migrated, the
runner writes and integrity-checks a `VACUUM INTO` backup and refuses to continue if it fails. The WebSocket joins before
snapshotting, forwards durable `seq` values, and signals `resync_required` on subscriber overflow; snapshots
expose `last_event_seq` so the client can discard duplicates and resync on a gap. The backend is
loopback-first and enforces an explicit Host allowlist; Studio HTTP responses are marked `no-store`.
