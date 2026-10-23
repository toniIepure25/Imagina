# ANIMUS — Architecture (P1)

ANIMUS sits **above** IMAGINA's observation, belief, generation, feedback, and control layers and reuses
the existing runtime (event store, WebSocket, session/safety patterns). It does not fork a parallel app.

## Layers (`backend/app/core/animus/`)
| Module | Responsibility |
|---|---|
| `claims.py` | Claim-level ladder (L0–L3) + authorization ceiling (L1) + forbidden-phrase audit |
| `vocab.py` | Versioned structured-attribute + object vocabulary (IBS-v1) |
| `models.py` | `ImaginationBeliefState` (IBS-v1), embeddings, observation/feedback/candidate envelopes, hashing |
| `belief_state.py` | `BeliefFusionEngine` — Gaussian + categorical + comparative updates; named `FusionConfig` |
| `synthetic_imaginer.py` | Digital twin (hidden `z_target`, noisy responses) — evaluator-only |
| `decoder.py` | `NeuralContentDecoder` contract + `SyntheticNeuralDecoder` (future-pluggable) |
| `observation.py` | `ObservationProvider`s: behavioral / simulated-neural / replay / future-neural (fail-closed) |
| `feedback.py` | Normalize all feedback channels → `FeedbackEvidence`; free-text → structured |
| `candidate_generator.py` | Generators + `BeliefToGenerationSpec` **privacy boundary** |
| `controller.py` | `AnimusActiveController` + baselines (static/random/greedy) + `AnimusPolicyConfig` |
| `metrics.py` | Benchmark-only vs real-user metrics; `AmplificationSessionSummary` |
| `personalization.py` | `AnimusUserModel` (local-first, non-clinical) |
| `loop_runtime.py` | First-class state machine (INITIALIZE…COMPLETE/ABORT), events, replay hashes |
| `benchmark.py` | Blind-target campaign + `TwinRespondent` |
| `replay.py` | `AnimusReplayManifest` + determinism verification |
| `evidence_registry.py` | Science→product boundary (references C3XAT/C3XRP/C3XRA, no reinterpretation) |
| `service.py` / `sdk.py` | Session registry + typed SDK facade |

## The loop as a state machine
`INITIALIZE → CALIBRATE → (OBSERVE → INFER → GENERATE → PRESENT → COLLECT_FEEDBACK → UPDATE_BELIEF →
SELECT_NEXT_ACTION → CHECK_CONVERGENCE → CONTINUE)* → COMPLETE | ABORT`. Every transition is typed,
timestamped, event-logged, and deterministic under a seed; belief hashes are recorded per step so a session
replays bit-exactly.

## Central representation — IBS-v1
Model-independent belief: Gaussian **visual** + **semantic** embeddings (mean + diagonal variance, each with
an `EmbeddingSpec` so CLIP is not assumed permanent), categorical **scene attributes**, **object** presence
probabilities, **spatial relations**, per-component confidence, and a global uncertainty. The system never
pretends to know one exact mental image — candidates are generated from the belief distribution.

## Pluggable neural boundary
`ObservationProvider` unifies evidence sources. A future validated decoder implements `NeuralContentDecoder`
and is exposed via `FutureNeuralDecoderProvider` — the controller and loop are unchanged. In P1 that
provider **fails closed** (no validated decoder, no scientific authorization).

## Privacy boundary
Generators receive only a sanitized `GenerationSpec` (semantic summary, scene graph, approved small
embedding, seed). Raw neural arrays, biosignal time series, and identifiers can never reach a generator —
enforced by `assert_no_forbidden_content` and a privacy test. No cloud API; CI uses deterministic adapters.

## API / SDK / events
`app/api/animus.py` exposes sessions, step/observe/feedback, belief/candidates/timeline/replay, and a
bounded benchmark run. Events (`animus.session.started`, `.observation.received`, `.belief.updated`,
`.candidate.generated/presented`, `.feedback.received`, `.controller.action`, `.convergence.updated`,
`.safety.event`, `.session.completed`) are persisted and drive the live workspace.

---

# ANIMUS Studio — product layer (additive)

The Studio is a **product surface over a symbolic scene**, not a new scientific claim. It reuses the
P1 belief/controller stack unchanged and adds a local, versioned scene-authoring loop:

```
intention → candidate scene → correction → new immutable version → regenerate →
select candidate → keep / undo / branch / save world → reopen and continue
```

## Canonical state — ANIMUS-SG-v1
`backend/app/core/animus/scene/model.py` defines an immutable, hashable `SceneGraph`: entities (kind,
transform, attributes with provenance/confidence/lock), relations, camera, lighting, atmosphere,
dynamics, and constraints. Every mutation is validated and hashed. `content_hash()` is the identity of a
version and is exposed to the client, so "same scene" is checkable rather than asserted.

