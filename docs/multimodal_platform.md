# IMAGINA Multimodal Research Platform

Branch: `product/multimodal-research-platform` (from `b879a23`). Code: `backend/app/multimodal/`,
API `backend/app/api/multimodal.py`, UI `frontend/app/multimodal/` (Research Command Center).

> **Scope.** Engineering is complete for the slice described here. **Nothing has been scientifically validated.** All
> results come from SYNTHETIC generators or REPLAY of synthetic recordings and show only that the software behaves as
> designed. No human data, hardware, or trained model has been validated. IMAGINA does not decode thoughts, dreams, or
> imagery content.

## 1. Gap analysis (state on 2026-10-12, before this work)

| Area | Before | Gap |
|---|---|---|
| Signal providers | `app/signals/` returned EEG-like *FeatureVectors* (simulated, replay, manual, LSL stub/real). `core/biosignals/` (V28–V44) held JSON-file demos, scene dynamics and a self-report "fusion" | No per-modality raw-sample abstraction, no ECG/EDA/resp/fNIRS/MEG/fMRI providers, no clock model |
| EEG processing | `services/eeg_dsp.py` (bandpower), `research/neural/*` (OpenMIIR/C1–C2 pipelines), CLI CSP/FBCSP benchmarks | No reusable window-level pipeline, ICA, Riemannian baseline, or leakage-checked evaluation API |
| fMRI | Extensive NSD-specific pipelines (`research/fmri`, ANIMUS P2) | No generic BIDS/NIfTI reader + GLM |
| Physiology | None | Missing entirely |
| Synchronization | `research/marker_sync.py`, `ring_buffer.py` (single EEG stream) | No multi-stream drift/offset/uncertainty |
| Closed loop | IQI/PID engine, curriculum, safety monitor, feedback policy (single simulated stream) | No explicit controller state machine, shadow mode, authorization gate, stale/disconnect watchdog, or replayable trace |

Existing modules were kept unchanged; the new package reuses `services/safety_monitor.DISSOCIATION_KEYWORDS`,
`services/feedback_policy_engine.PROMPTS`, `schemas/feedback.FeedbackAction`,
`research/statistics/multiplicity.holm_correction` and `research/neural/nested_validation.bootstrap_ci`.
The NeuroVerse export (`scripts/export_for_neuroverse.py`) was not modified.

## 2. Architecture

```
acquisition/  providers (synthetic | replay | device) -> SampleChunk(data, device_ts, local_ts, sample_indices)
sync.py       per-stream clock model (drift, offset, jitter) -> aligned windows + uncertainty + health
processing/   eeg, eeg_decoding, ecg, eda, respiration, fnirs, meg, fmri -> FeatureSet(Feature(value, unit,
              evidence_class, confidence, method, reason))
estimator.py  calibration profile -> ImageryState (10 dimensions, each with evidence class + uncertainty)
fusion.py     early / late / intermediate fusion, modality dropout, ablation, model registry, latency
controller.py state machine + safety gates + policy registry + bounded smoothing + hash-chained trace
corridor.py   Decision -> Dream Corridor FeedbackAction (+ audio, cue fading, probe trials); async variations
training.py   exercises, cue fading, cue-free probes, rest periods, arm allocation
runtime.py    steppable closed-loop session, synthetic responder, recording, replay verification
protocols.py  protocols A-G (runners + design simulations); evaluation.py splits, leakage, stats
storage.py    HDF5 per stream + JSON manifest, pseudonymization, consent, retention, review bundles
```

Controller states: `IDLE -> CALIBRATION -> BASELINE -> ACTIVE_SHADOW | FEEDBACK_RESEARCH`, plus `PAUSED`,
`SAFE_FALLBACK`, `TERMINATED`. Shadow is the default. `FEEDBACK_RESEARCH` with any REAL_SENSOR stream requires a
complete `FeedbackAuthorization` (protocol, ethics approval, supervisor, signal validation, safety review). Safety
gates run before the policy: stale data, disconnection, low quality, unknown/large alignment uncertainty, and low
confidence hold adaptation, escalating to `SAFE_FALLBACK` after 5 ticks. Distress keywords, low reported reality
orientation, discomfort, or sustained fatigue go straight to `SAFE_FALLBACK`; the session time limit terminates.
Policies that declare forbidden objectives (minimizing the perception-imagination distance, maximizing arousal,
reality confusion, dissociation) are rejected.

## 3. Feature status

