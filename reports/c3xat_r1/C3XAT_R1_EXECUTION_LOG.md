# C3XAT-R1 — Execution Attempt 2 of the Sealed C3XAT Experiment — Execution Log

**Execution of the frozen C3XAT experiment on OrchestrAI. No new protocol. Reuses the C3XAT seal
`bb0d07ac…` unchanged.** Nothing frozen is modified (dataset, subjects, ROIs, Model A, estimator,
permutation, bootstrap, seeds, cue/video falsification, dataset gate). Measurement-only — no geometry,
decoding, reconstruction, or semantic features. No neural outcome is fabricated.

## Decision
**`C3XAT_R1_BLOCKED_EXECUTION_INCOMPLETE`** (BLOCKED ≠ FAIL). Infrastructure is fully certified live and
execution has genuinely begun on the persistent cluster, but confirmatory measurement (fMRIPrep of
S1–S6 → atlas ROIs → sealed reliability → cue/video falsification) has not completed in this session and
will complete on the persistent cluster across resumption. **No R_I/R_P/Δ_I fabricated. C3XAG NOT
authorized. Attempt-1 decision `C3XAT_BLOCKED_EXECUTION` preserved.**

## Resolved live this session (real, verified)
1. **OrchestrAI connection** — explicit user kubeconfig (`~/Downloads/antoniu_iepure.yaml`), context
   `antoniu-iepure@default`, namespace **`runai-romania-dev`** (not the default context). `auth can-i`
   get pods / create jobs / create pvc / create pods → **yes**.
2. **Persistent storage** — default StorageClass `nfs-client` (NFS subdir provisioner). Created
   `c3xat-r1-workspace` **600Gi RWX**, status **Bound** (`pvc-5f104841-…`).
3. **Compute** — GPU node `k8s-worker-gpu-node-xe8545` with **4× NVIDIA GPU (A100)**.
4. **Egress** — from a cluster pod and the shell: OpenNeuro S3 (`ds005191/dataset_description.json`) and
   TemplateFlow S3 both **HTTP 200**.
5. **FreeSurfer license** — present locally; loaded into in-cluster Secret `c3xat-fs-license`
   (**never committed to git**).
6. **Container provenance** — fMRIPrep pinned: `nipreps/fmriprep:24.1.1` @
   `sha256:9aec0b83b3728795fa5a593d373c9bc5d4a7034e943a793173408e3b70e702c6` (bundles FreeSurfer/ANTs/
   AFNI/TemplateFlow). Target space MNI152NLin2009cAsym 2 mm, smoothing NONE.
7. **BIDS contract verified** — ds005191 v1.0.2 "Mind Captioning" (Horikawa, CC0), `sub-01…sub-06`;
   `ses-anat`, **5 imagery sessions** `ses-testImagery01…05`, `ses-testPerception01…02`, and
   `ses-trainPerception01…10` (excluded). Matches the sealed 5-imagery-session structure.
8. **Selective acquisition launched** — Job `c3xat-r1-acquire` running: `aws s3 sync s3://openneuro.org/
   ds005191 → PVC` excluding `*ses-trainPerception*` and `derivatives/*`; progress observed 7.2 / ~15.3
   GiB. Builds a SHA-256 manifest of all `.nii.gz/.tsv/.json` inputs on the PVC.

This **resolves the attempt-1 blocker**: `C3XAT_BLOCKED_EXECUTION` (attempt 1) was caused by the
OrchestrAI kubeconfig being absent that session. Here cluster, storage, GPU, egress, license and
container are all certified live.

## Atlas provenance
TemplateFlow does **not** host Wang2015 or Benson (empty S3 listing under `tpl-fsaverage` /
`tpl-MNI152NLin2009cAsym`). Authoritative source: Wang et al. 2015 maximum-probability atlas via
neuropythy (fixed-hash fetch; native fsaverage/FSL-MNI152), resampled into MNI152NLin2009cAsym 2 mm via
the **official TemplateFlow MNI152NLin6Asym→2009cAsym transform with label-safe interpolation** (no
custom registration); Benson14 via neuropythy for the secondary V1–V3. Atlas SHA-256 values are computed
and frozen **inside the pinned pipeline container before any R_I** — recorded null here, not fabricated.

## Not yet complete (runs persistently; resume to collect)
Full ds005191 sync · in-pipeline atlas hash resolution · fMRIPrep S1–S6 · S1 technical qualification
(no R_I inspection) · implementation-hash freeze · confirmatory session-disjoint R_I (n_perm=1000,
n_boot=1000, n_rep_point=200, seeds 20260909/+100/+200) · matched R_P · cue/video falsification
(G_cue/G_imagery/G_video, R_I_cuevideo_predicted, Δ_I) · per-subject PASS · dataset gate.

## Why BLOCKED, not FAIL
No genuine fail-closed blocker was hit — cluster, storage, egress, FreeSurfer, and container provenance
are all available. Only long-running preprocessing remains, which per protocol runs on the persistent
cluster and resumes. Incomplete confirmatory measurement is **BLOCKED, not FAIL**, and the dataset gate
is left unevaluated rather than being forced.

## Per-subject results (S1–S6)
`reliability_S1..S6.json`: status `EXECUTION_INCOMPLETE`; R_I, permutation p, bootstrap CI, min-seed R_I,
R_P, cue_gain, video_gain, R_I_cuevideo_predicted, Δ_I, Δ inference, PASS status all **null** (not
fabricated). PASS count so far: **0/6 confirmatory** (measurement pending).

## Authorization
**C3XAG NOT authorized** — only `C3XAT_D2_ATLAS_IMAGERY_QUALIFIED` (a completed, qualifying dataset
decision) authorizes preparing C3XAG. This gate authorizes nothing further.

## Integrity
No neural outcome fabricated; no ROI selected by performance; no geometry/decoding/reconstruction/
semantic features; C3XAT seal and all prior gates immutable; no kubeconfig, license, or token committed.
Tests `test_c3xat_r1_execution.py` (hermetic); ruff clean; CI job `c3xat-r1-execution`.

## STOP after C3XAT-R1
No C3XAG; no geometry; no decoding; no reconstruction; no C4.
