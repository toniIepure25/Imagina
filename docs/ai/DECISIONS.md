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

## ADR-007: Conservative Semantic Event Code Mapping

**Status:** Accepted  
**Date:** 2026-05-11  
**Context:** OpenMIIR FIF files contain 52 unique stim channel event codes across 10 subjects. These event codes are essential for unlocking perception vs imagery analysis, stimulus ID analysis, and trial-aligned EEG epoching. However, the semantic meaning of these codes (which codes represent perception/imagery/stimulus IDs/blocks) is not documented in the GitHub repository metadata.

**Decision:** Event codes are grouped into numerical families (low_single_digit, mid_100_range, mid_200_range, special_markers) based on pattern analysis. Confidence levels (`confirmed`, `strong_hypothesis`, `weak_hypothesis`, `unknown`) are assigned only based on supporting evidence from downloaded metadata or external documentation. Semantic labels are NEVER invented from numerical patterns alone. A production condition_manifest.json is generated ONLY if confirmed mappings are available, otherwise only a draft manifest with explicit warnings is produced.

**Consequences:**
- Event timing analysis can proceed (IEI distributions, code transitions, block boundary detection)
- Condition-aware analysis (perception vs imagery) is blocked until semantic mapping is confirmed
- Subject-level sanity checks (e.g., subject identity classification) remain possible
- Scientific claims about perception/imagery EEG differences are prohibited pending mapping
- Research dashboard shows amber status for condition analysis
- Contact with dataset authors or discovery of external documentation is required to unblock

---

## ADR-008: No Perception-vs-Imagery Condition Analysis Without Confirmed Semantic Mapping

**Status:** Accepted  
**Date:** 2026-05-11  
**Context:** OpenMIIR stim channels contain 52 unique event codes. Beat file naming confirms two-digit codes (11-44) map to stimulus×cue beat tracks. README confirms both perception and imagery conditions exist in the dataset. However, the explicit mapping of which event codes represent perception vs imagery vs stimulus IDs has NOT been confirmed from downloaded documentation or code. The 100-series vs 200-series code family distinction is a structural hypothesis only.

**Decision:** IMAGINA blocks all perception-vs-imagery condition analysis until a confirmed production condition_manifest.json exists. The system distinguishes three levels:
1. **Confirmed**: explicit code-to-label mapping from documentation
2. **Strong hypothesis**: structural evidence from multiple independent sources
3. **Weak hypothesis**: numerical patterns or single-source evidence

Only confirmed mappings produce production manifests. Strong hypotheses produce draft manifests with `scientific_use_allowed=false`. Condition eval is blocked until `semantic_mapping_resolved=true`.

**Consequences:**
- Research dashboard shows amber status for condition analysis
- All reports explicitly document what is confirmed vs hypothesized
- No false scientific claims about EEG differences between conditions
- Unblocks as soon as explicit mapping evidence is obtained
- Beat file naming is documented as confirmed structural evidence
- Event timing analysis and sequence motif extraction continue independently

---

## ADR-009: Binary Metadata Recovery with Safety Limits

**Status:** Accepted  
**Date:** 2026-05-11  
**Context:** OpenMIIR repository contains high-value metadata files in binary formats (.xlsx, .xls, .m, .mat) that may contain the explicit semantic mapping of event codes to conditions. These files were previously excluded by the downloader's file extension filter. Recovering and parsing these files is essential for unlocking perception-vs-imagery condition analysis.

**Decision:** Binary metadata files are allowed for download from the GitHub tree under strict conditions:
1. Only metadata/documentation file extensions: .xlsx, .xls, .ods, .m, .mat
2. Maximum file size: 10 MB (configurable via --max-file-size-mb)
3. .mat files additionally limited to 5 MB
4. Raw EEG (.fif, .edf, .bdf, etc.), audio, images, and model checkpoints remain permanently blocked
5. Downloaded binary metadata is stored in the same github_candidates/ directory as text metadata
6. A download_manifest.json tracks all downloaded and skipped files
7. Parsing uses openpyxl (preferred) or pandas for Excel; text-based parsing for MATLAB .m files

**Consequences:**
- 7 hard metadata files recovered (4 .xlsx, 2 .m, 1 .mat)
- MATLAB script yielded confirmed trigger semantics from code comments
- Excel parsing blocked by openpyxl dependency (pandas alone insufficient)
- No raw EEG or audio exposed through binary metadata channels
- Download manifest provides full audit trail

