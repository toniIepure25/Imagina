# C3XRP — Independent Replication & Precision Gate (Prospective Protocol)

**NOT C3XAT-R2 / C3XAG / C3XE / C3XR / C4.** C3XAT-R1 is CLOSED and immutable
(`C3XAT_D2_ATLAS_IMAGERY_LIMITED`, 1/6, sub-03 only). This gate is **design/discovery/seal only** — **no
real replication neural outcome is computed here.** C3XAG remains **NOT AUTHORIZED**.

## Scientific question
Does the cue/video-deconfounded stimulus-specific imagery reliability observed in C3XAT-R1 **replicate in
independent participants/data**, and can **increased independent measurement precision** distinguish
reproducible imagery signal from cue/video contamination **without subject selection**?
- **Replication** = independent participants / independent imagery measurements (not re-analysis of C3XAT).
- **Precision** = prospectively increasing independent measurement units to reduce uncertainty.

## Selected replication dataset
**`C3XRP_NO_PUBLIC_REPLICATION_DATASET`** (`dataset_selection_decision.json`, `candidate_matrix.json`).
A metadata-only audit found no public fMRI dataset that is simultaneously **independent** of the prior
program (C3XC/C3XD/C3XDR/C3XDR-R1/C3XAT/C3XAT-R1) **and** structurally sufficient for the C3XAT estimand
(≥50 distinct naturalistic imagery identities repeated across ≥4–5 independent imagery units, matched
perception with full identity correspondence, known cue/post-video timing, ≥6 eligible subjects):
- Structurally-capable imagery datasets are KamitaniLab-lineage — **GOD/ds001246 (used in C3XB)**, Mind
  Captioning/ds005191 (this program), Deep Image Reconstruction/ds001506 (shared subject pool) — or
  **NSD-Imagery (used in C3)** → `NOT_INDEPENDENT_REPLICATION`.
- Independent imagery datasets are insufficient: **SemReps-8K/ds006798** has only 3 imagery identities;
  THINGS-fMRI / BOLD5000 / NOD are perception-only. → `INSUFFICIENT`.
Requirements were **not weakened** to force a match. ds005191 may be used only for method validation,
replay, synthetic calibration, and precision planning — never as the replication outcome.

## Participant eligibility & denominator
All prospectively eligible subjects enter the denominator (ordinary technical MRI QC only). **No
responder enrichment; no selection by imagery ability/vividness/prior R_I/Δ/decoding/ROI signal.** The
replication must **not** target sub-02 or sub-03. Denominator is frozen (no shrinkage).

## Inherited measurement (unchanged where compatible)
- **Primary ROI** = `WANG25_TOPOGRAPHIC_VISUAL_NETWORK` (Wang2015 ProbAtlas_v4 archive `3743ac34…` →
  official MNI152NLin6Asym→2009cAsym transform → 2 mm grid, label-safe; mask hash `19b681ec…`). **No
  performance-defined or localizer ROI** may replace it for the primary endpoint.
- **Imagery R_I** — Spearman-Brown corrected stimulus-specific split-half reliability, independent unit =
  imagery session/acquisition block, content = fixed repeated identities; frozen `c3xb` estimator.
- **Matched perception R_P** — fixed-content estimand; each perception independent unit contains the
  complete identity set (inherent run-pair/block schedule; **no coverage-optimized or outcome-driven
  pairing**).
- **Cue/post-stimulus falsification** — Model-A forward operator; predicted contamination carries
  **exactly zero true-imagery contribution**; Δ = R_I_obs − R_I_contamination_predicted.
- **Δ inference** — conservative **paired** sensitivity (Δ point>0 AND paired bootstrap CI lower>0 AND
  Δ>0 every sealed seed). The rejected fixed-`R_pred` permutation is **not** restored.
- Inference: n_perm=1000, n_boot=1000, n_rep_point=200; seeds 20260909/+0/+100/+200.

## Subject PASS (conjunction — not R_I alone)
imagery R_I PASS **AND** matched R_P PASS **AND** cue/post-stimulus Δ PASS **AND** unit contract PASS
**AND** atlas QC PASS.

## Cohort gate (generalized, fixed denominator)
`required_passes = max(2, ceil(N/3))` — inherited from the C3XAT 2/6 = one-third rule, **not** chosen
from new outcomes. `n_pass ≥ required` → `C3XRP_REPLICATION_QUALIFIED`; `0 < n_pass < required` →
`C3XRP_REPLICATION_LIMITED`; `n_pass = 0` with complete valid measurement → `C3XRP_REPLICATION_FAIL`;
incomplete/invalid → `C3XRP_BLOCKED_*`.

## Precision planning (study design only)
`precision_design_analysis.json` — synthetic power/Type-I over imagery units {5,7,9,12} × Δ truth grid
{0,0.05,0.08,0.10,0.15} (Δ not chosen to resemble any subject). Targets: Type-I ≤ 0.05 at Δ=0; ≥80%
power at Δ=0.08; ≥90% at Δ=0.15. A future-acquisition recommendation only; changes no existing gate.

## Prospective acquisition (since no public dataset qualifies)
`prospective_acquisition_protocol.json` — ≥7 imagery sessions (if precision supports), fixed naturalistic
identities repeated once/session, complete-identity matched perception per unit, cue/imagery/post-video/
evaluation timed separately (deconvolvable), sealed timing/counterbalancing/QC. **Not designed around
sub-03.**

## Spatial-specificity endpoint (SECONDARY unless promoted before outcomes)
`spatial_specificity_prospective_design.json` — Wang25 vs 10 independently-seeded size-matched random
cortical controls (GM-constrained, Wang-excluded); E = R_I_Wang25 − mean(random); sealed one-sided
Wilcoxon across subjects. The C3XAT descriptive enrichment is **not** reused as inferential evidence.

## Negative controls, STOP rules, forbidden analyses
Negative controls inherit C3XAT (video-label permutation null; cue/post-video forward-contamination;
size-matched random cortex). **Forbidden before seal:** any real new-dataset R_I/R_P/Δ, pattern
similarity, ROI performance comparison, decoding, geometry, reconstruction, semantic/stimulus-feature
analysis. **STOP** after the seal + selection/NO_PUBLIC_DATASET decision + frozen precision design + tests
+ green CI. **No real replication neural outcome is executed in this task.**

## Next authorization required for execution
Execution requires: (1) acquiring/identifying a genuinely independent dataset satisfying this sealed
contract, then (2) a separate explicit authorization to run the sealed C3XRP measurement. Only a future
actual `C3XRP_REPLICATION_QUALIFIED` could later be considered toward authorizing a geometry gate — not
now.
