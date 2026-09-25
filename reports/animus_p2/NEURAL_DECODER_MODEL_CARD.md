# ANIMUS-P2 Neural Decoder — Model Card

> **Status: VALIDATED — `ANIMUS_P2_PERCEPTION_DECODER_VALIDATED` (via ANIMUS-P2-R).** The sealed P2
> pipeline was run UNCHANGED on the real 6-subject NOD cohort after the P2-R spatial-provenance recovery
> (raw ds004496 → pinned fMRIPrep → MNI152NLin2009cAsym:res-2 → sealed volumetric Wang25 ROI). The
> confirmatory firewall held: the implementation was frozen CI-green (`cc54226`) before any decoding metric
> was inspected. 2 of 6 subjects passed the frozen subject gate (`required_passes = max(2, ceil(6/3)) = 2`),
> so the dataset gate authorizes a **perception-content** claim. Imagery / dreams / reconstruction remain
> UNAUTHORIZED — a perception advance never raises them.

## Intended use
Estimate a frozen visual-content embedding from fMRI acquired **while a participant perceives a visual
stimulus**, for consumption by the ANIMUS closed loop as an observation source. Offline/replay only.

## Validated domain
Visual **perception** content only. **Not** imagery, **not** dreams, **not** image reconstruction, **not**
mental-state/thought decoding.

## Dataset / subjects
NOD ImageNet (ds004496 v2.1.2), prospectively-frozen denominator sub-01..06 (fixed before any outcome was
seen; no performance-based selection). Grouped-by-identity split 2800 train / 600 val / 600 test trials per
subject (leakage-free, verified). Target = open_clip `ViT-B-32 laion2b_s34b_b79k` embedding of the actual
stimulus image (not captions). ROI = Wang25 primary union in MNI152NLin2009cAsym:res-2, 7604 voxels,
coverage 1.0 (fMRIPrep MNI grid identical to the sealed atlas grid — no resampling).

## Per-subject results (held-out unseen identities; perm=1000, boot=1000, seeds 20260909/20261009/20261109)

| Subject | Margin M | perm p | boot CI95 lower | 2AFC | cat-matched 2AFC | beats low-level | Top-5 | median rank | reject frac | PASS |
|---------|---------:|-------:|----------------:|-----:|-----------------:|:---------------:|------:|------------:|------------:|:----:|
| sub-01  |  0.0019  | 0.288  | −0.0049 | 0.500 | — | — | — | — | — | ✗ |
| sub-02  |  0.0002  | 0.394  | −0.0010 | 0.500 | — | — | — | — | — | ✗ |
| sub-03  |  0.0003  | 0.393  | −0.0005 | 0.501 | — | — | — | — | — | ✗ |
| **sub-04** | **0.1217** | **0.001** | **0.1136** | **0.797** | **0.594** | **yes (0.0206)** | **0.053** | **84.5** | **0.09** | **✓** |
| sub-05  | −0.0068  | 0.971  | −0.0134 | 0.483 | — | — | — | — | — | ✗ |
| **sub-06** | **0.0822** | **0.001** | **0.0746** | **0.719** | **0.557** | **yes** | **0.035** | **131.5** | — | **✓** |

**Dataset decision:** n_eligible 6, n_valid 6, **n_pass 2 == required_passes 2 → VALIDATED.** sub-01/02/03/05
are at chance (M≈0, perm p 0.29–0.97, 2AFC≈0.50) — genuine subject variability, not an artifact: the passing
subjects survive permutation (p=0.001), identity-bootstrap CI (lower bound > 0), category-matched decoys
(2AFC > 0.5 within-synset, so not category-only), and a low-level image-statistics baseline (neural margin
> low-level margin). Retrieval is well above chance (chance Top-1 ≈ 0.0017) but modest in absolute terms.

## Model
Regularized linear (ridge) multi-output regression; alpha selected by nested validation (both passing
subjects selected α=10000). Bootstrap-ensemble (20) predictive uncertainty; validation-calibrated reject
option. A small MLP exists only as a SECONDARY descriptive comparator and cannot rescue the primary gate.
Real per-subject model-weights SHA-256 recorded in `results/animus_p2/model_manifest.json`.

## Product bridge (real, run only because VALIDATED; no product tuning)
Sealed `neural_initialization_experiment` on held-out perception trials, comparing UNINFORMED /
NEURAL_ONLY / BEHAVIORAL_ONLY / NEURAL_PLUS_BEHAVIORAL loops:

| Subject | neural-init gain (median) | gain CI95 | fused ≥ both | behavioral-only | neural-only | fused |
|---------|--------------------------:|-----------|:------------:|----------------:|------------:|------:|
| sub-04  | 0.0277 | [0.0274, 0.0325] | yes | 0.194 | 0.128 | 0.227 |
| sub-06  | 0.0152 | [0.0170, 0.0222] | yes | 0.191 | 0.076 | 0.210 |

Median gain across subjects 0.0215; both positive with CI lower bound > 0. Neural-initialized + behavioral
fusion exceeds both single modes (`fused_ge_both = true`) and starts far closer to the target (initial
similarity 0.128 vs ~0.001 uninformed for sub-04). **Honest limitation:** the neural start does **not**
reduce median iterations-to-threshold (`neural_faster = false`) — it yields a higher-quality converged
estimate and a better starting point, not faster convergence to the 0.45 cutoff. Belief fusion respects
decoder uncertainty (high-confidence observations move the posterior more).

## Evaluation
Held-out unseen identities: content margin M (+ permutation p, identity-bootstrap CI, multi-seed), 2AFC,
retrieval (Top-k/MRR/rank), category-matched and low-level-baseline controls, label-permutation collapse.

## Uncertainty
First-class per-observation uncertainty (ensemble spread), calibrated on validation; monotone error↔
uncertainty checked (rank corr 0.34 for sub-04); reject option exercised (reject fraction 0.09 for sub-04).

## Known failure modes
Category-only recovery (checked via category-matched decoys — passing subjects exceed chance within synset),
low-level-only structure (checked via low-level baseline — neural beats it), session/run fingerprints,
OOD stimuli/categories, high-motion/low-coverage trials (rejected). 4/6 subjects show no decodable
perception content under this protocol — the method does not generalize to every subject.

## OOD behaviour
Reject option returns `valid=false` above the validation-calibrated uncertainty threshold or on QC/ROI
failure. The decoder can say "no valid neural-content estimate."

## Privacy
Raw neural arrays and identifiers never leave the decoder toward any generator; only sanitized content
latents flow into ANIMUS. No raw neural data committed to Git — all cohort data stays on the OrchestrAIQ PVC.

## Claims allowed
"Experimental validated perception-content neural adapter: visual-content representations can be estimated
from fMRI during visual perception under the validated P2 protocol (2/6 NOD subjects; requires independent
replication)."

## Claims forbidden
Imagery neural content; thought/mind reading; dream decoding; mental-image reconstruction; real-time brain
reading; any claim that the 4 null subjects were excluded (they were not — the denominator was frozen).
