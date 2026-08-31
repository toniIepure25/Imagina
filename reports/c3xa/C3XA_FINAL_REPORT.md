# C3XA — DIR Target-Contract Correction and Dataset Requalification — Final Report

**NOT C4. No geometry. No reconstruction.** **Decision:
`C3X_RESTRICTED_ARTIFICIAL_IMAGERY_DATASET_QUALIFIED`** (C3XR for the natural, C3G-comparable family
is **NOT** authorized). This supersedes the historical C3X qualification, which was based on the
pre-correction 26-label contract.

## Provenance
- **Starting SHA (C3X final):** `d1a482ed89a10abf72376838d43332445857349f`
- **Branch:** `research/c3x-dir-target-contract-c3xa`
- **C3XA correction seal:** `reports/c3xa/c3xa_correction_seal.json`, self_hash `c4d59a59`, committed
  BEFORE any corrected reliability outcome; the FROZEN C3X run-disjoint estimator
  (`c3x_reliability.py`) was **reused unchanged** — only the valid-sample mask was corrected.

## Old C3X qualification vs C3XA correction
C3X reported `C3X_EXTERNAL_IMAGERY_DATASET_QUALIFIED` treating **all 26 bdpy Label values** as
imagery contents and using only perceptionNaturalImageTest as the matched control. **Two errors:**
(1) one of the 26 blocks/run is a **fixation** trial (no imagery); (2) the 25 real targets are **10
natural + 15 artificial**, so a combined reliability conflates within-family stimulus specificity
with reproducible **natural-vs-artificial separation**, and the matched control must include
**perceptionArtificialImage**.

## Authoritative experiment contract (PLOS paper doi:10.1371/journal.pcbi.1006633)
- Imagery = **25 memorized IMAGE exemplars** (10 natural + 15 artificial), NOT semantic categories.
- **26 blocks/run = 25 imagery + 1 fixation** ("maintain steady fixation without any imagery").
- Verified from data: 520 imagery samples = **500 target + 20 fixation** (26 labels × 20 runs);
  bdpy Label is a condition-local ordinal (Label k ↔ Img{k:04d}), vmap empty.
- Assignment (paper contract + KamitaniLab official reconstruction code): natural = Label 1–10,
  artificial = Label 11–25, **fixation = Label 26**. NOT from numeric-label equality, NOT from any
  neural result.

## Corrected, fixation-excluded, family-stratified reliability (VC)
| Subject | R_I natural | p | 95% CI | gate | R_I artificial | p | 95% CI | gate | R_P nat (C3X) | fixation repeatability | old incl-fix |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sub-01 | 0.127 | 0.079 | [−0.15, 0.25] | MARGINAL | 0.195 | 0.006 | [−0.08, 0.26] | MARGINAL | 0.282 (p .001) | 0.153 | 0.224 |
| sub-02 | 0.187 | 0.027 | [−0.13, 0.32] | MARGINAL | 0.386 | 0.001 | [0.09, 0.37] | **PASS** | 0.424 (p .001) | 0.388 | 0.349 |
| sub-03 | 0.174 | 0.057 | [−0.28, 0.32] | MARGINAL | 0.448 | 0.001 | [0.09, 0.45] | **PASS** | 0.653 (p .001) | 0.710 | 0.471 |

- **Natural (primary future geometry family): 0/3 PASS** — every subject's natural bootstrap CI
  includes 0 (and sub-01/03 have p ≥ 0.05). Within-family natural imagery is at best marginal.
- **Artificial: 2/3 PASS** (sub-02, sub-03 clean: p = 0.001, CI lower > 0; sub-01 marginal).
- **Matched perception reliable** (R_P_natural PASS 3/3 from C3X; R_P_artificial point ≈ 0.32/0.48/0.44).
- **Fixation sensitivity:** fixation-only pattern repeatability is substantial (0.15/0.39/0.71) and
  the old include-fixation R_I (0.22/0.35/0.47) exceeded the corrected within-family natural values
  — the C3X positive was **partly driven by the reproducible fixation state** and family separation.

## Family-separation confound control
A dedicated synthetic test (two families, **zero** within-family stimulus structure but a large
stable between-family mean) confirms the corrected procedure reports within-family reliability ≈ 0
(not a false positive), while a naive combined statistic is inflated by family separation. The
qualification uses **within-family natural** reliability, never the confounded combined statistic.

## Sealed requalification rule and outcome
Rule (frozen before corrected outcomes): D1 remains qualified for C3XR iff **≥ 2/3 subjects** show
R_I_natural > 0 AND perm p < 0.05 AND bootstrap CI lower > 0 AND split-robust, AND R_P_natural
reliable. **Natural: 0/3 → fails.** Artificial: 2/3 → qualifies as a restricted family.
⇒ **`C3X_RESTRICTED_ARTIFICIAL_IMAGERY_DATASET_QUALIFIED`.**

## Whether C3XR is authorized
**No** for the natural / C3G-comparable geometry question (natural imagery reliability is only
marginal). Artificial shapes are a reliable but **restricted** family that **does not authorize
broad natural-image perception→imagery geometry claims**. A natural-image external replication of
C3G is **not** presently supported by this dataset under the conservative reliability gate.

## Integrity
- C3/C3M/C3G/C3R/C3X untouched; C3X artifacts preserved (historical qualification retained,
  scientifically superseded, not rewritten). Seal committed before corrected inspection; frozen
  estimator reused unchanged; no post-result criteria change.
- **No geometry importable from the C3XA runner** (test-guarded); no geometry/reconstruction run.
  Vividness not used to select trials.
- Cluster API was down; the corrected screen ran locally and independently **reproduced the C3X
  certification exactly** (VC 11726/11114/9919). Perception R_P computed as point estimates locally;
  R_P_natural full-inference reliability referenced from C3X (identical perceptionNaturalImageTest
  data + estimator) — a documented, conservative environment adaptation, not a criteria change.
- Every file MD5 (figshare) + SHA-256 + HDF5-open certified; no raw neural data in git.

## Storage
Downloaded ~215 MB additional (perceptionArtificialImage sub-01/02/03) + reused ~535 MB C3X subset.

## Verification
- **Tests:** C3XA 6/6 pass (incl. family-separation-confound guard); full C3 suite green; ruff clean.
- CI-tested SHA / workflow run / job conclusions: recorded at closeout.

## Exact next scientific step
Not C3XR-natural. Options, in order of scientific value: (a) an **artificial-shape** external
geometry pilot could proceed as a clearly-labelled RESTRICTED replication (not a natural-image
claim); (b) to answer the original C3G natural-image question, seek a dataset/paradigm with
**demonstrably reliable natural-image imagery** (prospective reliability screen first, as in C3R/C3X)
— e.g. re-examine D2 (Mind Captioning) with its cue-only confound controls, or a higher-repetition
natural-image imagery acquisition. **Not started. No reconstruction. No C4.**
