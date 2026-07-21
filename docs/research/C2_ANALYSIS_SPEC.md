# C2 Analysis Spec — Content–State Decoding and Disentanglement

Frozen alongside [`C2_PROTOCOL.md`](C2_PROTOCOL.md). Confirmatory analyses
may not deviate from this document once training begins.

## 1. Primary confirmatory target and metric (H1)

- **Target:** 3-class visual stimulus category — `square`, `face_male`,
  `face_female` — decoded from imagery-phase EEG (perception-phase target
  used for the encoder's own training in the transfer analysis, Commit 5).
- **Primary metric:** class-weighted multiclass log loss (weights inversely
  proportional to the fixed 2:1:1 manifest class ratio established in
  `C2_PROTOCOL.md` §4), lower is better, chance = weighted log(3) under a
  uniform-probability classifier.
- **Secondary metrics:** balanced accuracy, macro F1 — both insensitive to
  the 2:1:1 imbalance by construction, reported for interpretability.

## 2. Primary confirmatory target and metric (H3, state)

- **Target:** binary cognitive state — perception vs. imagery, using the
  EQUAL-DURATION common window (first 2.0s of each phase; see §4).
- **Primary metric:** binary log loss.
- **Secondary metrics:** balanced accuracy, ROC-AUC.

## 3. Class inclusion rules and minimum trial floor

A participant is included in the confirmatory H1/H4 content-decoding
analysis if, after C2's own preprocessing/artifact-rejection pass (reusing
C1's fold-safe `preprocessing.py` unchanged), they retain at least 6 trials
of EACH of the 3 visual content classes in the imagery phase. This floor is
fixed before any model is trained. A participant who fails this floor is
excluded with the exact reason recorded in
`results/c2_data_eligibility.json` — never silently dropped, never
adjusted after seeing model performance.

## 4. Primary perception/imagery windows

- **Content decoding (H1, H2, H4):** perception window = full prespecified
  perception phase (`event_onset`, 2.0s duration, per C1's trigger
  codebook); imagery window = full prespecified imagery phase
  (`event_onset` = perception onset + 2.0s offset, 4.0s duration).
- **State decoding (H3), common analysis window:** the FIRST 2.0s of
  BOTH phases — perception's own complete 2.0s window, and imagery's
  first 2.0s (out of its full 4.0s) — so the two conditions being
  discriminated have identical epoch length. State-decoding features are
  computed only from this common window; the full 4.0s imagery window is
  never used for H3, precisely because unequal epoch length would let a
  trivial duration/sample-count artifact masquerade as state information.

## 5. Channel set, outer/inner folds, participant/session/block grouping

- **Channel set:** the same 30 expected YOTO channels as C1
  (`preprocessing.EXPECTED_YOTO_CHANNELS`), same missing-channel policy
  (excluded, never interpolated).
- **Outer folds:** leave-one-subject-out (LOSO), identical mechanics to
  C1's `participant_grouped_split`.
- **Inner folds:** participant-grouped k-fold within the outer-training
  set, reusing C1's `nested_validation.run_single_loso_fold`-style
  machinery, generalized for a classification (not ordinal-regression)
  target in Commit 3.
- **Session grouping:** where more than one session exists for a
  participant (sub-01 has ses-1 and ses-2 in ds005815), both sessions'
  trials for that participant stay together on the same side of every
  fold — a participant is never split across train/test by session.
- **Block grouping:** block index (from C1's `TRIALS_PER_BLOCK=48`
  convention) is retained as a covariate for the order-only/block-only
  nuisance baseline (Commit 3), never as a splitting criterion.

## 6. Model hierarchy (Commit 3, Commit 4)

Baselines (Commit 3, classical/leakage-safe):
```
chance / majority-class baseline
order-only model (trial_index_in_session, block_index only)
block/session-only model (block_index, session_index, participant-blind)
signal-quality-only model (C1's variants.extract_quality_only_features, reused)
regularized linear EEG decoder (multinomial logistic regression on classical features)
classical-feature decoder (C1's extract_classical_features, reused, band power/ERP/entropy)
```

Encoders (Commit 4, compact only — no large transformer):
```
EEGNet content encoder (reused/extended from C1's models.EEGNetBaseline)
compact temporal convolutional encoder (reused/extended from C1's CompactTCNBaseline)
compact contrastive content-state encoder (new: contrastive pretraining
  objective separating content-similarity from state-similarity structure)
```

Every encoder reports: architecture, parameter count, seed, training time,
inference time, checkpoint hash, input window, channel set, fold ID,
training participants — matching C1's `ModelSpec` provenance convention.

## 7. Required falsification / negative-control battery

1. pre-cue content decoding (features from before the stimulus was shown
   must not decode content above null);
2. temporal shift (a window displaced from the prespecified content-locked
   interval must not reproduce content-decoding performance);
3. channel-label permutation (fixed seed registry, reusing C1's
   `variants.CHANNEL_PERMUTATION_SEEDS` convention, new registry frozen
   for C2 in Commit 7);
4. order-only model (trial order alone must not decode content);
5. block/session-only model (block/session identity alone must not decode
   content);
6. signal-quality-only model (quality features alone must not decode
   content);
7. participant-only model (participant ID alone must not decode content —
   this IS expected to be informative for participant identity itself, but
   must not be conflated with content decoding, which is the point of the
   nuisance-probe separation in Commit 6);
8. within-block label shuffle (content labels shuffled within block/
   participant must collapse decoding to null);
9. paired-trial leakage check (no perception/imagery pair of the same
   physical trial may appear split across train and test of any fold);
10. outer-test-blind hyperparameter selection (reusing C1's
    `run_single_loso_fold` checkpoint-hash-invariance proof pattern);
11. behavior/random-noise comparison (content-decoding features replaced
    by random noise of the same dimensionality must not reproduce
    performance) where applicable;
12. equal-duration state control (H3's state-decoding result must not be
    reproducible by epoch-length/sample-count alone — verified by running
    the SAME state classifier on duration-matched pure-noise epochs).

## 8. Inferential unit, permutation scheme, multiplicity

- Inferential unit: participant, throughout — never the trial.
- Report per participant: metric value, then aggregate mean, bootstrap CI,
  participant-level exact-or-Monte-Carlo permutation p-value (reusing C1's
  `exact_sign_flip_test`/`sampled_sign_flip_p_value` machinery, generalized
  from a paired-difference target to a per-participant metric-vs-null
  comparison), heterogeneity (participant-level SD), leave-one-participant-
  out influence (each participant's effect on the aggregate estimate when
  excluded), and fixed-sample sensitivity (power at a prespecified minimum
  effect of interest, same convention as C1's `sensitivity.py`).
- Multiplicity: H1 (primary) is never multiplicity-corrected against
  anything. H2, H3 form the confirmatory secondary family; Holm-Bonferroni
  correction is applied across {H2, H3} before either is called
  significant, mirroring C1's convention (`C1_ANALYSIS_SPEC.md` §8). H4,
  H5 are exploratory/structural, never assigned confirmatory p-values.
- Trials are never treated as independent participants; a participant's
  multiple trials contribute to that ONE participant's aggregate metric,
  never to inflated participant-count.

## 9. Fixed-sample sensitivity analysis

Run before any confirmatory result is interpreted, against the actual
post-QC usable participant count and the observed outer-fold metric
variance, reusing C1's `sensitivity.py` machinery (Monte Carlo sign-flip
approximation for the per-replication p-value, given the same computational
infeasibility of exact enumeration inside a simulation loop that motivated
that design in C1). A null H1/H2/H3 result is reported as "supported within
sensitivity" only if power at the prespecified minimum effect of interest
clears 0.80; otherwise it is reported as inconclusive, never as proof of
absence.

## 10. Result artifact schema

```
results/c2_protocol_decision.json
results/c2_data_eligibility.json
results/c2_split_manifest.json
results/c2_content_decoding.json
results/c2_state_decoding.json
results/c2_cross_state_transfer.json
results/c2_disentanglement.json
results/c2_negative_controls.json
results/c2_sensitivity.json
results/c2_final_decision.json
```

Every artifact carries: `dataset_id`, `dataset_version`, `dataset_hash`,
`code_sha`, `preprocessing_hash`, `split_hash`, `feature_or_encoder_hash`,
`model_spec_hash`, `estimand_id`, `random_seed_registry`, usable
participants, trial counts, `confirmatory_or_exploratory`, `created_at`.
Replay fails closed when any of these differ from recorded provenance,
following the same convention established in C0.2 and C1.

## 11. Gate decision rules (restated from the task specification, frozen here)

```
Full content-state pass:
  C2_NEURAL_CONTENT = PASS
  C2_PERCEPTION_IMAGERY_TRANSFER = PASS
  C2_STATE_SEPARATION = PASS
  C2_SUBJECT_INVARIANCE = PASS
  C2 = COMPLETE

Partial representational pass:
  C2_NEURAL_CONTENT = PASS
  C2_PERCEPTION_IMAGERY_TRANSFER = NULL_OR_INCONCLUSIVE
  C2 = COMPLETE_PARTIAL_REPRESENTATION

Subject-specific only:
  C2_NEURAL_CONTENT = WITHIN_SUBJECT_ONLY
  C2_SUBJECT_INVARIANCE = FAIL
  C2 = COMPLETE_SUBJECT_SPECIFIC

Valid null:
  C2_NEURAL_CONTENT = NULL_SUPPORTED_WITHIN_SENSITIVITY
  C2_PERCEPTION_IMAGERY_TRANSFER = NULL_SUPPORTED_WITHIN_SENSITIVITY
  C2 = COMPLETE_WITH_NULL_RESULT

Failure by confounding:
  C2 = FAILED_BY_CONFOUNDING_OR_LEAKAGE
```

`FAILED_BY_CONFOUNDING_OR_LEAKAGE` applies when order, block, signal
quality, duration, participant, or session explains the apparent result
(i.e., any nuisance-only baseline in §7 matches full-model performance).
