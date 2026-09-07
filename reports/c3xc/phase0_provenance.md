# C3XC — Phase 0 Provenance & Dataset Certification

## Source / lineage
- **C3XB final SHA (source):** `d8cce52a7f804d00ffccff365a2e3e8975a598ed` (decision `C3XB_GOD_CATEGORY_IMAGERY_FAIL`).
- **Branch:** `research/mind-captioning-imagery-qualification-c3xc`.
- **Trigger satisfied:** D2 is inspected because C3XB (GOD) FAILED, per the frozen conditional rule
  (`d2_contract_extraction.md`). No dataset-level outcome fishing.

## Environment
- Windows-10 (10.0.19045); Python 3.13.5; numpy 2.3.1; scipy 1.16.0; h5py 3.16.0.

## Dataset identity (certified)
- **Raw:** OpenNeuro **ds005191**, latest snapshot **1.0.2** (verified via OpenNeuro GraphQL; created
  2024-05-29), DOI `doi:10.18112/openneuro.ds005191.v1.0.2`, author Tomoyasu Horikawa. 6 subjects
  (01–06); sessions anat + testImagery01–05 + testPerception01–02 + trainPerception01–11; tasks
  testImagery/testPerception/trainPerception; **398.8 GB / 2633 files** (raw BIDS — NOT downloaded; too
  large and not required for the qualification).
- **Preprocessed (OPERATIVE source):** Figshare article **25808179**, selected version **v2**, DOI
  `10.6084/m9.figshare.25808179.v2`, license CC BY 4.0. Title "Mind captioning: Evolving descriptive
  text of mental content from human brain activity" (Horikawa 2025, Science Advances
  10.1126/sciadv.adw1464). Code: github.com/horikawa-t/MindCaptioning.

## Raw vs preprocessed decision
- Analysis uses **B. official preprocessed Figshare data ONLY** (`testImagery_S{1..6}.mat`,
  `testPerception_S{1..6}.mat`). Raw BIDS is the provenance anchor only; the two are **not mixed**.
- The 398.8 GB raw set is infeasible to download in this environment and is unnecessary: the frozen
  C3X-family reliability estimator operates on the preprocessed single-trial multivoxel patterns, which
  the figshare `.mat` files provide directly.
- **Files used** (figshare v2 IDs + supplied_md5 pinned in `results/c3xc/c3xc_candidate_inventory.json`;
  SHA-256 computed on download): testImagery_S1..S6 and testPerception_S1..S6 (~2.4 GB total). The
  `trainPerception_*.mat`, `decfeat_wb.zip`, `feature.zip` (deberta-large / timesformer features —
  FORBIDDEN in this program), `res_encoding.zip`, `res_textgen.zip`, and Supplementary videos are
  **not used**.

## Preprocessed format certified (from testImagery_S1.mat, HDF5 v7.3 MATLAB)
- `braindat`: (148513 voxels × 360 samples) float32 — single-trial preprocessed amplitudes (whole brain).
- `metainf`: `Session`(1×360), `Run`(1×360), `Block`(1×360), `Label`(6×360) with
  `label_type = [Condition, cueID, imageryID, stimID, accuracy, vividness]`; ROI machinery
  `roiname`(1853), `roiname_used`(1679), `roiind_value`(148513×1853 uint8 membership), `xyz`, `volInds`.
- Preprocessing (Horikawa/KamitaniLab pipeline, as for GOD): per-sample amplitudes are block-averaged
  responses of the recall/stimulus period after hemodynamic-delay shift, run/session-normalized; each
  sample represents one recall (imagery) or one video presentation (perception). Exact temporal-window
  provenance is documented at the level of the release (single amplitude per trial; no within-trial time
  axis) — audited in `cue_audit.md`.
- **Raw/preprocessed consistency:** the preprocessed session/run/subject structure (6 subjects; 5
  testImagery sessions; 2 testPerception sessions) matches the OpenNeuro BIDS session listing exactly →
  no material disagreement.

## Structural facts certified (Phase 1 summary; full in subject_certification.json)
- **Imagery:** 360 samples = **72 videos × 5 sessions**; `imageryID` 72 unique; each of the 5 sessions
  contains all 72 videos exactly once ⇒ **5 independent session-repetitions per video**. `cueID`=0 and
  `stimID`=0 during imagery ⇒ **no target video shown during recall** (pure cued recall; `accuracy` and
  `vividness` behavioural ratings present).
- **Perception:** 360 samples = **72 videos × 5 repetitions** (2 sessions, 10 runs); `stimID` 72 unique,
  `stimLabel` 1–72.
- **Correspondence:** imagery `imageryID` set == perception `stimID` set == the same 72 videos ⇒
  **72/72 exact** perception↔imagery correspondence.
- **Independence unit for imagery reliability = SESSION** (5 fully-balanced units, one trial per
  (session, video)) — structurally identical to GOD run-pairs, so the frozen C3XB run-pair-disjoint
  estimator applies with unit:=session (see seal).
