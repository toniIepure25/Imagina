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

## ADR-031: Objective Imagery Reconstruction Error as Primary Endpoint

**Status:** Accepted
**Date:** 2026-07-14
**Context:** Previous primary outcome was self-reported vividness (subjective, Likert scale). This does not distinguish genuine imagery improvement from demand characteristics, expectancy, or response bias.

**Decision:** The primary endpoint is a standardized multi-feature objective imagery reconstruction error (composite of orientation, hue, spatial frequency, position, and size errors). Subjective vividness is retained as a secondary construct only.

**Consequences:**
- The system can detect genuine imagery improvement vs. subjective-only change.
- Falsification tests can verify that the system correctly handles subjective-only scenarios.
- No vividness, confidence, or effort measure is labeled as objective.

---

## ADR-032: Separate Objective and Subjective Constructs

**Status:** Accepted
**Date:** 2026-07-14
**Context:** Previous design treated vividness as the primary measure, conflating objective and subjective outcomes.

**Decision:** Six constructs are explicitly separated: imagery precision (objective), imagery control (objective), imagery stability (objective), metacognitive calibration (objective), subjective vividness (subjective secondary), perceptual/motor control (negative control).

**Consequences:**
- Endpoint registry enforces objective/subjective classification.
- Analysis reports clearly label which results are confirmatory vs. exploratory.
- Subjective-objective dissociation is a testable hypothesis.

---

## ADR-033: Simulation-Based Power Analysis

**Status:** Accepted
**Date:** 2026-07-14
**Context:** Previous power analysis used formula-based approximation (F-test) which cannot account for the complexity of the within-subjects crossover design with hierarchical data.

**Decision:** Power analysis uses full Monte Carlo simulation: generate complete studies with the cognitive agent model, run the exact confirmatory analysis, and record operating characteristics across multiple scenarios.

**Consequences:**
- Power estimates account for actual model complexity, missingness, and design features.
- Type-I error is directly validated under strict null scenarios.
- Monte Carlo SE is reported; power values are not presented as exact.
- Multiple adversarial scenarios (practice-only, subjective-only, carryover) are tested.

---

## ADR-034: Williams Sequences for Counterbalancing

**Status:** Accepted
**Date:** 2026-07-14
**Context:** Initial simulation used fixed condition ordering, creating systematic confounding between condition and session index.

**Decision:** Use balanced Williams sequences (6 orders for 3 conditions) to counterbalance conditions across participants. Each condition appears equally in each period.

**Consequences:**
- Eliminates systematic condition-period confounding.
- Type-I error under null is controlled.
- Carryover effects can be estimated.

---

## ADR-035: LeakageGuard for Adaptation/Evaluation Separation

**Status:** Accepted
**Date:** 2026-07-14
**Context:** Adaptive feedback policies could potentially access confirmatory endpoint values from the same trial, creating circular reasoning where the outcome being evaluated is influenced by the evaluation itself.

**Decision:** `LeakageGuard` class automatically detects and blocks reserved fields (composite_endpoint_score, component_errors, etc.) from being passed to the adaptive policy. Automated tests verify leakage prevention.

**Consequences:**
- Objective evaluation outcomes are structurally separated from online adaptation signals.
- Leakage attempts are detected and can be reported.
- The separation is testable and falsifiable.

---

---

## ADR-025: SHA-256 Deterministic RNG Streams

**Status:** Accepted
**Date:** 2026-07-14
**Context:** Python built-in `hash()` is non-deterministic across processes and `PYTHONHASHSEED` values. Scientific simulation results must be exactly reproducible.

**Decision:** All scientific randomness uses `hashlib.sha256`-based `derive_seed()` with explicit canonical serialization, organized into 14 named streams. No use of built-in `hash()` for scientific seeds.

**Consequences:**
- Identical results across processes, machines, and CI environments.
- Named streams ensure changing one RNG (e.g., dropout) doesn't affect others (e.g., stimulus generation).
- RNG version tracked in every manifest and simulation result.

---

## ADR-026: Observed-Scale Causal Oracle

**Status:** Accepted
**Date:** 2026-07-14
**Context:** The C0 simulation truth was a latent-parameter contrast (`adaptive_precision_effect - yoked_practice_effect`), not the actual primary estimand measured by the analysis. Bias and coverage calculations were comparing different quantities.

**Decision:** Oracle computes counterfactual potential outcomes `E[Y(adaptive) - Y(yoked)]` on the observed composite reconstruction error scale using common random numbers and production scoring code.

