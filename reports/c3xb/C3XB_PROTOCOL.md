# C3XB — Natural-Object Imagery Qualification on Generic Object Decoding (GOD)

**Prospective protocol, sealed BEFORE any neural reliability outcome is inspected.**
**NOT C4. No reconstruction. No geometry computed in this gate.**

## 0. Question and scope
Does GOD (OpenNeuro ds001246 v1.2.1; Figshare 7387130 — selected release v8, see provenance
amendment; Horikawa & Kamitani 2017, Nat Commun 8:15037) contain sufficiently reliable
**natural-object CATEGORY imagery** to support a *future* category-level perception<->imagery
geometry experiment?

### Terminology binding (mandatory, machine-readable in the seal)
- GOD imagery is **"natural-object CATEGORY imagery"**: the subject imagines *any* exemplar of a
  cued object category. The matched perception is **"CATEGORY-MATCHED PERCEPTION"**.
- GOD is **NEVER** described as "exact-image imagery" or "pixel-matched" imagery. Those terms
  belong to DIR (C3X/C3XA), a different paradigm.
- Any future geometry authorized by a C3XB PASS addresses **category-level geometry only**
  (gate name `C3XR-CAT`), and does **NOT** authorize exact-image / pixel-matched C3XR.

## 1. Provenance (frozen)
- OpenNeuro ds001246, snapshot **1.2.1** (verified latest = 1.2.1), raw-BIDS anchor only.
- Figshare article **7387130**, operative preprocessed bdpy .h5 source.
  - **Provenance amendment (pre-outcome):** the mission pinned v6, but Figshare no longer serves
    versions 1-7 (`/versions` returns `[8]`; `/versions/6` -> HTTP 404). The only retrievable
    release is **v8** (DOI 10.6084/m9.figshare.7387130.v8, CC BY 4.0, published 2026-06-03), a
    later curated release that **supersedes v6**. Because the reason to pin a post-correction
    version was the corrected `category_index`/`image_index`, and v8 is strictly later than v6,
    v8 satisfies — and exceeds — that requirement. Exact v8 file IDs + supplied_md5 are pinned in
    `results/c3xb/c3xb_candidate_inventory.json`; SHA-256 is computed on download; no older cached
    GOD file is accepted. Full detail: `c3xb_candidate_inventory.json.provenance_amendment`.
- Files used: `Subject{1..5}_Imagery.h5` (imagery) and `Subject{1..5}_ImageNetTest.h5`
  (category-matched perception). Training set, CNN feature files, and anatomicals are **not** used.

## 2. Trial invariants to verify EMPIRICALLY in Phase 1 (structural, not neural outcomes)
Imagery, per subject:
- 50 object categories; 10 reps/category; **500 imagery trials**; 20 runs; 25 trials/run.
- Every **2 consecutive runs cover all 50 categories exactly once** -> 10 disjoint run-pairs, each
  covering all 50 once. Violation => `BLOCKED_GOD_RUN_CATEGORY_CONTRACT` (gate cannot proceed on
  the run-pair unit for that subject).

Perception (ImageNetTest), per subject:
- 50 categories x 1 exemplar x **35 valid reps**; one-back repetition ("catch") events excluded.

Category correspondence:
- The 50 imagery categories correspond 1:1 to the 50 perception categories, **certified from
  `category_index`/metadata, NOT from row order**. 50/50 required.

## 3. Cue-leakage audit (Phase 1) — decides whether primary reliability may proceed
GOD imagery trial = **3 s visual WORD cue -> 15 s eyes-closed imagery -> 3 s vividness rating**.
A word cue is a visual/lexical event that could imprint a reproducible, category-specific pattern
independent of imagery. We must audit how the released single-trial patterns were built:
- temporal window (which volumes / seconds relative to trial onset),
- HRF handling / regression model, number of volumes averaged,
- whether the cue interval contributes to the estimated pattern.

States:
- `CUE_CONTAMINATION_CONTROLLED` — released patterns provably exclude the cue interval (e.g. modeled
  from the imagery/maintenance window only, cue as a separate regressor). Primary reliability may
  use the released patterns.
- `CUE_CONTAMINATION_PRESENT` — the cue interval demonstrably contributes. Primary reliability must
  instead be computed from a **leakage-safe GLM built from raw BIDS** with separate cue / imagery /
  evaluation regressors, frozen before outcomes.
- `CUE_CONTAMINATION_UNRESOLVED` — provenance insufficient to decide. Dataset -> 
  `C3XB_BLOCKED_BY_CUE_PROVENANCE`.

