# KNOWN_ISSUES.md — Risk and Issues Register

---

## RISK-001: Dry EEG Low SNR

**Risk:** Real EEG signals (when introduced in V2) are weak, noisy, and easily contaminated by muscle artifacts, eye blinks, and environmental noise.  
**Impact:** High — proxy metrics derived from noisy EEG would be unreliable, undermining the core value proposition.  
**Mitigation:** Use MNE preprocessing pipeline with artifact detection (ICA, SSP). Require signal quality metrics before accepting data. Start with dry-electrode Muse/OpenBCI which have known SNR limitations — document these clearly.  
**Owner:** TBD  
**Status:** Mitigated in architecture (signal quality checks in feature engine, signal quality warnings in safety monitor) but not yet tested with real hardware.

---

## RISK-002: Artifact Contamination

**Risk:** Eye blinks, jaw clenching, head movement, and muscle tension produce artifacts that look like real EEG bands and could corrupt state estimation.  
**Impact:** Medium — could cause false positives in attention/relaxation proxies, leading to incorrect feedback and curriculum decisions.  
**Mitigation:** Apply ICA-based artifact removal in MNE preprocessing pipeline (V2). Use signal quality metrics to flag contaminated windows.  
**Owner:** TBD  
**Status:** Not yet implemented (V2 scope).

---

## RISK-003: Non-Stationarity Across Days

**Risk:** EEG patterns vary significantly across sessions and days due to electrode placement, skin impedance, fatigue, caffeine, and user state. Cross-session comparisons may be unreliable.  
**Impact:** High — longitudinal progress tracking and curriculum progression may be invalid if baselines drift.  
**Mitigation:** Per-session calibration with quality scores. Normalization metadata stored in calibration profiles. Acknowledge limitation in reports.  
**Owner:** TBD  
**Status:** Partially mitigated (calibration profiles exist in V1). Real EEG will amplify this risk.

---

## RISK-004: Placebo/Confound Risk

**Risk:** Perceived improvements in imagery quality could be due to practice effects, expectation, relaxation from the breathing cues, or simple exposure — not the adaptive feedback loop.  
**Impact:** High for scientific validity — without controlled experiments, we cannot attribute effects to the system.  
**Mitigation:** Include fixed-difficulty control conditions in experiment protocol framework. Conduct formal within-subjects repeated-measures experiments (V3 roadmap). Explicitly state this limitation in documentation.  
**Owner:** TBD  
**Status:** Experiment protocol framework exists in V1 but controlled validation studies are not yet designed or conducted.

---

## RISK-005: Overclaiming Risk

**Risk:** Users, media, or even developers may describe IMAGINA as "mind reading" or "dream decoding." This damages scientific credibility and could attract regulatory scrutiny.  
**Impact:** Critical — could harm the project's reputation, invite regulatory action, and mislead users.  
**Mitigation:** Claims discipline enforced via AGENTS.md, scientific claims policy, visible disclaimers in UI, and a scientific-guardian agent. All code, docs, and UI text must use proxy/estimate language.  
**Owner:** All contributors  
**Status:** Actively mitigated (claims policy in `docs/scientific_claims.md`, disclaimers throughout UI and docs).

---

## RISK-006: Fatigue and Overstimulation Risk

**Risk:** Extended imagery training sessions could cause mental fatigue, eye strain, or in rare cases, dissociation-like experiences or discomfort.  
**Impact:** Medium — user safety risk. Could cause negative experiences that discourage use and raise ethical concerns.  
**Mitigation:** Safety monitor with fatigue >0.80 warnings, 20-minute session limit, dissociation keyword detection, breathing/reset cues, and visible safety disclaimers. Users can stop any session at any time.  
**Owner:** TBD  
**Status:** Mitigated in V1 (safety monitor operational, all checks active). Should be tested with real users.

---

## RISK-007: Privacy Risk with Neural Data

**Risk:** If future versions transmit raw EEG or session data to external services (for AI processing, analytics, or cloud storage), user privacy could be compromised. Neural data is especially sensitive.  
**Impact:** Critical — privacy breach of neural/proxy data could have legal, ethical, and reputational consequences.  
**Mitigation:** Local-first architecture. No external API calls for session or neural data. No authentication or cloud sync. Data export is user-initiated only. Privacy rules enforced via AGENTS.md and security-auditor agent.  
**Owner:** All contributors  
**Status:** Mitigated in architecture (local-first, no cloud). Must be maintained in all future versions.

