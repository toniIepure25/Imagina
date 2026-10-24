# C3XAT-R1 — Final Report (Execution Attempt 2)

**Execution of the frozen C3XAT experiment on OrchestrAI. Reuses the C3XAT seal `bb0d07ac…` and the
C3XAT-R1 execution seal `23a6f92d…` unchanged. No new protocol, nothing frozen modified.** Measurement-
only — no geometry, decoding, reconstruction, or semantic features. No neural outcome fabricated.

## Decision
**`C3XAT_R1_BLOCKED_ATLAS_SPACE_PROVENANCE`** (BLOCKED ≠ FAIL). Supersedes the interim checkpoint
`C3XAT_R1_BLOCKED_EXECUTION_INCOMPLETE` (preserved, not rewritten). **Dataset gate NOT evaluated.
C3XAG NOT authorized.** `execution_attempt = 2`; no C3XAT-R2; seals unchanged.

## What succeeded (real, verified)
- **Live OrchestrAI execution** via explicit user kubeconfig, namespace `runai-romania-dev`.
- **Acquisition COMPLETE** — exact manifest: **1063 files, 139,957,018,247 bytes**, `manifest_sha256
  749ded7b…`, 0 partial/zero-byte, trainPerception excluded; every sub-01…06 has 5 testImagery + 2
  testPerception + anat.
- **Trial contract verified** from real events: 72 videos / **360 imagery trials** / 5 sessions; **72/72**
  imagery↔perception correspondence.
- **fMRIPrep 24.1.1 (`sha256 9aec0b83…`) SUCCEEDED for ALL 6 subjects** — recon-all finished without
  error for every subject after the per-subject `--fs-subjects-dir` fix resolved the earlier shared-
  fsaverage race (documented in `fmriprep_failure_classification.json`).
- **S1 technical qualification PASS** — 30 imagery + 10 perception MNI runs; grid **97×115×97 @ 2 mm**
  with affine bit-identical to the frozen MNI152NLin2009cAsym res-02 reference; motion6 + csf + wm + 7
  cosine confounds on all runs; MNI brain mask, GM probseg, FreeSurfer surfaces present (no R_I inspected).
- **Pre-outcome corrections applied & CI-green** — Model A grouped-eval rebuilt from the real
  `trial_type=-5` events and proven **bit-identical** to C3XD `build_run`; design rank-deficiency 0, max
  imagery VIF 1.37; Delta inference switched to the sealed **conservative paired sensitivity**; five-
  session estimator clarified (estimator unchanged); R_P unit frozen (perception RUN, run-disjoint).
- **Spatial transform resolved & hashed** — official TemplateFlow MNI152NLin6Asym→MNI152NLin2009cAsym
  transform (`2e3869a0…`) + res-02 references.

## Why blocked (the one genuine, well-identified barrier)
The **primary** ROI `WANG25_TOPOGRAPHIC_VISUAL_NETWORK` requires an authoritative complete **volumetric**
25-area Wang2015 MPM in **MNI152NLin6Asym** (then the hashed transform → 2009cAsym 2 mm, one deterministic
resample identical for all subjects). Per-subject surface→volume projection is **explicitly forbidden**
for the primary route. That volumetric MPM **cannot be provenance-established from a stable, independently-
hashable public source in this environment**:

| Source | Result |
|---|---|
| neuropythy bundle (cluster-verified) | **surface `.mgz` only** — no volumetric NIfTI |
| TemplateFlow (fsaverage / MNI6Asym / 2009cAsym / fsLR) | no Wang |
| FSL FMRIB standard atlases | no Wang |
| Princeton napl ProbAtlas | HTTP 403 |
| OSF candidate downloads | HTTP 400 / not found |
| Web search ×3 | volumetric MNI form documented, but every pointer resolves to the surface-based neuropythy/occipital_atlas per-subject tools; no stable hashable direct file URL |

This is the `C3XAT_R1_BLOCKED_ATLAS_SPACE_PROVENANCE` condition the protocol designates as a genuine
fail-closed blocker (`atlas_space_provenance_blocker.json`). I did **not** fabricate a volumetric-MPM
provenance and did **not** substitute the forbidden per-subject surface projection.

### Correction of a prior over-claim
The earlier `atlas_provenance_resolved.json` recorded status `ATLAS_SPACE_PROVENANCE_RESOLVED` using
neuropythy **surface** labels with a construction route ("project fsaverage wang15 → each subject's
FreeSurfer surface → fill to MNI grid") — which is exactly the per-subject surface projection the primary
route forbids. That artifact is preserved; the transform/reference hashes in it remain valid, but the
Wang **primary volumetric-MPM** provenance was **not** actually resolved. This report corrects that.

## Per subject (S1–S6)
| Subject | Preprocessing | Wang voxel count | R_I / perm p / CI / min-seed | R_P | cue/video Δ | Status |
|---|---|---|---|---|---|---|
| S1–S6 | fMRIPrep **COMPLETE** (succeeded) | **not constructed** (primary atlas blocked) | **not computed** | **not computed** | **not computed** | **BLOCKED (not evaluable)** |

PASS count: **not evaluable**. Primary dataset decision: **not evaluated**. Secondary Benson / enrichment
/ negative controls: **not computed** (secondary cannot run or rescue while the primary is blocked). No
values fabricated.

## Authorization
**C3XAG NOT authorized** (requires `C3XAT_D2_ATLAS_IMAGERY_QUALIFIED`). This gate authorizes nothing
further.

## Resume path (execution_attempt stays 2 — no C3XAT-R2)
Supply, or identify a stable hashable public source for, the authoritative complete **volumetric**
Wang2015 25-area MPM in MNI152NLin6Asym. Then the **frozen** pipeline runs unchanged: hash it → apply the
already-hashed official transform to 2009cAsym 2 mm → deterministically resample onto the certified
97×115×97 subject grid → QC (grid/affine/labels/coverage) → freeze implementation → execute the sealed
R_I/R_P/cue-video campaign → primary Wang25 dataset decision → secondary analyses. No scientific component
changes; the ~140 GB raw data and all 6 fMRIPrep derivatives persist on the OrchestrAI PVC.

## Integrity
No neural outcome computed or fabricated; no ROI selected by performance; no per-subject surface
projection substituted for the primary; `implementation_freeze_manifest.json` correctly **not** written
(no valid primary ROI to freeze, no real R_I); C3XAT seal and all prior gates immutable; no kubeconfig/
license/token committed. Tests `test_c3xat_pipeline.py` (34) + `test_c3xat_r1_execution.py` hermetic;
ruff clean.

## STOP
Genuine fail-closed provenance blocker reached. No C3XAG, no geometry, no decoding, no reconstruction, no
C4. `execution_attempt = 2` remains open on the resume path above.
