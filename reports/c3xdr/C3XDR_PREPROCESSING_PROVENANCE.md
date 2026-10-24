# C3XDR — Preprocessing Provenance

**Status: `NOT_EXECUTED_BLOCKED`** — the raw preprocessing/registration pipeline was **not run** because
the Section-1 infrastructure gate failed (`C3XDR_BLOCKED_STORAGE`): no ≥300 GB storage, no container
runtime (docker/apptainer/singularity), and no reproducible neuroimaging stack (fMRIPrep / FSL / SPM /
FreeSurfer / nipype absent; only `nibabel` present). No large data was downloaded.

## Intended frozen pipeline (recorded for a future adequate-infrastructure replay)
The execution seal (`reports/c3xdr/c3xdr_execution_seal.json`) prospectively freezes the intent:
- Reproduce the published/KamitaniLab Mind Captioning preprocessing and functional-space construction
  as closely as practical, so the **released `metainf.roiname` localizer ROIs are directly reusable**
  (VC primary; V1/LVC/HVC secondary). fMRIPrep is acceptable ONLY if it yields a space compatible with
  the released ROI definition; otherwise the KamitaniLab pipeline is preferred for provenance
  compatibility. ONE pipeline is frozen and container-pinned.
- To be recorded when executed: container image + digest, software versions, exact command lines,
  parameters, per-input SHA-256, and the output-space definition. The pipeline must be replayable from
  raw BIDS + execution seal + container digest + commands, with no workstation/absolute-path fallback.
- Estimator and GLM are already frozen (Model A / LSA; session-disjoint reliability), independent of the
  preprocessing implementation.

## Why this is a BLOCK, not a FAIL
The scientific question (C3XD) is well-posed and design-identifiable (established in C3XD). C3XDR simply
could not be executed here for lack of storage + a reproducible preprocessing stack. `spec` details
therefore remain unfilled; see `results/c3xdr/c3xdr_preprocessing_spec.json` and the final report.
