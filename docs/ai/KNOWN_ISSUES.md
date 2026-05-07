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

*Last updated: 2026-05-07*
