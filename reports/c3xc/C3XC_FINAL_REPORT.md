# C3XC — Mind Captioning (D2) Imagery Qualification — Final Report

**NOT C4. No geometry. No reconstruction. No captioning/semantic decoding.**
**Decision: `C3XC_D2_SEMANTIC_IMAGERY_QUALIFIED`** — Mind Captioning (ds005191) contains reliable,
correctly-paired, cue-controlled **internally-generated SEMANTIC/EVENT (video-recall) imagery** in
visual cortex: **5/6 subjects PASS** the conservative frozen gate with reliable matched perception.
This is the **first** dataset in the C3-external program to qualify (DIR/C3XA and GOD/C3XB both
failed imagery). Authorizes **only** a future, separately-prespecified D2-content-scoped analysis —
**never** C3XR, C3XR-CAT, reconstruction, captioning, or C4.

## Provenance
- **Source SHA (C3XB final):** `d8cce52a7f804d00ffccff365a2e3e8975a598ed`.
- **Branch:** `research/mind-captioning-imagery-qualification-c3xc`.
- **Dataset:** raw OpenNeuro **ds005191 v1.0.2** (anchor only, 398.8 GB, not downloaded); OPERATIVE =
  preprocessed **Figshare 25808179 v2** (CC BY 4.0), `testImagery_S1..6.mat` + `testPerception_S1..6.mat`
  (~2.4 GB), 12 file IDs + supplied_md5 pinned + SHA-256 on download; raw/preprocessed not mixed;
  deberta/timesformer feature files excluded (forbidden).
- **Protocol seal:** `reports/c3xc/c3xc_protocol_seal.json` (self_hash `e3c2ac56`), committed in
  commit 1 BEFORE any neural outcome. D2 contract extraction: `reports/c3xc/d2_contract_extraction.md`.

## Experimental contract (all 6 subjects CERTIFIED)
- **Subjects:** 6 (S1–S6).
- **Imagery:** 360 samples = **72 videos × 5 sessions**; each session contains all 72 videos exactly
  once ⇒ **5 independent session-repetitions/video** (balanced unit). No video shown during recall
  (`stimID=cueID=0`); accuracy/vividness recorded (descriptive only, never used to select trials).
- **Perception (ImageNetTest analogue = testPerception):** 360 = **72 videos × 5 reps** (2 sessions,
  10 runs).
- **Correspondence:** **72/72 exact** imagery↔perception (video identity `imageryID`==`stimID`, not
  row order).
- **Content scope:** internally-generated **semantic/event** content — cued recall of dynamic
  Cowen & Keltner (2017) video clips. NOT static-image, NOT object-category, NOT exact-stimulus.
- **ROI (prespecified, released localizer masks):** primary **VC** (union of localizer visual areas,
  15k–21k voxels/subject); secondary earlyVC(V1)/LVC/HVC composites for the cue control.
- **Cue verdict:** **CUE_CONTROLLED** (see `cue_audit.md`): target-presentation leakage structurally
  absent (no video during recall); reliable imagery is HVC-dominant, not V1/cue-dominant.

## Estimator (frozen) + validated accelerators
- Normative: the FROZEN C3XB run-pair-disjoint estimator (`c3xb_reliability`, sha `33d483a1`) applied
  with **unit := SESSION** (D2 sessions satisfy its one-trial-per-(unit,content) precondition);
  within-session label-permutation null (1000), non-straddling hierarchical bootstrap over sessions
  (1000), split seeds 20260907/+100/+200.
- Accelerators, both proven **BIT-IDENTICAL** to the frozen estimator (synthetic fixtures AND real
  Subject1): `c3xb_fast` (sha `f5a19a7f`) and `c3xc_fast` (sha `dc2b9be3`, buffered — used for the
  screen because the 17k-voxel D2 null is allocation-bound; ~700 s/subject vs the unbuffered >110 min). The
  frozen estimator remains the definition; tests enforce equivalence.