---

## ADR-011: Experimental Condition Evaluation Artifacts Must Be Separate from Production Artifacts

**Status:** Accepted  
**Date:** 2026-05-11  
**Context:** V3.9.5 introduced experimental condition evaluation mode (`--allow-empirical-hypothesis true`) that uses empirically validated but undocumented StimTracker encoding hypothesis to evaluate perception vs imagery conditions. In V3.9.5.0, the experimental mode was overwriting the main `openmiir_condition_eval.json` artifact with experimental status, creating risk of accidental scientific overclaiming.

**Decision:** The condition eval CLI maintains two strictly separate artifact paths:
1. **Main/default artifact** (`openmiir_condition_eval.json`): Always reflects canonical production status (blocked unless confirmed documentation exists). Written on every run, regardless of mode.
2. **Experimental artifact** (`openmiir_condition_eval_experimental.json`): Written ONLY when `--allow-empirical-hypothesis true`. Contains `not_for_scientific_claims=true`, `production_valid=false`, `production_unlock_allowed=false`. Must never overwrite the main artifact.

**Consequences:**
- Automated tests verify main artifact stays "blocked" after experimental runs
- Dashboard shows separate main_status and experimental_status
- Experimental artifacts are clearly labeled as hypothesis-only
- Accidental scientific overclaiming is prevented by architectural separation
- Production condition analysis requires both confirmed documentation AND a production manifest

---

## ADR-015: Custom Migration Runner over Alembic

**Status:** Accepted
**Date:** 2026-07-10
**Context:** Merge Gate A requires versioned database migrations for the research governance schema. Two options were evaluated: Alembic (standard Python migration tool) and a custom lightweight runner.

**Decision:** Use a custom sequential migration runner because:
1. IMAGINA is local-first with a single SQLite file — Alembic's multi-database, multi-developer workflow overhead is unnecessary.
2. The migration runner is ~80 lines, auditable, and tested.
3. Each migration is a Python module with VERSION, DESCRIPTION, and async upgrade().
4. The schema_version table tracks applied migrations.
5. Failed migrations do not advance the version (rollback on error).
6. All migrations are idempotent (CREATE TABLE IF NOT EXISTS for legacy tables).

**Consequences:**
- Simpler than Alembic for this use case, but limited: no auto-generation, no downgrade support.
- Rollback must be handled manually if needed (SQLite ALTER TABLE is limited anyway).
- If the schema grows significantly, migration to Alembic remains possible.

---

## ADR-016: Balanced Williams Crossover Design

**Status:** Accepted
**Date:** 2026-07-10
**Context:** The previous implementation used independent random permutation sampling per participant, which does not guarantee balanced allocation across sequences. For a 3-condition crossover study, proper counterbalancing requires both position balance and first-order carryover balance.

**Decision:** Use the six Williams-style sequences (ABC, BCA, CAB, CBA, ACB, BAC) which provide:
- Position balance: each condition appears in each period equally over complete blocks.
- First-order carryover balance: each ordered pair of conditions appears equally.
- Transactional allocation: BEGIN IMMEDIATE prevents double-allocation under concurrency.
- Deterministic tie-breaking from study_seed + participant_id hash.
- Least-used-sequence selection for incomplete cohort balance.
- Immutable allocation: once committed, cannot be changed.

**Consequences:**
- Replaces the old independent rng.choice() approach in participant_registry.
- The old randomization.py generate_condition_sequence() still exists for backward compatibility but is not used by the new allocator.
- Withdrawal does not erase allocation records (audit trail preserved).

---

## ADR-017: Public/Operator API Separation

**Status:** Accepted
**Date:** 2026-07-10
**Context:** The participant API exposed condition_sequence and randomization_seed, contradicting condition blinding claims.

**Decision:** Split research API into:
- /api/research-protocol/public/ — participant-facing, no assignment data.
- /api/research-protocol/operator/ — operator-facing, includes assignment data with explicit warning.
- ParticipantPublicView schema excludes: condition_sequence, randomization_seed, sequence_id, current_condition, future_condition, yoked_source, policy_identifier.

This is honest role-oriented information separation, not authenticated access control.

**Consequences:**
- Participant-facing integrations cannot accidentally reveal assignment.
- No authentication system is required in this pass.
- Operator warning is included in response metadata.

---

## ADR-018: Transport-Independent Research Runtime

