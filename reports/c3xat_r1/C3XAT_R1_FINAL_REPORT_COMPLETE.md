# C3XAT-R1 — Complete Final Report (Execution Attempt 2)

**Successor closeout report; preserves all prior history. Seals `bb0d07ac…` (C3XAT) / `23a6f92d…`
(C3XAT-R1 exec) unchanged; execution_attempt = 2; no C3XAT-R2.** Measurement-qualification only — no
geometry, decoding, reconstruction, or semantic features.

## Final decision
**`C3XAT_D2_ATLAS_IMAGERY_LIMITED`** — PASS = **1/6** (sub-03 only); qualification required ≥2/6.
**C3XAG preparation NOT authorized.**

## 1. Scientific question
When visual ROIs are defined by an independently published, fully reproducible atlas (Wang 2015
topographic MPM) rather than the unrecoverable Mind Captioning localizer ROIs, does cue/video-
deconfounded naturalistic video imagery show reproducible stimulus-specific multivoxel activity across
independent imagery sessions, in raw-derived native functional space?

## 2. Provenance chain
OpenNeuro **ds005191 v1.0.2**, S1–S6, acquired to a 600Gi persistent OrchestrAI PVC (exact manifest:
1063 files, 139,957,018,247 bytes, `749ded7b…`, 0 partial, trainPerception excluded). **fMRIPrep
24.1.1** (`sha256:9aec0b83…`) preprocessed all 6 to **MNI152NLin2009cAsym 2 mm, no smoothing**
(per-subject FreeSurfer isolation resolved an initial shared-fsaverage race; recon-all succeeded for
all 6). Primary ROI = authoritative **Wang2015 ProbAtlas_v4 volume** (archive `3743ac34…`) →
MNI152NLin6Asym → official TemplateFlow transform (`2e3869a0…`) → 2 mm subject grid, label-safe:
**`WANG25_TOPOGRAPHIC_VISUAL_NETWORK`, 7604 voxels, mask `19b681ec…`** (certified: grid/affine match,
100% finite BOLD coverage).

## 3. Blocker / resolution history (all preserved, immutable)
1. `C3XAT_R1_BLOCKED_EXECUTION_INCOMPLETE` — interim checkpoint.
2. `C3XAT_R1_BLOCKED_ATLAS_SPACE_PROVENANCE` — **resolved** (ProbAtlas_v4 recovery, hashed).
3. `C3XAT_R1_BLOCKED_PERCEPTION_ESTIMAND` — **resolved** (fixed run-pair estimand, below).
4. Primary `C3XAT_D2_ATLAS_IMAGERY_LIMITED` — this closeout.

## 4. Final frozen implementation
`implementation_freeze_manifest_v2.json`, committed and CI-green **before any outcome**
(`real_R_I/R_P/Delta_before_v2_freeze = false`): imagery pipeline (bit-identical to C3XD Model A, real
`trial_type=-5` grouped eval), dedicated perception path, frozen `c3xb` estimator (unchanged), cue/video
forward operator, paired-Δ sensitivity, subject/dataset gates, Wang archive + mask + transform hashes,
inference (n_perm=1000, n_boot=1000, n_rep_point=200; seeds 20260909/+0/+100/+200), container digest.

## 5. Run-pair perception estimand clarification
The originally sealed run-disjoint R_P was **blocked pre-outcome**: across the C(10,5)/2 = 126 5-vs-5 run
splits, `min_common_videos = 64 < 72` for all subjects, so the frozen estimator's content set varied by
split. Resolution (metadata only, no outcomes): **fixed consecutive perception RUN-PAIRS** — proven for
all 6 subjects to give exactly **5 run-pairs, 72/72 disjoint videos per pair, one occurrence/video, 5
reps/video, 360 trials**. Sealed `R_P_RUNPAIR` (unit = run-pair; **same unchanged c3xb estimator**).

## 6. Primary S1–S6 table (frozen)
| subj | R_I | R_I p | R_I CI₉₅ | min-seed | R_P | R_P p | R_P CI₉₅ | R_I_cuevid | Δ_I | Δ CI₉₅ | PASS |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 0.097 | .003 | [−.028,.164] | 0.095 | 0.108 | .001 | [−.094,…] | 0.121 | −0.024 | [−.208,…] | **no** |
| S2 | 0.110 | .001 | [.020,.147] | 0.110 | 0.157 | .001 | [.054,.178] | 0.027 | 0.083 | [−.128,.149] | **no** |
| **S3** | **0.174** | **.001** | **[.067,.226]** | **0.173** | **0.208** | **.001** | **[.078,.247]** | 0.022 | **0.152** | **[.018,.224]** | **YES** |
| S4 | 0.024 | .193 | — | 0.022 | 0.153 | .001 | — | — | 0.064 | [−.046,…] | **no** |
| S5 | 0.064 | .005 | [−.024,…] | 0.063 | 0.097 | .002 | — | — | 0.072 | [−.047,…] | **no** |
| S6 | 0.078 | .046 | [−.136,…] | 0.078 | 0.043 | .055 | — | — | 0.078 | [−.104,…] | **no** |

