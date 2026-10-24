# C1 Protocol — Neural–Behavioral Alignment and Perception–Imagery Transfer

**Status:** Frozen prior to any model training. This document, together with
[`C1_DATASET_CANDIDATES.md`](C1_DATASET_CANDIDATES.md) and
[`C1_ANALYSIS_SPEC.md`](C1_ANALYSIS_SPEC.md), constitutes the pre-registration
for Scientific Gate C1. Confirmatory analyses may not deviate from this
document once training begins; any deviation is exploratory by definition.

## 1. Scope and non-goals

This is **not** an EEG classification demo and **not** an EEG-to-image
reconstruction project. It does not build a real-time BCI, and it does not
claim to read thoughts, reconstruct private mental content, or modify human
imagery ability. See §8, Scientific claim boundaries.

## 2. Primary and secondary scientific questions

**Primary question (H2):** Does trial-level EEG provide reliable,
out-of-sample information about objective imagery precision beyond behavioral
history, experimental design variables, subjective reports, and
participant-level baselines?

**Secondary question (H3/H4):** Is the useful neural information explained by
a shared but state-dependent representation between visual perception and
visual imagery?

These are kept strictly separate from neural signal reliability (H1),
cross-subject generalization (H5), and from each other. No single
classification-accuracy number stands in for more than one of these.

## 3. Dataset decision

```
PRIMARY_PAIRED_DATASET = FOUND
primary_confirmatory_dataset_id = ds005815 (YOTO)
```

Full audit in `C1_DATASET_CANDIDATES.md`. ds005815 is used for H1–H5 primary
and secondary confirmatory analyses. ds004306 is available for exploratory H1/
H3/H4 robustness checks only (no trial-level behavior, so it cannot serve H2).
THINGS-EEG2 and Alljoined-1.6M are available for perception-encoder
pretraining and external replication (Tier B) but carry no imagery condition
and cannot support H2/H3 primary claims. OpenMIIR is available only as an
auditory, modality-general control of the alignment infrastructure (H4), never
as evidence for the visual-imagery claim. EEG-ImageNet (Spampinato et al.) is
excluded entirely, including from pretraining, due to its documented
block/temporal confound (Li et al. 2018).

Because ds005815 was only audited at the metadata/methods level in Phase 0,
two items remain open and are treated as **stopping conditions** (§7), not
settled facts:
- the raw trigger-code table must be decoded and cross-checked against the
  paper's stimulus table before any epoch is labeled;
- the block/stimulus-category randomization must be empirically verified
  from the actual event stream, not assumed from the methods text.

## 4. Prespecified hypotheses

### H1 — Neural reliability
Post-cue EEG features contain reproducible within-subject structure beyond
pre-cue and temporally shifted controls. Measured via split-half reliability,
session-to-session reliability (ds005815 has 2 sessions/participant),
within-subject representational consistency, and subject-level confidence
intervals. Exploratory.

### H2 — Incremental behavioral validity (PRIMARY)
A behavior-plus-neural model improves held-out prediction of the objective
imagery-precision endpoint over an identical behavior-only model. Confirmatory.
Primary estimand defined in §5.

### H3 — Perception-to-imagery transfer
A representation trained on perception predicts imagery content or
imagery-associated behavior above a label-shuffled null, a temporal-shift
null, a pre-cue EEG null, a random visual-embedding null, and an
ocular-channel-only control (frontal-channel proxy — ds005815 has no dedicated
EOG channel; see residual risk in `C1_DATASET_CANDIDATES.md`). Transfer is
evaluated without imagery labels entering perception pretraining. Secondary
confirmatory.

### H4 — State dependence
Perception and imagery share content-related geometry, but their temporal or
spectral realization differs. Measured via RSA, CKA, cross-condition
retrieval, temporal generalization matrices, and regional/spectral ablations.
Exploratory; representational similarity is descriptive, not causal evidence.

### H5 — Cross-subject generalization
Any claim of participant-general neural information must survive
leave-one-subject-out (LOSO) evaluation. Subject-specific decoding is
reported separately and always labeled as such, never presented as
cross-subject performance.

## 5. Primary estimand (frozen)

```
Delta_OOS = performance(behavior_plus_neural) - performance(behavior_only)
```

- Both models use identical outer folds, identical inner folds, identical
  observations, and the identical evaluation metric.
- The exact metric depends on the frozen behavioral target type and is fixed
  in `C1_ANALYSIS_SPEC.md` before any confirmatory result is examined:
  continuous → out-of-sample R² (primary) and MAE/RMSE; binary → log loss
  (primary), ROC-AUC (secondary); ordinal → proper ordinal log score; circular
  error → circular loss.