**Consequences:**
- Simulation bias and coverage now compare estimates to the same quantity the analysis targets.
- Oracle effect is approximately zero under strict null (verified: −0.001035).
- Oracle can detect scenario-specific effects (medium adaptive: −0.043371).

---

## ADR-027: Multi-Estimator Confirmatory Inference

**Status:** Accepted
**Date:** 2026-07-14
**Context:** A single MixedLM fit is fragile — it can silently produce invalid standard errors, singular covariance, or non-convergent results.

**Decision:** Three prespecified estimators (GEE marginal, Hierarchical MixedLM, Randomization Inference) with explicit convergence detection and fallback semantics. `inference_valid=False` results never count as rejection or coverage.

**Consequences:**
- Non-converged models are clearly distinguished from valid results.
- Fallback rate is tracked separately from convergence rate.
- Current N=18 design causes 100% fallback — this is correctly detected and flagged.

---

## ADR-028: Primary Estimator Convergence Limitation — SUPERSEDED by ADR-029

**Status:** Superseded
**Date:** 2026-07-14
**Context:** With N=18 participants in a 3-period crossover, the primary GEE/MixedLM models with full adjustment (period, sequence, task family, carryover) do not converge. This produces 100% fallback rate and 0% valid inference.

**Decision:** Document as a known limitation rather than weakening the model or permitting permissive thresholds. The campaign correctly identifies this as a gate issue.

**Superseded by:** ADR-029 resolved convergence by switching to a proper GEE estimator with bias-reduced SE.

---

## ADR-029: GEE with Mancl-DeRouen Correction as Primary Estimator

**Status:** Accepted
**Date:** 2026-07-14
**Context:** The MixedLM-based estimator from C0.1 produced 100% fallback. The issue was not sample size but estimator choice: MixedLM requires ML/REML optimization of random-effect variance, which is unstable with few clusters. A marginal GEE with exchangeable working correlation avoids random-effect estimation entirely.

**Decision:** Use `statsmodels.GEE` with `Gaussian()` family, `Exchangeable()` correlation, and `cov_type="bias_reduced"` (Mancl-DeRouen small-sample correction). This produces valid inference at N=18 with type-I ≈ 0.05 and coverage ≈ 0.95.

**Consequences:**
- 100% valid_inference_rate, 0% fallback_rate at N=18
- Robust sandwich SE with small-sample correction avoids liberal type-I error
- MixedLM is retained as sensitivity analysis (`random_intercept_sensitivity`)
- Bootstrap resamples clusters and refits GEE for interval estimation

---

## ADR-030: All Science APIs Must Be DB-Backed

**Status:** Accepted
**Date:** 2026-07-14
**Context:** C0.1 used in-memory dictionaries (`_SIMULATION_RUNS`, `_ANALYSIS_RUNS`, etc.) for science endpoints. These are lost on restart and cannot be audited.

**Decision:** All research-science API endpoints read/write exclusively to the authoritative SQLite database using v007/v008 tables. In-memory caches are prohibited. Idempotency keys prevent duplicate runs.

**Consequences:**
- Campaign results survive restarts
- Export packages can be rebuilt from DB at any time
- Replay reconstructs sessions from persisted trial specs, responses, and scores
- Manifests and seals are persisted for provenance auditing

---

## ADR-031: Transactional Objective Task Execution

**Status:** Accepted
**Date:** 2026-07-14
**Context:** Objective trial execution must be atomic: if a leakage violation occurs mid-session, no partial results should remain in the database.

**Decision:** `execute_objective_session_persistent` inserts trial specs, responses, and scores per-trial within a transaction. LeakageGuard is checked BEFORE finalization — violations cause rollback. Seals are only written after all trials complete.

**Consequences:**
- No orphaned trial records on leakage violations
- Each trial's spec/response/score triple is atomically committed
- Leakage audit records are persisted alongside trial data

---

## ADR-032: Indicator Coding for Causal Contrast Identity

**Status:** Accepted
**Date:** 2026-07-14
**Context:** The previous effect coding (adaptive=1,yoked=-1) made the GEE coefficient represent the deviation from the unweighted grand mean, not the adaptive−yoked contrast. This caused the coefficient to be misaligned with the oracle estimand, producing zero coverage for medium_adaptive.

**Decision:** Use indicator (reference) coding: `adaptive_ind = 1 if adaptive else 0`, `fixed_ind = 1 if fixed else 0`, with yoked as the zero reference. The coefficient on `adaptive_ind` now equals `adjusted E[Y|adaptive] − E[Y|yoked]` — identical to the oracle estimand.

**Consequences:**
- Known-means test verifies recovery of exact contrast values
- medium_adaptive coverage is now 0.967 (was 0.0)
- All 10 scenarios pass at 1000 replicates

