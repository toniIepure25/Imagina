# IMAGINA Repository Restructure Audit

## Current State (V7.8)

### Repository Identity
The repository currently projects "EEG confound validation" as its primary identity
due to the overwhelming volume of EEG validation CLIs, artifacts, and thesis materials.
The original IMAGINA core — a closed-loop mental imagery training system — exists but
is buried under research/infrastructure layers.

### What Exists (IMAGINA Core)
- `backend/app/api/state.py` — state estimation endpoint
- `backend/app/api/tasks.py` — task management endpoint
- `backend/app/api/sessions.py` — session management endpoint
- `backend/app/api/feedback.py` — feedback policy endpoint
- `backend/app/api/reports.py` — report generation endpoint
- `backend/app/api/signals.py` — signal provider endpoint
- `backend/app/services/state_estimator.py` — rule-based state estimation
- `backend/app/services/pid_iqi_engine.py` — PID/IQI computation
- `backend/app/services/safety_monitor.py` — fatigue/safety checks
- `backend/app/services/curriculum_manager.py` — adaptive staircase curriculum
- `backend/app/services/feedback_policy_engine.py` — scene parameter mapping
- `backend/app/services/report_service.py` — session report aggregation
- `backend/app/schemas/` — Pydantic domain models
- `backend/app/core/` — config, constants, time helpers (nearly empty)
- `frontend/` — Next.js frontend with scene/dashboard components

### What Exists (EEG Validation / Overgrowth)
- ~50 CLI scripts in `backend/app/cli/` for EEG validation
- `backend/app/eeg_datasets/` — dataset adapters
- `backend/app/datasets/` — dataset loaders
- `backend/app/research/` — empty directory structure
- ~100 exports artifacts in `data/exports/`
- `docs/ai/` — session logs, decisions, task briefs
- Thesis chapters, defense packs, Q&A, flashcards (V7.4-V7.8)

### Proposed Target Structure

```
backend/app/
  core/                    # IMAGINA Core System
    events/                # Event store + domain events
    sessions/              # Session manager
    tasks/                 # Imagery task engine
    state/                 # State estimation
    metrics/               # IQI, PID computation
    curriculum/            # Adaptive curriculum
    feedback/              # Generative/procedural feedback
    personalization/       # User profile + adaptation
    safety/                # Safety/fatigue monitor
    reports/               # Session report generation

  api/
    imagina/               # IMAGINA-specific API routes
    (existing routes preserved)

  research/
    eeg_validation/        # EEG validation scripts (preserved, demoted)
    datasets/              # Dataset utilities (preserved)
    confounds/             # Metadata preflight protocol

  schemas/
    imagina/               # IMAGINA domain event schemas
    (existing schemas preserved)

  services/
    imagina/               # IMAGINA core services (moved from flat services/)
    (existing services preserved or migrated)

data/
  imagina/
    sessions/              # Session event logs
    profiles/              # User profiles
    configs/               # Task templates, curriculum configs
    reports/               # Generated reports

docs/
  imagina/                 # IMAGINA vision, boundaries, design docs
  research/                # EEG validation layer docs
  thesis_archive/          # V7.x thesis materials (preserved)
  adr/                     # Architecture decision records

demo_thesis/
  src/
    features/imagina/      # IMAGINA frontend pages
    components/imagina/    # Scene stabilizer, IQI/PID panels
    data/imagina/          # Frontend data/constants
```

### What Moves Where
- EEG validation CLIs → `research/eeg_validation/` (preserved, not primary)
- OpenMIIR artifacts → `research/eeg_validation/openmiir_negative_control/`
- PhysioNet artifacts → `research/eeg_validation/physionet_mi_baseline/`
- Thesis materials → `docs/thesis_archive/`
- IQI v2 from CLI → `core/metrics/` (consolidated)

### What Stays Untouched
- `backend/app/api/*` (all existing APIs)
- `backend/app/services/*` (core services)
- `backend/app/schemas/*` (domain schemas)
- `backend/app/storage/*` (SQLite storage)
- `backend/app/websocket/*` (WebSocket manager)
- `backend/app/signals/*` (signal providers)
- `frontend/` (Next.js app)
- `data/exports/` (existing artifacts preserved)

### Risks
- Breaking existing API routes — mitigated by preserving all existing routes
- Over-engineering new abstractions — mitigated by building only what's needed
- Forgetting old EEG work — mitigated by explicit archive/README

### Action Plan
1. Create target directories
2. Build IMAGINA core: schemas → services → API → frontend
3. Preserve/archive EEG validation
4. Write IMAGINA vision docs
5. Test and verify
