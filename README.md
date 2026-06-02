# IMAGINA

**A local-first platform for structured mental imagery training, protocol benchmarking, and closed-loop neuroadaptive UX research.**

IMAGINA is a personal exploratory system that enables users to define structured imagery protocols, run guided self-report training sessions, visualize adaptive symbolic scene feedback, track skill progression across nine imagery dimensions, benchmark protocols under deterministic closed-loop evaluation, experiment with tunable adaptive policy profiles, and export reproducible safe benchmark packs — entirely locally, without cloud services, telemetry, or neural data collection.

---

## What IMAGINA Is

IMAGINA addresses a gap in mental imagery research tooling: there is no standardized, local-first, safety-bounded platform for designing, running, benchmarking, and exporting structured imagery training protocols.

IMAGINA provides:

- A **protocol studio** with 8 built-in standardized protocols and a custom protocol designer
- A **guided session runtime** with 10-phase imagery sessions, micro-check-ins, and live self-report proxy metrics
- A **30-task imagery battery** across 10 categories (vividness, motion, multisensory, meta-control, etc.)
- A **9-dimension cognitive phenotype engine** that builds personal imagery profiles from task performance
- A **symbolic scene simulator** that renders adaptive visual feedback from self-report parameters
- A **longitudinal skill tree** with 5 unlock levels and 12 mastery milestones per dimension
- A **closed-loop evaluation benchmark** with 6 determinisitic scenarios and Grade-A scorecard generation
- A **benchmark Scenario SDK** for external JSON scenario validation, import/export, and custom suite building
- An **adaptive policy lab** with 6 built-in tunable policy profiles, matrix comparison, and leaderboard ranking
- A **safe export standard** that guarantees no raw EEG, no raw notes, and no forbidden claims in any artifact
- An **optional biosignal engineering sandbox** with simulated EEG, LSL/BrainFlow adapters, and signal quality monitoring

---

## What IMAGINA Is NOT

IMAGINA makes **no** clinical, diagnostic, therapeutic, BCI, neurofeedback validation, mind-reading, dream decoding, or neural decoding claims. It is not validated neurofeedback. It is not medical software. It is not a brain-computer interface. Every metric is a self-report proxy estimate. Every scene visualization is a symbolic training aid. Every biosignal summary is an engineering diagnostic. Every export enforces `raw_eeg_included = false`.

---

## Quick Start

```bash
# One-command demo experience
cd backend && python3 -m app.cli.imagina_demo full

# Start the frontend
cd frontend && npm run dev
```

Then open `http://localhost:3000/imagina/showcase` for the reviewer-ready project overview, or `http://localhost:3000/imagina/live` for the live neuroadaptive control room and benchmark lab.

```bash
# Docker (alternative)
docker compose -f docker-compose.release.yml up --build
docker compose -f docker-compose.release.yml run --rm imagina-demo-seed
```

---

## Architecture

### System Layers

IMAGINA is organized into eight modular layers, each with clearly defined responsibilities and safety boundaries:

