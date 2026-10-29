# AGENTS.md — IMAGINA Project Instructions for AI Coding Assistants

> **Read this first before any task in this repository.**

---

## Project Overview

IMAGINA is a **closed-loop mental imagery research platform** — not a mind-reading system. The legacy Dream Corridor surface estimates proxy metrics from simulated EEG-like signals; the newer ANIMUS instrument surface adds behavioural tasks, a symbolic scene studio, an epistemic interview, and a Scene Threshold observatory without claiming decoded neural content.

**Canonical scientific status:** [`docs/program/PROGRAM_STATUS.md`](docs/program/PROGRAM_STATUS.md), generated from `science/registry/`. If prose and the registry disagree, the registry wins.

**Flagship research question:** can a behavioural-assisted, uncertainty-aware instrument improve the *quality of inquiry* into mental imagery without overclaiming neural decoding? The operating claim ceiling is `L1_BEHAVIORAL_ASSISTED`.

---

## Scientific Boundaries

### Allowed Claims

- "IMAGINA estimates proxy metrics related to attention, self-reported vividness, behavioral stability, and simulated EEG-like signal patterns."
- "IMAGINA adapts visual feedback based on estimated imagery stability."
- "IMAGINA is a research prototype for closed-loop mental imagery training."
- "IMAGINA does not decode thoughts or dreams."
- "PID and IQI are deprecated legacy proxy scores; they are not validated measures of imagination, and they must not appear in primary research surfaces."

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
| **Legacy PID / IQI** (deprecated) | Hand-tuned composite proxy scores from the Dream Corridor demo. Not validated, not a measure of imagination ability, and excluded from primary research surfaces. See `claim.legacy_pid_iqi`. |
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
6. **Test your changes.** Always run `python scripts/verify.py --quick` (or `--ci`) after making changes.
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
python -m pytest app/tests -m "core or research" -q   # merge gate: ~1,090 tests
python -m ruff check .                                # lint
python -m app.cli.science_ledger --check              # claim/gate registry consistency
```

Key test files:
- `test_science_ledger.py` — registry schema, supersession, claim-evidence consistency
- `test_animus_*` — instrument, studio, observatory, epistemic interview contracts
- `test_safety_monitor.py` — fatigue, effort, dissociation checks
- `test_feedback_policy.py` — scene parameter mapping
- `test_signal_providers.py` — signal provider interfaces
- `test_replay_determinism.py` — seeded replay reproducibility
- `test_session_service.py` — session lifecycle

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
python scripts/verify.py --ci     # lint, ledger, backend gate, frontend, docker config
python scripts/verify.py --full   # --ci plus the complete backend suite
```

---

## AI Agent Workflow

When working on a task in this repository:

1. **Read relevant context files** (see `docs/ai/CONTEXT_INDEX.md` for which docs to read).
2. **Create/update a task brief** in `docs/ai/TASK_BRIEF.md` if the task is complex.
3. **Make changes** following coding rules above.
4. **Run `python scripts/verify.py --quick`** before considering the task done.
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
2. `python scripts/verify.py --quick` passes (or skipped checks are explained).
3. No prohibited claims appear in code, UI, or docs.
4. Safety boundaries are respected (no bypassed monitors, no removed disclaimers).
5. `docs/ai/SESSION_LOG.md` is updated.
6. Git status is clean of unrelated changes.

---

## Quick Reference

| Need | File |
|------|------|
| Canonical gate/claim status | `docs/program/PROGRAM_STATUS.md` |
| Claim and artifact registry | `science/registry/` |
| Ledger command | `python -m app.cli.science_ledger --check` (from `backend/`) |
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
