# IMAGINA — Closed-Loop Mental Imagery Training System

## What IMAGINA Is

IMAGINA is a research prototype for closed-loop mental imagery training.
It estimates imagery-related cognitive-state proxies (IQI, PID), adapts a
cognitive curriculum, and updates a procedural/generative feedback scene
to scaffold mental imagery practice.

## Core Loop

guided imagery task
→ self-report + proxy features
→ state estimation
→ Imagery Quality Index (IQI)
→ Perception-Imagination Distance (PID)
→ adaptive curriculum decision
→ procedural feedback (scene parameters + prompt)
→ next task or session summary

## What IMAGINA Is Not

- Not a mind-reading system
- Not a dream decoder
- Not a consciousness measurement tool
- Not a clinical therapy replacement
- Not a production BCI
- Not a validated neural decoder
- Not a guaranteed imagery improvement program

## How to Run

### Backend
```bash
cd backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Demo Session
```bash
curl -X POST http://localhost:8000/api/imagina/session/start
curl -X POST http://localhost:8000/api/imagina/session/{session_id}/task/start?task_id=shape_stabilization
curl -X POST http://localhost:8000/api/imagina/session/{session_id}/self-report -d '{"vividness":7,"stability":6,"effort":3}'
curl -X POST http://localhost:8000/api/imagina/session/{session_id}/step
curl -X GET http://localhost:8000/api/imagina/session/{session_id}/summary
```

### Frontend
```bash
cd frontend
npm run dev
```

## EEG Validation Layer

The research directory contains EEG validation tools for metadata preflight,
confound detection, and dataset suitability assessment. This is NOT the core
product — it is a safety/research module for optional neural integration.

See `docs/research/EEG_VALIDATION_LAYER.md`.

## Scientific Boundaries

### Safe Claims
- Estimates imagery-related cognitive-state proxies
- Supports guided imagery practice
- Adapts feedback based on estimated engagement and stability
- Computes experimental IQI and PID proxy metrics
- Provides a research prototype for neuroadaptive imagery training

### Forbidden Claims
- Mind reading, thought reconstruction, dream decoding
- Clinical therapy, diagnosis, treatment
- Production BCI, real-time neural control
- Guaranteed imagery improvement
- Consciousness measurement
- Validated neural decoding

## Architecture

```
backend/app/
  core/          ← IMAGINA Core (metrics, curriculum, feedback, safety)
  api/imagina/   ← IMAGINA API routes
  research/      ← EEG validation layer (optional)
  services/      ← Signal providers, state estimator, session loop
  schemas/       ← Domain models
```

See `docs/RESTRUCTURE_AUDIT.md` for the full restructuring plan.