```
┌─────────────────────────────────────────────────────────┐
│  REVIEWER INTERFACE                                     │
│  /imagina/live  ·  /imagina/showcase  ·  /imagina      │
├─────────────────────────────────────────────────────────┤
│  FRONTEND PANELS (40+)                                  │
│  Guided Sessions · Scene Renderer · Skill Tree          │
│  Benchmark Studio · Policy Lab · Live Control Room      │
├─────────────────────────────────────────────────────────┤
│  REST API (~100 endpoints)                              │
│  Calibration · Protocols · Tasks · Biosignals           │
│  Fusion · Scene Simulator · Benchmark SDK · Policy Lab  │
├─────────────────────────────────────────────────────────┤
│  CORE ENGINES                                           │
│  Guided Session Runtime · Self-Report IQI/PID Proxies   │
│  Adaptive Feedback Policy · Scene Simulator             │
│  Skill Tree · Protocol Studio · Adaptive Training       │
├─────────────────────────────────────────────────────────┤
│  BIOSIGNAL SANDBOX (Optional, BCI-Adjacent Only)        │
│  Simulated/LSL/BrainFlow Sources · Signal Quality       │
│  Marker Sync · Realtime Monitoring · Derived Feeds      │
├─────────────────────────────────────────────────────────┤
│  MULTIMODAL FUSION                                      │
│  Observation Builder · Adaptive State Estimator         │
│  Neuroadaptive Policy Engine (Preview-Only)             │
├─────────────────────────────────────────────────────────┤
│  BENCHMARK & EVALUATION                                 │
│  Closed-Loop Scenarios · Policy Matrix · Leaderboard    │
│  Scenario SDK · Custom Suites · UX Scorecard            │
├─────────────────────────────────────────────────────────┤
│  EXPORT LAYER                                           │
│  Safe Benchmark Packs · Protocol Exports                │
│  Reproducibility Manifests · Submission Packs           │
│  Guarantee: raw_eeg_included = false                    │
├─────────────────────────────────────────────────────────┤
│  PERSISTENCE (Local-First)                              │
│  JSON/JSONL · No Cloud · No Telemetry · No Accounts     │
└─────────────────────────────────────────────────────────┘
```

### Module Map

| Version Range | Module | Capability |
|--------------|--------|------------|
| V8-V12 | Core Infrastructure | Session lifecycle, analytics, IQI/PID metrics, safety monitor, curriculum, event store |
| V13 | PID v2 Calibration | 8 reference tasks, perception-imagination distance metric |
| V14-V15 | Adaptive Training | PID-driven 7-day plan generation, day-by-day execution, adherence tracking |
| V16-V17 | Optimization & Experiments | Plan response model, N-of-1 controlled experiment engine |
| V18 | Evidence Dashboard | Unified evidence model, quality audit, timeline, research export pack |
| V19 | Task Battery & Phenotype | 30 tasks across 10 categories, 9-dimension cognitive phenotype builder |
| V20 | Guided Session Runtime | 10-phase guided sessions, micro-check-ins, live IQI/PID proxies, adaptive feedback |
| V21 | Skill Tree & Mastery | 5-level skill tree per dimension, 12 mastery milestones, plateau detection |
| V22 | Scene Simulator | 11 symbolic scene templates, adaptive visualization, session replay |
| V23 | Protocol Studio | 8 built-in protocols, benchmark engine, protocol comparison |
| V24 | External Protocol SDK | External JSON schema, validation, import/export, reproducibility manifests |
| V25-V27 | Release & Reliability | Public showcase, Docker release profile, CI/E2E reliability pack, smoke tests |
| V28-V29 | Biosignal Sandbox | Simulated/LSL/BrainFlow sources, signal quality, realtime monitoring |
| V30-V31 | Fusion & Live Events | Multimodal fusion, adaptive state estimator, neuroadaptive policy, live event bus |
| V32-V34 | Live Control Room | Reviewer-facing dashboard, closed-loop scene adaptation, visible scene dynamics |
| V35-V36 | Benchmark Scorecard | Closed-loop evaluation, Grade-A scorecard, evidence-based metrics |
| V37-V39 | Scenario SDK Studio | External scenario import/export, custom suites, scenario gallery, frontend studio |
| V40-V42 | Adaptive Policy Lab | 6 built-in policy profiles, policy matrix, leaderboard, functional frontend wiring |

---

## Key Innovations

