# TASK_BRIEF.md

## Current task — Phase 3B: Stage 0B Active Reality Testing (2026-10-29)

**Goal:** implement the approved active-inquiry extension as a simulation-only slice: formal model,
deterministic simulator, power and policy recovery, Stage 0 tests, protocol and registry entries. No
human data, API, migration, or UI.

**Scope**
- `docs/animus/ACTIVE_REALITY_TESTING_SPEC.md`, `docs/program/ART_PREREGISTRATION.md`,
  `docs/program/ART_ANALYSIS_PLAN.md`, `science/protocols/art-v1.yaml`.
- `backend/app/research/art/` model, design, metrics, simulator, power; `app/cli/art_simulate.py`,
  `app/cli/art_power.py`, `app/cli/art_recover.py`.
- `backend/app/tests/test_art_stage0.py`.
- `results/art/ART_STAGE0_SIMULATION.json`, `ART_STAGE0_POWER.json`, `ART_MODEL_RECOVERY.json`; three
  simulation-only registry gates and three claims.
- ADR-068, evidence-map addendum, and session log.

**Non-goals**
- No API, database migration, frontend route, human recruitment, clinical sample, or neural data.
- No claim above `L1_BEHAVIORAL_ASSISTED`; no diagnosis, imagery-strength, decoding, or
  "revolutionary"/"first" claim.
- No training RCT or clinical extension; both remain blocked.

**Acceptance**
- `art_simulate --check`, `art_power --check`, and the 26 Stage 0 tests pass.
- `ANIMUS_P4_ART_SIM=PASS`, `ANIMUS_P4_ART_POWER=PASS`, and `ANIMUS_P4_ART_RECOVERY=PASS` in the
  ledger.
- Ruff clean; `verify.py --quick` passes; docs links pass.
- Each artifact is reproducible from the documented CLI command.

**Status:** implemented; verification recorded in the 2026-10-29 ART session-log entry.

---

## Previous task — Phase 3: Stage 0 epistemic source monitoring (2026-10-29)

**Goal:** implement the approved first slice of the source-monitoring program: specification,
preregistration draft, analysis plan, machine-readable protocol, claim-registry entries, and a
dependency-free simulation core that passes its design gate. No human data, API, migration, or UI.

**Scope**
- `docs/animus/SOURCE_MONITORING_SPEC.md`, `docs/program/PRM_PREREGISTRATION.md`,
  `docs/program/PRM_ANALYSIS_PLAN.md`, `science/protocols/prm-v1.yaml`.
- `backend/app/research/prm/` model, metrics, adaptive design, simulator, power; `app/cli/prm_simulate.py`,
  `app/cli/prm_power.py`.
- `backend/app/tests/test_prm_stage0.py`.
- `results/prm/PRM_STAGE0_SIMULATION.json`, `results/prm/PRM_STAGE0_POWER.json`, and registry entries for
  the two simulation-only gates.
- ADR-067 and session log.

**Non-goals**
- No API, database migration, frontend route, human recruitment, clinical sample, or neural data.
- No claim above `L1_BEHAVIORAL_ASSISTED`; no diagnosis, imagery-strength, or decoding claim.
- No `meta_d_prime` estimate in Stage 0; it is gated.

**Acceptance**
- Simulation `--check` and 15 Stage 0 tests pass.
- `ANIMUS_P3_SIM=PASS` and `ANIMUS_P3_POWER=PASS` in the ledger; 11 claims with the three new
  source-monitoring claims.
- Ruff clean; `verify.py --quick` passes; docs links pass.
- The artifact is reproducible from the documented CLI command.

**Status:** implemented; verification recorded in the 2026-10-29 session-log entry.

---

## Previous task — Phase 1: canonical claim registry and results ledger (2026-10-29)

**Goal:** replace hand-maintained, contradictory scientific status prose with one machine-readable
claim registry and one hash-chained results ledger, then generate the program status document from
them.

**Scope**
- `science/registry/claims.yaml` and `science/registry/gates.yaml` with controlled status vocabularies.
- JSON Schemas for claims, results, study bundles, and benchmark runs.
- `backend/app/research/ledger.py` plus a CLI that validates every `results/**/*.json`, detects two
  statuses for the same gate, requires provenance fields, and emits `docs/program/PROGRAM_STATUS.md`.
- Explicit supersession records for the ANIMUS P2/P2R conflict and the claims-boundary wording.
- Tests for schema validation, conflict detection, provenance completeness, and deterministic output.

