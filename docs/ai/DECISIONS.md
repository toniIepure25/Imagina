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

*Last updated: 2026-05-07*
