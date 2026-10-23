# ANIMUS Studio — API contract

Base path: `/animus/studio`. The API is local-only, unauthenticated, and deliberately small. Every
mutation returns a complete snapshot so a client can replace its scene state in one step.

## Concurrency

Mutations are serialized per session inside the local process. A client that renders a scene may send:

```http
X-Expected-Version: <active_version_id>
```

If the current branch head no longer matches, the server returns `409` with
`X-Studio-Error-Code: stale_version`. The client should refresh and retry against the new head. Omitting
the header keeps the previous last-write-wins behavior for scripts and tests; the web client always sends it.

## Errors

Error bodies keep FastAPI's `detail` string. A stable machine-readable code is returned in the
`X-Studio-Error-Code` response header (exposed through CORS).

| Status | Code | Meaning |
|---|---|---|
| 400 | `invalid_request` | Domain validation or a rejected claim phrase |
| 404 | `not_found` | Unknown session, world, version, branch, or candidate |
| 409 | `stale_version` | Expected version does not match the branch head |
| 409 | `session_archived` | Archived sessions cannot be mutated |
| 422 | — | Request model/schema validation (FastAPI) |
| 503 | `persistence_failed` | Local SQLite write failed; in-memory runtime was discarded |
| 503 | `corrupt_local_state` | Stored scene/history JSON cannot be decoded; back up the database |
| 503 | `database_unavailable` | Health check could not read the local schema |

## Requests

All JSON request models reject unknown fields. Limits are enforced in both the schema and the service.

| Method | Path | Body / notes |
|---|---|---|
| GET | `/health` | Live schema version and SQLite pragmas; `?deep=true` adds `quick_check` and FK diagnostics |
| GET | `/capabilities` | Frozen claim and capability envelope |
| POST | `/sessions` | `{title?, intention, seed?}`; `intention` 3–500 chars |
| GET | `/sessions?limit=1..100` | Recent sessions, newest first |
| GET | `/sessions/{id}` | Full snapshot |
| DELETE | `/sessions/{id}` | Deletes the session; `404` if absent |
| POST | `/sessions/{id}/intent` | `{text}`; may clarify without creating a version |
| POST | `/sessions/{id}/commands` | `{commands: 1..24, source_text?}` typed scene commands |
| POST | `/sessions/{id}/regenerate` | `{count:1..6, strength:0..1, seed?, locks?, preserve_user_edits?, vary_camera?}` |
| POST | `/sessions/{id}/candidates/{cid}/select` | Candidate must belong to the current head and be unselected |
| POST | `/sessions/{id}/undo`, `/redo` | Moves the active branch head |
| POST | `/sessions/{id}/branches` | `{name?, from_version_id?}`; duplicate names rejected |
| POST | `/sessions/{id}/branches/{bid}/switch` | Switches the active branch |
| GET | `/sessions/{id}/history` | Branch-scoped versions + undo/redo flags |
| GET | `/sessions/{id}/events?after_seq=0&limit=100` | Durable events after `seq`, ascending; `has_more` |
| GET | `/sessions/{id}/versions/{vid}` | Immutable version, including scene and diff |
| POST | `/sessions/{id}/worlds` | `{name, description?}`; saves scene + items + event atomically |
| GET | `/worlds?limit=1..100` | Saved worlds, newest first |
| GET/DELETE | `/worlds/{wid}` | Read or delete a saved world |
| POST | `/worlds/{wid}/open` | Creates a new active session from a saved world |

## Snapshots

A snapshot contains the active branch and version, symbolic `scene`, `diff`, `version`, full `history`,
`branches`, unselected `candidates` for the current head, claim/capability envelopes, warnings,
`has_undo`/`has_redo`, and `last_event_seq`. The redo stack is branch-local and persisted in `redo_json`,
so `has_redo` is accurate after a restart. Candidate scenes are never included once selected; they remain
auditable in SQLite with `selected = 1`. `last_event_seq` is additive; clients that predate it ignore it.

## Typed response contract

Every successful route declares a Pydantic response model in
`backend/app/schemas/animus_studio_responses.py`. The models are the wire contract, not implementation
details: scene graph, entity attributes, diffs, versions, branches, candidates, worlds, session lists,
health, and capability envelopes all have explicit fields. They allow extra fields so additive
`ANIMUS-SG-v1` renderer metadata stays forward-compatible without a client release.

`StudioSnapshotModel` is the base for full snapshots. `StudioIntentResponseModel` adds clarification
fields, `StudioCommandsResponseModel` adds the applied-command count, and
`StudioRegenerateResponseModel` requires the generated candidates and lock set. `VersionDetailModel`
adds the immutable scene, commands, diff, and generator to the version summary.
`StudioEventsResponseModel` and `EventRecordModel` define the durable event cursor.

The frontend mirrors the same contract in `frontend/lib/animusStudioApi.ts`: `StudioSnapshot`,
`StudioIntentSnapshot`, `StudioCommandsSnapshot`, `StudioRegenerateSnapshot`, `StudioVersionDetail`,
`StudioHistory`, `StudioHealth`, `StudioSessionList`, `StudioEventsResponse`, `StudioWorldSaveResult`,
the `StudioSceneCommand` union, and `StudioWebSocketMessage`. Request bodies use `StudioCreateInput`,
`StudioCommandsPayload`, `StudioRegenerateOptions`, `StudioBranchInput`, and `StudioWorldInput`.
WebSocket envelopes are validated at runtime by `parseStudioWebSocketMessage`.

## WebSocket

`GET /ws/animus/{session_id}` upgrades to a local WebSocket.

- Browser `Origin` must be one of `settings.cors_origins`; non-browser clients without an Origin are allowed.
- The server joins the bus before reading the snapshot, so a commit during connection setup is not lost.
- Initial message: `{"type":"snapshot","session":<snapshot>}`.
- Bus events are sent as `{"type":"event","event_type":"<original>","seq":<int>,...event fields}`. The
  envelope's `type` can no longer be overwritten by an event payload. `seq` is the durable event sequence;
  the snapshot's `last_event_seq` is the same counter. Clients ignore duplicates/older events and refresh
  the full snapshot on a gap.
- If a slow client's queue overflows, the server drains the backlog and sends
  `{"type":"resync_required","reason":"queue_overflow"}`; the client refreshes the snapshot.
- Client messages: `{"type":"ping"}` → `{"type":"pong"}`; `{"type":"intent","text","expected_version_id"?}`.
- Messages larger than 64 KiB close the socket with code `1009`; malformed JSON receives a typed error.
- Archived, stale, not-found, invalid, corrupt and persistence failures keep their HTTP-equivalent codes.
- The typed envelope is `StudioWebSocketMessage` in `frontend/lib/animusStudioApi.ts`.

## Privacy and claims

No endpoint uploads content, calls an external service, trains a model, or accepts neural data. The claim
ceiling remains `L1_BEHAVIORAL_ASSISTED`; image generation is `DISABLED`; neural/dream/reconstruction
content is `UNAUTHORIZED`; privacy scope is `local_only`.
