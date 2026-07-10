# Roadmap

## Current State (0.5.0-research)

- Local FastAPI/Next.js app with WebSocket closed-loop pipeline.
- Simulated EEG-like features (deterministic, not biological data).
- PID/IQI proxy metrics (hand-tuned, unvalidated).
- Dream Corridor 3D feedback scene.
- Replay, reports, safety monitor.
- Signal provider abstraction (simulated, manual, replay, LSL gated).
- Product/demo stack with guided sessions, skill tree, protocol studio, benchmarks.

## Research Platform Pivot

### Phase 0 — Repository Truth (current)

- Reconcile versions and documentation.
- Fix CI gaps, remove dead code.
- Add frontend typecheck.

### Phase 1 — Scientific Protocol and Governance

- Study-mode separation (demo vs. pilot vs. approved study).
- Consent and ethics gating.
- Randomization and counterbalancing engine.
- Instrument registry (VVIQ-2 metadata, Likert scales).
- Research protocol schema.

### Phase 2 — Research Experiment Engine

- Condition assignment (adaptive, fixed-feedback, yoked/sham).
- Trial scheduler with timing.
- Stimulus registry with content hashing.
- Trial-level data capture and provenance.
- Behavioral imagery-priming task.

### Phase 3 — Statistical Framework

- Power analysis tooling.
- Synthetic data generator.
- Preregistered LMM analysis pipeline.
- IQI/PID validation analysis.

### Phase 4 — Real Biosignal Acquisition (optional for initial study)

- Robust LSL provider with ring buffer.
- Proper spectral feature extraction.
- Marker synchronization.
- Offline MNE preprocessing.

### Phase 5 — Multimodal Evaluation (requires real data)

- Self-report, behavioral, EEG baselines.
- Incremental validity analysis.
- Group-aware evaluation.

### Phase 6 — Research Frontend

- Consent flow, operator dashboard.
- Behavioral task component.
- Condition blinding safeguards.
- Frontend test suite (Vitest + Playwright).

### Phase 7 — Publication Package

- Preregistration document.
- Reproducibility package.
- Synthetic dataset and analysis scripts.
- Software paper documentation.

## Scientific Non-Negotiables

- Simulated EEG is never experimental evidence.
- IQI/PID are exploratory proxies, not validated outcomes.
- No human data collection without ethics approval metadata.
- No claims of mind reading, dream decoding, or clinical neurofeedback.

V3 must not claim mind reading or dream decoding.