---

---

## ADR-033: Replay Reconstructs Inputs Exclusively from Sealed DB Evidence

**Status:** Accepted
**Date:** 2026-07-15
**Context:** Earlier replay accepted caller-provided trial_specs, scenario, seed, and response provider. This violated the fail-closed principle because corrupted or mismatched inputs could produce spurious exact matches.

**Decision:** `replay_from_db(db, session_id)` is the sole replay API. All replay inputs (scenario, trial specs, seed, response provider) are resolved from the canonical persisted manifest, frozen design, schedule rows, and scenario specification. No caller-provided authoritative inputs accepted.

**Consequences:**
- Replay is truly fail-closed: missing or corrupted evidence always fails
- exact_match requires ALL verification flags (manifest, seal, schedule, scoring, response_provider, content_hash)
- Cannot replay sessions that lack manifest or seal records

---

## ADR-034: Durable Science Worker with Atomic Claiming

**Status:** Accepted
**Date:** 2026-07-15
**Context:** POST /simulations previously called run_simulation() synchronously, making execution non-durable and blocking the HTTP response.

**Decision:** POST /simulations returns 202 immediately with status=queued. A dedicated ScienceWorker claims runs atomically using compare-and-set UPDATE with lease management. Workers can reclaim queued, checkpointed, or expired-lease runs. Cooperative abort via persisted abort_requested flag.

**Consequences:**
- Simulation execution survives process restart
- Two workers cannot claim the same run (atomic CAS)
- Abort is cooperative and preserves checkpoints
- v010 migration adds lease/abort/checkpoint columns

---

## ADR-035: Multi-Session Export Outbox Validation

**Status:** Accepted
**Date:** 2026-07-15
**Context:** Export validation assumed exactly one objective_session_completed event (formula: n_trials * 4 + 1). Multi-session exports have one completion event per session.

**Decision:** Count actual objective_session_completed events in outbox_events. Expected outbox count = n_trials * 4 + max(n_completion_events, 1).

**Consequences:**
- Single-session and multi-session exports both validate correctly
- Formula remains strict (exact count match required)

---

## ADR-036: Incremental Simulation with Sufficient-Statistics Accumulator

**Status:** Accepted
**Date:** 2026-07-15
**Context:** The science worker updated checkpoint_iteration without executing actual replicates. Resume ran full n_iterations regardless of checkpoint position.

**Decision:** Introduce `SimulationAccumulator` with sufficient statistics (valid/invalid counts, rejection counts, estimate sums/squared sums, coverage counts, width sums). `run_simulation_batch()` executes deterministic replicate ranges with absolute seed `base_seed + r * FROZEN_STRIDE`. Accumulator is serialized to JSON and persisted in `simulation_checkpoints` table after every batch. Resume loads persisted accumulator and continues from the checkpoint iteration.

**Consequences:**
- Worker executes real replicates in every batch
- Checkpoint includes actual evidence (not just iteration counter)
- Resume provably skips completed replicates
- Slight floating-point difference between uninterrupted and resumed runs due to float associativity across batch boundaries (within 1e-5 tolerance)

---

## ADR-037: Replay Inputs Resolved Exclusively from Sealed Manifest

**Status:** Accepted
**Date:** 2026-07-15
**Context:** replay_from_db used hardcoded `seed = 42`, `prev_condition = None`, and scenario fallback `next(iter(SCENARIOS.values()))` — violating fail-closed provenance.

**Decision:** Add `root_seed`, `previous_condition`, `participant_generation_index`, `scenario_id` to ObjectiveManifest. Replay resolves all inputs from manifest; missing values produce structured divergences and prevent exact_match. `response_provider_verified` requires ID, version, AND config hash. `schedule_verified` requires three-way hash match (DB, manifest, recomputed).

**Consequences:**
- No replay-critical value inferred from defaults
- All existing replay tests updated to supply new manifest fields
- Strict three-way schedule verification prevents hash drift

---

## ADR-038: All-Valid Export Semantics

**Status:** Accepted
**Date:** 2026-07-15
**Context:** Export validation used "any valid result" semantics for inference and campaigns — one valid result could mask failures.

**Decision:** `package.inference_valid = bool(required) and all(r.inference_valid for r in required)`. `package.campaign_valid = bool(required) and all(c.campaign_valid for c in required)`. Persist `invalid_inference_ids`, `failed_campaign_ids`, and counts. Export replay validation requires all 7 verification flags.

**Consequences:**
- One invalid inference or failed campaign invalidates the entire package
- Explicit tracking of which results failed and why


