# ANIMUS-P2 — Prospective Protocol (sealed)

Machine-readable seal: `results/animus_p2/animus_p2_protocol_seal.json` (self-hashed). This protocol is
frozen **before** any confirmatory test outcome; the confirmatory test partition is firewalled until this
seal is committed and CI-green.

## Question
Does independently acquired **visual-perception** fMRI contain enough stimulus-specific information to
predict a prospectively frozen visual representation for **previously unseen stimulus identities**, under
strict train/validation/test separation? (Perception only — not imagery.)

## Dataset
- Primary: **NOD (ds004496)**; fallback: **BOLD5000 (ds001499)** — selected on methodological criteria
  only (`results/animus_p2/perception_dataset_candidate_matrix.json`); forbidden variables (published
  decoding accuracy, neural SNR, our own outcomes, responsiveness) NOT used. Exact provenance/counts are
  verified at on-cluster staging; if the minimum content contract is unmet → `ANIMUS_P2_BLOCKED_DATASET`.
- Excluded as primary: NSD perception (used in C3), ds005191 Mind Captioning, ds001246 GOD.

## Partitions (grouped by identity)
70/15/15 train/val/test, grouped by **stimulus identity** (all repetitions of an identity in one
partition). Identity + near-duplicate (perceptual-hash) leakage audited. Split frozen with identity hashes
(`content_split_seal.json`).

## ROI
Primary **WANG25_TOPOGRAPHIC_VISUAL_NETWORK** (exact atlas provenance; per-subject QC; frozen voxel order;
no univariate outcome-based selection). Secondary: V1/V2/V3, whole visual cortex, whole GM, size-matched
random cortical controls (reported, never substituted for Wang25 after outcomes).

## Target representation
Frozen open vision-language embedding (pinned model/weights/preprocessing/dim/normalization in
`target_representation_seal.json`), derived from the **actual visual stimulus, not captions**. Captions are
secondary only.

## Neural features & preprocessing
Dataset-provided betas if exact/reproducible, else a frozen LSA/GLM (never mixed across subjects). Fold-safe
normalization/PCA (train-only fit; leakage-tested). Reuses C3XRA/C3XAT reproducibility discipline.

## Decoder & uncertainty
Primary: regularized linear (ridge) multi-output regression, alpha by nested validation. Uncertainty:
bootstrap decoder ensemble, calibrated on validation. Reject option on uncertainty/QC/OOD. Secondary
(descriptive): low-rank / small MLP — cannot rescue a failed primary.

## Primary statistic & subject gate
`M = mean_i ( cos(p_i,t_i) − mean_{j≠i} cos(p_i,t_j) )` over held-out test. Subject PASS: data/atlas QC PASS
**and** M>0 **and** within-test permutation p<0.01 **and** identity-bootstrap CI lower>0 **and** positive
under every sealed seed (20260909, +100, +200). Supporting: 2AFC, retrieval (Top-k/MRR/rank).

## Controls (mandatory)
Label permutation (must collapse), category-matched decoys, low-level-only baseline (neural must beat it),
run/session fingerprint + within/cross-run shuffle.

## Dataset gate
`required_passes = max(2, ceil(N/3))` over the fixed eligible denominator (no shrinkage). Outcomes:
`ANIMUS_P2_PERCEPTION_DECODER_VALIDATED / LIMITED / FAIL / BLOCKED_<reason>`.

## Claim authorization
Capability-scoped. Success authorizes **PERCEPTION_NEURAL_CONTENT only**. Imagery/dream/reconstruction
remain unauthorized regardless — validating perception can never raise them (invariant tested).

## ANIMUS integration
After validation only: a neural-initialization experiment (uninformed vs neural vs fused) on held-out
perception trials. The product bridge cannot rescue a failed scientific decoder. No image reconstruction in
the primary gate.

## Confirmatory unlock
The frozen test partition is unlocked only by `run_p2_confirmatory` after this seal is committed + CI-green.
