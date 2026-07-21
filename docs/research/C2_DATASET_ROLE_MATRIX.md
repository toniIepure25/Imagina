# C2 Dataset Role Matrix

Frozen alongside [`C2_PROTOCOL.md`](C2_PROTOCOL.md). Records each
candidate dataset's INTENDED role in C2 and its admissibility status. Only
`ds005815` has been independently re-verified this session (it is C1's
already-audited primary dataset, reused directly — see C1 Phase 0's
`C1_DATASET_CANDIDATES.md` for its original 10-criterion admissibility
audit, not repeated here). The other three candidates' roles are recorded
as **intended, not yet independently re-verified this session** — their
actual admissibility audits are explicitly deferred to the commits named
below, per the task specification's own structure. This document does not
claim knowledge it has not actually checked.

## Primary: ds005815 (YOTO v2.0.1)

**Role:** primary paired perception-imagery dataset, confirmatory for
H1-H5.

**Status:** ADMITTED, reused as-is from C1. Re-audit not required — C1's
Phase 0 admissibility audit, trigger-codebook verification (against the
authors' own analysis code, not guessed), license (CC0 1.0), and download
provenance (S3 mirror + pinned-commit ancillary CSV) all carry over
unchanged. This session's own real-data class-count audit (`C2_PROTOCOL.md`
§4) additionally confirms the primary visual-content subset
(`visual_square`, `visual_face_male`, `visual_face_female`) is present with
a consistent 2:1:1 per-participant ratio across all 16 C1-usable
participants.

## Secondary/exploratory: ds004306

**Intended role:** external exploratory perception-imagery replication,
IF access and metadata permit (per task specification, Commit 7's optional
exploratory-replication step).

**Status:** NOT YET AUDITED this session. Its real availability, license,
trigger/event semantics, and whether it contains a genuinely comparable
paired perception-imagery visual-content design are unverified claims at
this point in C2 — they will be independently checked (primary sources:
the dataset's own OpenNeuro/GitHub page, not secondhand descriptions)
immediately before any attempt to use it, in Commit 7. Per the protocol
(`C2_PROTOCOL.md` §5) and the task's explicit instruction, this dataset can
NEVER change the primary ds005815-based decision regardless of what its
audit finds — it is exploratory-only by construction, not a fallback
primary dataset.

## Secondary/exploratory: THINGS-EEG2

**Intended role:** perception-only representation pretraining or
benchmarking (optional).

**Status:** NOT YET AUDITED this session. If pursued at all, this would
only ever supply a PRETRAINING signal for the compact encoder architectures
(Commit 4) — never a source of confirmatory content or state LABELS for
ds005815's own trials, and never mixed into the frozen ds005815 LOSO
splits. Given the scope and real-data compute already required by the
ds005815-only confirmatory pipeline, using THINGS-EEG2 is treated as
optional/lowest-priority; if not pursued, this is recorded honestly in
`results/c2_protocol_decision.json` rather than silently implied to have
been used.

## Auxiliary control only: OpenMIIR

**Intended role:** auditory modality-general control only.

**Status:** NOT YET AUDITED this session. Never a source of visual-content
claims — per the task's explicit instruction, OpenMIIR is out of scope for
anything beyond an auditory-modality sanity check, if used at all.

## Explicitly excluded: EEG-ImageNet

**Status:** EXCLUDED, per explicit task instruction. Not audited, not used,
not reconsidered in this gate.

## Summary table

| Dataset | Role | Confirmatory? | Audited this session? |
|---|---|---|---|
| ds005815 (YOTO v2.0.1) | Primary paired perception-imagery | Yes (H1-H5) | Yes (reused from C1 + new class-count audit) |
| ds004306 | Exploratory replication | No — never overrides primary | No — deferred to Commit 7 |
| THINGS-EEG2 | Optional pretraining/benchmark | No | No — deferred to Commit 4, optional |
| OpenMIIR | Auditory-only control | No | No — deferred, auxiliary only |
| EEG-ImageNet | Excluded | N/A | N/A — not used |
