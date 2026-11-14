# TASK_BRIEF.md

## Current task — Phase 0I: identification-first adjudication and policy layer (2026-10-31)

**Goal:** make the CRT package top-tier by fixing the full-model likelihood bug, auditing sources,
adding formal pairwise identifiability and full-joint-model design screening, a policy-choice layer,
an optional NumPyro backend, and Stage 0I registry gates. Computational and documentation only.

**Scope**
- `analysis/crt/full_model.py`, `identifiability.py`, `policy_model.py`, `inference.py`,
  `design_optimization.py`.
- `backend/app/cli/crt_stage0i.py`; `backend/app/tests/test_crt_stage0i.py`.
- `science/protocols/crt-v1.yaml` v0.7.0; Stage 0I artifacts and seven gates.
- `docs/research/CRT_SOURCE_AUDIT.md`, `CRT_STAGE0I_PROTOCOL.md`.

**Non-goals**
- No human data, pilot, IRB, recruitment, clinical sample, API/DB/UI, or neural data.
- No claim upgrade; no “first”, “revolutionary”, or priority language.
- Quick screening is not target-scale SBC; no threshold tuning is authorized.

**Acceptance**
- Full-model prediction double count is fixed and regression-tested.
- Source audit and Stage 0I artifacts exist with honest decisions.
- Protocol audit, focused tests, ruff, ledger, docs links, and `verify.py --quick` pass.
- Human collection remains blocked.

**Status:** implemented and verified at the code-path/governance level. Source audit PASS; inference
backend BLOCKED (NumPyro absent); quick identifiability, design, policy calibration, policy recovery,
full-model Laplace SBC/recovery, target projection, and target readout design are REVIEW/LIMITED;
readiness is BLOCKED. The target readout screen runs at N=432/T=240 but fails to recover M7, so the
next step is a full-model design/SBC revision under NUTS, not recruitment.

---

## Previous task — Phase 0H: rival-account models, design optimization, and adversarial package (2026-10-31)

**Goal:** make CRT a theory-discriminating program by implementing M6/M7, adding an offline
model-discrimination design screen, a full joint latent-source model, pre-specified SBC/recovery gates,
and an adversarial/Registered Report package. Computational and documentation only.

**Scope**
- `analysis/crt/trial_model.py` (M6/M7), `analysis/crt/design_optimization.py`,
  `analysis/crt/full_model.py`.
- `backend/app/cli/crt_stage0h.py`; `backend/app/tests/test_crt_stage0h.py`.
- `docs/program/CRT_STAGE0H_PROTOCOL.md`, `CRT_ADVERSARIAL_COLLABORATION.md`,
  `CRT_REGISTERED_REPORT_PACKAGE.md`, `CRT_NEURAL_EXTENSION.md`.
- `science/protocols/crt-v1.yaml` v0.6.0; registry artifacts/gates; Stage 0H results.

**Non-goals**
- No human data, pilot, IRB, recruitment, clinical sample, API/DB/UI, or neural data.
- No claim upgrade; no "first"/"revolutionary"/priority language.
- The full joint model observes test choice; it is not the policy POMDP.

**Acceptance**
- M0–M7 model space and M6/M7 covariates are explicit and tested.
- Design optimization, full-model SBC, and recovery artifacts are generated with honest decisions.
- Protocol audit, focused tests, ledger, ruff, docs links, and `verify.py --quick` pass.
- Human collection remains blocked.

**Status:** implemented and verified. Model space passes; design optimization is `REVIEW` (0.625 minimum
pairwise); full-model screening SBC/recovery are `REVIEW`; readiness is `BLOCKED`. `verify.py --quick`
passes (4 passed, 2 skipped; backend 684.9s). The result is a design diagnosis, not human evidence.

---

## Previous task — Phase 0G: CRT theory adjudication, trial-level model, and calibration planning (2026-10-31)

**Goal:** make CRT a theory-adjudicating registered program by adding a formal three-account test,
a trial-level hierarchical readout model with SBC/recovery, an N=480/d=0.20 design, and a calibration
protocol. Computational and documentation only.

**Scope**
- `docs/research/CRT_STAGE0G_SCOPING_PROTOCOL.md`; `docs/program/CRT_THEORY_ADJUDICATION.md`;
  `docs/program/CRT_STAGE0G_PROTOCOL.md`; `docs/program/CRT_CALIBRATION_PROTOCOL.md`.
- `analysis/crt/trial_model.py` and `backend/app/tests/test_crt_trial_model.py`.
- `science/protocols/crt-v1.yaml` version 0.5.0; `backend/app/research/crt/protocol.py` Stage 0G
  design fields; preregistration/analysis-plan/spec H1 SESOI updates.
