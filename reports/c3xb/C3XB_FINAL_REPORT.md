# C3XB — Natural-Object CATEGORY Imagery Qualification on Generic Object Decoding (GOD) — Final Report

**NOT C4. No geometry. No reconstruction.**
**Decision: `C3XB_GOD_CATEGORY_IMAGERY_FAIL`** — GOD does **not** provide reliable natural-object
CATEGORY imagery in VC under the conservative run-pair-disjoint gate (0/5 subjects PASS), **despite
strongly reliable category-matched perception**. No future geometry gate (C3XR-CAT) is authorized.
The frozen D2 fallback (Mind Captioning, ds005191 v1.0.2) becomes the next candidate — **not
inspected here** (STOP after C3XB).

## Question and scope
Does GOD (OpenNeuro ds001246 v1.2.1; Figshare 7387130; Horikawa & Kamitani 2017, Nat Commun 8:15037)
contain reliable **natural-object CATEGORY imagery** — imagining any exemplar of a cued object
category — to support a *future* category-level perception↔imagery geometry experiment? GOD is
**natural-object CATEGORY imagery**, never "exact-image"/"pixel-matched" (that is DIR, C3X/C3XA).

## Provenance (sealed before outcomes)
- Seal `reports/c3xb/c3xb_protocol_seal.json` (self_hash `d4ec63d7`), committed **before** any neural
  outcome, freezing the estimator, gates, terminology, D2 fallback, and ROIs.
- **Pre-outcome provenance amendment:** the mission pinned Figshare v6, but Figshare now serves only
  **v8** (`/versions`→[8]; v1–7→HTTP 404). v8 (DOI 10.6084/m9.figshare.7387130.v8, CC BY 4.0)
  supersedes v6 and carries the corrected `category_index`/`image_index` that motivated pinning a
  post-correction version. v8 file IDs + supplied_md5 pinned; SHA-256 verified on download; no older
  cache reused. OpenNeuro snapshot verified latest = 1.2.1.

## Phase 1 — data contract + cue-leakage audit (all 5 subjects CERTIFIED)
- **Imagery**: 50 categories × exactly 10 reps, 500 trials, 20 runs, 25/run; the **RUN-PAIR CONTRACT
  holds** (every 2 consecutive runs cover all 50 categories exactly once → 10 balanced run-pairs).
- **Category-matched perception (ImageNetTest)**: 50 categories × 35 valid reps, 1750 trials; one-back
  catch trials already excluded in the release (1750 = 50×35, `trial_type`≡1).
- **Correspondence**: 50/50, certified from WNID integer of `stimulus_number` (vmap `n%08d_%d`), **not
  row order**.
- **Officially-released ROIs**: VC (primary) + V1,V2,V3,V4,LOC,FFA,PPA; LVC/HVC only as clearly-labelled
  composites of released masks.
- **Cue-leakage audit → `CUE_CONTAMINATION_CONTROLLED`** (for the reliability question): released
  imagery patterns are block-averaged single-trial amplitudes of the imagery-maintenance period
  (Kamitani pipeline), 500 rows = 500 blocks, no within-trial time axis. Provenance limitation logged
  (exact averaging window not re-quotable in-env: nature.com auth / PMC reCAPTCHA). The within-trial
  early-vs-late control is **not computable** from the block-averaged release and is **deferred as a
  hard prerequisite for C3XR-CAT**. Corroborating within-release **ROI-profile control: HVC > V1 for
  all 5 subjects** — the (weak) imagery reliability is higher-visual-cortex-dominated, i.e. consistent
  with object imagery and **against** a V1-dominated visual word-cue artifact.

## Estimator (frozen) and a validated accelerator
- **RUN-PAIR-DISJOINT** reliability (`c3xb_reliability.py`, sha256 `33d483a1`): independent unit = a
  2-run pair; split 5 pairs vs 5 → 5 reps/category/half, 250 trials/half; statistic R_I_GOD = Pearson r
  of concatenated 50-category-mean patterns, Spearman-Brown corrected. Core primitives imported
  UNCHANGED from the frozen C3X estimator; proven **bit-identical** to `run_disjoint_reliability` when
  pair==run. Permutation null (1000) permutes category identities within each run-pair; non-straddling
  hierarchical bootstrap (1000) resamples whole run-pairs within fixed disjoint halves; split seeds
  20260901/+100/+200.
