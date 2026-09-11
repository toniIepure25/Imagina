# C3XPA — Author Spatial Artifact Acceptance — Final Report

**Provenance-validation gate ONLY. NO raw BOLD, NO R_I/R_P, NO decoding, NO geometry, NO captioning, NO
reconstruction. NOT C3XDR-R2 / C3XE / C4.** C3XC / C3XD / C3XDR / C3XDR-R1 / C3XPR immutable.

## Decision
**`C3XPA_NO_AUTHOR_ARTIFACT_RECEIVED`** — the gate's hard precondition is **not met**: no authoritative
author response or spatial artifact has been received. The gate therefore did **not start** validation.
This is explicitly **not** a certification outcome (`RECOVERED` / `PARTIAL` / `CONTRADICTION` /
`UNAVAILABLE`), each of which requires received material. **C3XDR-R2 remains NOT authorized.**

## Why the precondition is unmet (authoritative, from the record)
- The C3XPR author request was **prepared but not sent** (`results/c3xpr/author_request_manifest.json`
  `auto_send=false`; `C3XPR_DECISION.json` `author_request_sent=false`,
  `author_response_obtained=false`). Sending was deliberately left to the user per C3XPR.
- A non-destructive search of user-owned locations (Downloads, `$HOME`) found **no** author-provided
  spatial material: no VC/LVC/HVC/V1 NIfTI masks, no BOLDref/EPI, no coordinates/grid/affine bundle, no
  transform chain, no FreeSurfer/registration derivative, and no author reply.
- Per the seal, **author silence ≠ "unavailable"** — so `C3XPA_AUTHOR_CONFIRMS_PROVENANCE_UNAVAILABLE`
  is **not** emitted; that state needs an explicit authoritative "cannot supply".

## Provenance
- Starting SHA `b42358d…` (C3XPR final) → branch `research/d2-author-spatial-artifact-c3xpa`.
- C3XPR decision `C3XPR_PUBLIC_ROI_PROVENANCE_PARTIAL` / state `C3XPR_AUTHOR_ARTIFACT_REQUIRED`
  preserved; C3XDR scientific seal `7afc7946…` unchanged. Phase-0 seal
  `reports/c3xpa/c3xpa_protocol_seal.json`.

## Received material
- Author response date: none. Sender identity: none. Delivery mechanism: none.
- Artifact inventory: **empty** (`received_artifact_manifest.json` `NO_ARTIFACT_RECEIVED`, n_items 0).
  Artifact route (masks / coordinates / transform / preprocessing derivative / ROI-generating
  derivatives): **none received**.
- Reference-space definition: `NOT_APPLICABLE_NO_ARTIFACT`.

## Per subject (S1–S6)
No artifact received → per-subject provenance **not evaluable** (`spatial_correspondence_S1..S6.json`,
status `NO_ARTIFACT_RECEIVED`, all comparison fields null, `exact_match=false`). **No values were
fabricated.** Subjects certified exact: **0/6**. Cohort rule S1–S6 unchanged (no subject dropping).

## Overall provenance decision & C3XDR-R2 authorization
`C3XPA_NO_AUTHOR_ARTIFACT_RECEIVED`. **C3XDR-R2 authorized: NO.** Authorization requires
`C3XPA_AUTHOR_ROI_PROVENANCE_RECOVERED` — an authoritative artifact establishing **exact** (100%
released coordinate-set agreement, no approximation) ROI↔raw-native correspondence with a certified
native reference, cohort satisfiable — under the unchanged C3XDR seal. The C3XPA validation protocol
(routes A–E, exact-match criteria) is frozen and ready to execute the moment such material arrives.

## Integrity / verification
Provenance-only; no raw BOLD, no neural values, no reliability/geometry imports; no fabricated artifact
or correspondence; no atlas substitution; no subject dropping; no outcome-based ROI acceptance; author
silence not treated as unavailable. No private/binary author artifacts (none exist) and no credentials
committed. Prior gates immutable. Tests `test_c3xpa_acceptance.py` (hermetic, synthetic fixtures only);
ruff clean; CI job `c3xpa-author-artifact`; CI-tested SHA / run recorded at closeout.

## Next action
If/when the authors provide per-subject VC/LVC/HVC(+V1) masks + a native BOLD reference (or an
acceptable route-B/C/D/E artifact), **re-run C3XPA validation on the received material**; only an exact
recovery then authorizes preparing C3XDR-R2. **STOP after C3XPA — do not execute C3XDR-R2, no raw BOLD,
no reliability, no geometry, no decoding, no reconstruction, no C4.**