**Status:** Accepted
**Date:** 2026-07-13
**Context:** The existing WebSocket session loop is tightly coupled to FastAPI/WebSocket objects and module-level state. Research sessions need persistent, deterministic, reproducible execution.

**Decision:** Create `ResearchSessionRuntime` that injects all dependencies (clock, ID generator, feedback policy, safety monitor, event sink, database). The runtime has no dependency on FastAPI, WebSocket, or frontend state. Synthetic sessions continue executing even if no client is connected.

**Consequences:**
- Same runtime code works for API-triggered, CLI, and test execution.
- Existing demo WebSocket runtime is preserved unchanged.
- DeterministicClock and DeterministicIdGenerator enable exact replay.

---

## ADR-019: Optimistic Concurrency for State Machines

**Status:** Accepted
**Date:** 2026-07-13
**Context:** Research sessions and trials need explicit state machines with protection against concurrent modification.

**Decision:** Use `state_version` compare-and-swap (CAS) semantics. Every transition increments the version; zero rows updated means a conflict. Terminal states are immutable. All transitions are persisted in transition tables.

**Consequences:**
- No silent state corruption from concurrent callers.
- Full audit trail of every state change.
- Slight overhead from version checking on every transition.

---

## ADR-020: Canonical Serialization for Replay Hashing

**Status:** Accepted
**Date:** 2026-07-13
**Context:** Deterministic replay requires comparing scientific outputs between runs. Simple `json.dumps(sort_keys=True)` is insufficient because float precision and non-finite values can cause divergence.

**Decision:** Implement versioned canonical serializer with: sorted keys, compact separators, UTF-8, allow_nan=False, float precision to 8 decimal places. Canonicalization version is tracked in manifests.

**Consequences:**
- Replay hashes are stable across Python versions (within float representation).
- NaN/Infinity in scientific output is a hard error, caught early.
- Version field allows future format evolution without breaking old hashes.

---

## ADR-021: Persistent Run Lifecycle with Idempotent Commands

**Status:** Accepted
**Date:** 2026-07-13
**Context:** The Merge Gate B API used an in-memory `_active_runs` dict as source of truth for run state, which was lost on process restart.

**Decision:** Persist all run state in `runtime_runs` table via `RunService`. Idempotency enforced through `runtime_commands` table (same key + same input hash → return existing; different input → 409 conflict). On startup, lifespan hook marks non-terminal runs as `interrupted`.

**Consequences:**
- Run state survives process restart.
- Idempotent retries are safe; conflicting inputs are rejected.
- Recovery scan on startup prevents phantom "running" states.

---

## ADR-022: Injectable Pipeline Adapters for Runtime

**Status:** Accepted
**Date:** 2026-07-13
**Context:** The runtime had inline `_generate_features`, `_estimate_state`, `_compute_pid`, `_compute_iqi` methods. These could not be swapped for different implementations.

**Decision:** Define protocol interfaces (SignalProvider, FeatureProcessor, StateEstimator, MetricProcessor, CurriculumProcessor) and inject them into the runtime constructor. Provide deterministic implementations for synthetic execution.

**Consequences:**
- Runtime is transport-independent and adapter-testable.
- Future LSL/real-EEG adapters implement the same protocols.
- Session isolation ensured by creating fresh adapter instances per session.

---

## ADR-023: Transactional Outbox for Atomic Event Persistence

**Status:** Accepted
**Date:** 2026-07-13
**Context:** Domain record writes and event publications were separate operations. A crash between write and publish could lose events.

**Decision:** PersistentOutboxWriter writes events to `runtime_event_outbox` within the same transaction as domain records. OutboxDispatcher reads and forwards committed events to consumers, marking them published.

**Consequences:**
- No lost events on crash-before-commit (both domain + events roll back).
- Eventually-observable events on crash-after-commit (outbox rows survive for later dispatch).
- Dispatch failures tracked with attempt count and last error.

---

## ADR-024: Immutable Session Manifests with Completion Sealing

**Status:** Accepted
**Date:** 2026-07-13
**Context:** Reproducibility requires a complete record of every configuration parameter used to execute a session. The `session_manifests` table existed but was never populated.

**Decision:** Create a manifest before each session starts, capturing all config (study, protocol, participant, policy, provider, yoked info, seed, processor IDs, software version). After session completes, seal with terminal status, content hash, and seal hash. Manifests are immutable after creation.