## ADR-039: ANIMUS-P2-R VALIDATED — preserve the P2E block as a snapshot; advance the live decision

**Status:** Accepted
**Date:** 2026-09-26
**Context:** The P2E ROI-spatial-provenance block and the P2 confirmatory decision share one live file
(`results/animus_p2/ANIMUS_P2_SCIENTIFIC_DECISION.json`). ANIMUS-P2-R recovered the MNI2009c provenance and
the sealed decoder returned `ANIMUS_P2_PERCEPTION_DECODER_VALIDATED` (2/6 NOD subjects), so the live file
must legitimately advance — but the P2E historical block and its guards/tests must not be falsified.

**Decision:**
- Preserve the P2E block byte-for-byte as `results/animus_p2e/ANIMUS_P2E_DECISION_SNAPSHOT.json` (self-hash
  intact; normalized SHA equals the anchor-pinned hash).
- Repoint `p2r_anchor.json` immutable ref for the P2 decision to that snapshot (same file_sha256) and
  re-self-hash the anchor.
- P2E guard/test now check the historical block on the snapshot; P2R guard/test replace the pre-result
  "perception BLOCKED" check with a confirmatory-firewall check (freeze committed before any metric
  inspected) + a legitimate-outcome check. The invariant "imagery is never authorized by a perception
  advance" is asserted on the LIVE file in both suites.
- The real product bridge (`run_p2_product_bridge.py`) runs only when the live decision is VALIDATED and is
  gated by the capability enforcement; no product tuning.

**Consequences:**
- CI stays green across the milestone advance without rewriting history.
- The historical block remains auditable and byte-verifiable; a future FAIL/LIMITED re-run would still be
  representable on the live file without touching the snapshot.
- PERCEPTION_NEURAL_CONTENT=VALIDATED; imagery/dream/reconstruction UNAUTHORIZED; C3XAG unauthorized.

---

## ADR-040: Multimodal research platform as a separate package with a shadow-first controller

**Context:** The platform must add ECG/HRV, EDA, respiration, fNIRS, MEG and fMRI next to EEG, synchronize streams,
fuse them, and close the loop with Dream Corridor, without breaking the existing FeatureVector-based session stack,
the ANIMUS research tree, or the NeuroVerse export.

**Decision:**
- New package `backend/app/multimodal/` with raw-sample providers (`SampleChunk`), a per-stream clock model
  (`sync.py`), per-modality pipelines emitting `FeatureSet`s whose every value carries an `EvidenceClass`, a
  calibrated `ImageryStateEstimator`, and a `FeedbackController` state machine. Existing modules are reused, not
  modified (safety keywords, prompts, `FeedbackAction`, Holm, bootstrap).
- `ACTIVE_SHADOW` is the default mode. `FEEDBACK_RESEARCH` with any REAL_SENSOR stream requires a complete
  `FeedbackAuthorization`; synthetic/replay sessions may use it to exercise the control path.
- Safety gates precede the policy and can only make feedback more conservative. Unknown alignment uncertainty
  (host-receive timestamps) holds adaptation by default.
- Vividness is never inferred from physiology unless a registered predictor card says `VALIDATED`; the
  perception-imagination distance is a research metric with `objective_allowed=False`, and policies declaring it
  (or arousal maximization, reality confusion, dissociation) as an objective are rejected.
- Decisions are hash-chained; `replay_controller` re-executes logged inputs and must reproduce every hash.
- MEG/fMRI are offline-only (`StreamInfo` rejects real-time synthetic/replay MEG/fMRI).
- Biosignals are stored as chunked HDF5 per stream with a JSON manifest; review bundles exclude raw arrays unless
  the consent record allows it.

**Consequences:**
- The legacy session/WebSocket stack is untouched; integration with it (and SQLite persistence of multimodal
  manifests) is follow-up work.
- All current results are synthetic and labeled as such in the API, UI and reports.

---

*Last updated: 2026-10-12 — ADR-040 multimodal research platform*

---

## ADR-041: ANIMUS Studio uses a symbolic scene graph as canonical product state

**Status:** Accepted
**Date:** 2026-10-22
**Context:** The P1 engine produces belief/candidate envelopes but had no durable, editable product object.
A photoreal image model would hide provenance, add network/privacy risk, and invite unsupported imagery-content
claims. The product needs a visible candidate that can be corrected precisely, locked, diffed, versioned,
branched, and reopened.

