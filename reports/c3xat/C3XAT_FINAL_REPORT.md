# C3XAT — Atlas-defined Cue-Deconfounded Raw Imagery Qualification — Final Report

**NEW prospectively-sealed measurement-qualification gate. NOT a C3XDR replay and NOT an exact
replication of the released KamitaniLab ROI analysis. Measurement qualification ONLY — NO geometry, NO
decoding, NO reconstruction, NO semantic features.** C3XC / C3XD / C3XDR / C3XDR-R1 / C3XPR / C3XPA
preserved unchanged; C3XDR seal `7afc7946…` untouched.

## Decision
**`C3XAT_BLOCKED_EXECUTION`** (BLOCKED ≠ FAIL). The protocol is fully sealed and every
publicly-verifiable contract and atlas/preprocessing provenance spec is frozen, but the confirmatory
pipeline — selective raw ds005191 acquisition + reproducible fMRIPrep of S1–S6 to MNI152NLin2009cAsym
2 mm + WANG25/Benson/gray-matter ROI construction + spatial QC + sealed reliability + cue/video
falsification — requires the OrchestrAI cluster and **cannot be completed in this session** (the live
kubeconfig is not present here; never committed, per policy). **No R_I / R_P / falsification outcome was
computed or fabricated.** The dataset gate was therefore **not** evaluated. **C3XAG is NOT authorized.**

## Scope (no historical decision superseded — `c3xat_scope_registry.json`)
- **C3XDR**: exact replay using original released KamitaniLab ROI definitions; still blocked by missing
  released↔raw spatial provenance.
- **C3XPA**: dormant author-artifact validator; may resume if authoritative spatial material arrives.
- **C3XAT**: new atlas-defined raw-fMRI analysis; does **not** reproduce the original ROI definition.

## Provenance
Starting SHA `bf58713` (C3XPA final) → branch `research/d2-atlas-raw-imagery-c3xat`. Phase-0 seal
`reports/c3xat/c3xat_protocol_seal.json` freezes dataset, subjects, preprocessing, output space, primary
ROI (WANG25), secondary ROI (Benson V1–V3), whole-cortex control, Model A GLM, nuisance, reliability
estimator, null, bootstrap, split seeds, cue/video falsification, subject PASS rule, and the dataset
decision rule — all before any outcome.

## What is certified now (publicly verifiable, no BOLD)
- **Dataset contract** (`dataset_contract.json`): ds005191 v1.0.2, S1–S6, include/exclude sets,
  72-video / 5-rep / 360-imagery-trial / 5-session contract, 72/72 correspondence requirement,
  fail-closed. Empirical events verification is part of execution.
- **Preprocessing provenance** (`preprocessing_provenance.json`): fMRIPrep → MNI152NLin2009cAsym 2 mm,
  smoothing NONE; exact version/digest/hash strings frozen to their concrete values at container-pull.
- **Atlas provenance**: Wang 2015 complete MPM (`wang2015_atlas_provenance.json`, 25 maps / 22 regions,
  no performance subselection) and Benson14 via pinned Neuropythy (`benson14_atlas_provenance.json`,
  secondary). Canonical public identity pinned; **SHA-256/MD5 recorded null and set to the verified
  digest of the exact downloaded file at construction — no hash fabricated.**
- **Infrastructure re-audit** (`infrastructure_reaudit.json`): OrchestrAI remains certified by C3XDR-R1
  (Kubernetes, 107 TB NFS, A100); unchanged, so no new scientific decision is derived from it. Live
  re-audit needs the kubeconfig (absent here).

## Execution-state records (honest, non-fabricated)
`roi_qc_S1..S6.json` (ROI_NOT_CONSTRUCTED_EXECUTION_BLOCKED, all counts/hashes null),
`reliability_S1..S6.json`, `perception_reliability.json`, `cuevideo_falsification.json`,
`negative_controls.json`, `secondary_benson_results.json`, `spatial_enrichment_control.json` — all
status EXECUTION_BLOCKED with null outcome fields. The frozen estimator + seeds + operators will produce
these records unchanged at confirmatory execution.

## What would unblock
Run the sealed pipeline on OrchestrAI: pull the pinned fMRIPrep container, preprocess S1–S6, construct
and QC the WANG25 + Benson V1–V3 + gray-matter masks (freeze hashes), then execute the frozen reliability
and cue/video falsification. Download and hash-verify the Wang2015 MPM and Benson14 template (fill the
null SHA-256 fields). S1 technical qualification must not be used to modify the pipeline.

## Relation to prior work (required wording)
The exact released-ROI replay **remains provenance-blocked**. C3XAT independently tests the core
imagery-measurement question using prospectively defined public atlas ROIs. **C3XDR was not "rescued";
no original Kamitani localizer ROI is reproduced.** Any future comparison to C3XC is a *cross-pipeline
descriptive comparison*, not a replication effect (different spatial definitions).

## Authorization
None. Only `C3XAT_D2_ATLAS_IMAGERY_QUALIFIED` would authorize **preparing** (not executing) the
separately-sealed **C3XAG** gate. This gate authorizes nothing further: not C3XAG execution, C3XE, C3XR,
C3XR-CAT, C3XDR-R2, geometry, decoding, reconstruction, or C4.

## Integrity / verification
No raw BOLD inspected; no neural outcome fabricated; no ROI selected by performance; secondary ROI cannot
rescue primary; no semantic features; no geometry imports; no reconstruction; no atlas binaries or raw
data committed (provenance/hashes only); no credentials committed. Prior gates immutable. Tests
`test_c3xat_qualification.py` (hermetic, synthetic fixtures only); ruff clean; CI job
`c3xat-atlas-imagery`; CI-verified SHA / run recorded at closeout.

## STOP after C3XAT
No geometry, no C3XAG, no decoding, no reconstruction, no C4.
