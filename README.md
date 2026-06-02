# IMAGINA

**Local-first mental imagery protocol lab and benchmark SDK.**

IMAGINA is a personal exploratory mental imagery training and research platform. It lets users define structured imagery protocols, run guided self-report sessions, visualize symbolic scene feedback from self-report proxies, track skill progression across nine imagery dimensions, benchmark protocols through deterministic closed-loop evaluation, experiment with adaptive policy profiles, and export reproducible safe benchmark packs — all locally, without cloud services, telemetry, or neural data collection.

---

## Quick Start

### One-Command Demo

```bash
cd backend && python3 -m app.cli.imagina_demo full
cd frontend && npm run dev
```

Open `http://localhost:3000/imagina/showcase` for the reviewer-ready overview.

### Docker

```bash
docker compose -f docker-compose.release.yml up --build
docker compose -f docker-compose.release.yml run --rm imagina-demo-seed
```

---

## Architecture

IMAGINA is organized into modular layers:

| Layer | Purpose |
|-------|---------|
| **Frontend Panels** | Next.js + TypeScript + Tailwind — live control room, scene renderer, benchmark studio |
| **API Routes** | FastAPI REST endpoints (~100) — calibration, protocols, tasks, biosignals, fusion, SDK |
| **Core Engines** | Guided session runtime, self-report IQI/PID proxies, adaptive feedback, scene simulator, skill tree, protocol studio |
| **Biosignal Sandbox** | Optional simulated/LSL/BrainFlow biosignal sources — signal quality, markering, realtime monitoring (BCI-adjacent, not BCI) |
| **Multimodal Fusion** | Observation, adaptive state estimation, neuroadaptive policy previews (no auto-intervention) |
| **Protocol SDK** | External protocol schema, validation, import/export, reproducibility manifests |
| **Benchmark SDK** | Deterministic closed-loop evaluation, scenario runner, metrics, scorecard, leaderboard |
| **Export Layer** | Safe benchmark packs, protocol exports, submission packs — no raw EEG, no raw notes |
| **Safety Boundary** | Every artifact enforces non-clinical, non-diagnostic, non-BCI, non-mind-reading boundaries |

### Module Map (V13-V42)

```
V13-V19: PID Calibration • Adaptive Plans • N-of-1 Experiments • Evidence Dashboard
         • Task Battery (30 tasks, 10 categories) • Cognitive Phenotype Engine (9 dimensions)

V20-V23: Guided Session Runtime (10 phases, micro check-ins, IQI/PID proxies)
         • Skill Tree (5 levels, mastery milestones) • Scene Simulator (11 templates, replay)
         • Protocol Studio (8 built-in protocols, benchmark engine)

V24-V27: External Protocol SDK • Public Showcase • Release Candidate Hardening
         • Dockerized Release • CI/E2E Reliability

V28-V34: Biosignal Adapter (simulated/LSL/BrainFlow) • Realtime Dashboard
         • Multimodal Fusion • Live Control Room • Closed-Loop Scene Adaptation
         • Visible Scene Dynamics Engine

V35-V42: Closed-Loop Benchmark (Grade-A scorecard) • Benchmark Scenario SDK
         • Scenario Studio • Adaptive Policy Lab (6 built-in profiles, matrix, leaderboard)
```

---

## Key Innovations

- **Self-report IQI/PID proxy metrics** — transparent formulas, no neural measurement claims
- **Symbolic scene visualization** — adaptive visual feedback from self-report parameters, not mental image reconstruction
- **Deterministic closed-loop benchmarks** — evaluate software behavior, not clinical outcomes
- **Policy experimentation lab** — built-in profiles, matrix comparison, leaderboard ranking
- **Reproducibility manifests** — protocol hashes, task registry hashes, exact CLI commands
- **Safe export standard** — no raw EEG, no raw notes, no forbidden claims in any export

---

## Safety Boundaries

IMAGINA makes **no** clinical, diagnostic, therapeutic, BCI, neurofeedback validation, mind-reading, dream decoding, or neural decoding claims. Every artifact includes:

- `not_clinical = true`
- `not_diagnostic = true`
- `not_bci_claim = true`
- `not_neurofeedback_claim = true`
- `raw_eeg_export_default = false`

All metrics are self-report proxy estimates. The symbolic scene simulator is a visualization aid. The biosignal sandbox is optional BCI-adjacent infrastructure only.

---

## Running Tests

```bash
# Full project verification
bash scripts/verify.sh

# Backend integration tests
cd backend
python3 -m app.cli.imagina_v24_sdk_standard_test
python3 -m app.cli.imagina_v25_public_showcase_test
python3 -m app.cli.imagina_v42_policy_lab_functional_wiring_test

# Closed-loop benchmark suite
cd backend
python3 -m app.cli.imagina_v35_closed_loop_benchmark_test
python3 -m app.cli.imagina_v36_closed_loop_frontend_scorecard_test
```

---

## SDK CLI

```bash
# Protocol SDK
python3 -m app.cli.imagina_sdk schema
python3 -m app.cli.imagina_sdk validate --file protocol.json
python3 -m app.cli.imagina_sdk import --user demo_user --file protocol.json

# Benchmark SDK
python3 -m app.cli.imagina_sdk demo
python3 -m app.cli.imagina_sdk benchmark-export --user demo_user --run-id <id>

# Release CLI
python3 -m app.cli.imagina_release all
python3 -m app.cli.imagina_release verify

# Demo CLI
python3 -m app.cli.imagina_demo full
```

---

## Frontend Routes

| Route | Purpose |
|-------|---------|
| `/imagina` | Main training dashboard |
| `/imagina/live` | Live neuroadaptive control room + benchmark lab |
| `/imagina/showcase` | Reviewer-ready project overview |

---

## Project Structure

```
backend/
  app/
    core/
      imagery/          Task battery, guided sessions, skill tree, protocol studio, SDK, showcase
      adaptive/          PID calibration, plan optimization, N-of-1 experiments
      biosignals/        Simulated/LSL/BrainFlow sources, fusion, live events, policy lab, benchmarks
      evidence/          Evidence model, quality audit, export packs
      protocols/         Personal intelligence, protocol engine
    api/imagina/         ~100 REST endpoints
    cli/                 SDK, demo, release, local CI, ~30 integration tests
frontend/
  app/imagina/live/      Live control room + benchmark studio
  app/imagina/showcase/  Reviewer showcase
  components/imagina/    40+ panels: tasks, guided sessions, scene, skill tree, protocols, benchmarks
  hooks/                 useLiveNeuroadaptiveDemo, useAdaptivePolicyLab
  lib/                   API client, WebSocket, feedback mapping
docs/                    Architecture, API contracts, demo scripts, whitepaper, safety boundaries
scripts/                 verify.sh, Docker smoke, AI context
```

---

## Limitations

- All metrics are self-report proxy estimates — not neural measurements
- N-of-1 experiments are personal exploratory — not randomized controlled trials
- No EEG/neural data validation — biosignal features are simulated or optionally streamed
- Protocols are locally defined — no shared cloud registry
- Frontend requires local server — no static deployment

---

## Future Roadmap

- Real EEG/LSL sensor integration (gated behind metadata preflight validation)
- Multi-user local profiles
- PDF/HTML benchmark export
- Multi-protocol meta-analysis
- Public protocol registry

---

*IMAGINA is a personal exploratory mental imagery training and research platform. It is non-clinical, non-diagnostic, non-BCI, not neurofeedback validation, not mind-reading, and not mental image reconstruction.*