**Decision:** The Studio's canonical state is the versioned **ANIMUS-SG-v1** symbolic `SceneGraph`. All edits are
typed commands, all versions are immutable and content-hashed, and regeneration is a seeded perturbation that
preserves locked paths and `USER_EXPLICIT` values. Rendering is local procedural React Three Fiber; candidate
thumbnails are CSS palettes. Persistence is additive SQLite migrations v014–v015. The Studio claim ceiling is
`L1_BEHAVIORAL_ASSISTED`; image generation is DISABLED and neural/dream/reconstruction content is UNAUTHORIZED.

**Consequences:**
- Every candidate is explainable and diffable; locks are enforceable rather than a UI convention.
- The renderer approximates rather than reconstructs; unknown parser nouns become abstract forms.
- No image model, upload, external inference, or new scientific claim is introduced.
- P1 APIs/tables and the frozen research artifacts are untouched; the old `/imagina/animus` route redirects.

---

*Last updated: 2026-10-22 - ADR-041 ANIMUS Studio*

---

## ADR-042: ANIMUS Studio writes are serialized, atomic, and optimistically checked

**Status:** Accepted
**Date:** 2026-10-22
**Context:** The first vertical slice persisted a commit through several independent SQLite calls
(version, branch, session, event). A crash or a concurrent request could leave a version the session did
not point at, two requests could commit from the same head, and a selected candidate could remain visible
as a stale candidate. The client also had no way to distinguish a stale view from a validation error.

**Decision:** Run one local process with a per-session `asyncio.Lock`. Persist each product mutation as a
single SQLite transaction (session head + version + branch + event, plus candidate selection where
relevant). Publish bus events only after commit; if the write fails, evict the runtime so the next request
reloads durable state. Scope candidates to `source_version_id`, hide selected candidates, reject stale
selection, and add an optional `X-Expected-Version` request header that returns `409 stale_version`.
Versions use strict inserts; branches/candidates use keyed upserts. v016 adds only the supporting indexes.

**Consequences:**
- A crash cannot expose a version that is not the session/branch head.
- Concurrent requests can no longer fork one branch silently; stale clients receive a typed conflict.
- Single-process is now an explicit product assumption; horizontal scaling would require a durable lock
  or a database-level optimistic check, which is out of scope for the local product.
- Existing clients remain compatible: omitting the header keeps last-write-wins, and error bodies keep
  their string `detail`; the stable code travels in `X-Studio-Error-Code`.
- No new dependency, external call, neural data path, or claim surface is introduced.

---

## ADR-043: ANIMUS Studio has one explicit typed wire contract

**Status:** Accepted
**Date:** 2026-10-23
**Context:** The Studio service returns JSON-compatible dictionaries and the first client duplicated
their shape inline. That made additive scene fields easy to add but made required fields, optional
clarification fields, and frontend command/WS unions easy to drift apart. OpenAPI described almost
nothing beyond request bodies.

**Decision:** Declare a Pydantic response model for every successful Studio route in
`backend/app/schemas/animus_studio_responses.py`, with `extra="allow"` so additive renderer metadata
does not break older clients. Keep internal persisted shapes in runtime-free `TypedDict`s under
`backend/app/core/animus/studio/types.py`. Mirror the same contract in `frontend/lib/animusStudioApi.ts`,
including intent/commands/regenerate snapshot variants, version detail, history, health, worlds,
the complete command union, and the WS message envelope. The service remains framework-independent;
FastAPI is only the serialization boundary.

**Consequences:**
- OpenAPI and the client now describe the same snapshot fields, including `entity_count` and world
  item `world_id`.
- A response model mismatch fails the contract test rather than silently changing the wire format.
- Additive fields remain compatible by design; removing or renaming a required field is now a visible
  contract change.
- No new dependency, external call, neural data path, or claim surface is introduced.

---

## ADR-044: Studio redo is branch-scoped and durable

**Status:** Accepted
**Date:** 2026-10-23
**Context:** Undo/redo was held only in the in-memory `RevisionStore`. The branch head was durable, but a
restart after undo lost the redo stack. Reconstructing it from version parents is unsafe: a new commit
after undo creates a sibling, and guessing which siblings were redo targets would resurrect stale history.

**Decision:** Add `redo_json` to `animus_studio_branches` in additive migration v017. Persist a branch's
redo ids in the same atomic bundle as its head (commit, undo, redo, branch, switch). Clear redo on every
new commit and persist the cleared list. Load the stack per branch into `RevisionStore.from_snapshot`;
expose `redo_ids()` for the persistence helper. Strictly decode stored branch/redo JSON and surface a
typed `corrupt_local_state` 503 rather than silently loading an empty scene.

**Consequences:**
- Undo → restart → redo works; undo → new commit → restart does not resurrect stale redo.
- The database remains the only source of truth; no extra process, cache, or dependency is added.
- A corrupt record is visible and actionable instead of being hidden by defaults.
- Existing v014–v016 databases upgrade in place; v017 is idempotent.

