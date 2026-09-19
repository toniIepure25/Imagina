# ANIMUS-P2E — Real Confirmatory Execution: Closeout

**Terminal decision: `ANIMUS_P2_BLOCKED_ROI_SPATIAL_PROVENANCE`** (a specific §7 block, not the prior vague
PENDING). Branch `product/animus-p2e-real-confirmatory` from P2 tip. No neural outcome was computed or
fabricated; the P2 scientific seal is unchanged.

## What P2E did
Ran REAL reconnaissance on the OrchestrAIQ cluster to execute the sealed confirmatory: probed the sealed
primary (NOD ds004496) and fallback (BOLD5000 ds001499) provenance against the staged volumetric Wang25 MNI
atlas. Jobs `animus-p2e-inventory`, `animus-p2e-xfmhunt`, `animus-p2e-b5kprov` (all Completed) established
the spatial-provenance facts below. Feature extraction / decoding were **never reached** — the pipeline is
gated at the ROI spatial-transform stage, before any neural outcome.

## Why it is blocked (verified, not slowness)
- Sealed ROI = Wang25 volumetric MPM in **MNI152NLin2009cAsym 2mm** (staged, confirmed 97×115×97 @ 2mm).
- **NOD** public fMRIPrep: only `space-T1w`; **anat derivatives absent**; no MNI↔T1w transform; ciftify is
  fsLR/CIFTI (not the sealed volumetric MPM).
- **BOLD5000** public fMRIPrep: `space-T1w/fsnative/orig`; **no** MNI152NLin2009cAsym space; only
  `target-fsnative`/`space-orig→T1w` affines — **no MNI↔T1w transform**; FreeSurfer present; "spm"
  derivatives are the study's own functional ROI masks, not Wang25 and not per-image betas.
- Therefore the exact reproducible relation between the sealed MNI Wang25 ROI and each subject's BOLD space
  cannot be established from either dataset's published provenance (**§7**). The sealed-authorized remedy
  (pinned fMRIPrep-to-MNI re-derivation) is a cohort re-preprocessing decision that **§2** forbids
  introducing during confirmatory execution — it requires a fresh prospective seal (P2-R).

## §63 closeout answers (with real facts; no fabricated numbers)
1. Dataset/version: sealed primary NOD ds004496; fallback BOLD5000 ds001499 (both audited on OpenNeuro S3).
2. Eligible N / valid N: **0 decoded** — blocked at ROI spatial provenance before subject selection.
3–14. Test identities, per-subject M, CIs, permutation p, 2AFC, Top-k, MRR, controls, calibration, reject:
   **not computed** (no decode run; reported as N/A rather than invented).
15–16. Subject PASS / required_passes: **0** / n/a (no valid cohort decoded).
17. Decision: **ANIMUS_P2_BLOCKED_ROI_SPATIAL_PROVENANCE**.
18–19. Neural initialization gain / neural-vs-behavioral-vs-fused: **not run** (product bridge is only run
   after a VALIDATED scientific gate; §47).
20. Newly authorized claim: **none**.
21. Still-forbidden: imagery neural content, thought decoding, dream decoding, mental-image reconstruction.
22. Same `NeuralContentDecoder` interface suitable for P3: **yes** (unchanged; gated).
23. Largest remaining blocker toward closed-loop imagery: for P2, the ROI spatial-provenance gap (needs a
   P2-R re-seal authorizing fMRIPrep-to-MNI re-derivation); for imagery specifically, C3XRP independent
   human replication + a separate P3 seal remain the gating scientific prerequisites.

## Integrity
Seal unchanged; primary respected; fallback rule respected (both lack the MNI relation — not a
performance-based switch); Wang25 ROI unchanged; no atlas switch; no invented registration; test firewall
intact; no partial-outcome peeking; C3XAG unauthorized; imagery unauthorized; no fabricated numbers. See
`results/animus_p2e/{spatial_transform_certification,fallback_activation,execution_status,final_integrity_audit,red_team_audit}.json`.