**Non-goals**
- No new instrument, task, neural gate, or product surface.
- No change to the claim ceiling or to any frozen protocol.
- No rewrite of historical result artifacts; supersede, do not overwrite.

**Constraints**
- Preserve `L1_BEHAVIORAL_ASSISTED`; `PERCEPTION_NEURAL_CONTENT` remains blocked/limited until a sealed
  replication resolves P2 vs P2R.
- Every generated document must be reproducible from the registry and ledger.
- Do not call this review systematic.

**Acceptance**
- `python -m app.cli.science ledger` (or equivalent) validates all registered results and exits 0.
- An injected duplicate/conflicting gate status fails the command.
- `docs/program/PROGRAM_STATUS.md` is generated and matches the ledger.
- Ruff, merge-gate tests, and the claim audit pass.

**Status:** implemented. Evidence: `science/registry/`, `backend/app/research/ledger.py`,
`docs/program/PROGRAM_STATUS.md`, ADR-066, 2026-10-29 session-log entry. Verified by 10 ledger tests
and `python -m app.cli.science_ledger --check`.

---

## Historical brief — Lumen: scene engine and interface overhaul (2026-10-26)

**Goal:** make `/animus/imagine` feel like a deliberate world instrument rather than a keyword demo: a layered,
walkable, first-person place with a professional Lumen interface, while keeping the future diffusion lane honest and
blocked until A100 access exists.

**Scope**
- Deterministic world grammar: biomes, archetypes, seven layers, palette, focal object, path, camera, provenance.
- Layered composer with a capped entity budget and per-entity semantic attributes (`layer`, `collidable`, `anchor`,
  `semantic_source`, `variant`).
- Procedural sky, terrain/path, practical light, ambient motes, architecture bodies, bloom post-FX, and quality-aware
  reduced-motion fallback.
- First-person collision from semantic attributes, velocity smoothing, head bob, reset, pointer lock, and capture.
- Lumen UI: world strip with five presets and `?preset=`, scene-read overlay, stage lens, walk/look coach mark,
  underline instrument tabs, mobile instrument sheet, and sharper composer/status rails.
- Cross-project entry points: landing page, `/animus`, `/animus/worlds`, `/science`.
- Docs, ADR-064, session log, and verification.

**Non-goals**
- No A100 worker, diffusion weights, text encoder, video model, or generated imagery in this build.
- No raw EEG/HRV/EDA, session id, or participant id sent anywhere.
- No claim that the world is a reconstruction, decode, measurement, diagnosis, or treatment.
- No backend, database, schema, API, or new frontend runtime dependency.
- No new saved-world format; `?preset=` is presentation state only.

**Constraints**
- Claim ceiling `L1_BEHAVIORAL_ASSISTED`.
- Text owns semantics; signals only tune perceptual budget, light, fog, motion, and density.
- Local procedural remains default and fallback; diffusion stays visibly offline.
- Preserve `/animus/imagine`, the `/imagina/animus` redirect, ANIMUS identity, `SceneGraph` compatibility, and the
  existing download/consent contract.
- Do not modify canonical `docs/architecture.md`, `docs/metrics.md`, `docs/scientific_claims.md`, `docs/ethics.md`.

**Acceptance**
- `/animus/imagine` loads at 390/1440 px with a visible canvas, no console errors, and no horizontal overflow.
- Preset selection changes the world title, URL, and scene hash; invalid `?preset=` falls back with a notice.
- Signals change the scene hash but not the biome, archetype, or focal object.
- Every entity is traceable to a layer and semantic source; the walkable path stays clear.
- First-person toggle, movement, collision, reset, fullscreen, capture, consent, and offline request download still
  work.
- Typecheck, lint, build, vitest, targeted Playwright, bundle budget, and claim audit pass and are recorded.

**Status:** implemented. Evidence: `docs/animus/LUMEN_WORLD_ENGINE.md`, ADR-064, 2026-10-26 session-log entry.

---

## Historical brief — Imagine 2.0: stage-first, adaptive, diffusion-ready (2026-10-25)

**Goal:** turn `/animus/imagine` into a professional stage-first instrument with a real fail-closed diffusion seam,
richer derived conditioning, adaptive safety, and a hybrid skybox contract — without pretending a model exists.

**Scope**
- 16D conditioning (6 state, 4 band, 2 physiology, 4 meta), quality gate, and eight aesthetic controls.
- Adaptive policy with cap/deadband/hysteresis/dwell/fatigue stop, 60-sample trace, and four simulated scenarios.
- Stage-first desktop/mobile UI, first-person pointer lock, drag fallback, touch joystick, collision, reset,
  fullscreen, capture.
