# ANIMUS-P2-XR — Independent Cross-Dataset Replication Protocol (prospective seal)

**Parent:** P2-R `ANIMUS_P2_PERCEPTION_DECODER_VALIDATED` (remote CI-green at
`71371b2fd74ab13a7cfc7e75937b27286d70381c`; NOD ds004496 now **CLOSED for development**).
**Seal:** `results/animus_p2xr/animus_p2xr_protocol_seal.json` (self-hashed). **Firewall:** no real
replication decoding metric (M / 2AFC / retrieval / subject-PASS / dataset-PASS) is computed until this seal
**and** the implementation freeze are committed CI-green.

## Primary question
Does the **exact frozen** ANIMUS P2 perception→visual-latent decoding **method** replicate prospectively on
independent cohorts, scanners/protocols and stimulus datasets — **without outcome-guided rescue**? This is
replication of the method and effect, not decoder development, and not reuse of NOD subject weights.

## What may change vs P2 (and nothing else)
1. **Dataset I/O adapters** (`BOLD5000Adapter`, `THINGSfMRIAdapter`) — translate BIDS layout + event tables
   into the frozen `(onset, duration, stimulus_id)` contract only. They never touch ROI/HRF/GLM/nuisance/
   encoder/decoder/metrics/gates.
2. **Per-dataset participant denominators** (frozen below, before any outcome).

Everything else is inherited UNCHANGED and pinned by normalized SHA in the seal: Wang25 ROI
(MNI152NLin2009cAsym:res-2, sha `19b681ec…`, 7604 vox), pinned fMRIPrep
(`@sha256:9aec0b83…`), no smoothing, frozen LSA/GLM feature extraction, open_clip ViT-B-32
`laion2b_s34b_b79k` (dim 512, unit-L2, image-derived), ridge decoder + fold-safe normalization +
nested-validation α + bootstrap-ensemble uncertainty + reject option, content margin M, 1000 permutations,
1000 identity bootstraps, seeds 20260909/20261009/20261109, and the P2 subject gate.

## Replication panel (verified from OpenNeuro source metadata)
| Dataset | OpenNeuro | Version | Subjects (N) | Task | TR | PE | Fieldmaps | Design | Unique identities |
|---|---|---|---|---|---|---|---|---|---|
| BOLD5000 | ds001499 | v1.3.1 | CSI1, CSI2, CSI3, CSI4 (4) | task-5000scenes | 2.0 s | j- | spin-echo EPI | slow event-related | 4916 (CSI1-3) / 2952 (CSI4) |
| THINGS-fMRI | ds004192 | v1.0.7 | sub-01, sub-02, sub-03 (3) | task-things | 1.5 s | j | phasediff | rapid event-related | 8740 each |

Total denominator **N = 7**. THINGS keeps `trial_type ∈ {exp, test}`, excludes `catch` (attention probes).
Both datasets are **measurement-contract compatible** — the frozen LSA/GLM applies without semantic change
(THINGS' rapid design yields noisier betas: a real dataset difference the replication *tests*, never a
reason to switch to LSS/GLMsingle for the confirmatory primary). Dataset-provided optimized betas are
declared SECONDARY only.

## Prospective stimulus splits (`stimulus_split_seal.json`)
Inherited P2 identity-grouped 70/15/15 split, seed 20260909, computed per subject with frozen train/val/test
identity hashes; all repetitions of an identity stay in one partition (leakage-free). Split hashes are
sealed before outcomes.

## Stimulus overlap (`stimulus_overlap_audit.json`)
BOLD5000↔NOD = 44 shared ImageNet basenames (0.9%); THINGS↔NOD = 0; BOLD5000↔THINGS = 0. Reported, not
excluded: evaluation is on **within-dataset held-out identities** and **no NOD outcome informs any
replication decoder**, so overlap cannot leak. SHA/perceptual-hash overlap is finalized at stimulus staging.

## Subject gate (inherited, unchanged)
data_contract ∧ atlas_qc ∧ M>0 ∧ permutation_p<0.01 ∧ bootstrap_CI_lower>0 ∧ all_seeds_positive.

## Dataset gate (inherited, per dataset independently)
`required_passes = max(2, ceil(N_valid/3))` → BOLD5000 2/4, THINGS 2/3.

## Cross-dataset decision (frozen before outcomes)
- BOTH datasets VALIDATED → `ANIMUS_P2XR_INDEPENDENT_REPLICATION_PASS`
- exactly ONE VALIDATED → `ANIMUS_P2XR_INDEPENDENT_REPLICATION_LIMITED`
- NEITHER VALIDATED → `ANIMUS_P2XR_INDEPENDENT_REPLICATION_FAIL`
- genuine technical/provenance impossibility → `ANIMUS_P2XR_BLOCKED_<reason>`

**No pooled/meta-analytic rescue** can convert two non-VALIDATED datasets into a PASS. The secondary
meta-analysis (§30) is descriptive only.

## Pre-outcome power / Type-I audit (`power_audit.json`)
Subject-gate Type-I ≈ 0, sensitivity ≈ 0.998; null cohorts → 100% cross-dataset FAIL; a strong-in-one/
weak-in-other configuration correctly yields LIMITED, never PASS; strong effects reach PASS.

## Negative controls (inherited family, per dataset)
label permutation; category-matched decoys (THINGS `things_category_nr`; BOLD5000 ImgType family + ImageNet
synset, coarser — documented); low-level visual baseline; run/session fingerprint; within/cross-run shuffle.

## Boundaries
Imagery / dream / reconstruction / C3XAG / P3 execution remain **UNAUTHORIZED**. P2-XR is perception
replication only. A FAIL or LIMITED is a valid, reportable scientific outcome and triggers no retuning.