---

## ADR-045: The Studio live channel joins before snapshotting and signals resync

**Status:** Accepted
**Date:** 2026-10-23
**Context:** The WebSocket handler read the snapshot before subscribing to the in-process bus. A commit
between those two operations was durable but invisible to the connected client. A full queue silently
dropped the oldest event, leaving the client permanently behind.

**Decision:** Subscribe to the bus before reading the snapshot, send the snapshot first, then forward
queued events. Every event carries a stable `type: "event"` envelope with the original type in
`event_type`. When a subscriber queue overflows, drain it and insert
`{"type":"resync_required","reason":"queue_overflow"}`; the client refreshes the full snapshot. Add a
read-only `GET /sessions/{id}/events?after_seq=&limit=` cursor over the existing durable event table for
audit and reconnect recovery. Centralize Studio error-to-code mapping for HTTP and WS.

**Consequences:**
- No event committed during connection setup is lost.
- A slow client is told to resync instead of silently diverging.
- Event history is no longer write-only.
- The single-process, local-only model is unchanged; no distributed fan-out or external broker is added.

---

## ADR-046: The local API is loopback-first with an explicit Host allowlist

**Status:** Accepted
**Date:** 2026-10-23
**Context:** The product is unauthenticated by design and stores personal scene history in local SQLite.
The previous default `backend_host` was `0.0.0.0`, and the API accepted any `Host` header. A user who
started the backend on a LAN interface, or visited a malicious page while it was running, could expose the
local API beyond the intended machine. Browser CORS is not a sufficient boundary because DNS rebinding
makes the attacker page same-origin from the browser's perspective.

**Decision:** Default `backend_host` to `127.0.0.1`. Install Starlette `TrustedHostMiddleware` with an
explicit allowlist (`127.0.0.1`, `localhost`, `testserver`, `test`, `backend`), configurable through
`ALLOWED_HOSTS`. Add `Cache-Control: no-store` and `X-Content-Type-Options: nosniff` to `/animus/studio`
responses. Container images may still listen on `0.0.0.0` internally, but host port publication must be
restricted to loopback unless authentication is added.

**Consequences:**
- A default local run is not reachable from another machine.
- DNS rebinding and browser caching of scene history are blocked at the transport boundary.
- A custom hostname needs an explicit `ALLOWED_HOSTS` entry; this is intentional and documented.
- No dependency, external call, or claim change is introduced.

---

## ADR-047: Migrations are backed up first and live events carry a durable sequence

**Status:** Accepted
**Date:** 2026-10-23
**Context:** A versioned migration is the one operation that can rewrite every local Studio record at
once. The previous runner had no recovery copy if an upgrade failed mid-way. Separately, the live channel
could deliver a duplicate or could miss a low-level publish during a reconnect; clients refreshed on every
event but could not tell whether their view was already current.

**Decision:** Before a non-empty database is upgraded, run `VACUUM INTO` to a file under
`<db_dir>/backups/pre-migration-v###-to-v###-<UTC>.db`, verify it with `PRAGMA quick_check`, and retain
the five newest backups. `VACUUM INTO` is used instead of copying the main file because WAL content may
not have been checkpointed. A backup or verification failure is fatal: the runner raises and refuses to
migrate. Empty/new databases skip the copy.

Every Studio event already has a durable SQLite `seq`; repository bundles now return the inserted `seq`,
the service tracks `last_event_seq`, snapshots expose it, and bus/WS events include `seq`. Clients ignore
events at or below their last seen sequence, treat a jump greater than one as a gap, and refresh the full
snapshot immediately (duplicates are ignored, normal events keep the short debounce). Additive fields keep
older clients and servers compatible. The client also treats 60 s without any message as a dead channel
and reconnects, and aborts an in-flight mutation when a new mutation starts or the view unmounts.

**Consequences:**
- A failed upgrade leaves a consistent pre-upgrade database next to the live one; startup fails closed
  rather than continuing without a recovery point.
- Backup disk use is bounded by five files; operators can copy them elsewhere, but nothing is uploaded.
- Duplicate events no longer trigger redundant refreshes, and a dropped event produces an immediate
  resync rather than a silent divergence.
- Sequence gaps still rely on a full snapshot refresh; there is no partial replay protocol.
- No dependency, external call, neural data path, or claim change is introduced.

---

## ADR-048: Profile estimates are multidimensional, uncertainty-first, and composite-free