| Innovation | Description |
|-----------|-------------|
| **Self-Report IQI/PID Proxy Metrics** | Transparent weighted formulas from vividness, stability, confidence, effort, fatigue. Not neural measurement. |
| **Symbolic Scene Visualization** | Scene clarity, fog, detail, motion, and stability adapt based on self-report proxies and policy previews. Not mental image reconstruction. |
| **Deterministic Closed-Loop Benchmarks** | 6 scenarios evaluate whether the adaptive pipeline responds correctly to specific check-in patterns. Software behavior benchmark, not clinical validation. |
| **Policy Experimentation Lab** | 6 built-in tunable policy profiles (balanced, clarity-first, fatigue-protective, signal-strict, recovery-first, conservative-safe). Matrix comparison and leaderboard ranking. |
| **Reproducibility Manifests** | Every benchmark run produces a manifest with protocol hashes, task registry hashes, scene registry hashes, and exact CLI reproduction commands. |
| **Safe Export Standard** | All exports (benchmark packs, protocol exports, submission packs, biosignal packs) are validated to exclude raw EEG, raw notes, and forbidden claims. |
| **Optional Biosignal Sandbox** | Simulated EEG, LSL, and BrainFlow/OpenBCI adapters provide BCI-adjacent engineering infrastructure without making BCI or neurofeedback claims. |
| **Local-First Architecture** | All data is stored locally as JSON/JSONL. No cloud accounts, no telemetry, no external APIs. |

---

## Safety Boundaries

Every IMAGINA artifact — protocol, session, benchmark, export, report, scene, policy — includes:

```
analysis_mode           = "personal_exploratory_training"
not_clinical            = true
not_diagnostic          = true
not_mind_reading        = true
not_bci_claim           = true
not_neurofeedback_claim = true
production_valid        = false
raw_eeg_export_default  = false
```

The system performs deterministic validation for forbidden terms (`clinical`, `diagnosis`, `therapy`, `treatment`, `BCI-ready`, `mind-reading`, `dream decoding`, `validated neurofeedback`, `neural reconstruction`, `medical`, `patient`, `disorder`) in all externally importable artifacts (protocols, benchmark scenarios, policy profiles). Violations trigger validation failures with `safe_to_import = false`.

---

## SDK CLI

```bash
# Protocol SDK
python3 -m app.cli.imagina_sdk schema                     # View external protocol schema
python3 -m app.cli.imagina_sdk example                    # Generate example protocol
python3 -m app.cli.imagina_sdk validate --file <path>     # Validate protocol against schema
python3 -m app.cli.imagina_sdk import --user <id> --file <path>  # Import protocol
python3 -m app.cli.imagina_sdk export-protocol --protocol-id <id>  # Export protocol

# Benchmark SDK
python3 -m app.cli.imagina_sdk demo                       # Seed demo user with full data
python3 -m app.cli.imagina_sdk manifest --user <id> [--run-id <id>]  # Build reproducibility manifest
python3 -m app.cli.imagina_sdk benchmark-export --user <id> [--run-id <id>]  # Export benchmark pack

# Release CLI
python3 -m app.cli.imagina_release all                    # Generate all release artifacts
python3 -m app.cli.imagina_release verify                 # Run verification suite

# Demo CLI
python3 -m app.cli.imagina_demo seed                      # Seed demo data
python3 -m app.cli.imagina_demo full                      # Seed + showcase + release manifest
python3 -m app.cli.imagina_demo verify                    # Run key regression tests
```

---

## Running Tests

```bash
# Full project verification (8 checks: ruff, pytest, frontend build, lint, Docker)
bash scripts/verify.sh

# Backend integration tests (30+)
cd backend
python3 -m app.cli.imagina_v24_sdk_standard_test          # Protocol SDK roundtrip
python3 -m app.cli.imagina_v25_public_showcase_test       # Public showcase integrity
python3 -m app.cli.imagina_v35_closed_loop_benchmark_test # Closed-loop benchmark suite
python3 -m app.cli.imagina_v36_closed_loop_frontend_scorecard_test  # Scorecard + metrics
python3 -m app.cli.imagina_v42_policy_lab_functional_wiring_test   # Policy lab UI verification

# Run a single benchmark scenario
python3 -m app.cli.imagina_sdk validate --file docs/examples/example_protocol.json
```

---

## Frontend Routes

