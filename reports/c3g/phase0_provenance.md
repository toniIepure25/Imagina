# C3G Phase 0 — Provenance & Starting-Point Certification

**Gate:** C3G — State-Specific Neural Geometry (NOT C4).
**Date:** 2026-08-26. **Subject:** subj01 only (no population claim).

## Source of truth
- **Source / C3M final SHA:** `11445aa90486865ae1fcb33b4e3699e6e501f419` (checked out; C3G branched from it).
- **New branch:** `research/state-specific-geometry-c3g`.
- **C3M decision inherited (immutable):** `C3M = COMPLETE_WITH_STATE_SPECIFIC_IMAGERY_NULL`.
- C3 and C3M artifacts are **not modified** by C3G.

## Environment
- GPU pod `orchestraiq-jupyter-5d6c688775-zv6ms` (Run:ai romania-dev), PVC `/home/jovyan/work`
  (NFS, persistent). Python `/home/jovyan/work/IMAGINA/venv/bin/python` 3.12 with numpy 2.5.2,
  scipy 1.18.0, h5py 3.16.0, nibabel 5.4.2, pandas 3.0.5. Repo checkout
  `/home/jovyan/work/IMAGINA/repo`; C3M/alignment modules re-synced bit-identical to the committed
  branch (`cross_session_alignment.py` sha256 `e177fd9fcf1cb39c…`,
  `run_c3m_vision_gate_m3m4.py` `2a9cd2967131da87…`).

## Frozen input hashes (verified bit-identical to C3/C3M)
| Input | Hash (prefix) | Status |
|---|---|---|
| frozen decoder weights | `df2dfd8961d7f738…` | recomputed == stored ✓ |
| ROI selection (nsdgeneral ∧ ncsnr>0) | `84e0d08be5d7e68b…` | ✓ |
| nsdgeneral.nii.gz | `c16620878feeaf82…` | == decoder roi_hash ✓ |
| perception ncsnr.nii.gz | `39217f54a32fcc32…` | == decoder ncsnr_hash ✓ |
| betas_nsdimagery.hdf5 | `31485ff0e4cb9e90…` | == C3-recorded ✓ |
| X_p rolling extraction (8 sessions 4,15,16,20,22,26,27,29) | per-session raw sha256 in `results/c3m_xp_extraction_subj01.json` | present ✓ |
| c3m_alignment_seal.json | self_hash `1332fee66e723b04…` | ✓ |
| c3m_final_decision.json | self_hash `b872ae52ea5eecf4…` | ✓ |

## Tests
- `backend/app/tests/test_c3m_alignment.py`: **6/6 pass**.

## C3M metric reproduction (deterministic)
Re-ran the frozen M3 CORAL vision gate (`run_c3m_vision_gate_m3m4`) end-to-end on the pod into an
isolated dir. Result **logically identical** to the committed `results/c3m_vision_gate_m3m4.json`
(content hash `1db3274fc1b9871a…` matches, modulo timestamp):
- Set B M0 identity: MRR 0.4517, dominant_fraction 0.938.
- Set B **M3 CORAL: MRR 0.8052, 2AFC 0.887, dominant_fraction 0.312, perm p 0.0014** (== committed).
- Set B M4: MRR 0.5594, dominant_fraction 0.646.

## Determination
**PROVENANCE PASS.** The C3M final state reproduces bit-/logically-identically; all frozen inputs
verified. C3G may proceed. C3G will not alter any C3/C3M artifact, threshold, hash, or decision.