**Status:** Accepted
**Date:** 2026-10-23
**Context:** A single "imagination score" would hide which process failed, invite comparisons the evidence
cannot support, and make an unvalidated behavioural task look like a clinical instrument. Imagery is
multidimensional and self-report/objective measures correlate only minimally.

**Decision:** Keep separate behavioural estimates for scene stability, discrimination, spatial view,
control, and confidence calibration. Ability estimates use a Beta-Binomial posterior (uniform prior) with
`n`, posterior uncertainty, and explicit `collecting/provisional/moderate` status. Calibration uses a Brier
score computed from confidence and outcome, separate from ability. Do not compute or display a composite.
Hide an estimate until at least three trials exist, and always show evidence count and limitations next to
the number. Calibration has no scalar ability estimate (`estimate = null`); its Brier score is withheld until
three confidence-rated trials, so `1 - Brier` cannot be relabelled as an accuracy score.

**Consequences:**
- The profile cannot be reduced to one leaderboard-friendly number.
- Sparse dimensions stay visibly uncertain instead of defaulting to a flattering or alarming value.
- The model is inspectable and reproducible with the standard library; no new dependency.
- A future validated instrument can replace the estimator behind the same payload contract.

---

## ADR-049: Adaptive practice is deterministic, server-scored, and evidence-seeking

**Status:** Accepted
**Date:** 2026-10-23
**Context:** An adaptive loop that sends the answer to the browser, or picks tasks by engagement, would be
easy to game and would not produce interpretable evidence. A fixed curriculum would leave some dimensions
unmeasured for a long time.

**Decision:** Rebuild each task on the server from `(scene, task_type, seed, difficulty)` and never publish
`correct_option_id` before submission. Return a `task_id` fingerprint over the scene hash and task identity;
submission must present the same fingerprint, so an edited scene cannot silently reuse an old task. Select
the first two trials for stability and calibration, then
prefer the dimension with the fewest trials, with a seeded tie-break. Adjust difficulty by a bounded step
after a short rolling window, clamped to `[0.1, 0.9]`; do not use streaks, timers, or engagement signals.
Submission is idempotent per `client_trial_id` (checked before the version guard so a retry still returns
the saved trial), and `expected_version_id` rejects a task whose source scene has changed.

**Consequences:**
- A client cannot read the answer and cannot silently retry a mutated task under the same id.
- Task generation and scoring are replayable from a seed for audit and tests.
- The policy deliberately favours coverage over short-term success rate.
- Difficulty is a heuristic challenge point, not a validated threshold.

---

## ADR-050: The behavioural profile is experimental and never a diagnosis

**Status:** Accepted
**Date:** 2026-10-23
**Context:** Aphantasia and hypophantasia are variations in imagery experience, not deficits. The
measurement literature does not support diagnosis from a short local task, far transfer from cognitive
training, or claims that imagery strength was increased.

**Decision:** Publish the profile under `L1_BEHAVIORAL_ASSISTED` with `behavioral_profile =
EXPERIMENTAL`, `adaptive_practice = EXPERIMENTAL`, and `clinical_use = DISABLED`. Every profile payload
carries limitations and a no-diagnosis statement. Copy describes task performance and confidence
calibration, never imagery strength, neural content, treatment, or enhancement. The product does not claim
far transfer, a cure, or brain training.

**Consequences:**
- The instrument can be useful for reflection and research scaffolding without implying clinical validity.
- Aphantasic users are treated as a design variation; the UI never frames low imagery as failure.
- Any future clinical or enhancement claim requires a separate validated protocol and ethics review.
- The capability envelope makes the boundary machine-readable, not just editorial.

---

---

## ADR-051: Reconstruction is a behavioural proxy, not neural reconstruction

**Status:** Accepted
**Date:** 2026-10-23
**Context:** Multiple-choice tasks capture recognition but not how much of an object set or layout survives.
Drawing-from-memory studies show that reconstruction can expose object and spatial content, and aphantasia
work suggests object detail and spatial accuracy can dissociate. ANIMUS has no neural decoder and must not
imply one.

**Decision:** Add two deterministic reconstruction task families: `object_reconstruction` (token selection,
F1 with omissions/intrusions) and `spatial_layout` (normalized placement, mean position score and error).
Both are generated from the symbolic scene, scored server-side under `recon-v1`, and never send target flags
or target positions before submission. Persist `task_family`, `response_kind`, `scoring_version`, and
`error_profile_json` in migration v019. Show object and spatial scores separately; aggregate the error
signature descriptively; do not create a composite.

**Consequences:**
- The instrument gains a richer behavioural record without gaining a neural claim.
- Token composition and grid tolerance are versioned instrument choices and require validation.
- The local session still contains the target scene; the UI hides it, but this is not a secure assessment.
- `neural_reconstruction` remains `UNAUTHORIZED`; the claim ceiling remains L1.