**Consequences:**
- Full provenance chain for every session.
- Replay-from-manifest is possible: load manifest, reconstruct deps, rerun, compare hashes.
- Sealed manifests serve as audit records.

---

## ADR-025: Unified Database Ownership

**Status:** Accepted
**Date:** 2026-07-13
**Context:** The orchestrator was creating a separate per-study SQLite file while the API used the main deployment database. This split-brain persistence meant run metadata and scientific session data lived in different files.

**Decision:** The orchestrator now accepts an existing `aiosqlite.Connection` from the API. All runtime entities (runs, sessions, trials, feedback, manifests, seals, outbox, exports) share the same authoritative database.

**Consequences:**
- Single DB per deployment — no split-brain.
- API can read sessions/failures directly after orchestrator completes.
- Process restart can still access all data.

---

## ADR-026: Completion Seals as Append-Only Tamper-Evident Records

**Status:** Accepted
**Date:** 2026-07-13
**Context:** Manifest sealing (ADR-024) only stored a `sealed_at` timestamp on the manifest row. No separate immutable record existed for content hash, terminal status, or seal hash.

**Decision:** Create `session_completion_seals` table (v005 migration) as an append-only table with UNIQUE(research_session_id). Seal hash covers all seal fields except itself. Service-level code prevents update or deletion of seals.

**Consequences:**
- Tamper detection: any modification to seal fields is detectable by recomputing seal hash.
- Session reproducibility requires valid seal + manifest + content hash match.
- Replay requires a completion seal before proceeding.

---

## ADR-027: Evidence-Derived Export and Replay Status

**Status:** Accepted
**Date:** 2026-07-13
**Context:** Previous API returned `export_ready: true` based on run status alone, and `replay_verified: false` as a placeholder.

**Decision:** `export_ready` is true only when a persisted `export_runs` record exists with a passing validation result. `replay_verified` is true only when all replay results for the study's sessions have `match = 1`.

**Consequences:**
- No false claims of export readiness or replay verification.
- Status endpoints reflect actual evidence in the database.

---

## ADR-028: True Transactional Outbox

**Status:** Accepted
**Date:** 2026-07-14
**Context:** `PersistentOutboxWriter.publish()` buffered events in memory and only wrote them during `flush()`. A crash between a domain `db.commit()` and the subsequent outbox write would lose the event, breaking the outbox pattern's atomicity guarantee.

**Decision:** `publish()` inserts the outbox row immediately into the database within the caller's active transaction. `flush()` becomes a no-op. Every `db.commit()` that follows a domain write + `sink.publish()` atomically persists both.

**Consequences:**
- Domain state and outbox events are always consistent after commit.
- Rollback removes both domain record and outbox event.
- Dispatcher delivery remains at-least-once after commit.

---

## ADR-029: Export Validation Before Publication

**Status:** Accepted
**Date:** 2026-07-14
**Context:** The previous export service renamed the staging directory to the final target before running validation. On overwrite, it deleted the existing export before verifying the replacement. `checksums.sha256` included itself (circular). `metadata.json` was written after checksums (not covered).

**Decision:** Write metadata.json before checksums. Exclude checksums.sha256 from itself. Validate the complete staging package before any rename. Use backup/swap for safe overwrites. Persist export records with granular status/validation columns.

**Consequences:**
- Invalid exports are never published to the final path.
- Overwrite never destroys a valid export before the replacement is verified.
- `export_ready` is evidence-derived from the newest persisted record with `status=valid`.

---

## ADR-030: Complete Versioned Manifest Dependencies

**Status:** Accepted
**Date:** 2026-07-14
**Context:** Session manifests lacked many dependency fields (feature processor, state estimator, metric processor, curriculum processor, clock, ID generator). The manifest used a weaker `_canonical_json()` than the replay canonicalizer. `git_sha` defaulted to `"synthetic"`.

**Decision:** Expand manifests to include all pipeline component IDs, versions, and config hashes. Unify canonicalization using the replay validator's `canonical_serialize()`. Resolve `git_sha` dynamically at import time via `git rev-parse HEAD`. Create a dependency registry for component resolution during replay. Replay fails closed on any mismatch.

**Consequences:**
- Every session manifest is a complete, verifiable bill of materials.
- Replay can reconstruct exact dependencies from the manifest.
- Unknown or mismatched components cause replay failure (fail-closed).

---

*Last updated: 2026-07-14 — PR Gate R0*
