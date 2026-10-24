# GOD Cue-Leakage Audit (C3XB Phase 1)

**Question:** could the reproducible category-specific structure measured by R_I_GOD be produced
by the visual WORD cue rather than by object imagery? GOD imagery trial =
**3 s visual word cue -> ~15 s eyes-closed imagery -> 3 s vividness rating**. A word cue is a
visual/lexical event and is category-informative (it names the category), so it is a genuine
leakage risk that must be audited before R_I_GOD is treated as an imagery reliability.

## What the released data actually is (verified from the files)
- Each subject's `Subject{N}_Imagery.h5` `dataset` is **(500, ~70k)**: exactly **500 rows = 500
  imagery blocks**, i.e. **one block-averaged single-trial amplitude vector per imagery trial**.
  There is **no within-trial time axis** in the release.
- Labels/structure (verified): `stimulus_number` -> 50 categories (WNID integer part, vmap
  `n%08d_%d`); `Run` 1..20; 25 trials/run; `evaluation` = vividness; `trial_type` == 2 (imagery).
- ROI masks are functional (`ROI_VC` and `ROI_{V1,V2,V3,V4,LOC,FFA,PPA}`), built by the
  KamitaniLab `update.py` (recorded verbatim in the file `header/callstack_code`).

## How the amplitudes were built (documented pipeline)
The Horikawa & Kamitani (2017, Nat Commun 8:15037) / KamitaniLab pipeline computes each block's
amplitude by averaging the fMRI volumes of the **stimulus/imagery period** after a
hemodynamic-delay shift, then normalizing per run (linear detrend + z-score). For imagery, the
averaged window is the **imagery-maintenance period**, not the preceding word-cue period; the
gross cue-period visual response is therefore **not** the averaging target.

**Provenance limitation (logged honestly):** the exact averaging-window sentence and the
hemodynamic-shift value could not be re-quoted from a primary source *in this environment*
(nature.com requires authentication; the PMC open-access page is behind a reCAPTCHA). The
determination above rests on (a) the direct structural evidence that the release is block-averaged
single-trial amplitudes and (b) the well-established, widely-replicated Kamitani preprocessing.
The data descriptor design (imagery: 20 runs, 25 categories/run, 10 samples/category; test: 50
images x 35) was confirmed against the OpenNeuro/figshare record.

## Residual risk and the discriminating control
Two residual concerns cannot be excluded by the block-average alone:
1. the 3 s word cue's **hemodynamic tail overlaps** the imagery averaging window;
2. the cue is **category-informative**, so a residual cue-driven signal would be category-specific
   — exactly the axis R_I measures.

The **definitive** discriminating control is a **within-trial early-vs-late imagery split** (cue
artifact is strongest early). This is **NOT computable from the block-averaged release** (no
within-trial time axis); it requires the **raw BIDS ds001246** time series and a cue/imagery/eval-
separated GLM.

A control that **is** computable from the release and is still discriminating is the
**ROI-profile control**: a visual word-cue artifact would be **early-visual (V1) dominated**,
whereas genuine object imagery is known to be **higher-visual-cortex (HVC: LOC/FFA/PPA) dominated**
with weak V1. R_I(HVC) > R_I(V1) is therefore evidence against a V1-driven cue artifact. This is
computed in Phase 2 and recorded in `god_cue_leakage_audit.json` (descriptive, after the primary
VC result).

## State and its consequence
**State: `CUE_CONTAMINATION_CONTROLLED`** — *for the reliability-qualification question in C3XB*.
Justification: the release excludes the gross cue-period response by design (imagery-period block
average), so R_I_GOD is a reproducibility statistic over imagery-period patterns, not cue-period
patterns; and the ROI-profile control provides a within-release check against a V1-driven cue
artifact.

**Bounded and enforced downstream:** this CONTROLLED verdict is scoped to *reliability*. It does
**not** certify a cue-vs-imagery dissociation. The within-trial early-vs-late (raw-BIDS,
cue-separated-GLM) control is recorded as a **HARD PREREQUISITE for the future C3XR-CAT geometry
gate** — a C3XB qualification authorizes C3XR-CAT *subject to* that control, so no cue-vs-imagery
claim escapes unearned. If the Phase-2 ROI-profile control had instead shown V1 >= HVC, the state
would be revised toward PRESENT/UNRESOLVED before any qualification.