Provenance is explicit: `USER_EXPLICIT`, `USER_IMPLIED`, `SYSTEM_DEFAULT`, `SYSTEM_INFERRED`,
`SIMULATED`. Neural provenance is fail-closed; product code cannot construct a scene whose provenance
claims imagery content.

## Meaning boundary
| Module | Responsibility |
|---|---|
| `scene/library.py` | Versioned object vocabulary, colours, styles, times, moods, attribute specs |
| `scene/compose.py` | Deterministic intention → scene composition; unknown nouns become abstract forms + warnings |
| `scene/intent.py` | Bounded natural-language corrections → typed commands + resolutions + clarification |
| `scene/commands.py` | Eight typed commands; every command validated; locked content cannot change |
| `scene/diff.py` | Added/removed/changed/locked-untouched explanation for every version |
| `scene/revisions.py` | Immutable versions, undo/redo, branch-from-version, deterministic numbering |
| `scene/regenerate.py` | Seeded candidate variants; preserves locks and `USER_EXPLICIT` edits |
| `scene/resolve.py` | Bridge from an IBS-v1 belief to an L0 symbolic scene |
| `studio/repository.py` | Local SQLite persistence; WAL, schema lock, atomic write bundles |
| `studio/service.py` | Async product service, per-session serialization, snapshot contract |
| `studio/errors.py` | Typed product errors shared by service, API, and WebSocket |
| `studio/types.py` | Runtime-free TypedDicts for persisted records, summaries, and event payloads |
| `studio/locks.py` | Per-session `asyncio.Lock` registry |
| `studio/claims.py` | Studio claim/phrase guard and capability envelope |
| `studio/bus.py` | In-process pub/sub; overflow emits `resync_required` instead of silently losing updates |
| `api/animus_studio_ws.py` | Live channel: Origin check, subscribe-before-snapshot, typed errors, intent |

## Persistence — migration v014 (additive)
New tables only: `animus_studio_sessions`, `_versions`, `_branches`, `_events`, `_candidates`,
`_commands`, `_worlds`, `_world_items`. No existing migration, P1 table, or event is altered. A session
loads its versions/branches back into a `RevisionStore`, so a backend restart preserves history, branch
heads, and saved worlds.

Migration **v015** repairs and tightens branch identity: branch rows are keyed by
`(session_id, branch_id)` because every session has a `main` branch. v015 rebuilds the table created by
v014, reconstructs any branch rows lost by the earlier global key, and the service reconciles the active
branch head against the session's durable `active_version_id` on load. This makes multiple sessions and
undo state restart-safe.

Migration **v016** is index-only: source-scoped candidate lifecycle lookups and recent-session/world
listing. It adds no table, column, or claim surface.

Migration **v017** adds `redo_json` to each branch. The redo stack is branch-local and survives a backend
restart; a new commit clears it and the clear is persisted in the same bundle. The migration is additive
and idempotent. Before a non-empty database is upgraded, the runner writes a `VACUUM INTO` copy under
`<db_dir>/backups/`, verifies it with `PRAGMA quick_check`, and keeps the five newest; a failed copy or
verification aborts startup instead of upgrading without a recovery point. SQLite connections use
`synchronous=FULL`, foreign keys, a 5 s busy timeout, WAL and a
1000-page autocheckpoint. Stored JSON is decoded strictly for scene, diff, commands, notes and event
payloads; undecodable records raise the typed `corrupt_local_state` error instead of becoming an empty
scene.

## Write integrity

Mutations are serialized by a per-session lock and persisted as one unit of work:

- create: session + root version + main branch + event;
- commit: session head + immutable version + branch head + event;
- candidate select: the same bundle plus `selected = 1`;
- branch/undo/redo/switch: session + branch (including `redo_json`) + event;
- candidates: replace the unselected set for one source version + event;
- world save: world + items + event.

Every bundle returns the durable event `seq` it inserted. The service keeps `last_event_seq`, snapshots
expose it, and live events carry the same `seq`. This is additive: older clients ignore the field.

The in-memory runtime is evicted if a durable write fails, so the next request reloads from SQLite instead
of serving a state the database never accepted. Versions use strict inserts; branch and candidate rows use
keyed upserts. Candidate rows are scoped to their `source_version_id`, selected candidates are hidden, and
a stale selection is rejected. The API accepts an optional `X-Expected-Version` header and returns
`409 stale_version` on a mismatch. Health diagnostics can report SQLite journal/synchronous/foreign-key
settings and, with `?deep=true`, `quick_check` plus `foreign_key_check`. Full transport details are in
[API_CONTRACT.md](API_CONTRACT.md).

