# C3X — External Imagery Dataset Qualification — Protocol

**NOT C4. No reconstruction. No geometry computed in C3X.** No further NSD-Imagery tuning.

- **Scientific parent (C3R):** `25a0524becbdcf6880c5dd571bba4fcaffb7ed0d` — decision
  `C3R_NO_RELIABLE_IMAGERY_IN_REMAINING_COHORT` (NSD-Imagery is measurement-bound for
  stimulus-specific perception<->imagery geometry; **not** "perception and imagery share a
  representation", **not** "imagery has no information" — the claim is dataset/paradigm specific).
- **Branch:** `research/external-imagery-qualification-c3x`.

## Central question
Which reproducibly obtainable fMRI imagery dataset provides **measurable stimulus-specific imagery
reliability** together with a compatible perception condition, sufficient to identify
perception<->imagery representational geometry? C3X selects DATASETS by prospectively-specified
measurement properties, **never** by whether a desired geometry result is positive.

## Candidates (metadata audited; see results/c3x/d{1,2,3}_metadata_audit.json)
- **D1 — Deep Image Reconstruction (OpenNeuro ds001506, CC0):** 3 subjects, ses-imagery 20 runs
  (3-4 sessions), matched ses-perceptionNaturalImageTest (24 runs), 2 mm / TR 2 s; imagery events
  carry `category_id` + `evaluation` (vividness); official V1-V4/VC ROIs via the figshare
  preprocessed bdpy release (DOI 10.6084/m9.figshare.7033577.v16). **Ranking: HIGH.**
- **D2 — Mind Captioning (ds005191, CC0):** 6 subjects, testImagery (video recall) + testPerception,
  2 mm / TR 1 s; VERBAL-cue confound (semantic vs visual imagery). **Ranking: MEDIUM.**
- **D3 — 7T imagined letters (Senden):** 6 subjects, 7T, K=4 letters, pRF; access-limited (not on
  OpenNeuro). **Ranking: BLOCKED_ACCESS.**

Ranking frozen (`results/c3x/c3x_ranking.json`) on design+access ONLY, before any neural outcome.
First empirical target: **D1**. D2 inspected ONLY if D1 does not reach DATASET_RELIABILITY_PASS.

## Measurement priority (frozen)
PRIMARY criterion = stimulus-specific imagery reliability on reproducible data — NOT decoder
accuracy, reconstruction quality, or published performance.

## Dataset-agnostic estimator (`c3x_reliability.py`, hashed in the seal)
Scientific definition unchanged: repeatability of stimulus-specific multivoxel patterns across
INDEPENDENT trials/runs. **RUN-DISJOINT** split halves where runs exist (half A = whole runs, half
B = complementary runs), content-balanced, no trial (and preferably no run) in both halves; Pearson
r of the concatenated content-mean patterns across halves, Spearman-Brown corrected. Reduces to the
C3G split-half quantity on a run-less fixture. Inference: stimulus-label permutation null (1000),
non-straddling split-half bootstrap CI (1000), split-seed robustness. Same estimator gives
imagery `R_I` and matched-perception `R_P`.

## Reliability spaces (prospective, per dataset)
- **D1 primary:** VC (visual-cortex aggregate) from the official masks. **Secondary:** V1, V2, V3,
  V4 (per released ROI metadata). No best-ROI selection after outcomes.
- **D2 (if reached):** a separately justified whole/visual/semantic hierarchy (paradigm is
  semantic/video).

## Reliability gates (conservative; same structure as C3R)
Per subject: `SUBJECT_RELIABILITY_PASS` iff R_I > 0 AND perm p < 0.05 AND bootstrap CI lower > 0 AND
min over split seeds > 0. `_MARGINAL` / `_NOISE_FLOOR` otherwise.
Dataset gate:
- **DATASET_RELIABILITY_PASS:** >= 2 subjects with imagery PASS AND their matched perception also
  reliable (>=2 guards against one anomalous subject moving the whole program).
- **DATASET_RELIABILITY_PROMISING:** exactly one clear pass, or multiple positive-but-underpowered.
- **DATASET_RELIABILITY_FAIL:** no subject provides demonstrably reliable imagery.
- **DATASET_QUALITY_BLOCKED:** matched perception itself unreliable for all subjects.

## Controls (per candidate)
stimulus-label permutation, run-label-only, trial-order-only, cue-only (D2), mean-pattern,
ROI-size control, random-voxel control, cross-run leakage audit. Reliability must vanish when
content identity is destroyed.

## Measurement ceiling (central)
Report imagery reliability ceiling, perception reliability ceiling, and attenuation ratio R_I/R_P
per dataset BEFORE any geometry/decoder claim (a dataset can have excellent perception yet
unmeasurable imagery, as NSD-Imagery did).

## Vividness (frozen ordering)
Primary reliability uses ALL valid imagery trials. Vividness-conditioned analyses (high/low, R vs
vividness) are SECONDARY, run only AFTER the primary status is frozen. A high-vividness-only sample
is never retrospectively defined as the confirmatory dataset.

## No geometry / no reconstruction in C3X
Do NOT compute G3/G4/G6/G8, SNR-matched geometry, or state transport; do NOT reconstruct.
Eligibility is determined independently of future scientific-endpoint values (guarded by test: no
geometry importable from the C3X runner).

## Decision
- D1 PASS -> `C3X_EXTERNAL_IMAGERY_DATASET_QUALIFIED`, qualified_dataset = ds001506; **STOP dataset
  hunting** (do not inspect D2 to pick a "better" one).
- D1 fail, D2 PASS -> `C3X_EXTERNAL_IMAGERY_DATASET_QUALIFIED`, qualified_dataset = ds005191.
- only D3 -> `C3X_RESTRICTED_TOPOGRAPHIC_IMAGERY_DATASET_QUALIFIED`.
- none -> `C3X_NO_AVAILABLE_DATASET_MEETS_RELIABILITY_GATE` (measurement-bound; a new prospective
  fMRI acquisition would be required).

If a dataset qualifies, the NEXT gate (`C3XR — External State-Geometry Replication`) will freeze the
C3G geometry hypotheses on the qualified dataset before observing geometry. **Not started in C3X.**

## Provenance
Every artifact records dataset + version/DOI, participant, file hashes (figshare MD5 + local
SHA-256), events/label hashes, ROI, trial-manifest hash, estimator hash, permutation/bootstrap spec,
code SHA, created_at. Replay fails closed on mismatch.