---

## ADR-052: Adaptive selection uses a coverage floor and expected information gain

**Status:** Accepted
**Date:** 2026-10-23
**Context:** Coverage-first selection guarantees some evidence per dimension but can waste trials on
dimensions with narrow posteriors. Pure information gain can starve a dimension with little evidence. The
adaptive-testing literature supports uncertainty-aware selection in simulation, not as a validated policy
for this instrument.

**Decision:** After two warmup trials, select any dimension with `n < 2` first. Otherwise select the
dimension with the highest expected information gain over the Beta posterior at the current difficulty.
Keep calibration cross-cutting: it is updated on every trial but is not selectable. Keep the existing
bounded challenge-point difficulty controller. Record the reason and expected gain in the adaptive payload.
Provide a deterministic simulation harness comparing coverage-first, information-gain, and fixed-cycle
policies.

**Consequences:**
- The policy is inspectable, seeded, and testable.
- Simulation results are policy mechanics, not human validation.
- If human or simulation evidence shows a regression, coverage-first remains a simple fallback.
- The policy still assumes exchangeable trials and a one-dimensional ability per task family; those
  assumptions are open validation questions.

---

## ADR-053: The epistemic interview reports a posterior, not a decoded image

**Status:** Accepted
**Date:** 2026-10-23
**Context:** Reconstruction produces a single behavioural score after the fact. It does not expose how
uncertainty changed or which observation was most informative. A binary probe with a confidence rating can
support an inspectable belief-update trace without crossing the L1 boundary. The design is informed by
adaptive-testing and scene-memory work, but no direct human validation of this interview exists.

**Decision:** Add `eri-v1` as a separate behavioural surface. Use a mean-field `Beta(1, 1)` posterior for
object presence and spatial relations; update it from the answer and confidence, mapping the hidden state to
the positive option (`present`/`left`) before updating; force one object and one spatial probe for coverage
when available; then select by expected information gain. Permit abstention, report coverage and
Brier separately, and never expose the hidden answer in the probe payload. Persist interview headers in
migration v020 and probe metadata on the existing trial ledger. Report no composite score.

**Consequences:**
- The interview is inspectable, deterministic, local-only, and separable from the five profile dimensions.
- The Beta response model is a design choice, not a fitted psychometric model.
- Abstention is data, not a correctness failure.
- The simulation can test policy mechanics only; human validity, calibration fit, and test–retest
  reliability remain open.
- `neural_reconstruction` remains `UNAUTHORIZED`; `clinical_use` remains `DISABLED`; the claim ceiling remains
  `L1_BEHAVIORAL_ASSISTED`.

---

## ADR-054: Scene Threshold uses 2-AFC sensitivity and reports no criterion

**Status:** Accepted
**Date:** 2026-10-24
**Context:** The profile and ERI both ask the person to report or reconstruct content. Neither estimates a
detection limit for a small scene change. A 2-AFC contrast task can measure sensitivity and a within-scene
threshold while keeping the target side hidden and the task local. In 2-AFC the yes/no criterion is not
identified, so reporting a criterion would be statistically misleading.

**Decision:** Add `contrast-v1` / `sdt-v1`. Build a pair from the encoded scene and one minimally changed
variant; withhold target side, feature, and delta; use a 2-down/1-up staircase for continuous features;
fit `p_correct(delta) = 0.5 + 0.5(1-lapse)sigmoid((delta-threshold)/slope)`; report d′, signed side bias,
per-feature thresholds, Brier/overconfidence/type-2 AUC when identifiable, and coverage. Persist sessions and
trials in migration v021. Add an observatory that exposes ERI evidence provenance, leave-one-out sensitivity,
and feature-level test–retest r/SEM/MDC95, with `insufficient` when fewer than three features align.

**Consequences:**
- No `criterion`, imagery-strength score, cross-scene norm, composite, or clinical category.
- Thresholds are within-scene normalized units; a lower value means finer discrimination, not stronger
  imagery.
- Two continuous feature types make reliability usually `insufficient`; that is honest, not a bug.
- No per-trial correctness feedback; the aggregate result appears only at completion.
- No new dependency, no image model, no external call; `local_only` and `L1_BEHAVIORAL_ASSISTED` remain.
- Human validation and recovery bias remain open; the simulation is not a validation study.

---

*Last updated: 2026-10-24 - ADR-051 reconstruction proxy, ADR-052 information-gain policy, ADR-053
epistemic interview, ADR-054 Scene Threshold 2-AFC*
