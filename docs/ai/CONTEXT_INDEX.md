# CONTEXT_INDEX.md — Which Docs to Read for Which Task

> AI agents: start every task by reading the docs listed for your task type.

---

## General Task (new feature, refactor, investigation)

1. `AGENTS.md` — coding rules, safety rules, privacy rules, definition of done
2. `docs/ai/PROJECT_CONTEXT.md` — architecture, modules, data flow, important files
3. `docs/program/PROGRAM_STATUS.md` — canonical gate and claim status (generated)

---

## Scientific status, claim, or result change

1. `docs/program/PROGRAM_STATUS.md` — generated gate/claim status, supersessions, provenance hashes
2. `science/registry/claims.yaml` — what may be claimed, forbidden interpretations, evidence links
3. `science/registry/artifacts.yaml` — canonical artifact per gate, status mapping, supersession
4. `science/schemas/` — claim, result-envelope, and ledger schemas
5. `docs/animus/ANIMUS_CLAIMS_BOUNDARY.md` — enforced product claim ceiling
6. `backend/app/research/ledger.py` — validation rules; run
   `python -m app.cli.science_ledger --check` from `backend/`
7. Never update a gate status in prose. Change the registry or add a superseding artifact first.

---

## Research protocol or simulation change

1. `docs/animus/ACTIVE_REALITY_TESTING_SPEC.md` — ART construct, task, model, and boundaries
2. `docs/program/ART_PREREGISTRATION.md` and `docs/program/ART_ANALYSIS_PLAN.md` — draft study and
   statistical plan
3. `science/protocols/art-v1.yaml` — machine-readable `ANIMUS-ART-v1`
4. `backend/app/research/art/` — model, design, metrics, simulator, power
5. Run `python -m app.cli.art_simulate --check` and `python -m app.cli.art_power --check` from
   `backend/`; regenerate artifacts only with the documented CLI commands.

---

## Multimodal acquisition / closed-loop work

1. `docs/multimodal_platform.md` — architecture, status table, limitations
2. `docs/ai/DECISIONS.md` — ADR-040 (shadow-first controller, evidence classes, offline MEG/fMRI)
3. `docs/hardware_validation_checklist.json` — required before any hardware touches a person

---

## Frontend / interface change

1. `AGENTS.md` — coding, safety, privacy, and claim rules
2. `frontend/AGENTS.md` — Next.js version-specific constraints
3. `docs/animus/INTERFACE_PRINCIPLES.md` — research basis, North Star, and interaction constraints
4. `docs/animus/RESEARCH_2_0.md` — 2022–2026 review and Palimpsest comparison rationale
5. `docs/animus/WORKBENCH_SPEC.md` — workbench state, keyboard map, preview, trace, and Stage lens contract
6. `docs/animus/ANIMUS_PRODUCT_VISION.md` — product loop and boundaries
7. `docs/ai/EVIDENCE_INSTRUMENT.md` — Glass Box registry, evidence marks, Method Atlas, claim audit, and budget rules
8. `docs/ai/STUDY_DESIGNER.md` — Falsification Studio, preregistration schema, allocation preview, Participant Mode
9. `docs/ai/PROJECT_CONTEXT.md` — frontend module map
10. `docs/animus/IMAGINE_LAB.md` — Imagine 2.0: 16D conditioning, adaptive policy, stage-first UI, fail-closed diffusion lane
11. `docs/animus/LUMEN_WORLD_ENGINE.md` — Lumen grammar, layered composer, presets, renderer, staged diffusion path
12. `docs/animus/DIFFUSION_WORKER.md` — A100 worker contract, security, deployment acceptance, rollback
13. `frontend/components/animus/` — existing components and patterns

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

## ANIMUS Studio / Behavioural Instrument

1. `docs/animus/README.md` — product routes and local run
2. `docs/animus/ANIMUS_ARCHITECTURE.md` — modules, migrations, practice loop
3. `docs/animus/MEASUREMENT_MODEL.md` — dimensions, scoring, limitations
4. `docs/animus/RECONSTRUCTION_SPEC.md` — `recon-v1` task and scoring contract
5. `docs/animus/ADAPTIVE_POLICY.md` — coverage floor, information gain, difficulty
6. `docs/animus/VALIDATION_PROTOCOL.md` — proposed independent study
7. `docs/animus/ANIMUS_CLAIMS_BOUNDARY.md` — allowed and forbidden copy
8. `docs/animus/COMPARISON_RESEARCH.md` — comparison chamber evidence, limits, proposed studies
9. `backend/app/core/animus/studio/` — tasks, reconstruction, adaptive, profile, service
10. `frontend/app/animus/` and `frontend/components/animus/` — product surfaces

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

*Last updated: 2026-10-23*
