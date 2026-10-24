# C3R — Prospective Imagery Reliability Replication and Foundation Gate — Protocol

**NOT C4. No reconstruction. No geometry computed in C3R.** No further C3G tuning on subj01.

- **Scientific parent:** `df81474def42f517b45af73cab13742e9adf7a05` (C3G closeout).
- **Technical parent:** `7a04b1c1c2080d91afa7f96787bcabc2f550c947` (no-diff CI retrigger).
- **C3G source:** `11445aa90486865ae1fcb33b4e3699e6e501f419`. **Branch:** `research/imagery-reliability-replication-c3r`.
- **C3G CI:** run `32985840538` — jobs cancelled/queued by GitHub runner backlog ⇒ `C3G_CI = PENDING_RUNNER_INFRASTRUCTURE` (does not block C3R; no empty retrigger commits).

## Question
Do subj02, subj05, or subj07 contain **measurable stimulus-specific imagery reliability** above
their own empirical noise floor, so that a perception↔imagery state-geometry analysis is
*identifiable at all*? C3G on subj01 closed as `SIMPLE_ATTENUATION_SUPPORTED` because imagery
reliability ≈ 0.011 (noise floor). Selection here depends **only** on prospectively measured
imagery reliability, never on geometry (which is not computed in this gate).

## Primary quantity
`R_I(subject)` = Set-B imagery stimulus-pattern split-half reliability in nsdgeneral (∧ ncsnr>0),
using the **inherited C3G estimator** `c3g_geometry.split_half_reliability` (sha256 a289a915…):
per-content split of the 16 reps into halves, mean pattern per content, Pearson r of the
concatenated 6-content mean-pattern vectors across halves, averaged over 200 random splits,
Spearman-Brown corrected. Same trial definition, content aggregation, ROI/ncsnr rule, orientation,
preprocessing, and split-half construction as C3G.

## Row mapping (certified upstream, subject-independent)
visB `192:240` (48 Set-B vision), imgB `336:384 ∪ 624:672` (96 Set-B imagery, 6 content × 16 reps).
No participant-specific offsets. A participant violating this structure ⇒ `BLOCKED_PARTICIPANT_DATA_CONTRACT`.

## Inference (sealed before results)
- **Null:** permute the 96-trial content-label vector (preserves 16 reps/content, run structure,
  ROI dim, marginal distribution), recompute reliability with the same estimator; 1000 perms;
  one-sided p = (#null ≥ observed + 1)/(n+1).
- **Bootstrap CI:** resample the 16 reps within each content with replacement (preserve 6×16),
  recompute; 1000 resamples; percentile 2.5/97.5.
- **Split-seed robustness:** seeds {base, +100, +200}, base 20260826.

## Reliability gate
- **RELIABILITY_PASS:** R_I > 0 AND perm p < 0.05 AND bootstrap CI lower bound > 0 AND min over
  split seeds > 0.
- **RELIABILITY_MARGINAL:** positive point estimate but CI includes 0 OR perm p ≥ 0.05 (descriptive
  only; not used for confirmatory geometry).
- **RELIABILITY_NOISE_FLOOR:** R_I ≤ 0 or indistinguishable from the null.

Descriptive practical-effect bins (NOT thresholds): R_I > 0.05 / 0.10 / 0.20. subj01 ≈ 0.011
compared descriptively only — never a post-hoc selection cutoff.

## Vision control (critical)
Compute same-session Set-B VISION reliability R_P with the same estimator:
- VISION_RELIABLE_IMAGERY_RELIABLE → geometry identifiable.
- VISION_RELIABLE_IMAGERY_NOISE_FLOOR → imagery-specific attenuation.
- VISION_UNRELIABLE_SESSION_QUALITY_BLOCKER → do NOT interpret low imagery as cognitive attenuation.

## Acquisition scope
Phase 1 acquires **imagery data only** per subject (betas_nsdimagery.hdf5 + nsdgeneral +
prf-visualrois + streams + ncsnr) — no core-NSD perception betas. Storage preflight before
download; if imagery cannot fit ⇒ `BLOCKED_C3R_STORAGE`. Every object certified (size, SHA-256,
HDF5 open, shape/dtype). No raw neural data in git.

## Gate decision states
`C3R_RELIABLE_IMAGERY_FOUND` (list qualified/marginal/noise-floor) · `C3R_NO_RELIABLE_IMAGERY_IN_REMAINING_COHORT`
(measurement-bound, NOT evidence of geometric equivalence) · `C3R_BLOCKED_BY_DATA_ACCESS_OR_INTEGRITY`.

## Phase 5 (conditional)
Only for RELIABILITY_PASS subjects: build the frozen C3-family perception foundation (40 sessions
betas_fithrf, image-safe split, train-only preprocessing, nsdgeneral∧ncsnr>0, frozen CLIP ViT-L/14,
ridge decoder, strict controls) via rolling extraction preserving the ROI union (nsdgeneral, V1-V3,
hV4, ventral, lateral, parietal, low-ncsnr control). Report perception MRR / perm p / top-k /
median rank / 2AFC / alpha / voxel count / controls → PERCEPTION_FOUNDATION_{PASS,NULL,BLOCKED}.
Eligible for future C3G replication iff IMAGERY_RELIABILITY_PASS ∧ PERCEPTION_FOUNDATION_PASS.
No geometry here; the future C3G replication reuses the sealed C3G family without threshold tuning.

## Population posture
Qualification is by prospectively measured imagery reliability. One qualifier ⇒ still
subject-specific; multiple ⇒ report participant-level + conditional qualified-cohort aggregation,
never unbiased population prevalence.