Additional temporal control (always reported): **early-vs-late imagery** reliability. Cue artifact
is strongest early in the trial; if reliability is carried disproportionately by the early window it
is a red flag even under a nominally CONTROLLED provenance.

## 4. Reliability estimator (FROZEN)
- Inherited, unchanged: `c3g_geometry.py` (sha256 `a289a915...`), `c3x_reliability.py`
  (sha256 `623c9236...`).
- New unit for GOD: `c3xb_reliability.py` (sha256 `33d483a1...`) —
  **RUN-PAIR-DISJOINT** reliability. Independent unit = a **2-run pair** (10 pairs, each all 50
  categories once). Split = 5 run-pairs -> half A, 5 -> half B => 5 reps/category/half, 250
  trials/half. Statistic **R_I_GOD** = Pearson r of concatenated 50-category-mean patterns across
  halves, Spearman-Brown corrected. The core statistic primitives are IMPORTED UNCHANGED from
  `c3x_reliability`; on a fixture where pair-labelling == run-labelling the estimator is
  **bit-identical** to `run_disjoint_reliability` (proved:
  `test_c3xb_reliability.py::test_reduces_to_c3x_run_disjoint`).
- **Permutation null** (>=1000): permute category identities WITHIN each run-pair.
- **Bootstrap** (>=1000): **non-straddling hierarchical** — fix a disjoint 5v5 pair split, resample
  whole run-pairs within each half with replacement (never straddling; propagates between-
  acquisition variance). This is the corrected C3R/C3X bootstrap discipline.
- Split seeds: base = 20260901, +100, +200. ~200 point-estimate split replicates (N_REP_POINT).

## 5. ROIs
- Primary ROI = **VC**. Secondary (reported, not gating unless VC ambiguous): V1, V2, V3, V4, LVC,
  HVC, LOC, FFA, PPA — **officially released ROIs only**.

## 6. Subject gate (reuse conservative C3R/C3X gate, unchanged)
Imagery PASS iff: R_I > 0 AND permutation p < 0.05 AND bootstrap CI lower > 0 AND
min-over-seeds > 0. Otherwise MARGINAL (R_I>0 but a criterion fails) or NOISE_FLOOR (R_I<=0).

## 7. Category-matched perception
`R_P_category` from ImageNetTest (50 categories x 35 reps), run-disjoint (frozen C3X estimator).
Labelled **CATEGORY-MATCHED PERCEPTION**. Same PASS gate. Attenuation ratio R_I/R_P reported.

## 8. Dataset gate (frozen)
- **>= 2/5 subjects** with imagery PASS **AND** category-matched perception PASS **AND** cue control
  acceptable (CONTROLLED, or CONTROLLED via leakage-safe GLM) => `C3XB_GOD_CATEGORY_IMAGERY_QUALIFIED`.
- Exactly **1/5** such subject => `C3XB_GOD_CATEGORY_IMAGERY_PROMISING`.
- **0/5** => `C3XB_GOD_CATEGORY_IMAGERY_FAIL`.
- Cue provenance UNRESOLVED and not repairable from raw => `C3XB_BLOCKED_BY_CUE_PROVENANCE`.

Qualification authorizes ONLY the restricted future gate **`C3XR-CAT`** (category-level geometry),
**NOT** exact-image C3XR. This is recorded machine-readably in the decision.

## 9. D2 fallback (frozen BEFORE GOD outcomes)
`fallback_if_GOD_fail = ds005191` (Mind Captioning v1.0.2). **Do NOT inspect D2 if GOD passes.**

## 10. Integrity constraints
- No raw fMRI/neural data committed to git; paths via env vars; SHA-256 + MD5 certified on download.
- No destructive git. Prior artifacts (C3..C3XA) preserved; C3XA history NOT rewritten.
- Seals frozen before confirmatory inspection; frozen estimators reused unchanged; no post-result
  criteria change (documented pre-outcome amendments only, for genuine bugs/provenance).
- No reconstruction; no C4; no state geometry in C3XB. No CLIP/DINO/CNN/diffusion features.
- Vividness ratings: descriptive only, AFTER the primary result is frozen; never used to select trials.
- Cross-dataset comparison (vs DIR/C3X/C3XA) descriptive only.

## 11. Negative / sanity controls
- Noise fixtures at the noise floor (non-inflated CI) — covered by frozen tests.
- Permutation null centered near 0.
- Family/label-shuffle within run-pair destroys reliability.
- Early-vs-late imagery temporal control (Section 3).

## STOP condition
Stop after C3XB. Do not run category geometry (C3XR-CAT), do not start reconstruction, do not begin C4.