- FastAPI capabilities/jobs/cancel/delete/assets with a file-backed store and a mock-tested state machine.
- `IMAGINA-DIFFUSION-REQUEST-v2` and `MANIFEST-v1`; hybrid skybox preview, provenance lens, A/B toggle.
- A100 runbook, `imagine.diffusion` evidence, ADR-063, docs, screenshots, and full verification.

**Non-goals**
- No A100/GPU worker, weights, text encoder, or real generated image in this build.
- No raw EEG/HRV/EDA, session id, or participant id sent to a worker.
- No claim that the scene or skybox is reconstructed imagery, decoded content, a measurement, or a treatment.
- No claim that adaptive feedback improves imagery, attention, or wellbeing.

**Constraints**
- Claim ceiling stays `L1_BEHAVIORAL_ASSISTED`; the route says what it does not do.
- Local procedural remains default and fallback; diffusion lane fails closed.
- No database migration, no GPU dependency, no new frontend runtime dependency.
- Preserve Studio/ANIMUS orbit behavior; first-person additions are opt-in for Imagine.
- Do not modify canonical `docs/architecture.md`, `docs/metrics.md`, `docs/scientific_claims.md`, `docs/ethics.md`.

**Acceptance**
- `/animus/imagine` loads at 390/1440px with visible stage, no console errors, no overflow.
- 16D vector, quality hold, policy hysteresis/dwell/fatigue, scenarios, manifest allowlist, collision, request v2
  unit-tested.
- Backend blocked default writes no job; mock success/cancel/failure and local asset serving tested.
- Consent is required; offline download is v2; mocked skybox applies with provenance and returns to procedural.
- Typecheck, lint, build, vitest, pytest, E2E, UI audit, claim audit, bundle budget pass and are recorded.

**Status:** implemented. Evidence: `docs/animus/IMAGINE_LAB.md`, `docs/animus/DIFFUSION_WORKER.md`, ADR-063,
2026-10-25 session-log entry.

---

## Historical brief — IMAGINA 4.0: the falsifiable instrument (2026-10-26)

**Goal:** raise every frontend surface to instrument grade by making evidence provenance inspectable, making the
study plan precede the data, and removing the performance/accessibility debt that undercut the research framing —
without backend, schema, API, or claim changes.

**Scope**
- Glass Box evidence registry, per-metric marks, drawer, header toggle, and `/method` Method Atlas.
- Static, negation-aware claim/evidence audit with a generated artifact.
- Five-step Falsification Studio at `/research/design` (`IMAGINA-PREREG-v1`, local hash lock, local export).
- Local-only Participant Mode at `/research/participant`.
- Evidence marks across science, profile, report, multimodal, datasets, analysis, and ANIMUS metrics.
- `ChartFrame` chart-plus-table fallbacks, `VirtualList` long lists, lazy 3D routes, DPR cap, visibility pause,
  WebGL context-loss recovery, semantic-token cleanup.
- Bundle regression script and expanded unit/E2E coverage.

**Non-goals**
- Backend, database, migration, schema, or API changes.
- Live participant recruitment, data collection, ethics approval, or registry deposition.
- Neural decoding, image generation, dream content, diagnosis, or clinical claims.
- A composite imagery score, efficacy claim, or statistical power guarantee.
- New runtime dependencies, telemetry, or external calls.

**Constraints**
- Claim ceiling stays `L1_BEHAVIORAL_ASSISTED`; PID/IQI remain experimental proxy composites.
- Participant Mode is a demonstration, not a study; no persistence or network.
- Study Designer may plan but must never claim power, p-values, efficacy, or approval.
- Preserve stable URLs, the `/imagina/animus` redirect, and ANIMUS visual identity.
- Do not modify canonical `docs/architecture.md`, `docs/metrics.md`, `docs/scientific_claims.md`, `docs/ethics.md`.

**Acceptance**
- Every evidence-aware metric opens a focus-trapped record with method, uncertainty, and “cannot show”.
- `/method`, `/research/design`, and `/research/participant` load at 390/1440px without overflow or console errors.
- A completed draft can be locked, hashed, revised, and exported locally.
- Claim audit passes with zero affirmative prohibited phrases and zero orphan evidence ids.
- Typecheck, lint, build, vitest, bundle budget, and instrument E2E are run and recorded.

**Status:** complete. Evidence is in `docs/ai/EVIDENCE_INSTRUMENT.md`, `docs/ai/STUDY_DESIGNER.md`, ADR-061, and
the 2026-10-26 session-log entry.

