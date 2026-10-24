# C3XRP Replication — Preregistration (DRAFT, OSF-ready)

> Design-only draft. No data collected. `{{ }}` = institutional details to complete before registration.
> This registers a **genuinely independent** replication; the design is frozen in `results/c3xra/` (each
> file self-hashed) and `backend/app/research/fmri/c3xra_*.py`.

## 1. Study information
- Title: Independent replication of imagery-specific topographic reliability in human visual cortex.
- Authors: `{{AUTHORS}}`. Institution: `{{INSTITUTION}}`. Registration platform: OSF.

## 2. Motivation and independence statement
A prior **internal** assessment (C3XAT-R1) returned **LIMITED** (imagery-specific reliability reached the
sealed criterion in 1 of 6 sessions of a single retrospective dataset). **That result MOTIVATES this
replication but does NOT determine any decision here.** Specifically, C3XAT-R1 did **not** influence:
recruitment or the sample, inclusion/exclusion criteria, the ROI, the estimator, the thresholds, or the
analysis — all of which are pre-specified independently below and frozen before data collection. We do not
recruit for vividness/imagery ability, do not enrich for responders, and do not target anyone resembling
any prior individual.

## 3. Hypothesis
Imagery of the fixed naturalistic-video identity set evokes **imagery-specific** reliable patterns in the
Wang2015 topographic visual ROI, **above** cue/post-video contamination (Delta > 0).

## 4. Design (frozen)
- Participants: `{{N}}` evaluable (recruit to a ceiling), healthy MRI-safe adults
  (`results/c3xra/participant_plan.json`).
- Units: **7 imagery** units (each identity once/unit; 6 runs/unit) and **7 complete-content perception**
  units (72/72 identities/unit as disjoint run-pairs) — chosen in
  `results/c3xra/final_measurement_schedule_decision.json` (not auto-minimum).
- Stimuli: fixed 72-identity set, same for every participant/unit
  (`results/c3xra/stimulus_provenance.json`); the final naturalistic set is a declared external
  prerequisite.
- Timing: frozen jittered cue→imagery→post-video→eval (`results/c3xra/timing_design_audit.json`;
  rank-deficiency 0, condition ≤ 100, VIF ≤ 5, cue↔imagery |r| ≤ 0.6).
- Acquisition: 3 T, ≤ 2 mm BOLD, AP/PA fieldmaps, T1w (`reports/c3xra/MRI_ACQUISITION_SPEC.md`).
- Preprocessing: fMRIPrep → MNI152NLin2009cAsym 2 mm, **no smoothing**
  (`results/c3xra/preprocessing_execution_seal.json`).

## 5. Primary analysis (frozen, inherited estimator)
- GLM: MODEL_A_LSA (per-trial imagery/cue/post-video + grouped unmodulated evaluation + frozen nuisance).
- **R_I** (imagery reliability) and **R_P** (perception reliability): frozen run-pair-disjoint estimator
  with permutation p, non-straddling bootstrap CI, and seed-robustness.
- **Contamination:** cue+post-video predicted betas (zero imagery contribution by construction).
- **Delta = R_I(observed) − R_I(contamination)**, conservative **paired** sensitivity (shared split +
  resample for observed and predicted; Delta > 0 AND paired 95% CI lower > 0 AND Delta > 0 under every
  sealed seed).
- **Subject PASS (conjunction):** imagery PASS **and** perception PASS **and** Delta PASS, with the fixed
  unit contract and ROI QC satisfied.
- Sealed inference: n_perm = 1000, n_boot = 1000, n_rep_point = 200, seed 20260909 (offsets 0/100/200).

## 6. Cohort decision (fixed denominator)
- `required_passes = max(2, ceil(N/3))` over the **fixed** evaluable denominator (all technically-complete
  eligible participants; no shrinkage). Technical validity is defined in
  `results/c3xra/acquisition_qc_seal.json` and is **never** based on neural reliability.

## 7. Outcomes and the claims each authorizes
- **C3XRP_REPLICATION_QUALIFIED** (`n_pass ≥ required_passes`): the imagery-specific topographic reliability
  effect **replicated** independently at the cohort level. Authorizes: "independently replicated under the
  frozen C3XRP criteria."
- **C3XRP_REPLICATION_LIMITED** (`0 < n_pass < required_passes`): effect present in some but not enough
  participants. Authorizes only: "partial/limited independent support"; does **not** authorize a general
  replication claim.
- **C3XRP_REPLICATION_FAIL** (`n_pass = 0` with complete measurement): no independent support under the
  frozen criteria. Authorizes: "did not replicate under these criteria."
- **C3XRP_BLOCKED_\<reason\>** (e.g. incomplete measurement, stimulus provenance): no outcome claim; the
  study is technically incomplete and the block reason must be reported.

## 8. Secondary (non-gating)
- Spatial specificity `E = R_I(Wang25) − mean(R_I(random matched masks))`
  (`results/c3xra/spatial_specificity_freeze.json`); behavioral measures are descriptive only
  (`results/c3xra/behavior_secondary_seal.json`). Neither gates the primary outcome.

## 9. What is not part of this study
No decoding, reconstruction, geometry/alignment (C3XAG), or downstream C3X/C4 work. This preregistration
covers acquisition + the frozen primary/secondary analyses only.
