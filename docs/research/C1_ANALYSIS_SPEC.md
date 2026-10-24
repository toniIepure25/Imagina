# C1 Analysis Specification

Companion to `C1_PROTOCOL.md`. This document freezes the exact statistical
machinery before any model is trained. It will be extended (not weakened) as
implementation commits land; any change to an already-frozen value after
confirmatory results exist must be logged as a protocol deviation, not
silently edited.

## 1. Primary behavioral target (to be finalized against decoded ds005815 events)

Candidate targets, in order of preference, pending the Commit 2 trigger-code
decode:
1. Per-trial vividness rating (1–5, ordinal) — the only behavioral variable
   confirmed present in ds005815 at the trial level.
2. If a defensible continuous transform of vividness is supportable after
   decode (e.g., a validated composite with reaction-time or other recorded
   channel), it will be documented here before use; it is not assumed now.

**Primary metric family: ordinal.** Per `C1_PROTOCOL.md` §5, the frozen
primary metric for an ordinal target is a proper ordinal log score (e.g.
cumulative-link/ordinal-logistic negative log-likelihood on held-out trials,
aggregated per participant). Secondary: Spearman rank correlation between
predicted and observed vividness, per participant.

## 2. Behavior-only model (frozen covariate set)

May include only:
- prior behavioral performance (vividness on preceding trials for the same
  participant, available before the current trial);
- condition (perception/imagery instructed condition and modality: visual,
  auditory, multimodal);
- period/session index, block index, trial index within block;
- task family / stimulus category (face, square, tone, etc. — identity of
  the class, not the specific exemplar, to avoid stimulus-identity leakage
  into a per-trial behavioral prediction that must generalize);
- participant-level baseline (mean vividness across all other trials for
  that participant, computed only from training folds);
- subjective variables only if independently recorded per trial (none
  currently confirmed beyond vividness itself, which is the target, not a
  covariate).

## 3. Behavior-plus-neural model

Identical behavior-only covariates, plus frozen neural features from:
- Commit 4 classical features (ERP amplitude/latency, band power, spectral
  entropy, alpha/beta summaries) as the first, interpretable pass;
- Commit 5 compact encoder representations (linear/ridge, EEGNet-style,
  compact temporal conv) as a second pass, each evaluated separately and
  reported as distinct rows, never pooled into one number.

## 4. Cross-validation design

```
Outer: leave-one-subject-out (LOSO), 20 folds (one per ds005815 participant)
Inner: participant-grouped k-fold within the outer-training participants,
       for hyperparameter selection only — never touches the outer-test
       participant's data
```

Both behavior-only and behavior-plus-neural models use the identical outer
fold assignment, identical inner fold assignment, identical trial-level
observations, and the identical evaluation metric. Any preprocessing step
that estimates parameters from data (normalization, ICA component selection,
PCA, spatial filters, feature selection, imputation, artifact thresholds) is
fit only within the outer-training participants' folds, never on the held-out
participant, per `C1_PROTOCOL.md` §9.

## 5. Inferential procedure

- Primary estimand: subject-level paired difference in outer-fold performance
  (`Delta_OOS`), one value per held-out participant.
- Inference: subject-level bootstrap (resampling participants with
  replacement) or exact sign-flip/permutation test on the paired
  differences — both preserve the participant as the unit of resampling.
  The specific choice is finalized once the usable-participant count is known
  post-QC (small-N favors exact sign-flip over bootstrap; documented in the
  results artifact, not changed after confirmatory results are seen).
- Report: point estimate, confidence interval, calibration diagnostics,
  heterogeneity across participants, and influence diagnostics (leave-one-
  participant-out sensitivity of the aggregate estimate).

## 6. Leakage-safe permutation nulls

