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
| GET | `/profile` | Experimental profile: five dimensions, error signature, epistemic and contrast summaries, no composite |
| POST | `/profile/reset` | Deletes all local trials, interview probes, and contrast sessions; resets estimates |
| GET | `/protocols` | Built-in versioned practice protocols |
| POST | `/sessions/{id}/practice/start` | `{task_type?, difficulty?}`; returns task without its answer |
| POST | `/sessions/{id}/practice/trials` | Scores a task, appends a trial, returns next task + profile |
| POST | `/sessions/{id}/interviews/start` | `{max_probes?, form_id?, difficulty?, expected_version_id?}`; returns first binary probe |
| POST | `/sessions/{id}/interviews/{iid}/probes` | Scores a probe, appends a trial, returns next probe or reconstruction |
| GET | `/interviews/{iid}` | Interview summary, reconstruction, and refreshed profile |
| GET | `/sessions/{id}/interviews` | Local interview index for the session |
| POST | `/sessions/{id}/contrast/start` | `{max_trials?, form_id?, difficulty?, occasion?, delay_hours?, source_version_id?, expected_version_id?}`; returns the first hidden-target pair |
| POST | `/sessions/{id}/contrast/{cid}/trials` | Scores one 2-AFC trial, returns the next pair or result |
| GET | `/contrast/{cid}` | Contrast summary, thresholds, calibration, and refreshed profile |
| GET | `/sessions/{id}/contrast` | Local contrast index for the session |
| POST | `/contrast/{cid}/reflection` | Optional strategy reflection after completion |
| GET | `/sessions/{id}/observatory` | Belief, evidence provenance, discrimination, and test–retest reliability |

## Practice

`practice/start` reads the current scene head and returns:

```json
{
  "session_id": "...",
  "source_version_id": "...",
  "task": {
    "task_id": "task_...",
    "task_type": "attribute_recall",
    "task_seed": 1234,
    "difficulty": 0.35,
    "dimension": "stability",
    "prompt": "...",
    "options": [],
    "response_kind": "token_selection",
    "tokens": [{"token_id": "obj_...", "kind": "castle", "label": "Castle", "role": "subject", "color": "#..."}],
    "layout": null,
    "preview_seconds": 6
  },
  "adaptive": {"task_type": "object_reconstruction", "dimension": "stability",
               "reason": "calibration_warmup", "expected_gain": null},
  "profile": {"...": "..."},
  "claim_level": "L1_BEHAVIORAL_ASSISTED"
}
```

The payload never includes `correct_option_id`, `target_token_ids`, or target positions. Option tasks carry
`options`; reconstruction tasks carry `tokens` and a `response_kind`.

`practice/trials` requires `task_id`, `task_type`, `task_seed`, `difficulty`, a `response` object,
`confidence` (0–1), `latency_ms`, and `client_trial_id`. Valid responses are
`{"option_id": "..."}`, `{"selected_token_ids": [...]}`, or
`{"placements": [{"token_id": "...", "x": 0.0, "z": 0.0}]}`. `task_id` binds the task to the scene
fingerprint, task type, seed, difficulty, and `recon-v1` where applicable; a stale or edited scene therefore
fails closed. `expected_version_id` may be supplied; the server also accepts `X-Expected-Version`. The task
is rebuilt from the source scene and must match the submitted identity. The response includes the scored
`trial`, optional `next_task`, refreshed `profile`, and `idempotent`. Trial rows expose `task_family`,
`response_kind`, `scoring_version`, and `error_profile`. Reusing `client_trial_id` returns the original trial
without creating a second one. With a supplied expected version, a changed scene returns `409 stale_version`;
otherwise a stale task identity or invalid response returns `400 invalid_request`. Idempotent retries are
checked before the version guard, so a retry can still return the original trial after the scene has moved
on.

`GET /profile` returns the five separate dimensions plus a descriptive `error_signature`:

```json
{
  "error_signature": {
    "n": 16,
    "omissions": 3,
    "intrusions": 1,
    "mean_spatial_error": 0.21,
    "spatial_n": 6,
    "epistemic_n": 12
  },
  "epistemic": {
    "n_interviews": 1,
    "n_probes": 12,
    "mean_brier": 0.18,
    "overconfidence": 0.06,
    "abstention_rate": 0.08,
    "mean_information_gain": 0.21
  },
  "contrast": {
    "n_sessions": 2,
    "n_completed": 2,
    "n_trials": 32,
    "median_threshold": 0.34,
    "mean_dprime": 1.42,
    "mean_brier": 0.16,
    "calibration_n": 32,
    "last_contrast_id": "ct_..."
  }
}
```

`n` is the total ledger count; `epistemic_n` is the subset from epistemic interviews. The signature has no
composite and no clinical category. The `epistemic` and `contrast` summaries are separate evidence streams;
they are not summed with the five dimensions. `contrast.median_threshold` excludes censored thresholds. `GET /protocols` returns declarative protocol
metadata only. It does not start or mutate a run. Protocol
runs and export remain Phase C; the current practice endpoints record trials against the local profile.