| Feature | Status |
|---|---|
| 7-modality provider registry, capability discovery, metadata/unit/rate validation | IMPLEMENTED |
| Synthetic providers EEG(1–16 ch)/ECG/EDA/resp/fNIRS with ground truth + fault injection | IMPLEMENTED |
| Offline synthetic fixtures: EDF, SNIRF, FIF (MEG), BIDS/NIfTI (fMRI) | IMPLEMENTED |
| Replay: EDF, SNIRF, FIF, CSV/JSONL+sidecar, IMAGINA-HDF5 | IMPLEMENTED |
| LSL inlet adapter (with `time_correction`) | INTERFACE ONLY (pylsl not installed; untested against a stream) |
| BrainFlow adapter | INTERFACE ONLY (brainflow not installed) |
| ADS1299 transport-independent frame protocol (CRC, sequence loss, µV scaling) | IMPLEMENTED (bench protocol) / HARDWARE REQUIRED |
| Real-time MEG / fMRI | NOT IMPLEMENTED (offline modalities by design) |
| Sync engine: drift/offset/jitter, uncertainty, late/missing samples, markers, health | IMPLEMENTED |
| ECG R-peaks, ectopic handling, HR/RMSSD/SDNN/pNN50, LF/HF gating (≥120 s, ≥90% NN) | IMPLEMENTED; VALIDATION REQUIRED on real ECG |
| EDA tonic/phasic, SCRs, artifacts, event-related SCR, baseline | IMPLEMENTED; VALIDATION REQUIRED |
| Respiration cycles, rate, Ti/Te, regularity, RSA (quality-gated) | IMPLEMENTED; VALIDATION REQUIRED |
| EEG referencing, notch/band-pass, artifact/quality, PSD, Morlet TFR, epoching, ICA (frontal EOG proxy) | IMPLEMENTED |
| ASR | NOT IMPLEMENTED |
| EEG baselines: CSP+LDA, FBCSP, Riemannian tangent space, ShallowNet (PyTorch) | IMPLEMENTED (synthetic only) |
| fNIRS OD → TDDR → mBLL (MNE) with metadata refusal, short-channel regression, HRF GLM | IMPLEMENTED; HARDWARE/DATA REQUIRED |
| MEG FIF import, bad channels, epochs, time-resolved decoding | IMPLEMENTED; source space NOT IMPLEMENTED (needs MRI) |
| fMRI BIDS discovery, TR-aware design, motion/drift nuisance, ROI, GLM, LSA betas | IMPLEMENTED; not scanner neurofeedback |
| Fusion (early/late/intermediate), missing modalities, modality dropout, ablation, registry, latency | IMPLEMENTED; VALIDATION REQUIRED (synthetic benefit is by construction) |
| Imagery State Estimator with evidence classes; vividness only from self-report or a VALIDATED predictor | IMPLEMENTED; no validated predictor exists |
| Perception–Imagination Distance research metric (configurable, `objective_allowed=False`) | IMPLEMENTED (research only) |
| Controller state machine, policies (rules, PID controller on IQI, sham, none), gates, trace, replay | IMPLEMENTED |
| Dream Corridor bridge (existing 3D scene), audio params, cue fading, probe trials | IMPLEMENTED |
| Generative variations (async, validated, deterministic fallback) | IMPLEMENTED (interface; no generator connected) |
| Curriculum: 11 exercises, cue fading, probes, rest, arm allocation | IMPLEMENTED |
| Protocols A–D runners; E–G design simulations | IMPLEMENTED; DATA REQUIRED for any finding |
| Storage: HDF5, manifest, pseudonyms, consent, retention, raw-free review bundle | IMPLEMENTED (not yet wired to SQLite) |
| Research Command Center UI | IMPLEMENTED (build verified; not visually inspected in a browser) |
| Real-sensor neurofeedback | NOT IMPLEMENTED / HARDWARE + AUTHORIZATION REQUIRED |

## 4. Demonstrations (synthetic)

`python -m app.cli.multimodal_demo` → `reports/multimodal/SYNTHETIC_DEMO_REPORT.json`. Representative results
(180 s sessions, 5 synthetic streams, 2 s ticks, this Windows workstation):

| Scenario | Final state | Adaptive feedback ticks | Fallback rest ticks | Replay reproduced |
|---|---|---|---|---|
| Default (shadow) | ACTIVE_SHADOW | 0 | 0 | yes |
| Simulated FEEDBACK_RESEARCH | FEEDBACK_RESEARCH | 16 | 0 | yes |
| EEG disconnect at 90 s + ECG 250 ppm drift | SAFE_FALLBACK | 6 | 42 | yes |
| Scripted distress text at 100 s | SAFE_FALLBACK | 6 | 41 | yes |
| Operator emergency stop at 80 s | TERMINATED | 0 | 0 | yes |

Processing latency per tick (all five pipelines, incl. MNE fNIRS): p50 ≈ 44–52 ms. Fusion inference: late p50 0.63 ms,
intermediate p50 0.97 ms. These are wall-clock software numbers, not end-to-end sensor-to-display latency.

Infrastructure checks on synthetic data: decoders reach chance on zero-effect data (negative control); the E–G
two-arm analysis rejects at 5.25% under the null (400 simulations, α = 0.05).

## 5. Limitations

- Synthetic generators define the "ground truth"; good recovery shows pipeline correctness, not physiological validity.
- EDA SCR onsets are biased ~0.3 s early (zero-phase smoothing); ~0.01 µS spurious SCRs can appear from slow drift.
- Host-receive timestamps cannot reveal constant transport latency; such streams report `alignment_uncertainty=unknown`
  and the controller holds by default (`require_known_alignment`).
- Cross-subject Riemannian decoding fails without re-centering (LOSO at chance in the synthetic demo).
- In-memory API sessions (max 20); live sensor sessions are not exposed through the API.

## 6. Next priorities

1. Install and test `pylsl`/`brainflow` against a recorded LSL stream (`pylsl` replay outlet) and the BrainFlow synthetic
   board; measure end-to-end latency with a hardware marker.
2. Validate ECG/EDA/respiration pipelines on public reference datasets (e.g. PhysioNet) with known annotations.
3. Run Protocol A on existing real EEG (OpenMIIR) and NSD/NOD fMRI via the new generic readers; compare with the
   prior research pipelines.
4. Riemannian re-centering for cross-subject transfer; FBCSP band selection inside nested CV.
5. Persist session manifests in SQLite alongside the existing event store; WebSocket streaming for the UI.
6. Preregister protocols E–F before any participant work; complete the hardware checklist (`docs/hardware_validation_checklist.json`).