## Results (primary ROI = VC; imagery R_I full 1000 perm / 1000 boot)
| Subject | R_I | perm p | 95% CI | min-seed | gate | R_P (point) | attenuation R_I/R_P | HVC>V1 |
|---|---|---|---|---|---|---|---|---|
| S1 | 0.172 | 0.001 | [0.050, 0.211] | 0.171 | **PASS** | 0.468 | 0.37 | yes |
| S2 | 0.114 | 0.001 | [0.039, 0.197] | 0.114 | **PASS** | 0.524 | 0.22 | yes |
| S3 | 0.200 | 0.001 | [0.066, 0.221] | 0.199 | **PASS** | 0.477 | 0.42 | yes |
| S4 | 0.047 | 0.001 | [−0.018, ...] | 0.046 | MARGINAL | 0.454 | 0.10 | no |
| S5 | 0.074 | 0.001 | [0.015, ...] | 0.074 | **PASS** | 0.446 | 0.17 | yes |
| S6 | 0.081 | 0.001 | [0.008, ...] | 0.080 | **PASS** | 0.392 | 0.21 | yes |

- **Imagery: 5/6 PASS** (S1,S2,S3,S5,S6): R_I>0, permutation p=0.001, bootstrap CI lower>0, min-over-
  seeds>0. S4 is MARGINAL (permutation-significant but bootstrap CI includes 0; near noise floor).
- **Perception: reliable in all 6** (point R_P 0.39–0.52, all ≫ noise; sealed point-only mode). The
  **S1 full-inference anchor** (frozen C3X run-disjoint, n_perm=200) corroborates: R_P=0.468, p=0.005,
  bootstrap CI lower 0.341 > 0 → **PASS** (`results/c3xc/c3xc_RP_anchor_S1.json`). Attenuation
  R_I/R_P ≈ 0.1–0.4.
- **Cue-profile:** HVC>V1 for all 5 PASS subjects — reliable imagery is higher-visual-cortex dominant.

## Dataset gate (sealed) and decision
Frozen rule: **≥2/6** subjects with imagery PASS **AND** matched perception PASS **AND** cue control
acceptable → qualified. Result: **5/6 both-PASS; cue = CUE_CONTROLLED** ⇒
**`C3XC_D2_SEMANTIC_IMAGERY_QUALIFIED`** (`results/c3xc/C3XC_DECISION.json`). Far exceeds the threshold.

## Integrity
- Seal committed before neural outcomes; frozen estimator unchanged; two accelerators proven
  bit-identical (synthetic + real S1); no imagery-driven tuning; behavioural ratings never used to
  select trials; no forbidden features (deberta/timesformer excluded). No raw neural data in git (ROI
  arrays extracted out-of-repo, .mat deleted); MD5+SHA-256 verified. Prior gates (C3XA/C3XB) untouched.
- Tests: c3xc qualification 6/6, fast-equivalence 6/6 (c3xb_fast + c3xc_fast vs frozen); full inherited
  gate suite green; ruff clean.

## Authorization (do not broaden)
A future, **separately-prespecified, D2-content-scoped (semantic/event video-recall) reliability-
bounded analysis** is the ONLY downstream scope authorized. **Not** authorized: C3XR, C3XR-CAT,
reconstruction, captioning/semantic decoding, C4. Authorization is a decision artifact only.

## Scientific bottom line
Cleanly separating the four questions: **reliability** — imagery patterns reproduce across independent
sessions in 5/6 subjects (p=0.001, CI>0); **content correspondence** — 72/72 exact at video identity;
**cue validity** — CONTROLLED (no stimulus during recall; HVC-dominant reliable signal); **perception
positive control** — reliable in all 6. Mind Captioning therefore provides sufficiently reliable,
correctly-paired, cue-controlled internally-generated **semantic/event** content for the intended next
gate — unlike DIR (natural exact-image) and GOD (natural-object category), which failed. The content is
semantic/event, NOT category or static-image, so it does not revive the GOD/DIR geometry questions;
any downstream use must match the semantic/event scope.

## Next candidate (record only; NOT executed)
None is prospectively ranked beyond D2 for this question. A future C3XR-family gate would need to be
prospectively defined for the D2 semantic/event scope before any geometry/reconstruction is considered
— out of scope here. **STOP after C3XC.**
