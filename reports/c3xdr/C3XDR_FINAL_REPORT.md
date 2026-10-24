# C3XDR — Infrastructure-Enabled Execution Rerun of C3XD — Final Report

**Execution rerun of the sealed C3XD question. NOT C3XE / C3XR / C3XR-CAT / C4. No geometry,
captioning, semantic decoding, or reconstruction.**

## Decision
**`C3XDR_BLOCKED_STORAGE`** — the Section-1 infrastructure gate failed: this environment has no
execution location with the required ≥300 GB usable persistent storage, no container runtime, no
reproducible neuroimaging preprocessing/registration stack, and no reachable remote/pod compute.
Per protocol, **no large data was downloaded** and no raw neural outcome was produced. This is a
**BLOCK, not a FAIL** (imagery is not shown to be unreliable). C3XC and C3XD remain immutable and valid.

## Provenance / lineage
- Starting SHA `d60cbfde4cab53270298f4b0df59e3beb8cfddab` (C3XD final) → branch
  `research/d2-cue-deconfounded-imagery-c3xdr` from that SHA. CI-verified SHA `2de1874568bacffe…`
  (CI run **34406371440 = SUCCESS**, c3xdr + all inherited gates + backend-core green); this
  documentation commit advances the branch tip past that SHA.
- C3XC final `fce7a04…` (`C3XC_D2_SEMANTIC_IMAGERY_QUALIFIED`); C3XD final `d60cbfd…`
  (`C3XD_BLOCKED_RAW_PIPELINE_INFEASIBLE`, seal `1a680c1b…`, CI 34368467455) — **preserved unchanged**.
- Execution seal `reports/c3xdr/c3xdr_execution_seal.json` self_hash `7afc7946…`, committed before any
  raw inspection; freezes Model A (LSA) as primary, the frozen reliability estimator, ROI/cue contracts,
  two-stage execution, and decision rules.

## Infrastructure audit (`results/c3xdr/infrastructure_audit.json`)
- Host `DESKTOP-C2MF2DI`; drives C: 15.4 GB free / D: **37.1 GB free** (best); NTFS; write ≈ 345 MB/s,
  read ≈ 2356 MB/s.
- kubectl present but **no cluster reachable** (localhost:8080 refused; no KUBECONFIG; `~/.kube` holds
  only `cache/`). No network mounts. No docker/apptainer/singularity. No fMRIPrep/FSL/SPM/FreeSurfer/
  nipype/nilearn (only nibabel).
- **Requirement (≥300 GB storage + reproducible container-pinned preprocessing stack + optional remote
  compute) NOT met.** Shortfalls: 37.1 GB « 300 GB (raw subset alone 139.4 GB, peak ~223 GB); no
  preprocessing stack; no container runtime; no remote compute.

## Raw snapshot / download
ds005191 v1.0.2. Selected subset (frozen, inherited from C3XD): testImagery + testPerception + events/
sidecars for S1–S6; **trainPerception excluded**. **Downloaded bytes: 0** (gate failed first). Raw input
hashes: N/A (nothing acquired).

## Preprocessing / ROI / per-subject
- Preprocessing: `NOT_EXECUTED_BLOCKED` (`C3XDR_PREPROCESSING_PROVENANCE.md`, `c3xdr_preprocessing_spec.json`);
  no container digest / versions to report.
- ROI provenance: `NOT_EXECUTED_BLOCKED` (raw functional space not produced; VC mapping not attempted;
  the C3XD `BLOCKED_C3XD_ROI_PROVENANCE` risk remains unresolved). VC voxel counts per subject: N/A.
- Event contract: certified in C3XD (360 imagery = 72 videos × 5 sessions balanced; 72×5 perception;
  72/72 correspondence) — carried forward, not re-derived.
- Model A (LSA) confirmation: frozen prospectively from the C3XD synthetic analysis; **not run on real
  BOLD** (no A/B/C re-comparison; primary GLM never touched real outcomes).
- Per participant R_I_raw / p / CI / min-seed / gate, R_P_raw, attenuation, R_cue, R_postvideo,
  cue_gain_empirical, video_gain_empirical, R_I_cuevideo_predicted, Delta_I, falsification, early-vs-late,
  previous/next controls: **NOT_PRODUCED_BLOCKED** (per-subject stubs recorded; no trials fabricated).
- Raw-vs-C3XC comparison: N/A (no raw R_I).

## Dataset decision / authorization
Subjects processed: 0. The ≥2/6 gate was **not evaluated**. Decision `C3XDR_BLOCKED_STORAGE`. Authorizes
**nothing**; **C3XE preparation NOT authorized**; never C3XR/C3XR-CAT/reconstruction/captioning/
semantic-decoding/geometry/C4.

## What would unblock
An execution host with ≥300 GB (pref ≥500) usable persistent storage AND a reproducible container-pinned
preprocessing/registration stack producing a space compatible with the released ROIs; then replay the
frozen execution seal — selective raw acquisition (trainPerception excluded) → Model-A LSA betas →
certified VC ROI mapping → frozen session-disjoint reliability gate + cue+video-only falsification.

## Integrity / verification
Execution seal before any raw inspection ✓; frozen estimator/model unchanged (hashes pinned) ✓; no
model/ROI/subject/trial selection on outcomes (nothing was run) ✓; no semantic features ✓; no geometry
imports (test-enforced) ✓; no raw neural data in git; no large download attempted ✓; C3XC/C3XD immutable
(empty diff) ✓. Tests: `test_c3xdr_execution.py` (hermetic); ruff clean. CI job
`c3xdr-d2-cue-deconfounded-imagery` (C3XDR + inherited C3XD/C3XC/C3XB/C3XA/C3X/C3R/C3G/C3M + backend-core
+ Ruff): CI run 34406371440 = SUCCESS on SHA `2de1874568bacffe…` (all jobs green).

## Scientific bottom line
C3XDR neither confirms nor refutes C3XC/C3XD: it is an execution attempt that could not proceed past the
infrastructure gate in this environment. The scientific plan is fully frozen and replayable; the barrier
is purely operational (storage + preprocessing stack). **STOP after C3XDR.**