Permutations preserve the repeated-measures structure. Depending on which
falsification test is being run, shuffling is restricted **within**:
- participant (never across participants, which would let one participant's
  baseline explain another's outcome);
- session (for session-confound checks);
- condition (for condition-confound checks);
- task family (for stimulus-category-confound checks);
- experimental block (for block/temporal-confound checks, the exact failure
  mode documented for EEG-ImageNet).

A global shuffle across all observations is never used — it destroys the
dependence structure the repeated-measures design relies on and would produce
an invalid null distribution.

## 7. Required falsification tests (all must run automatically, all confirmatory)

1. Pre-cue EEG must not match post-cue predictive performance.
2. Temporally shifted EEG must underperform correctly aligned EEG.
3. Trial labels shuffled within valid exchangeability blocks (§6) must remove
   the effect.
4. Random channel permutations must degrade spatial models.
5. Ocular/frontal-proxy channels alone must not reproduce the claimed neural
   increment (see `C1_PROTOCOL.md` §11 on the EOG limitation).
6. Participant ID alone must not explain cross-subject performance.
7. Signal-quality metrics alone must not reproduce the primary result.
8. Duplicate stimulus leakage must be impossible across confirmatory folds
   (verified structurally by the split manifest, not just assumed).
9. Hyperparameter selection must not inspect outer-test results (verified by
   construction of the nested CV, not just documented).
10. Behavior-plus-random-noise must not reproduce behavior-plus-neural gains.

## 8. Multiplicity

- Exactly one primary hypothesis (H2) and one primary estimand.
- Secondary hypotheses (H3, and the H5 generalization check) are clearly
  labeled secondary; their p-values are corrected using Holm-Bonferroni
  across the secondary family (explicitly selected here, before results
  exist, per the protocol's requirement to freeze the procedure in advance).
- Exploratory analyses (H1, H4, any channel/time map not in the frozen
  feature set) are never assigned confirmatory p-values.

## 9. Fixed-sample sensitivity analysis

Because the dataset's participant count is fixed at audit time (20 in
ds005815, fewer after QC exclusions), a simulation-based sensitivity analysis
estimates the minimum detectable subject-level `Delta_OOS` under:
- the observed (post-QC) usable participant count;
- the observed metric variance from the behavior-only model's outer-fold
  performance;
- the planned paired inference procedure (§5) and alpha (0.05, two-sided,
  pending Holm-Bonferroni adjustment for the secondary family);
- realistic missingness/exclusion rates from Commit 3 QC.

This runs **before** the primary result is interpreted and is reported
regardless of outcome. A null result is not treated as proof of absence
unless the sensitivity analysis shows the design was adequately powered to
detect a pre-specified minimum effect of interest; if not, the gate decision
is `NULL_SUPPORTED_WITHIN_SENSITIVITY` only when that power condition holds,
otherwise the null is reported as inconclusive.

## 10. Result artifacts (schema, populated by later commits)

```
results/c1_dataset_decision.json
results/c1_preprocessing_qc.json
results/c1_split_manifest.json
results/c1_reliability.json
results/c1_alignment.json
results/c1_incremental_validity.json
results/c1_negative_controls.json
results/c1_sensitivity.json
results/c1_final_decision.json
```

Every artifact carries: `dataset_id`, `dataset_version`, `dataset_hash`,
`code_sha`, `preprocessing_hash`, `split_hash`, `model_spec_hash`,
`estimand_id`, `random_seed_registry`, `created_at`,
`confirmatory_or_exploratory`. Replay fails closed when dataset hashes,
preprocessing, fold membership, model specification, frozen encoder weights,
or neural feature hashes differ from the recorded provenance — following the
same replay-fail-closed convention established in Scientific Gate C0.2.

## 11. Gate decision rules (restated from the task specification, frozen here)

```
Full pass:
  C1_NEURAL_FOUNDATION = PASS
  C1_INCREMENTAL_BEHAVIORAL_VALIDITY = PASS
  C1_PERCEPTION_IMAGERY_TRANSFER = PASS
  C1 = COMPLETE

Neural foundation pass only (no admissible paired dataset):
  C1_NEURAL_FOUNDATION = PASS
  C1_INCREMENTAL_BEHAVIORAL_VALIDITY = BLOCKED_BY_PAIRED_DATA
  C1 = PARTIAL_DATA_BLOCK

Scientific null (valid, sufficiently sensitive, EEG does not improve prediction):
  C1_NEURAL_FOUNDATION = PASS
  C1_INCREMENTAL_BEHAVIORAL_VALIDITY = NULL_SUPPORTED_WITHIN_SENSITIVITY
  C1 = COMPLETE_WITH_NULL_RESULT

Failure (unreliable representations or negative controls expose leakage):
  C1 = FAILED_BY_RELIABILITY
```

Since `PRIMARY_PAIRED_DATASET = FOUND` (ds005815), the `BLOCKED_BY_PAIRED_DATA`
branch is not expected to apply unless a Commit 2/3 stopping condition
(`C1_PROTOCOL.md` §10) forces it.