---

## Historical brief — ANIMUS interface upgrade (2026-10-24)

**Goal:** make the ANIMUS frontend a coherent, research-grounded instrument: preserve authorship, make state
and uncertainty inspectable, support deliberate practice, and remove inherited generic-product chrome — without
new runtime dependencies or claim changes.

**Scope**
- Research synthesis of HCI/psychology sources informing interaction design.
- Dedicated ANIMUS shell, session instrument rail, responsive navigation, and skip link.
- Accessible command palette for navigation and discovery.
- Studio scene index for direct spatial selection.
- State-aware “Next move” metacognitive card.
- Instrument-suite map on the ANIMUS home page.
- Global visual tokens, metadata, and stale-brand cleanup.
- Interface principles, ADR-055, README, and session log.

**Non-goals**
- Backend/API/schema changes or new measurement claims.
- Neural decoding, image generation, dream content, diagnosis, or clinical framing.
- A composite imagery score, norms, leaderboards, or person comparison.
- Usability, efficacy, or validation claims without a study.

**Constraints**
- No new runtime dependency; local-only; no external calls or telemetry.
- No execution or local install in this session; static verification only.
- Preserve the `L1_BEHAVIORAL_ASSISTED` ceiling and all existing Studio/P1 behavior.

**Acceptance**
- All ANIMUS routes use the dedicated shell and remain reachable at their existing URLs.
- Command palette, scene index, and next-move card are keyboard-accessible and degrade under reduced motion.
- Boundaries remain visible; no prohibited claim or composite score appears in UI copy.
- Research provenance is recorded separately from design inference.
- Typecheck/lint/build/UI verification are either run and recorded, or explicitly marked pending.

---

## Historical brief — ANIMUS 5.0 Scene Threshold observatory (2026-10-24)

**Goal:** add a contrastive 2-AFC scene-discrimination task and a provenance-aware longitudinal observatory,
without adding neural input, an image model, a diagnosis, a composite score, or a new dependency.

**Scope**
- Additive SQLite v021 contrast session and trial tables.
- Deterministic presence/position/colour pairs with hidden target, feature, and delta.
- 2-down/1-up staircase and fitted 75%-correct threshold; d′, signed side bias, Brier, coverage.
- Evidence provenance, leave-one-out sensitivity, and feature-level test–retest reliability.
- Contrast start/submit/summary/list/reflection and observatory API.
- Observatory UI, profile card, and Studio entry point.
- Deterministic simulation and honest validation/claims documentation.

**Non-goals**
- Neural decoding, neural reconstruction, dream content, image generation.
- Clinical diagnosis, treatment, cure, imagery-strength, or far-transfer claims.
- Cross-scene norms, leaderboards, composite scores, or person comparison.
- A criterion estimate from 2-AFC, which is not identified.

**Constraints**
- No new runtime dependency; local-only; no external calls.
- No execution or local install during this session; static verification only.
- Preserve existing Studio/P1 behavior and claim ceiling.

**Acceptance**
- Start returns a pair without target side, feature, delta, or answer.
- Submit is idempotent, rejects a stale scene, and returns the next pair or result.
- Abstention is excluded from d′/thresholds and included in coverage.
- Thresholds are withheld when sparse and marked when censored.
- Observatory reports `insufficient` reliability below three aligned features.
- Capability envelope keeps neural/clinical/image-generation boundaries.
- Tests and docs are present; runtime verification remains explicitly pending.

---

## Historical brief — ANIMUS 4.0 epistemic reconstruction interview (2026-10-23)

**Goal:** add a separate behavioural interview that asks binary questions about a hidden symbolic scene,
updates a transparent posterior, and reports uncertainty/calibration/coverage without adding neural input,
an image model, a diagnosis, or a composite score.

**Scope**
- Additive SQLite v020 interview header and probe metadata.
- `eri-v1` object-presence and spatial-relation probes with hidden answers.
- Mean-field Beta belief, coverage floor, then expected-information-gain selection.
- Binary choice, confidence in `[0.5, 1.0]`, and abstention.
- Posterior reconstruction with object/relation entropy and separate scores.
- Interview start/submit/summary/list API and local profile summary.
- Interview UI, profile card, and Studio entry point.
- Deterministic policy simulation and honest validation/claims documentation.

**Non-goals**
- Neural decoding, neural reconstruction, dream content, image generation.
- Clinical diagnosis, treatment, cure, imagery-strength, or far-transfer claims.
- A single "imagination score", norms, leaderboards, or cross-person comparison.
- Participant recruitment or data collection.

