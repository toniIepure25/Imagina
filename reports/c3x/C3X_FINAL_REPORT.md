# C3X — External Imagery Dataset Qualification — Final Report

**NOT C4. No reconstruction. No geometry computed.** **Decision:
`C3X_EXTERNAL_IMAGERY_DATASET_QUALIFIED`, qualified_dataset = `ds001506` (Deep Image Reconstruction).**

## Provenance
- **Starting SHA (C3R final):** `25a0524becbdcf6880c5dd571bba4fcaffb7ed0d`
- **Branch:** `research/external-imagery-qualification-c3x`
- **C3R lineage verified:** HEAD was at the C3R final SHA; C3R decision
  `C3R_NO_RELIABLE_IMAGERY_IN_REMAINING_COHORT` (NSD-Imagery measurement-bound).
- **C3X seal:** `reports/c3x/c3x_protocol_seal.json`, self_hash `bf545a78...`, committed BEFORE any
  candidate reliability value was inspected. Dataset-agnostic run-disjoint estimator hash
  `623c9236...`.

## Candidate table (design/access; ranking frozen before neural outcomes)
| Dataset | Subj | Imagery contents | Reps | Imagery runs | Matched perception | Scanner | Voxel | Access | Priority |
|---|---|---|---|---|---|---|---|---|---|
| **D1 ds001506 DIR** | 3 | **26 categories** | **~20** | 20 | perceptionNaturalImageTest (50×~24) | 3T, TR 2s | 2mm | OpenNeuro CC0 + figshare | **HIGH** |
| D2 ds005191 Mind Captioning | 6 | 72 videos | ~5 | ~30 | testPerception | TR 1s | 2mm | OpenNeuro CC0 | MEDIUM |
| D3 7T letters (Senden) | 6 | 4 letters | high | 4 | matched | 7T | sub-mm | access-limited | BLOCKED_ACCESS |

## D1 empirical qualification (figshare preprocessed VC bdpy; official V1-V4/VC ROIs)
Run-disjoint split-half reliability; stimulus-label permutation null (1000); non-straddling
bootstrap CI (1000); split-seed robustness. R_I = VC imagery; R_P = matched perception-test.

| Subject | valid imagery | R_I (VC) | R_I 95% CI | R_I p | null | seed-min | R_P (VC) | R_P p | atten R_I/R_P | Gate |
|---|---|---|---|---|---|---|---|---|---|---|
| sub-01 | 26×~20, 20 runs | **0.224** | [0.003, 0.238] | 0.001 | −0.004 | 0.219 | 0.282 | 0.001 | 0.79 | PASS / PASS |
| sub-02 | 26×~20, 20 runs | **0.349** | [0.096, 0.326] | 0.001 | −0.003 | 0.347 | 0.424 | 0.001 | 0.82 | PASS / PASS |
| sub-03 | 26×~20, 20 runs | **0.471** | [0.163, 0.442] | 0.001 | −0.003 | 0.462 | 0.654 | 0.001 | 0.72 | PASS / PASS |

Secondary ROIs (imagery R_I): reliable across the visual hierarchy (V1–V4 all positive; e.g. sub-03
V1 0.49, V2 0.55, V3 0.63, V4 0.51). Permutation null ~0 in every subject confirms the reliability
is stimulus-specific (destroying content identity collapses it). Run-disjoint splits preclude
within-run leakage.

## Dataset decision
All **3/3 subjects** reach `SUBJECT_RELIABILITY_PASS` for imagery with reliable matched perception
⇒ `DATASET_RELIABILITY_PASS` (≥2 required). ⇒ **`C3X_EXTERNAL_IMAGERY_DATASET_QUALIFIED`,
qualified_dataset = ds001506.** Per the sealed rule, **dataset hunting STOPS** — D2 was **not**
inspected (it remains a future external replication/generalization dataset). D3 not acquired
(access-limited).

## Measurement ceiling and cross-dataset contrast (descriptive)
Imagery R_I range 0.22–0.47; perception R_P range 0.28–0.65; **attenuation ratio R_I/R_P mean ≈ 0.78**
(imagery is ~three-quarters as reliable as perception). This contrasts sharply with NSD-Imagery
(subj01 imagery R_I ≈ 0.011, noise floor). **Descriptive only** — it motivates a falsifiable
cross-dataset hypothesis (does state-specific geometry emerge only when imagery reliability is
sufficient?) that is **not** tested in C3X.

## Integrity
- **C3/C3M/C3G/C3R untouched.** Seal committed before any reliability inspection; ranking frozen on
  design+access before any neural outcome.
- **Inherited scientific quantity:** the run-disjoint estimator reduces to the C3G split-half
  reliability on a run-less fixture (test-guarded); improvement over C3R = run-disjoint splits.
- **No geometry importable from the C3X runner** (test-guarded); no geometry or reconstruction was
  computed. Vividness not used to select trials (primary used all valid imagery trials).
- Every file MD5 (figshare) + SHA-256 + HDF5-open + shape/label certified; no raw neural data in git.

## Storage
Downloaded ~535 MB (6 figshare bdpy files). Pod work NFS free ~117 TB. No 40-session perception data
acquired.

## Verification
- **Tests:** C3X 8/8 pass; full C3 suite (c3x+c3r+c3g+c3m) green; **ruff clean**.
- CI-tested SHA / workflow run ID / job conclusions: recorded at closeout (see session log / final
  message).

## Exact next scientific gate
**`C3XR — External State-Geometry Replication`** on ds001506: freeze the C3G geometry family
(G3 participation ratio, G4 subspace overlap, G6 CKA, G8 crossnobis RDM, SNR-matched perception
control, BH-FDR q=0.05) on this qualified dataset BEFORE observing any geometry result — testing
whether state-specific perception→imagery geometry emerges when imagery reliability is sufficient.
**Not started in C3X. No reconstruction. No C4.**