---

## RISK-008: Latency Risk for Generative Feedback

**Risk:** V3 plans include generative AI post-session summaries. If generative models are run locally, latency could be high. If run via API, privacy is at risk.  
**Impact:** Medium — slow feedback degrades user experience; API calls risk privacy.  
**Mitigation:** Plan for local-only generative models. If external APIs are ever considered, they must use non-sensitive data only and require explicit architecture decision and privacy review.  
**Owner:** TBD  
**Status:** Deferred to V3. No generative AI components exist in V1.

---

## RISK-009: Evaluation Validity Risk

**Risk:** V1 metrics are tested with simulated data and self-report. The evaluation harness validates internal consistency but not real-world validity against validated imagery questionnaires (VVIQ, OSIVQ) or behavioral measures.  
**Impact:** High — all V1 results may be internally consistent but externally invalid.  
**Mitigation:** Validation plan in `docs/scientific_claims.md`. Compare IQI with VVIQ/OSIVQ in future studies. Publish results with full methods and data transparency.  
**Owner:** TBD  
**Status:** Not yet validated. Evaluation harness tests internal consistency only.

---

## RISK-010: Simulated Data Not Equivalent to Real EEG

**Risk:** V1 simulated EEG-like features are deterministic mathematical functions, not real neural data. Results obtained with simulated data do not generalize to real EEG.  
**Impact:** Medium — V1 demos and metrics are illustrative, not scientifically valid as EEG studies.  
**Mitigation:** Clearly label all V1 metrics as "simulated proxy." Do not compare V1 results to published EEG studies. Document limitation prominently.  
**Owner:** TBD  
**Status:** Mitigated through documentation and claims policy. Must remain explicit.

---

## RISK-011: Frontend Test Coverage Gap

**Risk:** The frontend has no automated tests (`npm test` script is missing). UI regressions and logic bugs in session flow, scene rendering, or metric displays could go undetected.  
**Impact:** Medium — frontend bugs could affect user safety (e.g., incorrect safety banner behavior) or scientific data quality (e.g., incorrect metric display).  
**Mitigation:** Add `npm test` script with a test framework (vitest/jest + testing-library). Prioritize tests for session flow, safety banner, and metric display components.  
**Owner:** TBD  
**Status:** Not yet mitigated. No frontend test infrastructure exists.

---

## RISK-012: Repomix Compatibility

**Risk:** `repomix.config.json` and `scripts/ai_context.sh` assume repomix is available. If repomix is not installed or the config schema doesn't match the installed version, context snapshots will fail.  
**Impact:** Low — context snapshots are a convenience, not a critical path dependency.  
**Mitigation:** Check for repomix availability in ai_context.sh before running. Document installation step.  
**Owner:** TBD  
**Status:** Mitigated (ai_context.sh checks for repomix binary).

---

## RISK-013: Module-Level Mutable Session State

**Risk:** `_session_states: dict[str, dict]` in `session_stream.py` and `_replay_states` in `replay_service.py` are module-level mutable globals with no cleanup on process restart. Stale state from crashed or leaked sessions could cause incorrect "session already running" errors.  
**Impact:** Low — single-process local deployment makes concurrent access unlikely, and the dict is keyed by session UUID. Stale entries would only persist within a single process lifetime.  
**Mitigation:** Acceptable for single-process local-only V2. If the system ever moves to multi-worker or cloud, replace with a proper distributed state store.  
**Owner:** TBD  
**Status:** Noted in V2.0 review. No action needed for V2.

---

## RISK-014: Calibration Lookup Performs Full Table Scan

**Risk:** `calibration_service.get_calibration(session_id)` iterates all calibration records to find one by session_id. With many sessions, this becomes O(n).  
**Impact:** Low — in local-only use with tens or hundreds of sessions, the scan is negligible.  
**Mitigation:** Add a `session_id` index or a dedicated lookup query when calibration volume grows.  
**Owner:** TBD  
**Status:** Noted in V2.0 review. Acceptable for current scale.

---

## RISK-015: Session Loop Exception Handling Silently Drops Events

