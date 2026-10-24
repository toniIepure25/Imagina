# AGENTS.md — IMAGINA Project Instructions for AI Coding Assistants

> **Read this first before any task in this repository.**

---

## Project Overview

IMAGINA is a **closed-loop mental imagery training research prototype** — not a mind-reading system. It estimates proxy metrics related to attention stability, self-reported vividness, behavioral consistency, and simulated EEG-like signal patterns. The system adapts visual/audio/generative feedback as a scaffold for mental imagery practice, then reports session outcomes.

**Flagship MVP:** Dream Corridor Scene Stabilizer (3D corridor that responds to estimated imagery state).

---

## Scientific Boundaries

### Allowed Claims

- "IMAGINA estimates proxy metrics related to attention, self-reported vividness, behavioral stability, and simulated EEG-like signal patterns."
- "IMAGINA adapts visual feedback based on estimated imagery stability."
- "IMAGINA is a research prototype for closed-loop mental imagery training."
- "IMAGINA does not decode thoughts or dreams."
- "PID and IQI are experimental proxy metrics that require validation."

### Prohibited Claims (MUST NEVER APPEAR)

- "Reads your mind" / "Decodes your dreams" / "Shows what you are imagining"
- "Cures aphantasia" / "Guarantees lucid dreaming"
- "Diagnoses mental health conditions" / "Clinically validated neurofeedback"
- "Measures consciousness objectively" / "Controls reality"

If you are unsure whether a claim is allowed, consult `docs/scientific_claims.md`.

---

## System Architecture

```
backend/   — FastAPI (Python 3.10+), port 8000
frontend/  — Next.js 16 + TypeScript + Tailwind 4 + React Three Fiber, port 3000
docs/      — Architecture, metrics, ethics, claims, demo script, experiments
data/      — Local SQLite database, exports
research/  — Config files, notebook placeholders
scripts/   — Verification scripts
```

**Backend modules:**
- `api/` — REST endpoints (sessions, tasks, state, feedback, replay, reports, calibration, experiments, exports, users, signals, health)
- `websocket/` — WebSocket manager + session stream loop
- `services/signal_simulator.py` — Deterministic simulated EEG-like signal generator
- `services/feature_engine.py` — Feature pass-through (V1) / normalization (V2)
- `services/state_estimator.py` — Rule-based state estimation from features + self-report
- `services/pid_iqi_engine.py` — PID/IQI composite metric computation
- `services/curriculum_manager.py` — 8-level adaptive staircase curriculum
- `services/feedback_policy_engine.py` — Maps state to 10 scene params + prompt
- `services/safety_monitor.py` — Fatigue, effort, dissociation, time limit checks
- `services/report_service.py` — Aggregates events into session summary
- `signals/` — Signal provider abstraction (simulated, replay, manual, LSL stub)
- `evaluation/` — Offline cohort simulation, replay validator, metric sanity
- `storage/` — SQLite via aiosqlite; event sourcing pattern
- `schemas/` — Pydantic v2 models for all domain types
- `core/` — Config, constants, time helpers, error types

**Frontend modules:**
- `app/page.tsx` — Landing page
- `app/session/page.tsx` — Full session flow
- `app/replay/page.tsx` — Deterministic demo replay
- `app/reports/[sessionId]/page.tsx` — Session report
- `app/science/page.tsx` — Scientific notes
- `app/profile/page.tsx` — Local user profile
- `app/experiments/page.tsx` — Experiment protocols
- `components/scene/` — React Three Fiber 3D corridor components
- `components/metrics/` — MetricsDashboard, TimelineChart, CurriculumTimeline
- `components/session/` — Setup, Calibration, SelfReport, Controls
- `lib/websocket.ts` — Typed WebSocket client
- `lib/api.ts` — REST API helper

---

## Core Domain Concepts

| Concept | Definition |
|---------|-----------|
| **PID** (Perception-Imagination Distance) | Composite proxy: 0.45*neural_proxy_dist + 0.35*behavioral_dist + 0.20*uncertainty. Range 0–1, lower is better. |
| **IQI** (Imagery Quality Index) | Composite proxy: 0.35*attention + 0.30*engagement + 0.20*behavioral + 0.15*relaxation, weighted by confidence. Range 0–1, higher is better. |
| **Attention Stability** | Inverse theta/beta style proxy from simulated/simulated features + self-report. |
| **Relaxation** | Relative alpha-band proxy from simulated features + self-report relaxation. |
| **Imagery Engagement** | Task-related parietal/gamma proxy engagement from features + vividness/self-report. |
| **Fatigue** | Trend-based theta/lower-alpha increase + self-report fatigue + session duration. |
| **Curriculum** | 8-level adaptive staircase (3-up/1-down), each level has success thresholds for IQI/PID. |
| **Signal Provider** | Abstraction layer for simulated, replay, manual, and future LSL EEG streams. |
| **Safety Monitor** | Checks fatigue >0.80, overeffort, session >20min, dissociation keywords, signal quality. |

See `docs/metrics.md` for full formulas and interpretations.

---

## Coding Rules