- New Stage 0G artifacts; registry gates and docs.

**Non-goals**
- No human calibration, pilot, confirmatory study, IRB, recruitment, or clinical sample.
- No API, DB, UI, neural data, training RCT, or claim upgrade.
- No “first”, “revolutionary”, or priority language.
- The trial-level readout model is not the full CRT POMDP; that remains a registration blocker.

**Acceptance**
- Scoping protocol and theory table exist with exact query counts and non-systematic caveat.
- Trial-level SBC and recovery artifacts are generated with scope strings and explicit limitations.
- Protocol audit accepts N=480/d=0.20/calibration N=80; preregistration and analysis plan match.
- Focused tests, ruff, ledger check, docs links, and `python scripts/verify.py --quick` pass.
- No claim status increases; human collection remains blocked.

**Status:** implemented as a computational/documentation slice. Trial-level readout SBC passes (target
`delta_d` coverage 0.955). Recovery is a post hoc M0/M2/M4 conditional pass (0.90) after the full-set
runs failed (0.375 prior-averaged; 0.733 effect-conditioned); the gate is `LIMITED`. Calibration is
protocol-only. Registration remains `BLOCKED`; full joint CRT POMDP SBC, pre-specified full-set
recovery, calibration, model-based power, independent review, and ethics remain required.

---

## Previous task — Phase 0F: CRT protocol integrity, design power, and distortion assay (2026-10-30)

**Goal:** make the CRT registration decision-complete and falsifiable by fixing trial arithmetic and
contrast confounding, quantifying design power, validating a false-seen distortion assay, adding a
conditional hierarchical screening and endpoint-level full SBC/model recovery, and blocking
registration until the remaining statistical work is done. Simulation and documentation only.

**Scope**
- `science/protocols/crt-v1.yaml` version 0.4.0 and `backend/app/research/crt/protocol.py`.
- `backend/app/research/crt/design.py` design-power grid; `distortion.py` assay; `hierarchical.py`
  screening.
- `analysis/crt/hierarchical_sbc.py`: standalone endpoint-level full hierarchical SBC and M0/M2/M3/M4
  recovery.
- `backend/app/cli/crt_stage0f.py`; `app/tests/test_crt_stage0f.py`.
- Canonical artifacts `results/crt/CRT_STAGE0F_*.json`; registry gates.
- Docs: Stage 0F protocol, preregistration, analysis plan, counterfactual spec, literature positioning,
  ADR-073, RISK-059, task brief, session log, status.

**Non-goals**
- No human calibration, pilot, confirmatory study, IRB, recruitment, or clinical sample.
- No API, DB, UI, neural data, training RCT, or claim upgrade.
- No trial-level CRT hierarchical SBC; endpoint-level SBC is complete.
- No “first”, “revolutionary”, or priority language.

**Acceptance**
- `python -m app.cli.crt_stage0f --check` passes protocol integrity.
- Protocol audit passes; design power, distortion, hierarchical screening, endpoint hierarchical SBC,
  and M0/M2/M3/M4 recovery artifacts are regenerated; registration package is `BLOCKED` with explicit
  blockers.
- Focused tests, ruff, ledger check, docs links, and `python scripts/verify.py --quick` pass.
- No claim status increases; human collection remains blocked.

**Status:** implemented; the design-power result is `REVIEW` because N=240 is underpowered for d=0.20.
Endpoint SBC and M0/M2/M3/M4 recovery pass; registration is blocked pending design revision and a
trial-level CRT hierarchical SBC.

---

## Previous task — Phase 0E: CRT model repair, counterfactual audit, and psychometrics (2026-10-30)

**Goal:** repair the Stage 0C/0D oracle prediction and prediction/outcome double counting, add a
dual-hypothesis counterfactual prediction assay, run policy competition, add test-facet reliability
and posterior PIT calibration, add conditional SBC/model recovery, regenerate the canonical simulation
artifacts, and downgrade claims that do not survive. Simulation only. No human data, API, DB, UI,
clinical sample, or neural data.

**Scope**
- `backend/app/research/crt/model.py`: belief-based posterior-predictive prediction.
- `backend/app/research/crt/simulate.py`: `prediction_source`, `prediction_format`, `source_update`;
  outcome-only posterior; dual prediction fields; `cost_only` policy.
- New modules: `model_repair.py`, `counterfactual.py`, `policy.py`, `psychometrics.py`, `pit.py`,
  `recovery.py`.
- `backend/app/cli/crt_stage0e.py` and six focused test files.
- Stage 0E artifacts in `results/crt/CRT_STAGE0E_*.json`; new registry gates; downgrade Stage 0D
  specificity gate to `LIMITED` via a superseding belief-based artifact.
