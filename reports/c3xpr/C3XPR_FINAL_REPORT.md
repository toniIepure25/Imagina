# C3XPR — ROI / Spatial Provenance Recovery — Final Report

**Provenance-only gate. NO raw BOLD, NO neural outcomes, NO reliability/geometry/decoding/captioning/
reconstruction. NOT C3XDR-R2 / C3XE / C4.** C3XC / C3XD / C3XDR / C3XDR-R1 immutable.

## Decision
**`C3XPR_PUBLIC_ROI_PROVENANCE_PARTIAL` → `C3XPR_AUTHOR_ARTIFACT_REQUIRED`.** The released ROI voxel
sets can be reconstructed **exactly in the released 2 mm world frame** (membership + world coordinates +
regular lattice all exact), but their **exact, reproducible correspondence to a raw-derived native
functional space cannot be recovered from public artifacts**. A minimal author request is prepared (not
sent). **C3XDR-R2 is NOT authorized.** This is not `UNRECOVERABLE` — no authoritative author response
exists yet, and silence ≠ unrecoverable.

## Provenance
- Starting SHA `9c28f08…` (C3XDR-R1 final) → branch `research/d2-roi-provenance-recovery-c3xpr`.
- C3XDR-R1 decision `C3XDR_R1_BLOCKED_ROI_PROVENANCE` preserved; C3XDR scientific seal `7afc7946…`
  unchanged. Seal `reports/c3xpr/c3xpr_protocol_seal.json`.

## Blocker clarification
The blocker is **ROI/spatial provenance**, not "no preprocessing pipeline exists." The paper specifies
substantial functional-preprocessing methodology; the gap is the spatial reference/transform and the
ROI-defining derivatives (`c3xdr_r1_blocker_clarification.json`).

## Published preprocessing information vs remaining unknowns
- **Publicly specified:** functional-preprocessing methodology; manual FreeSurfer correction reported;
  released data on a regular 2 mm isotropic world lattice.
- **Publicly unspecified / unverified:** identity of the released world frame (native-anat vs MNI — not
  labelled); no released reference EPI/BOLDref; no released affine/header; no raw→released transform;
  exact tool versions not machine-verified here.
- **Requires (unreleased) derivative:** manually-corrected FreeSurfer surfaces (drive bbregister /
  surface geometry / retinotopic + localizer ROI boundaries / VC-LVC-HVC membership); localizer +
  retinotopy runs/GLMs that defined the ROIs. (`published_preprocessing_contract.json`,
  `manual_freesurfer_dependency.json` = `PUBLIC_PROVENANCE_DEPENDS_ON_UNRELEASED_MANUAL_FS_DERIVATIVE`.)

## OpenNeuro task inventory (ds005191 v1.0.2, S1–S6)
Present: T1w, inplaneT2, fieldmaps, testImagery, testPerception, trainPerception. **Absent for every
subject: retinotopy, pRF, and all functional localizers (0 hits).** ⇒ the ROI-defining runs are not
public → route 5 unavailable. (`openneuro_spatial_inventory.json`.)

## Figshare / Zenodo / Git-history findings
- Figshare 25808179 (v1 & v2): only `.mat` + DNN-feature zips + result zips + videos — **no ROI masks,
  reference EPI, affine, transform, surface, localizer, or retinotopy files** (`figshare_spatial_inventory.json`).
- Zenodo 15686864: a code snapshot zip only — no spatial artifacts.
- GitHub `horikawa-t/MindCaptioning`: analysis-only; `getRoiVoxelIdx.m` reads ROI indices **only** from
  the released `.mat`; 100 commits of history scanned → **no** spatial support files ever present
  (`zenodo_github_provenance.json`).

## Released .mat spatial schema (structural-only; `released_mat_spatial_schema.json`)
`metainf` provides: ROI membership `roiind_value` (148513×1853, masks over released voxels), `roiname`
(1853; 1679 used), per-voxel world coordinates `xyz` (148513×3, **world mm**), `volInds`, `voxind_all`.
- Regular **2 mm** isotropic lattice, exact round-trip (residual **0.0**); occupied bbox 78×86×63.
- **No** affine, **no** full parent-grid dims, **no** BOLDref identifier, **no** world-frame label.
- **Can an exact NIfTI ROI mask be reconstructed in the released frame?** YES.
- **Can it be exactly related to raw native functional space from public data?** NO — the released
  world frame is unidentified and unreferenced; resampling into a fresh preprocessing would be
  approximate (sealed-forbidden) and depends on the unreleased manual-FS registration.

## Can exact masks be reconstructed publicly?
- **VC in native raw space:** NO (public). LVC/HVC/V1 in native raw space: NO (public).
- VC/LVC/HVC **in the released 2 mm frame:** YES (exact) — but that frame cannot be tied to raw native
  space without the missing reference/transform.

## Minimal missing artifact & author request
Smallest unblocking artifact: **per-subject VC/LVC/HVC (+V1) NIfTI masks + matching native-space BOLD
reference image (S1–S6)**; acceptable alternatives: ROI coords+grid+affine, BOLDref+transform, or the
manual-FS registration derivative. Prepared (NOT sent): `AUTHOR_REQUEST_EMAIL.md`,
`GITHUB_ISSUE_DRAFT.md` — no neural-outcome, no subject/ROI-performance language.
Author request prepared: **yes**. Author response obtained: **no** (expected at closeout).

## C3XDR-R2 authorization
**Not authorized.** Only `C3XPR_PUBLIC_ROI_PROVENANCE_RECOVERED`, or receipt of the requested
authoritative spatial artifacts (a future gate), may authorize preparing C3XDR-R2. C3XPR does not
authorize substituting an atlas/whole-brain/probabilistic-retinotopy VC (that would be a new analysis
family, not a C3XDR replay).

## Integrity / verification
Provenance-only; no raw BOLD, no neural values, no reliability/geometry imports; no substitute/
approximate ROI; released `.mat` inspected structurally only; nothing non-public obtained; no
credentials. Prior gates immutable. Tests `test_c3xpr_provenance.py` (hermetic); ruff clean; CI job
`c3xpr-roi-provenance`; CI-tested SHA / run recorded at closeout.

## Scientific bottom line
The ROI **definitions** are exactly known in the released frame, but the public release omits the single
spatial link (reference image / affine / transform, or the ROI-defining localizer+manual-FS
derivatives) needed to place them exactly in an independently reproduced native functional space. The
C3XDR raw replay therefore remains blocked on **one small, well-identified artifact**, obtainable by a
minimal author request. **STOP after C3XPR — do not execute C3XDR-R2.**
