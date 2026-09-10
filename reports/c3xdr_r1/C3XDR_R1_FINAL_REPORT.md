# C3XDR-R1 — Remote Infrastructure Rescue & Frozen Replay — Final Report

**Execution attempt 2 of the sealed C3XDR question. Protocol / Model A / estimator / ROI / storage
threshold UNCHANGED. NOT C3XE / C3XR / C3XR-CAT / C4. No geometry, captioning, semantic decoding, or
reconstruction.**

## Decision
**`C3XDR_R1_BLOCKED_ROI_PROVENANCE`** — the remote **infrastructure gate PASSED** (the OrchestrAI
Kubernetes cluster, 107 TB persistent NFS, and container execution are available via the kubeconfig
that attempt-1's audit never tested), which **resolves the `C3XDR_BLOCKED_STORAGE` blocker**. But the
Phase-1 provenance gate — required *before* any raw download — **fails**: the released KamitaniLab
localizer ROIs (VC, V1, LOC, FFA, PPA…) cannot be reproducibly mapped into a raw-derived functional
space from public artifacts, and no reproducible preprocessing pipeline is published. Per the sealed
"do NOT approximate ROI mapping" rule, execution stops here. **BLOCK, not FAIL** (imagery reliability
was never tested). C3XC / C3XD / C3XDR remain immutable.

## Provenance / lineage
- Starting SHA `4079e45…` (C3XDR final) → branch `research/d2-cue-deconfounded-imagery-c3xdr-r1`.
- Old C3XDR decision `C3XDR_BLOCKED_STORAGE` (correct for attempt 1); execution seal `7afc7946…`
  (unchanged; `execution_attempt=2`). C3XC `fce7a04…`, C3XD `d60cbfd…` preserved.

## Infrastructure (see `C3XDR_R1_ENVIRONMENT_PROVENANCE.md`)
- Kubeconfig discovered: `…/Downloads/antoniu_iepure.yaml` (sha256 `d9380cc3…`, never committed).
  Cluster `https://10.130.123.31:10443` **reachable+authenticated**; namespace `runai-romania-dev`;
  full pod/job/pvc/exec permissions.
- Execution pod `orchestraiq-jupyter-…-fbxj5` (Running 5d+): 256 CPU / 1007 GiB RAM / A100-40GB; image
  digest `sha256:85ab9304…`.
- Persistent storage: NFS PVCs `orchestraiq-jupyter-pvc` + `-extra-pvc` (nfs-client), **107 TB free**
  (138 T total) at `/home/jovyan/{legacy-work,work}` → **≥300 GB requirement MET**. Persistence via the
  Bound nfs-client PVC contract (no write-probe, to avoid disturbing the production workspace).
- Verdict: **`C3XDR_R1_REMOTE_INFRA_PASS`**.

## Phase-1 preprocessing / ROI provenance (the blocker)
Investigated the authoritative public sources (KamitaniLab `horikawa-t/MindCaptioning` repo; Figshare
25808179; OpenNeuro ds005191):
- The repo is **analysis-only** (decoding/encoding/text-generation). `getRoiVoxelIdx.m` derives ROI
  voxel indices **solely from the released `.mat` `metainf.roiname`/`roiind_value`** — it does not
  define or map ROIs from raw.
- **No** preprocessing-from-raw pipeline/parameters, **no** ROI masks, **no** raw→functional transform,
  and **no** released reference EPI are published. Figshare ships block-averaged single-trial amplitude
  `.mat` + DNN features + results + videos — no timeseries, no ROI mask, no transform.
- Therefore none of the three sealed Phase-1 options is satisfiable: (1) the exact KamitaniLab
  functional space cannot be reproduced (no published pipeline); (2) the released-ROI space cannot be
  targeted (undocumented, no reference volume); (3) no independently certifiable raw→released ROI
  transform exists. Approximating VC is sealed-forbidden ⇒ **`C3XDR_R1_BLOCKED_ROI_PROVENANCE`**.
- Consistent with C3XD's `BLOCKED_C3XD_ROI_PROVENANCE`: this confirms the ROI/preprocessing provenance
  — not storage — is the true, infrastructure-independent barrier.

## Raw acquisition / per-subject
- **Downloaded bytes: 0** (stopped before download, per protocol). trainPerception excluded.
- Preprocessing spec / S1 technical qualification / per-subject R_I, R_P, cue_gain,
  R_I_cuevideo_predicted, Δ_I, temporal controls: **NOT_EXECUTED / NOT_PRODUCED_BLOCKED** (stubs
  recorded; nothing fabricated). ≥2/6 gate **not evaluated**; subjects processed: 0.

## Authorization
**Nothing authorized. C3XE preparation NOT authorized** (never C3XR/C3XR-CAT/reconstruction/captioning/
semantic-decoding/geometry/C4). BLOCKED ≠ FAIL.

## What would unblock
Authoritative KamitaniLab preprocessing pipeline+parameters (to reproduce the released functional space
so the localizer ROIs are directly reusable), **or** released ROI masks / reference EPI / raw→functional
transform enabling an independently certified ROI mapping (an author request may be required). With that,
the frozen C3XDR seal can be replayed on the now-available remote infrastructure.

## Integrity / verification
Execution seal referenced unchanged (attempt=2) ✓; Model A / estimator / ROI / threshold unchanged ✓;
no outcome-based selection (nothing run) ✓; no raw neural data, **no credentials, no kubeconfig** in git
✓; no large download ✓; C3XC/C3XD/C3XDR immutable ✓. Tests: `test_c3xdr_r1_execution.py` (hermetic);
ruff clean; CI job `c3xdr-r1-remote-execution`: run **34523717512 = SUCCESS** on SHA `e91e9214…` (all jobs green).

## Scientific bottom line
C3XDR-R1 advances the program by **resolving the infrastructure blocker** and **isolating the true
barrier**: the raw cue-deconfounded re-test is well-posed and now has adequate compute/storage, but it
cannot proceed because the released ROI definition is not reproducibly mappable to raw space from public
artifacts. This is an operational/provenance limit of the public release, not a neural result. **STOP
after C3XDR-R1.**