| Route | Purpose |
|-------|---------|
| `/imagina` | Main imagery training dashboard |
| `/imagina/live` | Live neuroadaptive control room, benchmark studio, policy lab |
| `/imagina/showcase` | Reviewer-ready project overview, architecture, demo flow, safety boundaries |
| `/imagina/session` | Full guided imagery session flow |
| `/imagina/reports/[sessionId]` | Per-session report with metrics, scene summary, biosignal data |
| `/imagina/replay` | Deterministic session replay |
| `/imagina/science` | Scientific notes and claims policy |
| `/imagina/profile` | Local user profile |
| `/imagina/experiments` | Experiment protocol definitions |
| `/research` | EEG validation artifacts (forensic layer, not IMAGINA core) |

---

## Project Structure

```
imagina/
├── backend/
│   └── app/
│       ├── core/
│       │   ├── imagery/       # V19-V23: Task battery, guided sessions, skill tree, scene,
│       │   │                   #          protocol studio, SDK, showcase, release health
│       │   ├── adaptive/      # V14-V17: PID training, adaptive plans, N-of-1 experiments
│       │   ├── biosignals/    # V28-V42: Simulated/LSL/BrainFlow, fusion, live events,
│       │   │                   #          scene dynamics, closed-loop benchmarks, policy lab
│       │   ├── evidence/      # V18: Evidence model, quality audit, export packs
│       │   ├── protocols/     # V10-V12: Personal intelligence, protocol engine, experiment design
│       │   ├── calibration/   # V13: PID v2 calibration
│       │   └── sessions/      # V8-V9: Session manager, event store
│       ├── api/imagina/       # ~100 REST endpoints
│       ├── cli/               # 30+ integration tests, SDK, demo, release, CI CLI tools
│       └── research/          # Preserved EEG validation forensics (OpenMIIR, PhysioNet)
├── frontend/
│   ├── app/imagina/           # /imagina, /imagina/live, /imagina/showcase
│   ├── components/imagina/    # 40+ panels: tasks, sessions, scene, skill tree, benchmarks
│   ├── hooks/                 # useLiveNeuroadaptiveDemo, useAdaptivePolicyLab
│   └── lib/                   # API client, WebSocket, feedback mapping
├── docs/                      # Architecture, metrics, claims, V14-V42 docs, demo scripts, whitepaper
├── scripts/                   # verify.sh, Docker smoke, AI context tools
├── docker-compose.release.yml # 3-service Docker profile (backend, frontend, demo-seed)
└── README.md
```

---

## Limitations

| Limitation | Detail |
|-----------|--------|
| Self-Report Proxy Metrics | IQI, PID, capability scores, and all dimension profiles are subjective self-report estimates — not neural or physiological measurements. |
| N-of-1 Experiments | Personal exploratory only — not randomized controlled trials. Results apply to the individual user. |
| No EEG Validation | Biosignal features are simulated or optionally streamed. The system does not validate or claim EEG-based classification, decoding, or neurofeedback. |
| Locally Defined Protocols | Protocols are stored and run locally. There is no shared cloud protocol registry. |
| Frontend Server Required | The Next.js frontend requires a local development server. Static deployment is not currently supported. |
| Hardware Optional | LSL/BrainFlow adapters require optional dependencies (`pylsl`, `brainflow`) and compatible hardware. All tests pass without hardware. |

---

## Future Directions

- **Real EEG/LSL sensor integration** — gated behind metadata preflight validation and raw-data exclusion from public exports
- **Multi-user local profiles** — independent training histories, phenotypes, and benchmarks on a single machine
- **PDF/HTML export** — formatted benchmark reports, scorecards, and protocol documentation
- **Multi-protocol meta-analysis** — cross-protocol trend analysis and statistical comparisons
- **Public protocol registry** — optional opt-in sharing of anonymized protocol definitions

---

*IMAGINA is a local-first personal exploratory mental imagery training and research platform. It is non-clinical, non-diagnostic, non-BCI, not neurofeedback validation, not mind-reading, and not mental image reconstruction.*
