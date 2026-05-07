# CONTEXT_INDEX.md — Which Docs to Read for Which Task

> AI agents: start every task by reading the docs listed for your task type.

---

## General Task (new feature, refactor, investigation)

1. `AGENTS.md` — coding rules, safety rules, privacy rules, definition of done
2. `docs/ai/PROJECT_CONTEXT.md` — architecture, modules, data flow, important files

---

## Bug Fix

1. `AGENTS.md` — coding rules
2. `docs/ai/TASK_BRIEF.md` — edit before starting
3. `docs/ai/KNOWN_ISSUES.md` — check if the bug is a known risk
4. `docs/ai/PROJECT_CONTEXT.md` — find relevant modules
5. Relevant source files — inspect the affected code

---

## Architecture Change

1. `AGENTS.md` — architecture overview, module boundaries
2. `docs/ai/PROJECT_CONTEXT.md` — current architecture, target architecture, data flow
3. `docs/ai/DECISIONS.md` — existing architecture decisions, ADR format
4. `docs/architecture.md` — canonical architecture documentation
5. `docs/roadmap.md` — V1/V2/V3 evolution plan

---

## Safety or Privacy Change

1. `AGENTS.md` — safety and ethics rules, privacy rules
2. `docs/ai/KNOWN_ISSUES.md` — safety and privacy risks
3. `docs/ai/DECISIONS.md` — safety architecture decisions (ADR-006, ADR-001)
4. `docs/ethics.md` — ethics and safety principles
5. `backend/app/services/safety_monitor.py` — safety monitor implementation

---

## Scientific Claims, UI Text, or Documentation

1. `AGENTS.md` — allowed and prohibited claims
2. `docs/scientific_claims.md` — full claims policy
3. `docs/metrics.md` — metric formulas and limitations
4. `docs/ethics.md` — ethics principles

---

## Adding or Modifying Metrics

1. `AGENTS.md` — core domain concepts
2. `docs/metrics.md` — current formulas, components, interpretation
3. `docs/ai/PROJECT_CONTEXT.md` — data flow, PID/IQI engine
4. `backend/app/services/pid_iqi_engine.py` — implementation
5. `backend/app/services/state_estimator.py` — state estimation feeding PID/IQI
6. `backend/app/tests/test_pid_iqi_engine.py` — metric tests

---

## Adding or Modifying Signal Providers

1. `AGENTS.md` — signal provider abstraction
2. `docs/ai/PROJECT_CONTEXT.md` — signals module, data flow
3. `docs/architecture.md` — signal provider architecture
4. `backend/app/signals/base.py` — signal provider interface
5. `backend/app/signals/*.py` — existing providers as examples
6. `backend/app/tests/test_signal_providers.py` — provider tests

---

## Adding or Modifying Frontend Scenes/Components

1. `AGENTS.md` — frontend module overview, coding rules
2. `docs/ai/PROJECT_CONTEXT.md` — frontend architecture
3. `frontend/AGENTS.md` — Next.js-specific agent rules
4. Relevant component files in `frontend/components/`
5. `frontend/lib/feedbackMapping.ts` — feedback parameter mapping

---

## Full Repository Analysis / AI Context Snapshot

1. Run `bash scripts/ai_context.sh` to generate `docs/ai/repo_snapshot.md`
2. Read `docs/ai/repo_snapshot.md` for full repository context
3. If repomix is not available, use the Task tool with the "explore" agent for deep searches

---

## Writing Tests

1. `docs/ai/TASK_BRIEF.md` — acceptance criteria and verification
2. Existing test files for patterns and conventions
3. `backend/pyproject.toml` — pytest and ruff config
4. `AGENTS.md` — testing and verification section

---

## CI/CD Changes

1. `AGENTS.md` — verification commands
2. `.github/workflows/ci.yml` — current CI pipeline
3. `backend/pyproject.toml` — backend tool config
4. `frontend/package.json` — frontend scripts

---

*Last updated: 2026-05-07*
