# C3R — Prospective Imagery Reliability Replication and Foundation Gate — Final Report

**NOT C4. No reconstruction. No geometry computed.** Subjects screened: subj02, subj05, subj07.
**Decision: `C3R_NO_RELIABLE_IMAGERY_IN_REMAINING_COHORT`.**

## Provenance
- **Technical parent (branch base):** `7a04b1c1c2080d91afa7f96787bcabc2f550c947`
- **Scientific parent (C3G closeout):** `df81474def42f517b45af73cab13742e9adf7a05`
- **C3G source:** `11445aa90486865ae1fcb33b4e3699e6e501f419`
- **Branch:** `research/imagery-reliability-replication-c3r`
- **C3G CI:** run `32985840538` -> `C3G_CI = PENDING_RUNNER_INFRASTRUCTURE` (GitHub cancelled/queued
  the jobs under org runner backlog; not a code failure). No empty retrigger commits were made.
- **C3R seal:** `reports/c3r/c3r_protocol_seal.json`, self_hash `fb37f320...`, committed BEFORE any
  reliability value was inspected (one documented, conservative pre-decision bootstrap-CI bug fix;
  see Integrity).

## Question
Does any of subj02/05/07 have measurable stimulus-specific mental-imagery reliability above its own
empirical noise floor, so that a perception<->imagery state-geometry analysis is identifiable at
all? (subj01 closed C3G as SIMPLE_ATTENUATION with imagery reliability ~= 0.011.) Selection depends
ONLY on the sealed imagery-reliability criterion; geometry was not computed.

## Primary quantity and inference (sealed)
`R_I` = Set-B imagery split-half reliability in nsdgeneral (per subject), using the INHERITED C3G
estimator (`c3g_geometry.split_half_reliability`, sha256 a289a915). Inference: stimulus-label
permutation null (1000), non-straddling split-half bootstrap CI (1000), split-seed robustness.
Same estimator applied to same-session Set-B VISION (`R_P`) as a data-quality control.

## Per-subject results (imagery only acquired; ~3 GB total)

| Subject | Vol | V (nsdgen ∧ ncsnr>0) | R_I | R_I 95% CI | R_I p | Imagery gate | R_P | R_P p | Vision gate | Quality class |
|---|---|---|---|---|---|---|---|---|---|---|
| subj02 | 84×106×82 | 14088 | **−0.024** | [−0.46, 0.31] | 0.52 | **NOISE_FLOOR** | 0.481 | 0.001 | PASS | VISION_RELIABLE_IMAGERY_NOISE_FLOOR |
| subj05 | 78×97×79 | 12902 | 0.104 | [−0.50, 0.40] | 0.23 | **MARGINAL** | 0.195 | 0.15 | MARGINAL | VISION_UNRELIABLE_SESSION_QUALITY_BLOCKER |
| subj07 | 81×95×78 | 12511 | −0.078 | [−0.60, 0.35] | 0.65 | **NOISE_FLOOR** | −0.070 | 0.53 | NOISE_FLOOR | VISION_UNRELIABLE_SESSION_QUALITY_BLOCKER |

Descriptive reference: subj01 imagery ~= 0.011 (never a selection cutoff). Practical-effect bins
(descriptive, not thresholds): only subj05 exceeds R_I>0.05/0.10 — but its CI includes 0 and p=0.23,
and its own vision is unreliable, so this is not usable.

Secondary ROI R_I (imagery) are mixed and small (e.g. subj02 V1 −0.33, parietal 0.27; subj05
parietal 0.30) and do not change the nsdgeneral-primary gate.

## Cohort classification
- **Qualified (RELIABILITY_PASS): none.**
- Marginal: subj05.
- Noise-floor (imagery): subj02, subj07.
- Session-quality blockers (vision not reliable): subj05, subj07.
- Imagery-specific attenuation (vision reliable, imagery at noise floor): **subj02** — replicates
  subj01's phenotype.

## C3R decision
`C3R_NO_RELIABLE_IMAGERY_IN_REMAINING_COHORT`. No participant reaches prospectively-defined imagery
reliability. Therefore **Phase 5 (perception foundation) is NOT triggered** for any subject, no
core-NSD perception betas were downloaded, and no geometry was computed. **Subjects eligible for a
future C3G replication: none.**

## Storage
Work NFS free 117 TB; local xfs free 119 GB. Phase-1 imagery download ~= 2.9 GB total (subj02 1.10
GB, subj05 0.90 GB, subj07 0.90 GB + ~1 MB ncsnr + ~60 KB ROIs each). Not blocked. No 40-session
perception data acquired (correctly withheld — no qualifier).

## Integrity
- **C3/C3M/C3G untouched.** No frozen artifact/threshold/hash modified.
- **Seal committed before any reliability inspection.** One amendment: the originally sealed
  bootstrap resampled reps within content with replacement, which straddled the split-half boundary
  and spuriously inflated CIs (subj02 point −0.024 but CI [0.36,0.63]). Replaced with a
  non-straddling split-half bootstrap (disjoint halves first, then within-half resampling). The
  point estimate and permutation null are UNCHANGED; the fix is **conservative** (deflates the
  inflated CI, so it can only make PASS harder). subj02's NOISE_FLOOR gate is determined by R_I<=0
  and permutation p=0.52 — independent of the CI; subj05/07 were not inspected before the fix. A
  regression test (`test_bootstrap_ci_not_inflated_on_noise`) guards it. All three re-run uniformly.
- **Inherited estimator** used verbatim (code hash recorded); no new estimator invented after seeing
  subjects. **No geometry function is callable from the C3R runner** (guarded by test).
- Every acquired object SHA-256 + HDF5-open + shape/dtype certified; no raw neural data in git.

## Interpretation
None of the remaining NSD-Imagery participants provides sufficiently reliable stimulus-specific
imagery patterns for the sealed state-geometry question, so that question is not identifiable in
this cohort — a measurement-bound conclusion, **not** evidence that perception and imagery share a
representation. subj02 independently replicates subj01's imagery-specific attenuation (reliable
seen-vision, imagery at the noise floor). subj05 and subj07 additionally fail the same-session
vision quality control, so their low imagery cannot even be attributed to cognitive attenuation.

## Next step (not started)
The perception->imagery state-geometry question is presently **bounded by imagery measurement
quality**, not by geometry method. A productive continuation is NOT further tuning on this cohort,
but acquiring or identifying imagery data with demonstrable stimulus reliability (e.g. a
higher-repetition or higher-SNR imagery paradigm, or additional NSD-Imagery participants if the
cohort is expanded), gated by the same prospective reliability screen before any geometry.
