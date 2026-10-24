# C3XPR — ROI / Spatial Provenance Recovery (provenance-only gate)

**Provenance-only. NO raw BOLD download/analysis, NO R_I/R_P, NO neural outcomes, NO geometry,
decoding, captioning, or reconstruction. NOT C3XDR-R2, NOT C3XE, NOT C4.** C3XC/C3XD/C3XDR/C3XDR-R1
remain immutable.

## Question
Can the exact spatial definition of the released Mind Captioning ROIs (**VC, LVC, HVC, V1 where
applicable**) be reproducibly related to raw-derived native functional space using authoritative public
or author-provided spatial artifacts? The C3XDR/C3XDR-R1 blocker is **ROI/spatial provenance
insufficiency**, NOT "no preprocessing method exists" (the paper specifies substantial preprocessing).

## Allowed recovery routes (frozen; any ONE, if exact, recovers provenance)
1. exact released ROI masks + reference BOLD/EPI;
2. exact ROI voxel coordinates + parent grid + affine;
3. exact released-space reference + raw→released transform chain;
4. preprocessing/registration derivatives sufficient to recreate the released space;
5. released retinotopy/localizer derivatives sufficient to regenerate the exact ROIs.

**Approximate or substitute ROIs are forbidden** (no nearest-neighbour spatial guessing; no vanilla
recon-all substitute for the manually-corrected FreeSurfer; no atlas VC substitution). Exact
reconstruction requires: exact coordinate round-trip, exact voxel counts, exact affine/grid agreement,
100% in-brain validity, and the same method working for every subject.

## Evidence separation
Every finding is tagged PUBLICLY SPECIFIED / PUBLICLY UNSPECIFIED / REQUIRES DERIVATIVE, and public
audit is kept distinct from any author-provided evidence. Negative searches are recorded, not only
positive findings.

## Decision states
- `C3XPR_PUBLIC_ROI_PROVENANCE_RECOVERED` — exact mapping to raw native functional space achievable from
  public artifacts → STOP; authorize preparation of C3XDR-R2 only (do NOT execute it).
- `C3XPR_PUBLIC_ROI_PROVENANCE_PARTIAL` / `_INSUFFICIENT` — prepare a minimal author request; state
  `C3XPR_AUTHOR_ARTIFACT_REQUIRED`.
- `C3XPR_ROI_PROVENANCE_UNRECOVERABLE` — ONLY after (1) exhaustive public audit, (2) exact mapping
  proven impossible, AND (3) an authoritative author response confirms the artifacts cannot be
  provided. **Silence/no-reply is NOT unrecoverable.**

## Author request (if PARTIAL/INSUFFICIENT)
Identify the SMALLEST unblocking artifact — preferred: per-subject **VC/LVC/HVC NIfTI masks + matching
native-space BOLD reference image** for S1–S6. Prepare (do NOT send) `AUTHOR_REQUEST_EMAIL.md` +
`GITHUB_ISSUE_DRAFT.md`. The email states goal (independent raw-fMRI reproducibility), what is
understood (published methods), what is missing (exact ROI↔raw spatial correspondence); it must contain
**no** neural-outcome or subject/ROI-performance ("which is best") language.

## Scope guard
If public provenance is ultimately unrecoverable, C3XPR does NOT authorize substituting an independent
atlas/whole-brain/probabilistic-retinotopy VC — that would be a NEW analysis family, not a C3XDR replay,
and would need its own separate protocol. C3XPR does not alter the frozen C3XDR seal.

## STOP after C3XPR (do not execute C3XDR-R2).