- Docs: Stage 0E protocol, model-repair audit, counterfactual specification, evidence update; update
  CRT protocol, preregistration, analysis plan, theory audit, Stage 0D protocol, task brief, session
  log, and risks.

**Non-goals**
- No human calibration, pilot, confirmatory study, IRB, recruitment, or clinical sample.
- No API, database migration, frontend route, neural data, training RCT, or claim upgrade.
- No composite score, diagnosis, imagery-strength claim, neural decoding, or LLM in the loop.
- No "first", "revolutionary", or priority language.

**Acceptance**
- `python -m app.cli.crt_stage0e --check` passes.
- `python -m app.cli.crt_stage0d --check` still passes on the preserved historical oracle path.
- `ANIMUS_P5_CRT_MODEL_REPAIR=PASS`, `_PSYCHOMETRIC=PASS`, `_RECOVERY_BELIEF=PASS`;
  `_SPECIFICITY=LIMITED`, `_COUNTERFACTUAL=LIMITED`, `_POLICY=LIMITED` in the ledger.
- Ruff, focused CRT tests, ledger check, docs links, and `python scripts/verify.py --quick` pass.
- Each Stage 0E artifact is reproducible from the documented CLI command.
- No claim status increases; training and clinical remain `BLOCKED`.

**Status:** implemented; the recovery artifact is generated with
`python -m app.cli.crt_stage0e --write --recovery`; verification recorded in the 2026-10-30 Stage 0E
session-log entry.

---

## Previous task — Phase 0D: CRT theory tournament and design controls (2026-10-30)

**Goal:** implement the approved CRT Stage 0D slice: a theory audit and competing-model signature
analysis, specificity and active-selection controls, test-likelihood calibration design, G-theory
decision study, simulation-only gates, and the documents needed for PI/adversarial review. No human
data, API, migration, UI, clinical sample, or neural data.

**Scope**
- `backend/app/research/crt/theory.py`, `gtheory.py`, `calibration.py`; extend `simulate.py` with
  `prediction_mode` and `selection_mode`.
- `backend/app/cli/crt_stage0d.py` and focused tests.
- Canonical artifacts in `results/crt/CRT_STAGE0D_*.json`; four simulation-only registry gates.
- `science/protocols/crt-v1.yaml` updated with Stage 0D controls, sub-studies, and N=240 targets.
- Theory audit, novelty matrix, model predictions, Stage 0D protocol; update CRT spec, preregistration,
  analysis plan, ADR-070, evidence map.
- N=240 reliability planning target with a power check at true ICC 0.80 / lower bound 0.70.

**Non-goals**
- No human calibration, pilot, or confirmatory study; no IRB, recruitment, or clinical sample.
- No API, database migration, frontend route, neural data, training RCT, or claim upgrade.
- No composite score, diagnosis, imagery-strength claim, neural decoding, or LLM in the loop.
- No "first" or "revolutionary" language.

**Acceptance**
- `python -m app.cli.crt_stage0d --check` passes.
- `ANIMUS_P5_CRT_THEORY`, `_SPECIFICITY`, `_GTHEORY`, and `_CALIBRATION` are `PASS` in the ledger.
- Existing Stage 0C gates retain their status; no claim status changes.
- Ruff, focused tests, ledger check, and `python scripts/verify.py --quick` pass.
- Each Stage 0D artifact is reproducible from the documented CLI command.

**Status:** implemented; verification recorded in the 2026-10-30 session-log entry.

---

## Previous task — Phase 3B: Stage 0B Active Reality Testing (2026-10-29)

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

---

## 2026-10-29 - CRT Stage 0C

**Goal:** implement Counterfactual Reality Testing (CRT) Stage 0C as a simulation/specification
slice, with no human data, API, DB, UI, clinical sample, or neural data.

**Acceptance criteria:**

- [x] Fix the ART default card menu and add a regression test.
- [x] Add `backend/app/research/crt/` with model, design, metrics, simulation, recovery, and power.
- [x] Add deterministic CLIs for simulation, recovery, and power.
- [x] Add `backend/app/tests/test_crt_stage0.py` with 35 tests.
- [x] Add `ANIMUS-CRT-v1`, draft preregistration, draft analysis plan, ADR-069, and evidence-map
      addendum.
- [x] Add CRT claims (UNVALIDATED/BLOCKED), simulation-only gates, and canonical artifacts.
- [x] Regenerate the ledger/status and run the focused verification.

**Non-goals:** human pilot or main study, API, migration, frontend, clinical sample, neural data,
training RCT, claim upgrade, priority claim, or "revolutionary" language.
