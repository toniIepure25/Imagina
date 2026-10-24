# C3XPA — Author Spatial Artifact Acceptance (provenance-validation gate)

**Provenance-validation ONLY. NO raw BOLD, NO R_I/R_P, NO decoding, NO geometry, NO captioning, NO
reconstruction. NOT C3XDR-R2 (which C3XPA may at most AUTHORIZE, never execute), NOT C3XE, NOT C4.**
C3XC / C3XD / C3XDR / C3XDR-R1 / C3XPR remain immutable.

## Hard precondition
This gate runs **only after** an authoritative response or spatial artifact is actually received from
the Mind Captioning authors. It does **not** run merely because a request was prepared or sent.

**Precondition status at creation: UNMET.** The C3XPR author request was *prepared but not sent*
(`results/c3xpr/author_request_manifest.json` `auto_send=false`; `C3XPR_DECISION.json`
`author_request_sent=false`, `author_response_obtained=false`), and a non-destructive search found **no**
author-provided spatial artifact (no VC/LVC/HVC/V1 NIfTI, no BOLDref/EPI, no coordinates/transform/
FreeSurfer derivative, no author reply). Therefore C3XPA does not proceed to validation; see
`C3XPA_DECISION.json` (`C3XPA_NO_AUTHOR_ARTIFACT_RECEIVED`). This document defines the validation
protocol that will execute **when** such material arrives.

## The sole question (when material is received)
Does the received authoritative material establish an **exact, independently verifiable** mapping
between the released Mind Captioning VC/LVC/HVC(/V1) ROI definitions and the raw-derived native
functional space?

## Phase 0 — seal before opening any received artifact
Record C3XPR parent SHA, C3XPR decision, C3XDR seal hash, and (when received) date/time, sender
identity, delivery mechanism, original filename(s) and byte sizes — **before** inspecting any
neural/binary content. Keep original files immutable; commit only hashes/manifests/metadata/validation
results (never large/private binaries unless license+size permit).

## Acceptable artifact routes (any one may suffice, exactly)
- **A — direct masks:** per-subject VC/LVC/HVC(/V1) NIfTI + matching BOLDref/EPI (preferred).
- **B — coordinates:** ROI membership + voxel ijk/world coords + parent-grid dims + affine + orientation
  + reference-space identity, sufficient to reconstruct masks exactly.
- **C — transform:** released-space reference image + raw→released transform chain (direction,
  interpolation, versions fully defined).
- **D — preprocessing derivative:** manually-corrected FreeSurfer subject + registration derivative +
  functional reference, sufficient to reproduce the exact released space.
- **E — ROI-generating derivatives:** retinotopy/localizer/surface derivatives + ROI code, sufficient
  to regenerate exactly the published ROIs.

A textual author statement (e.g. "coordinates are native space") is provenance but is sufficient ONLY
if it unambiguously identifies an already-public reference/transform enabling an independently checkable
mapping.

## Exact-match requirement (no approximation)
Certification requires **100% coordinate-set agreement** with the released `.mat` ROI definition:
released voxel count reproduced exactly, released world-coordinate set reproduced exactly, no missing /
no extra coordinates, exact subject/ROI correspondence, coordinate round-trip residual 0. **Dice ≈ 1 is
NOT sufficient** unless a discrepancy has an authoritative deterministic explanation. No atlas / no
whole-brain substitution. No outcome-based ROI acceptance (never inspect which ROI yields stronger
imagery reliability / decoding / geometry).

## Per-subject cohort rule
The frozen cohort is S1–S6. Fewer than 6 certified → `C3XPA_PARTIAL_AUTHOR_ARTIFACT`; do not drop
subjects or change cohort rules post hoc.

## Decision states
Per subject: `ROI_PROVENANCE_EXACT` / `_PARTIAL` / `_CONTRADICTORY` / `_UNUSABLE`. Overall:
`C3XPA_AUTHOR_ROI_PROVENANCE_RECOVERED` (exact; authorizes preparing C3XDR-R2 under the SAME frozen
seal — does not execute it) / `_PARTIAL` (no C3XDR-R2) / `C3XPA_AUTHOR_PROVENANCE_CONTRADICTION` /
`C3XPA_AUTHOR_CONFIRMS_PROVENANCE_UNAVAILABLE` (only on an explicit authoritative "cannot supply").
**Precondition unmet → `C3XPA_NO_AUTHOR_ARTIFACT_RECEIVED` (gate not started; not a certification
state).** Author silence ≠ unavailable ≠ any certification outcome.

## STOP after C3XPA. Do not execute C3XDR-R2.