## 7. Exact subject PASS reasoning
Primary PASS requires **all** of: Wang25 R_I PASS (R_I>0, perm p<0.05, bootstrap CI lower>0, min-seed>0),
Wang25 R_P PASS (same rule), cue/video Δ PASS (Δ point>0, paired bootstrap CI lower>0, Δ>0 every seed),
unit contract PASS, atlas QC PASS.
- **S3 — PASS**: all criteria met.
- **S2 — FAIL (Δ)**: R_I PASS and R_P PASS, but paired-Δ CI lower = −0.128 < 0 → cue/video criterion fails.
- **S1** R_I CI lower <0; **S4** R_I p=0.19; **S5** R_I CI lower <0; **S6** R_I CI lower <0 (and R_P p=0.055).

## 8. Primary dataset decision
1/6 PASS → **`C3XAT_D2_ATLAS_IMAGERY_LIMITED`** (committed before any secondary analysis; SHA `94521b2`).
No subject dropped, no seed selection, no ROI/nuisance/threshold change.

## 9. Secondary enrichment (SECONDARY_DESCRIPTIVE — cannot change the primary)
Imagery R_I (same frozen estimator) in Wang25 vs 3 ROI-size-matched (7604) random cortical controls
(sealed seeds, disjoint from Wang, inside cortical GM). The secondary **reproduces the primary Wang25
R_I exactly** (consistency check). Cohort: Wang25 mean **0.091** (median 0.088) vs random mean **~0.064**.
Wang25 − mean(random): S1 +0.040, S2 +0.039, **S3 +0.065 (largest)**, S4 −0.000, S5 +0.024, S6 −0.004.
Descriptively Wang25 tends higher than size-matched random cortex, most for sub-03. **No sealed
inferential enrichment test existed, so no post-outcome p-value is computed and no "Wang > all random"
threshold is applied to any conclusion.** Cortical gray-matter (126,006 voxels) R_I: NOT_RUN
(computationally prohibitive at full inference; not the size-matched comparison; explicitly deferred, not
silently omitted).

## 10. Negative controls (`C3XAT_R1_SECONDARY_RESULTS.json`)
- **Video-label permutation** — RUN (the within-session permutation null inside every R_I; criterion perm p<0.05).
- **Cue-only / post-video-only contribution** — RUN (the sealed cue/video forward-contamination operator → R_I_cuevideo_predicted; Δ paired sensitivity; zero true-imagery contribution proven).
- **ROI-size-matched random cortex** — RUN (3 controls; descriptive, above).
- Cortical gray matter — NOT_RUN (cost, deferred). Session-only / trial-order / motion-quality-only /
  global-mean / previous-video / next-video / early-vs-late — **NOT_RUN** (not part of the sealed
  C3XAT-R1 execution; not invented post-outcome).

## 11. Integrity audit (`final_integrity_audit.json`, all pass)
6 subjects, no drop; 360 imagery + 360 perception target trials each; 5 imagery sessions; 5 perception
run-pairs; 72 videos/pair; 7604-voxel ROI; mask `19b681ec…`; freeze-v2 precedes all outcomes; primary
decision commit precedes secondary results; no seed selection; no nuisance/ROI/model/threshold change.

## 12. Claims supported
One subject (**sub-03**) showed reproducible cue/video-deconfounded stimulus-specific imagery-related
multivoxel structure in the independently defined Wang25 visual-topographic ROI, with reliable matched
perception (run-pair R_P) and conservative evidence that imagery reliability exceeded predicted cue/video
contamination.

## 13. Claims NOT supported
Cohort-level qualification was **not** met (1/6 < required 2/6) → atlas-defined naturalistic imagery
reliability is **LIMITED** under the sealed experiment. No cohort-level visual-specific representation; no
decoding; no reconstruction; no exact Kamitani localizer ROI reproduction. **No cohort-level geometry
study is authorized.** sub-02 is a formal PRIMARY FAIL (reliable imagery+perception, failed the
conservative Δ contamination criterion) — the strongest non-passing subject, **not** a partial pass.

## 14. Future authorization
Because the result is LIMITED, **C3XAG preparation/execution is NOT authorized**, and no geometry/
decoding/reconstruction/C4 is authorized. The scientifically appropriate next direction — **not designed
or executed here** — is a *separately sealed replication/precision gate* testing whether the sub-03
effect and the sub-02 near-threshold structure reproduce without subject selection or post-hoc tuning.

## STOP
Final decision `C3XAT_D2_ATLAS_IMAGERY_LIMITED`. No C3XAT-R2, no C3XAG, no geometry, no decoding, no
reconstruction, no C4.
