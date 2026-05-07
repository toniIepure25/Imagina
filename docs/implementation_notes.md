# Implementation Notes

## V1 Design Decisions

1. **Simulated EEG:** V1 uses a seeded pseudo-random signal generator instead of real EEG hardware. This allows complete demo flow and deterministic replay without hardware dependencies.

2. **Rule-based state estimator:** Instead of a learned model, V1 uses weighted combinations with exponential smoothing. This is transparent and debuggable.

3. **SQLite event store:** Lightweight, local-first, zero-config. Every major computation is stored as an EventEnvelope for replay and reporting.

4. **No external APIs:** No LLMs, no cloud services, no paid assets. Everything runs locally.

5. **Deterministic replay:** Seeded RNG in SignalSimulator means identical seeds produce identical sessions, enabling reproducible demos and testing.

## Extension Points for V2

- `FeatureEngine.process()` — replace pass-through with real MNE/bandpower extraction
- `SignalSimulator` — replace with LSL stream reader for Muse/OpenBCI
- `StateEstimator` — train a small model on labeled data
- `FeedbackPolicyEngine` — optimize parameters via reinforcement learning
- Add audio guidance module alongside visual feedback
- Add post-session generative visual summaries

## Known V1 Limitations

- No real neural data
- Self-report is subjective and sparse
- Metric weights are hand-tuned
- No cross-user normalization
- 3D scene is procedural/minimal (no high-fidelity assets)
- No persistent user model across sessions
