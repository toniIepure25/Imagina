# DECISIONS.md — Architecture Decision Log

All significant architectural decisions for the IMAGINA project are recorded here using a lightweight ADR (Architecture Decision Record) format.

---

## ADR-001: Local-First Privacy Architecture

**Status:** Accepted  
**Date:** 2026-05-07  
**Context:** IMAGINA processes neural-proxy and self-report data that is sensitive. Cloud-based architectures risk privacy breaches and make scientific claims harder to defend.

**Decision:** All data stays in local SQLite. No cloud authentication, no telemetry, no external API calls for session or neural data. Export is user-initiated only.

**Consequences:**
- No multi-user or cross-device sync.
- No server-side analytics.
- Users manage their own data lifecycle (delete DB = delete all data).
- Future LSL EEG data must also remain local.

---

## ADR-002: Scientific Claim Discipline

**Status:** Accepted  
**Date:** 2026-05-07  
**Context:** Mental imagery and neural interfaces are easily overclaimed. IMAGINA must remain scientifically defensible and avoid misleading users.

**Decision:** All system outputs and documentation use proxy/estimate language. A specific allow-list and deny-list of claims is maintained in `docs/scientific_claims.md`. All agents must check claims against this policy.

**Consequences:**
- Every new UI text, API field description, or doc paragraph must be checked against the claims policy.
- Marketing and external communication must be reviewed separately.
- The system can never claim to "read minds" even if future versions improve proxy accuracy.

---

## ADR-003: Closed-Loop Feedback Is Proxy-Based, Not Thought Reconstruction

**Status:** Accepted  
**Date:** 2026-05-07  
**Context:** The Dream Corridor scene adapts to estimated state. It would be tempting to claim it shows what the user is imagining. This is scientifically unsound and ethically problematic.

**Decision:** The corridor is explicitly framed as an adaptive scaffold — not a decoded or reconstructed mental image. The visual mapping is transparently documented: clarity follows IQI proxy, fog follows uncertainty/fatigue, wall distortion follows instability, etc.

**Consequences:**
- Never describe the corridor as "showing" or "visualizing" the user's imagery.
- Always describe it as "adapting to" or "responding to" estimated proxy metrics.
- The scaffolding metaphor must be maintained in all documentation and UI.

---

## ADR-004: Separate Signal Processing, State Estimation, Curriculum, Feedback, and Reporting

**Status:** Accepted  
**Date:** 2026-05-07  
**Context:** Early prototyping can blur boundaries between signal processing, state estimation, and feedback. This creates coupling that makes V2/V3 upgrades harder.

**Decision:** Maintain clear module boundaries:
1. `signals/` — data source abstraction
2. `services/feature_engine.py` — feature normalization
3. `services/state_estimator.py` — state inference
4. `services/pid_iqi_engine.py` — metric computation
5. `services/curriculum_manager.py` — level progression
6. `services/feedback_policy_engine.py` — scene param mapping
7. `services/safety_monitor.py` — independent safety checks
8. `services/report_service.py` — aggregation
9. `storage/` — persistence

**Consequences:**
- Each module can be independently tested and replaced.
- V2 can swap in a learned state estimator without touching feedback or curriculum.
- Safety monitor runs as an independent layer, not embedded in other modules.

---

## ADR-005: Use Simulated/Replay Signal Providers Before Real Hardware

**Status:** Accepted  
**Date:** 2026-05-07  
**Context:** Real EEG hardware introduces complexity (LSL, drivers, electrode quality, artifact handling) that would slow down core algorithm development.

**Decision:** V1 uses simulated signal providers (seeded, deterministic) and replay providers. The signal provider abstraction makes real LSL a drop-in replacement in V2 without rewriting the metric/feedback pipeline.

**Consequences:**
- Simulated data is not equivalent to real EEG — V1 results are not scientifically valid as EEG studies.
- All V1 metrics must be labeled as "simulated proxy" not "EEG-derived."
- The LSL provider stub exists but is not functional — documented as future work.

---

## ADR-006: Safety Override and Cooldowns Are First-Class System Features