## Product HTTP API
`app/api/animus_studio.py`, prefix `/animus/studio`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/health`, `/capabilities` | Claim and capability envelope |
| POST/GET/DELETE | `/sessions`, `/sessions/{id}` | Create, list, load, delete |
| POST | `/sessions/{id}/intent` | Natural-language correction (may return clarification, no version) |
| POST | `/sessions/{id}/commands` | Typed direct edits (colour, size, lock, transform, relations, atmosphere) |
| POST | `/sessions/{id}/regenerate` | Generate 1–6 procedural candidates preserving locks |
| POST | `/sessions/{id}/candidates/{cid}/select` | Commit a candidate as a new version |
| POST | `/sessions/{id}/undo`, `/redo` | Move the branch head |
| POST | `/sessions/{id}/branches`, `.../{branch}/switch` | Branch and switch |
| GET | `/sessions/{id}/history`, `/versions/{vid}` | Version and branch inspection |
| GET | `/sessions/{id}/events?after_seq=&limit=` | Durable event history, ascending cursor |
| POST | `/sessions/{id}/worlds`; GET/DELETE `/worlds/*`; POST `/worlds/{id}/open` | World library |

Responses are whole **snapshots** (scene, version, diff, branches, history, capability envelope,
undo/redo flags, `last_event_seq`) so the client replaces state atomically. Each successful route declares an explicit
Pydantic response model in `app/schemas/animus_studio_responses.py`; internal records use the
runtime-free TypedDicts in `app/core/animus/studio/types.py`. Errors keep a string `detail` and add a
stable `X-Studio-Error-Code` header: 404 unknown session/world, 400 invalid command or claim-bearing
copy, 409 stale version/archived session, 503 local persistence failure or `corrupt_local_state`.
OpenAPI declares the 400/404/409/503 error model and header on every Studio route.

## Live channel
`WS /ws/animus/{session_id}` validates the browser Origin, joins the bus **before** reading the snapshot,
then sends the initial snapshot and forwards durable events under a stable `type: "event"` envelope with
the original type in `event_type`. Each forwarded event keeps its durable `seq`; the snapshot's
`last_event_seq` lets the client detect duplicates and gaps. A slow client that overflows its queue receives
`{"type":"resync_required","reason":"queue_overflow"}` instead of silently missing updates. The channel
accepts `ping` and `intent` (with optional `expected_version_id`), caps messages at 64 KiB, maps archived,
stale, not-found, validation and persistence errors to their stable codes, and closes invalid Origins with
code `1008`. No external network is used.

## Local exposure
The backend default is loopback-only (`settings.backend_host = 127.0.0.1`). The app also installs
`TrustedHostMiddleware` with an explicit host allowlist and sends `Cache-Control: no-store` plus
`X-Content-Type-Options: nosniff` on `/animus/studio` responses, and the browser client requests every
Studio API call with `cache: "no-store"`. Together these prevent a browser page on
another origin from silently reaching the unauthenticated local API through DNS rebinding, and keep scene
JSON out of browser caches. Docker images still bind `0.0.0.0` **inside** their container; the composed
host port should be restricted to loopback when the app is not intentionally shared.

## Client resilience
The web client sends `X-Expected-Version`, aborts requests after 20 seconds, reads stable error codes,
guards against stale mutation responses, and keeps a typed `loadError` so 404, 503, timeout and unreachable
backend states get distinct copy. It validates WebSocket envelopes before they reach React, ignores events
at or below `last_event_seq`, refreshes immediately when a sequence gap or `resync_required` is observed,
and otherwise refreshes on a short debounce. It reconnects with capped exponential backoff and jitter, sends
a heartbeat ping every 25 seconds, treats 60 seconds without any frame as a dead channel, and aborts the
initial load or an in-flight mutation when a newer mutation starts or the view unmounts. Failed corrections
keep their text in the prompt bar so the user can edit and retry.

## Renderer
`frontend/components/animus/` renders the scene graph with React Three Fiber primitives: procedural
castle, terrain, water, sky shader, weather, stars, fog, fire, creatures, portals, and abstract forms.
The renderer is a **deterministic visualisation of symbolic state**, not an image model. It has no
texture downloads, no external generation, and no neural input. Candidate previews are CSS gradients
derived from the same scene palette.

## Product routes
`/animus` (start), `/animus/studio/[sessionId]` (loop), `/animus/worlds` (library),
`/animus/about` (boundaries). The legacy `/imagina/animus` route redirects to `/animus`; the P1 engine and
its benchmark API remain available under `/animus/*` and are not replaced by the Studio.