- **The inferential unit is the participant.** The primary estimand is the
  subject-level paired difference in outer-fold performance, not a
  trial-pooled number.

## 6. Validation hierarchy (frozen)

```
Level 1: within-subject repeated-trial reliability
Level 2: subject-dependent held-out-trial decoding
Level 3: leave-one-subject-out generalization
```

Level 2 results are never reported as cross-subject BCI performance. Only
Level 3 supports a participant-general claim.

## 7. Confirmatory vs. exploratory analyses

**Confirmatory (locked before training):**
- H2 primary estimand under the frozen metric, folds, and covariates.
- H3 transfer test against its five prespecified nulls.
- The ten falsification tests in `C1_ANALYSIS_SPEC.md`.

**Exploratory (reported as such, never used to inflate the confirmatory claim):**
- H1 reliability diagnostics.
- H4 RSA/CKA/temporal-generalization maps.
- Any channel, band, or time-window map not in the frozen H2/H3 feature set.
- Any result from ds004306, THINGS-EEG2, Alljoined-1.6M, or OpenMIIR.

## 8. Scientific claim boundaries

**Allowed:** EEG representations contain or do not contain decodable
information under the tested protocol; perception representations transfer or
do not transfer to imagery; neural features improve or do not improve
held-out behavioral prediction; results generalize only under the evaluated
subject and dataset regime.

**Forbidden without new prospective human evidence:** the system improves
human imagery; the system reads thoughts; the system reconstructs private
mental content; the system is a functional real-time BCI; the system has
clinical efficacy; the system causally modifies imagery ability.

## 9. Leakage threats (enumerated)

1. Fitting normalization, ICA component selection, PCA, spatial filters,
   feature selection, imputation, or artifact thresholds on data that includes
   held-out participants or held-out trials.
2. Hyperparameter or architecture selection that inspects outer-test results.
3. Duplicate-stimulus leakage across confirmatory folds (same exact stimulus
   image/sound appearing in both an outer-train and outer-test fold).
4. Participant ID or session ID acting as a proxy for the behavioral target.
5. Global (non-block-respecting) permutation shuffles that destroy the
   repeated-measures dependence structure and inflate apparent significance.
6. Ocular or muscle artifact channels carrying the effect instead of
   content-related neural signal.
7. Block-order/temporal drift correlated with stimulus category or condition
   (the exact failure mode documented for EEG-ImageNet — see
   `C1_DATASET_CANDIDATES.md`).

## 10. Stopping conditions

Work on H2/H3 confirmatory analyses stops and reverts to exploratory-only
status if, during Commit 2/3 ingestion and QC:
- the ds005815 trigger-code decode cannot be reconciled with the paper's
  stimulus table with full confidence;
- empirical block/stimulus-category confound analysis shows condition is not
  adequately decorrelated from block or trial-order;
- retained-trial fraction after artifact rejection falls so low that the
  effective per-participant trial count cannot support the frozen inner/outer
  CV design;
- fewer than the number of usable participants required by the fixed-sample
  sensitivity analysis (`C1_ANALYSIS_SPEC.md`) remain after quality control.

If a stopping condition triggers, the gate decision is
`C1_NEURAL_FOUNDATION = PASS`, `C1_INCREMENTAL_BEHAVIORAL_VALIDITY =
BLOCKED_BY_PAIRED_DATA` or `C1 = FAILED_BY_RELIABILITY`, per the decision
rules in `C1_ANALYSIS_SPEC.md` — never a weakened version of the original
criteria.

## 11. Expected limitations (declared in advance)

- 20 participants is adequate for exploratory subject-level inference but
  modest for a high-powered LOSO test; the fixed-sample sensitivity analysis
  quantifies the minimum detectable effect under this constraint rather than
  treating a null as proof of absence.
- ds005815 has no dedicated EOG channel; the ocular-only negative control is
  weaker than it would be with true EOG.
- The dataset's own metadata contains at least one documented authoring
  error (a copied resting-state description in the task `eeg.json`), which
  motivates independent verification over trusting sidecar text at face
  value.
- Single-site, single-hardware data; cross-hardware generalization is not
  claimed.

## 12. No-efficacy claim boundary

Nothing in C1 is evidence that IMAGINA's feedback loop improves imagery
ability, that EEG features should drive real-time feedback, or that any
clinical or educational efficacy exists. C1 is strictly an offline,
retrospective analysis of neural-behavioral alignment under the tested
protocol and dataset regime.