**Status:** Accepted  
**Date:** 2026-05-07  
**Context:** Mental imagery training systems can induce fatigue, overeffort, and in rare cases dissociation-like experiences. Safety must be architected in from the start, not bolted on later.

**Decision:** The SafetyMonitor runs on every 2-second window and has authority to:
- Trigger warnings (fatigue > 0.80 for 2+ consecutive windows)
- Trigger session stop (dissociation keywords, session > 20 minutes)
- Trigger simplification (overeffort: high effort + high fatigue)
- Trigger breathing/reset cues

Safety signals have priority over curriculum advancement and feedback aesthetics.

**Consequences:**
- Safety logic must never be bypassed or reduced in severity for "better UX."
- Any new feedback mechanism must include safety checks.
- The 20-minute limit is a reasonable default but may need adjustment based on user research.

---

## ADR-007: SQLite Event Sourcing for Persistence

**Status:** Accepted  
**Date:** 2026-05-07  
**Context:** Session data needs to be persisted for reports, replay, and offline analysis. Traditional relational schemas make it hard to reconstruct session timelines.

**Decision:** Use event sourcing: every computation (features, state, PID, IQI, feedback, safety events) is stored as an EventEnvelope in the SQLite events table. Sessions table holds metadata.

**Consequences:**
- Full session replay is possible by re-reading events.
- Export formats (JSONL, CSV) can be generated from the event store.
- Adding new event types does not require schema migrations.
- Event store size grows linearly with session length — acceptable for local-only storage.

---

## ADR-008: Backend as Single FastAPI Service (No Microservices)

**Status:** Accepted  
**Date:** 2026-05-07  
**Context:** The system could be split into separate services for signal processing, state estimation, and feedback. This would add deployment complexity without clear benefit at the V1/V2 stage.

**Decision:** Single FastAPI process with modular internal architecture. Docker Compose runs backend + frontend as two services.

**Consequences:**
- Simpler development and deployment.
- All modules share the same Python process — no serialization overhead.
- If V3 requires heavy ML inference, a separate inference service may be warranted. This decision can be revisited then.

---

## ADR-009: Session Loop Uses Provider Abstraction, Not Direct SignalSimulator Calls

**Status:** Accepted
**Date:** 2026-05-07
**Context:** Prior to V2.1, the session loop in `session_stream.py` instantiated `SignalSimulator` directly, bypassing the `SignalProvider` abstraction. This meant a real LSL provider would require duplicating the entire session loop or modifying it per-provider.

**Decision:** The session loop resolves providers via the registry (`get_provider(provider_id)` with fallback to `simulated.default`). All provider lifecycle calls (`start`, `next_window`, `stop`) go through the abstraction. Self-report and scenario/seed parameters are passed through kwargs and optional params.

**Consequences:**
- Any provider implementing the `SignalProvider` protocol can drive the session loop without code duplication.
- The `next_window()` signature was extended with optional `self_report` and `total_windows` params (backward compatible).
- Simulated provider now correctly passes self-report influence to `SignalSimulator`.
- Replay service still uses `SignalSimulator` directly for demo creation (separate code path, acceptable).

---

## ADR-010: EEG Schema Contract — Optional Real-EEG Metadata Fields

**Status:** Accepted
**Date:** 2026-05-07
**Context:** Phase 1 of V2.1 prepares the schema contracts for real EEG/LSL integration without implementing any real signal processing. All new fields must be backward-compatible with existing V2.0 simulated/manual/replay flows.

**Decision:** Added 16 optional fields to EEGSampleWindow, 14 to FeatureVector, 9 to CalibrationProfile, and 2 to SessionSummary. All new fields have safe defaults: `None`/`False`/`0`. Raw EEG samples remain `Optional[list[list[float]]] = None` with `raw_persisted: bool = False` — raw EEG is never persisted by default. Artifact scores are constrained to [0,1]. Channel counts and sampling rates have `>=0` and `>0` validation where provided. SessionSummary derives `real_signal` and `provider_type` from the session's `signal_provider_id` prefix.

**Consequences:**
- Existing simulated/manual/replay providers produce FeatureVectors with `real_signal=False` and all new fields at their defaults — zero behavioral change.
- Future RealLSLProvider can simply set `real_signal=True` and populate EEG metadata fields — no schema migration needed.
- Export CSV format is unchanged (explicit field list). JSONL naturally includes all new fields when populated.
- Data dictionary now documents all V2.1 EEG metadata fields with limitation notes.