**Constraints**
- No new runtime dependency; local-only; no external calls.
- No execution or local install during this session; static verification only.
- Preserve existing Studio/P1 behavior and claim ceiling.

**Acceptance**
- Start returns a probe without the hidden answer or target flag.
- Submit is idempotent, rejects a stale scene, and returns the next probe or reconstruction.
- Abstention is excluded from Brier and included in coverage.
- Profile exposes five dimensions, error signature, and epistemic summary; no composite.
- Capability envelope keeps neural/clinical/image-generation boundaries.
- Tests and docs are present; runtime verification remains explicitly pending.

---

## Historical brief — Merge Gate B.1: Runtime Completion and Evidence Hardening

---

## Goal

Close all persistence, replay, export, outbox, manifest, API, Playwright, and CI gaps
identified during Merge Gate B audit, producing a fully hardened synthetic-only experiment
runtime on `research/scientific-platform`.

## Why This Matters

Merge Gate B established the core runtime architecture but left critical gaps: run state was
ephemeral (in-memory dict), outbox table was unpopulated, manifests were never created,
export lacked atomicity and validation, and Playwright tests only checked page loads.
Gate B.1 closes these gaps to produce a runtime that can serve as the foundation for
human-participant studies (after further validation work).

## Scope

- B1-1: Persistent run lifecycle with idempotent commands (v004 migration, RunService)
- B1-2: Injectable pipeline adapters (SignalProvider, FeatureProcessor, etc.)
- B1-3: Transactional outbox pattern (PersistentOutboxWriter, OutboxDispatcher)
- B1-4: Session manifest creation and completion sealing
- B1-5: Canonical normalization (recursive normalize()) and replay-from-manifest
- B1-6: Atomic export service with validator (checksums, data classification)
- B1-7: Orchestrator correctness (no INSERT OR REPLACE, typed errors, manifest integration)
- B1-8: API semantics (sessions, failures, export validation endpoints)
- B1-9: Full Playwright E2E workflow (create → poll → verify)
- B1-10: CI jobs (backend-runtime, playwright, docker-smoke)
- B1-11: Documentation and final verification

## Non-Goals

- Human participant readiness
- Real EEG/LSL integration
- Statistical fitting or analysis
- Authentication or user tracking
- Publication-ready scientific claims

## Starting HEAD

`67802f3` on `research/scientific-platform`

## Results

- **384 backend tests** passing (core + research markers)
- **0 ruff errors**
- **Frontend build clean** (18 routes)
- **7 new backend modules**: run_service, pipeline_adapters, outbox, manifest,
  export_service, v004 migration, pipeline_adapters
- **7 new test files**: test_run_service, test_outbox, test_manifest,
  test_export_service (plus updates to existing test files)
- **11 commits** on `research/scientific-platform`
- B9: Playwright E2E, Docker smoke, regression coverage
- B10: Documentation reconciliation

## Non-Goals

- Human data collection
- Real EEG acquisition (LSL, MNE, BrainFlow)
- Objective behavioral tasks (binocular rivalry, psychophysics)
- Statistical model fitting (LMM execution)
- Publication claims
- Authentication infrastructure
- Cloud services or telemetry
- Generative AI
- Clinical claims
- Mind-reading or dream-decoding language

## Constraints

- [x] No prohibited scientific claims
- [x] No raw EEG/neural data sent to external APIs
- [x] No hardcoded secrets
- [x] No bypassing safety monitors
- [x] Follow existing code conventions
- [x] Small, focused diffs
- [x] Do not modify V8–V44 product/demo behavior
- [x] All synthetic records clearly classified

## Starting HEAD

`6bcd39b050f1cbd06f5f4a4115abda9372efbb28`

## Actual Starting HEAD (this session)

`ce40448` (continuation from prior Merge Gate B session)

## Commit Sequence

1. fix(research): close Merge Gate A integrity gaps
2. feat(storage): add persistent synthetic runtime schema
3. feat(runtime): add persistent session and trial state machines
4. feat(runtime): implement transport-independent research runtime
5. feat(runtime): unify adaptive fixed and yoked policy contracts
6. feat(runtime): add frozen yoked trajectory libraries
7. feat(runtime): add synthetic study orchestration and export
8. feat(runtime): add deterministic replay validation
9. feat(research-ui): add synthetic runtime operator workflow
10. test(runtime): add synthetic E2E and release smoke coverage
11. docs: document persistent synthetic runtime boundaries

---

*Created: 2026-07-10*
