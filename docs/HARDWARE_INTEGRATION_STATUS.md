# Hardware Integration Status (Phase 2)

Branch `product/multimodal-research-platform`. Environment: OrchestrAIQ Jupyter pod (Linux, Python 3.13.15, 16-CPU cgroup
quota), dedicated venv `mm-phase2/venv`. **No physical device was connected, and no electronics touched a person.**
Participant-facing feedback with real sensors stays disabled by default (ACTIVE_SHADOW + `FeedbackAuthorization`).

## Installed libraries

| Library | Version | Use |
|---|---|---|
| pylsl / liblsl | 1.18.5 / 1.18 | LSL inlet adapter, replay outlet |
| brainflow | installed (pip, latest) | `BoardShim` synthetic board |
| mne | 1.12.1 (pinned) | readers, preprocessing |
| mne-nirs | 0.7.3 | fNIRS GLM reference |
| neurokit2 | 0.2.13 | ECG/EDA reference implementation |
| wfdb | 4.3.1 | PhysioNet readers |
| pyriemann | 0.12 | Riemannian reference |

## What was tested (`backend/app/tests/test_multimodal_hardware_sim.py`, marker `hardware`, 7/7 passed on the pod)

| Path | Test | Result |
|---|---|---|
| LSL replay outlet → `LSLInletProvider` | sample fidelity (values match source to 1e-5), `time_correction` < 10 ms on one host, sync engine reports a known alignment uncertainty and zero gaps, median pull latency < 0.5 s | PASS |
| LSL dropout | outlet pauses 1 s at 500 Hz → inlet infers 500 ± 25 missing samples from timestamps; sync engine gap count equals provider drop count | PASS |
| LSL disconnect | outlet destroyed and recreated with the same `source_id`; inlet (`recover=True`) continues; dropped samples counted | PASS |
| LSL recording + replay | inlet chunks → HDF5 recorder → `FileReplayProvider` twice: bit-identical, equal to received data | PASS |
| BrainFlow synthetic board | 16 EEG channels, effective rate within 10% of 250 Hz, package-counter gap accounting consistent, monotonic local time; sync method `host_receive_time` → alignment uncertainty reported as *unknown* (controller holds by default) | PASS |
| BrainFlow reconnect | `try_reconnect` releases and re-prepares the session; sample indices continue increasing | PASS |
| ADS1299 bench fixture | 10 Hz / 50 µV sine at 250 Hz encoded as frames; 1% dropped frames, 0.5% corrupted frames, random 1–63-byte split reads, sequence wraparound past 65535 → amplitude exact to 1 LSB, peak at 10 Hz, CRC errors and lost frames counted exactly, indices monotonic across wrap, HDF5 round-trip identical | PASS |

## Fixes made during integration

- `BrainFlowProvider`: board timestamps (Unix wall clock) were passed through as local monotonic time; now kept as device
  timestamps and mapped onto the local clock at receipt. Gaps now come from BrainFlow's 0–255 package counter.
  Added `try_reconnect`.
- `LSLInletProvider`: LSL has no sample counter, so dropouts were invisible; gaps are now inferred from timestamp jumps
  (> 1.5 sample periods) and reflected in `sample_indices`, `dropped_before` and stats. `recover=True` on the inlet.
- New `acquisition/lsl_outlet.py` (`LSLReplayOutlet`) to publish synthetic or recorded streams over LSL with injected
  pauses and outlet restarts.

## Support levels after Phase 2

| Adapter | Level | What is still missing |
|---|---|---|
| LSL inlet | IMPLEMENTED, tested against LSL loopback | a real amplifier's LSL app; cross-host clock correction; measured end-to-end latency |
| BrainFlow | IMPLEMENTED, tested on synthetic board | any physical board |
| ADS1299 frame protocol | IMPLEMENTED (bench fixtures) / HARDWARE REQUIRED | firmware, transport (serial/BLE), electrical safety review |
| Real-time MEG / fMRI | NOT IMPLEMENTED | out of scope (offline modalities) |

## Not measured

- Sensor-to-host and display (render) latency: needs a hardware marker loop (photodiode on the display → acquisition).
- Electrical safety: every gating item in `docs/hardware_validation_checklist.json` remains NOT_STARTED.