---

## ADR-011: RealLSLProvider Skeleton — No Mandatory pylsl, No Fake Data

**Status:** Accepted
**Date:** 2026-05-07
**Context:** Phase 2 adds a RealLSLProvider skeleton to the provider registry without requiring pylsl and without implementing EEG window collection. The provider must fail safely rather than silently producing fake data.

**Decision:** RealLSLProvider is registered unconditionally in the provider registry. It checks for pylsl availability at init via `importlib.util.find_spec`. When pylsl is missing, `health()` returns `status="unavailable"` with a clear error message. `next_window()` raises `NotImplementedError` — it does not fall back to simulated or fake data. `discover_streams()` returns `[]` when pylsl is missing. pylsl is added as an optional `[lsl]` dependency group in pyproject.toml — normal installs do not require it.

**Consequences:**
- Normal installs (`pip install -e ".[dev]"`) work without pylsl.
- `scripts/verify.sh` passes without pylsl.
- Frontend can check `lsl.real` health status to display appropriate UI (future phase).
- No code path silently produces real EEG data.
- Window collection is deferred to Phase 3/4.

---

## ADR-012: Provider Readiness Contract — session_start_allowed in Metadata

**Status:** Accepted
**Date:** 2026-05-07
**Context:** After registering `lsl.real` in the provider registry (Phase 2), the system had no mechanism to prevent users from starting sessions with a provider whose `next_window()` raises `NotImplementedError`. All providers needed a standardized way to declare whether they can run live sessions.

**Decision:** Every provider's `metadata()` and `health()` dicts include three standardized fields: `session_start_allowed: bool`, `window_collection_implemented: bool`, and `disabled_reason: str | None`. Backend guardrails in `session_service.start_session()` and `session_stream.run_session_loop()` check `metadata().session_start_allowed` before starting a session. Frontend `SessionSetup` disables provider selection when `session_start_allowed=False` and displays the disabled reason. `lsl.real` reports `session_start_allowed=False` with a clear reason. All existing providers report `session_start_allowed=True`.

**Consequences:**
- Adding a new non-executable provider in the future requires setting `session_start_allowed=False` and a descriptive `disabled_reason`.
- Frontend can check `session_start_allowed` without knowing provider-specific logic.
- Backend REST and WebSocket both have independent guardrails — defense in depth.
- `session_start_allowed` defaults to `True` when absent from metadata — safe for providers that haven't been updated.

---

## ADR-013: Mock-First RealLSLProvider with Two-Tier Readiness Contract

**Status:** Accepted (updated Phase 3A.5)
**Date:** 2026-05-07
**Context:** Phase 3A implemented window collection but kept `metadata().session_start_allowed=False` from Phase 2.5. This created a deadlock: the metadata check in backend guardrails always rejected lsl.real before reaching the dynamic health check. The readiness contract needed to cleanly separate static capability from runtime state.

**Decision (updated Phase 3A.5):** Two-tier readiness contract with explicit guardrails:
1. `metadata()` contains static capability flags only: `window_collection_implemented`, `real_signal_supported`, `clinical_use`, `raw_persistence_default`. Does NOT contain `session_start_allowed`.
2. `health()` contains runtime readiness: `session_start_allowed` (pylsl installed + stream found + experimental flag), `stream_found`, `available`, `connected`, `disabled_reason`.
3. Backend guardrails check `metadata().window_collection_implemented` first (must be True), then `metadata().session_start_allowed` if present (explicit `is False` check), then `health().session_start_allowed` (runtime decision).
4. Uses `is False` checks (not `not ...`) to avoid accidentally allowing providers with missing fields.

**Consequences:**
- lsl.real is blocked when experimental flag is off (health blocks)
- lsl.real can start when experimental flag is on AND stream exists
- lsl.real is blocked when flag is on but no stream (health blocks)
- All other providers continue to report `session_start_allowed=True` in both metadata and health

---

*Last updated: 2026-05-07 — Phase 3A.5*