**Risk:** In `session_stream.py`, a bare `except Exception: break` during WebSocket emit will silently stop the session loop if any message fails to send. This is by design (client disconnected), but there is no distinction between transient network errors and permanent disconnects.  
**Impact:** Low — the finally block calls `complete_session()` and emits `session_stopped`, so session termination is still recorded.  
**Mitigation:** Added `logging.getLogger().warning()` to the completion failure handler. The emit break is acceptable for V2 (local WebSocket connection is stable).  
**Owner:** TBD  
**Status:** Mitigated with logging. Low risk for local deployment.

---

## RISK-016: pylsl Installation Varies by Platform

**Risk:** pylsl requires liblsl system library which installs differently on Linux, macOS, and Windows. Users may encounter platform-specific installation issues beyond standard pip.  
**Impact:** Medium — LSL integration is optional. Users without pylsl can still use simulated/manual/replay providers.  
**Mitigation:** pylsl is in an optional `[lsl]` dependency group, not mandatory. RealLSLProvider health reports `unavailable` when pylsl is missing. Documentation should include platform-specific installation notes.  
**Owner:** TBD  
**Status:** Mitigated by optional dependency architecture. RealLSLProvider skeleton handles missing pylsl gracefully.

---

## RISK-017: LSL Stream Discovery Is Local-Network, Not Local-Process Only

**Risk:** LSL may discover streams on the local machine or local network depending on configuration. Users should understand that LSL stream names may be visible on the local network segment. This is not an external-internet exposure, but it is broader than local-process-only.  
**Impact:** Low — IMAGINA remains local-first. Stream metadata (name, type, channel count) is the only data exposed via discovery. No raw EEG samples are transmitted.  
**Mitigation:** Health metadata includes `raw_persistence_default=False` and `clinical_use=False`. Future documentation should note: "LSL may discover streams on the local machine or local network depending on configuration."  
**Owner:** TBD  
**Status:** Noted in Phase 2. No raw EEG data is collected or transmitted.

---

## RISK-018: RealLSLProvider.next_window() Raises NotImplementedError

**Risk:** If a frontend or session loop calls `next_window()` on `lsl.real` before Phase 3/4 is implemented, it will crash with `NotImplementedError`. The session loop's current provider resolution defaults to `simulated.default`, so this only occurs if a user explicitly selects `lsl.real`.  
**Impact:** Low — `window_collection_implemented=False` in metadata allows frontend to disable the provider in future UI. Session loop default is `simulated.default`.  
**Mitigation:** Frontend should check `metadata().window_collection_implemented` before enabling provider selection (future Phase 6). Until then, `lsl.real` is visible but not usable.  
**Owner:** TBD  
**Status:** Mitigated by metadata flag and session loop default. Phase 2.5 added guardrails: `session_start_allowed` metadata field, backend REST/WebSocket checks, and frontend provider disable logic. Will be fully resolved when Phase 3 implements window collection.

---

## RISK-019: Simplified DSP Bandpower Proxies Are Not Clinical-Grade

**Risk:** Phase 3A FeatureEngine uses stdlib `math`-based time-domain heuristics (zero-crossing rate, amplitude statistics) to estimate bandpower rather than FFT-based spectral analysis. These proxies are crude approximations of actual EEG bandpower and should not be compared to published EEG studies using proper FFT/wavelet methods.  
**Impact:** Medium — feature estimates may not correlate well with real EEG bandpower as measured by clinical or research-grade tools.  
**Mitigation:** FeatureEngine docstring states: "simplified experimental EEG feature proxies, not clinical-grade EEG analysis." Future phase can add numpy-based FFT for more accurate bandpower.  
**Owner:** TBD  
**Status:** Documented limitation. Acceptable for V2.1 mock-first phase.

---

## RISK-020: LSL Sample Collection Uses Blocking Thread Executor

**Risk:** RealLSLProvider.next_window() uses `asyncio.get_event_loop().run_in_executor()` to call the blocking `pylsl.StreamInlet.pull_sample()` synchronously. This creates thread overhead and may add latency under high load.  
**Impact:** Low for single-session local use. May become noticeable with multiple concurrent sessions or low-latency requirements.  
**Mitigation:** Acceptable for V2.1 single-user deployment. Future: use native async LSL backend or dedicated collector thread with asyncio.Queue buffer.  
**Owner:** TBD  
**Status:** Documented limitation. No action needed for V2.1.

---

*Last updated: 2026-05-07 — Phase 3A*