- **Accelerator (`c3xb_fast.py`)**: a vectorized path that exploits the GOD balance (one trial per
  (pair,category)) and reproduces the frozen estimator's RNG order. Asserted **bit-identical** to the
  frozen estimator on synthetic fixtures (`test_c3xb_fast.py`) **and on Subject1's committed frozen
  1000/1000 result** (reliability, p, CI, null, bootstrap, seeds). Subject1 keeps its frozen-estimator
  JSON; S2–S5 use the accelerator (their R_I additionally matched independent frozen partial runs
  exactly). This was necessary because a single frozen subject takes ~60–95 min single-threaded here.

## Phase 2 — reliability results (primary ROI = VC)
| Subject | R_I_GOD (VC) | perm p | 95% CI | min-seed | gate | R_P category | attenuation R_I/R_P | HVC R_I | V1 R_I |
|---|---|---|---|---|---|---|---|---|---|
| Subject1 | 0.050 | 0.240 | [−0.151, 0.205] | 0.047 | MARGINAL | 0.653 (full, **PASS**, p .005) | 0.076 | 0.048 | 0.034 |
| Subject2 | 0.087 | 0.155 | [−0.155, 0.197] | 0.073 | MARGINAL | 0.564 (pt) | 0.155 | 0.209 | −0.028 |
| Subject3 | 0.179 | 0.004 | [−0.032, 0.221] | 0.179 | MARGINAL | 0.782 (pt) | 0.229 | 0.259 | 0.088 |
| Subject4 | 0.072 | 0.161 | [−0.130, 0.186] | 0.069 | MARGINAL | 0.727 (pt) | 0.099 | 0.148 | 0.035 |
| Subject5 | 0.011 | 0.414 | [−0.205, 0.190] | 0.005 | MARGINAL | 0.583 (pt) | 0.019 | 0.023 | −0.030 |

- **Imagery: 0/5 PASS.** Every subject's bootstrap CI includes 0. Even the strongest subject (Subject3,
  R_I=0.179, permutation p=0.004) fails the conservative gate because its bootstrap CI lower bound is
  −0.032 (the non-straddling hierarchical bootstrap, which propagates between-run-pair variance, does
  not certify it > 0). Imagery reliability is at/near the noise floor.
- **Category-matched perception: strongly reliable** (Subject1 full-inference PASS, R_P=0.653, p=0.005;
  Subject2–5 point R_P 0.56–0.78, all far above noise). R_P is a documented point-only environment
  adaptation for S2–S5 (full R_P inference ~30 min/subject, not decision-critical; anchored to
  Subject1's full PASS on the identical estimator/data — the C3XA precedent).
- **Attenuation R_I/R_P = 0.02–0.23**: imagery patterns carry only a small fraction of the reproducible
  category structure that perception carries.

## Decision (sealed gate applied)
Dataset qualified iff ≥2/5 subjects with imagery PASS **and** category-matched perception PASS **and**
cue control acceptable. Result: **0/5 imagery PASS → 0/5 both-pass**; cue = CONTROLLED. ⇒
**`C3XB_GOD_CATEGORY_IMAGERY_FAIL`** (`results/c3xb/c3xb_decision.json`). **C3XR-CAT is NOT authorized**
(and exact-image C3XR was never on the table). No geometry computed; no reconstruction; not C4.

## Interpretation (measurement-bound, not cue-contaminated)
The null is **measurement-bound**: GOD single-session category imagery does not yield reproducible
category-specific VC patterns under an acquisition-respecting (run-pair-disjoint), non-straddling
gate, even though the same subjects' category-matched perception is highly reliable. It is **not** a
cue artifact — HVC>V1 across all subjects shows the little imagery structure present is object-like,
not word-cue-like. This mirrors the C3XA finding on DIR (natural imagery only marginal) with a
different dataset and paradigm: reliable natural-image/-category *imagery* geometry is not currently
supported by either KamitaniLab dataset under the conservative reliability gate.

## Integrity
- Seal committed before outcomes; frozen estimator reused unchanged and its accelerator proven
  bit-identical (synthetic + real Subject1). No post-result criteria change. Vividness not used to
  select trials; no geometry importable from any C3XB runner. No CLIP/DINO/CNN/diffusion.
- Prior artifacts (C3…C3XA) preserved; C3XA history not rewritten. No raw neural data in git (ROI
  arrays extracted out-of-repo, .h5 deleted); every file MD5 + SHA-256 verified.
- Tests: C3XB estimator 7/7, fast-path equivalence 3/3, artifacts 4/4; full inherited gate suite green;
  ruff clean. CI job `c3xb-natural-object-imagery-qualification` added.

## Exact next scientific step
Per the sealed D2 fallback, the next candidate for a *reliable natural imagery* screen is **Mind
Captioning (ds005191 v1.0.2)** — subject to its own cue-only confound controls, screened
prospectively as here. **Not started. No reconstruction. No C4.** STOP after C3XB.
