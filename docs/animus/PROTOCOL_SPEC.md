# ANIMUS — Protocol Specification (v1, experimental)

A protocol is a small, versioned description of a practice run. It is declarative metadata, not a
treatment prescription and not a validated psychometric instrument. The runner remains local and
single-process.

## Protocol shape

```json
{
  "protocol_id": "core-calibration-12",
  "version": "ANIMUS-PROTOCOL-v1",
  "name": "Core calibration · 12 trials",
  "description": "Coverage-first calibration across the five dimensions.",
  "builtin": false,
  "spec": {
    "total_trials": 12,
    "max_minutes": 12,
    "task_types": ["attribute_recall", "style_recall", "candidate_discrimination",
                   "spatial_view", "control_choice"],
    "dimensions": ["stability", "discrimination", "spatial", "control", "calibration"],
    "stopping": { "max_consecutive_errors": 5, "fatigue_prompt": true },
    "difficulty": { "start": 0.35, "min": 0.1, "max": 0.9, "step": 0.08 }
  }
}
```

Validation is intentionally strict: known dimensions and task types only, `1..60` trials, `1..60` minutes,
difficulty bounds inside `[0.05, 0.95]` with `min < max`, and unknown top-level/spec fields rejected.
`clinical_use` is not a protocol field; it is a capability-envelope constant and cannot be raised by a
protocol.

## Built-in protocols

| ID | Trials | Purpose |
|---|---:|---|
| `core-calibration-12` | 12 | Broad coverage across all five dimensions |
| `stability-8` | 8 | Repeated scene-recall trials for the stability dimension |
| `spatial-8` | 8 | Repeated view-inference trials for the spatial dimension |

These are **content presets**, not validated instruments. They exist so a user can choose a bounded
session without designing a curriculum. Built-in protocols are idempotently upserted by the service and
listed through `GET /animus/studio/protocols`.

## Run lifecycle (target)

```
created → active → paused → completed
                 ↘ abandoned
```

The v018 schema already stores `animus_studio_protocols` and `animus_studio_protocol_runs`; v019 adds
`task_family`, `response_kind`, `scoring_version`, and `error_profile_json` to trial rows. Phase A
exposes protocols and trial recording; a full run lifecycle (pause/resume, completion summary, export) is
Phase C. Until then the UI treats each `practice/start` call as an adaptive run and records trials against
the local profile.

## Rules

1. A protocol cannot raise the claim ceiling or enable clinical use.
2. A protocol cannot add a dimension, task, or scoring rule that is not implemented and tested.
3. A completed run must report `n`, uncertainty, and limitations; it must not report a composite.
4. A run can be abandoned at any time; no streak, penalty, or loss is recorded.
5. Any user-authored protocol (Phase C) must pass the Studio claim guard before it is stored. It must not
   promise a cure, enhancement, diagnosis, neural decoding, or far transfer.
6. Protocol definitions are local data; no protocol is fetched from the network.

## Why this is not a clinical protocol

Clinical use would require a fixed administration procedure, norms, reliability and validity evidence,
adverse-event handling, and ethics oversight. None of those exist here. `clinical_use = DISABLED` is a
machine-readable boundary, not a disclaimer appended after the fact.