## Epistemic interview

`POST /sessions/{id}/interviews/start` reads the current scene head (optionally guarded by
`expected_version_id`) and returns:

```json
{
  "session_id": "...",
  "interview": {
    "interview_id": "eri_...",
    "source_version_id": "...",
    "protocol_version": "eri-v1",
    "form_id": "A",
    "difficulty": 0.45,
    "status": "active",
    "probe_count": 0,
    "max_probes": 12
  },
  "probe": {
    "probe_id": "pr_...",
    "task_id": "eri_...",
    "probe_type": "object_presence",
    "prompt": "Was the lantern present in the hidden scene?",
    "options": [{"id": "present", "label": "Present"}, {"id": "absent", "label": "Absent"}],
    "dimension": "stability",
    "difficulty": 0.45,
    "preview_seconds": 4
  },
  "profile": {"...": "..."},
  "claim_level": "L1_BEHAVIORAL_ASSISTED"
}
```

The client shows the source scene once for `probe.preview_seconds` before the first question. The probe
payload never includes `answer`, `target`, `is_target`, or a hidden entity id. `max_probes` must be within
`[6, 20]`; `form_id` is `A`, `B`, or `C`.

`POST /sessions/{id}/interviews/{iid}/probes` requires `probe_id`, `task_id`, `confidence` in `[0.5, 1.0]`,
`latency_ms`, and `client_trial_id`, plus either `choice` or `abstained: true`. The response includes the
scored `trial`, `next_probe` until the budget is exhausted, `reconstruction` on completion, refreshed
`profile`, and `idempotent`. Reusing `client_trial_id` returns the original trial. A stale source scene
returns `409 stale_version`; an unknown or replayed probe returns `400 invalid_request`.

The reconstruction exposes object and relation probabilities, object/relation entropy, object and spatial
accuracy, mean Brier, coverage, abstention rate, overconfidence, and mean realised information gain. It has
no composite score and no clinical category. `GET /profile` adds an `epistemic` summary with the same
separation.

## Scene Threshold

`POST /sessions/{id}/contrast/start` reads an immutable source version (current head by default) and
returns:

```json
{
  "session_id": "...",
  "contrast": {
    "contrast_id": "ct_...",
    "source_version_id": "...",
    "protocol_version": "contrast-v1",
    "form_id": "A",
    "max_trials": 16,
    "occasion": "baseline",
    "status": "active",
    "trial_count": 0
  },
  "trial": {
    "trial_id": "ctr_...",
    "task_id": "cst_...",
    "trial_index": 0,
    "prompt": "Which scene matches the one you saw?",
    "options": [
      {"id": "a", "label": "Scene A", "scene": {"...": "..."}},
      {"id": "b", "label": "Scene B", "scene": {"...": "..."}}
    ],
    "preview_seconds": 5
  },
  "profile": {"...": "..."},
  "claim_level": "L1_BEHAVIORAL_ASSISTED"
}
```

`max_trials` is `12–24` and defaults to `16`; `form_id` is `A`, `B`, or `C`. The payload never includes
`target_side`, the changed feature, the realised delta, or the answer. Starting a session does not persist
a trial; the first trial is written only on submit, so an abandoned start cannot inflate coverage.

`POST /sessions/{id}/contrast/{cid}/trials` requires `trial_id`, `task_id`, `confidence` in `[0.5, 1.0]`,
`latency_ms`, and `client_trial_id`, plus `choice` (`a`/`b`) or `abstained: true`. The service rebuilds the
expected pair from the stored source scene and the trial history; a mismatched trial identity fails closed.
The response contains `trial` metadata, `recorded`, optional `next_trial`, optional `result`, refreshed
`profile`, and `idempotent`. No per-trial correctness is returned. Reusing `client_trial_id` returns the
original trial. The expected version may be the pinned contrast source or the current head; any other
version returns `409 stale_version`. This lets a contrast finish on its immutable source scene even if the
branch moved after the session started. Idempotency is checked first.

`result` contains `n_trials`, `n_answered`, `coverage`, `dprime`, signed `side_bias`, per-feature
`thresholds` (`spatial_position`, `object_color`), `calibration` (`brier`, `overconfidence`, `type2_auc`),
and notes. A threshold is `null` with insufficient evidence; a censored threshold is marked. 2-AFC does not
identify a yes/no criterion, so no `criterion` field is returned.

`GET /sessions/{id}/observatory` returns the ERI belief layer (or an empty one), evidence with provenance
and leave-one-out sensitivity, the latest completed contrast result for the session, and a feature-level
test–retest panel. Reliability is `insufficient` when fewer than three aligned feature thresholds exist.
The observatory has no composite score.

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
`ProfileModel`, `PracticeStartResponseModel`, `PracticeSubmitResponseModel`, and `ProtocolListResponseModel`
define the measurement surface.

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