1. **Small diffs.** Do not rewrite unrelated files. Stay focused on the task.
2. **Follow existing patterns.** Match code style, imports, naming, and conventions of neighboring files.
3. **No comments unless asked.** Code should be self-documenting.
4. **Use existing libraries.** Check imports in neighboring files before introducing new dependencies.
5. **Check existing configs.** `backend/pyproject.toml` defines lint rules (ruff, line-length=120, E/F/I/N/W). `frontend/package.json` defines scripts (dev, build, lint).
6. **Test your changes.** Always run `scripts/verify.sh` after making changes.
7. **Update docs after major tasks.** See Documentation Rules below.

---

## Safety and Ethics Rules

1. **No raw EEG or neural data to external APIs.** Everything stays local.
2. **Safety monitor is a first-class system feature.** Do not bypass fatigue checks, cooldowns, or time limits.
3. **No dissociation-inducing UX.** Avoid strobe-like effects, isolation depths, or suggestion of altered states.
4. **All prompt text is deterministic templates.** No LLM-generated guidance that could make unverified medical claims.
5. **Disclaimers must be visible.** Landing page, session start, and reports must include scientific boundary language.
6. **Safety overrides always take priority over curriculum advancement.**

---

## Privacy Rules

1. **Local-first.** All data stays in SQLite on the user's machine. No cloud accounts, no telemetry.
2. **No hardcoded secrets.** No API keys, passwords, or tokens in source files.
3. **No reading .env files.** Configuration via environment variables only; `.env` is gitignored.
4. **No authentication or user tracking.**
5. **Data export must not include secrets.**

---

## Testing and Verification

### Backend

```bash
cd backend
python3 -m pytest app/tests/ -q        # 34 test files, ~400 tests
python3 -m ruff check .                 # lint
python3 -m mypy app/ --ignore-missing-imports  # type check (optional, not in CI)
```

Key test files:
- `test_pid_iqi_engine.py` — PID/IQI computation correctness
- `test_curriculum_manager.py` — Staircase progression/regression
- `test_safety_monitor.py` — Fatigue, effort, dissociation checks
- `test_feedback_policy.py` — Scene parameter mapping
- `test_signal_providers.py` — Signal provider interfaces
- `test_replay_determinism.py` — Seeded replay reproducibility
- `test_calibration_service.py` — Calibration profiles
- `test_report_service.py` — Report aggregation
- `test_session_service.py` — Session lifecycle
- `test_evaluation_harness.py` — Offline evaluation tools
- `test_profile_experiment_exports.py` — Profile and experiment exports

### Frontend

```bash
cd frontend
npm run lint      # ESLint
npm run build     # TypeScript compilation + Next build
```

### Docker

```bash
docker compose config   # Validate compose file
```

### Full verification

```bash
bash scripts/verify.sh
```

---

## AI Agent Workflow

When working on a task in this repository:

1. **Read relevant context files** (see `docs/ai/CONTEXT_INDEX.md` for which docs to read).
2. **Create/update a task brief** in `docs/ai/TASK_BRIEF.md` if the task is complex.
3. **Make changes** following coding rules above.
4. **Run `bash scripts/verify.sh`** before considering the task done.
5. **Update `docs/ai/SESSION_LOG.md`** with what was done, decisions made, tests run, remaining risks.
6. **Update `docs/ai/DECISIONS.md`** if any architectural decision was made or changed.
7. **Check scientific claims** — any new UI text, API field, or doc must not make prohibited claims.

---

## Documentation Rules

### Required docs in `docs/ai/`

| File | When to update |
|------|---------------|
| `SESSION_LOG.md` | After every major task or session |
| `DECISIONS.md` | When making or changing an architectural decision |
| `TASK_BRIEF.md` | Before starting a complex task (edit the template) |
| `KNOWN_ISSUES.md` | When discovering or mitigating a risk |
| `PROJECT_CONTEXT.md` | When architecture or module layout changes significantly |

### Required docs in root `docs/`

Do not modify `docs/architecture.md`, `docs/metrics.md`, `docs/scientific_claims.md`, or `docs/ethics.md` without explicit instruction. They are canonical references.

---

## Definition of Done

A task is done when:
1. All acceptance criteria are met.
2. `scripts/verify.sh` passes (or skipped checks are explained).
3. No prohibited claims appear in code, UI, or docs.
4. Safety boundaries are respected (no bypassed monitors, no removed disclaimers).
5. `docs/ai/SESSION_LOG.md` is updated.
6. Git status is clean of unrelated changes.

---

## Quick Reference

| Need | File |
|------|------|
| Architecture overview | `docs/architecture.md` |
| Metric formulas | `docs/metrics.md` |
| Allowed/prohibited claims | `docs/scientific_claims.md` |
| Ethics & safety | `docs/ethics.md` |
| Project roadmap | `docs/roadmap.md` |
| Experiment protocols | `docs/experiment_plan.md` |
| Demo walkthrough | `docs/demo_script.md` |
| Data dictionary | `docs/data_dictionary.md` |
| Offline evaluation | `docs/evaluation.md` |
| Reproducibility | `docs/reproducibility.md` |
| Implementation status | `docs/implementation_status.md` |

---

*This file governs all AI agent behavior in this repository. Any conflict with frontend/AGENTS.md or other local agent files should be resolved in favor of this file for project-wide concerns.*
