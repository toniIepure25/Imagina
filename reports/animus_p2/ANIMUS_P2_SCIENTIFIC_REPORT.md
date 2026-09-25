# ANIMUS-P2 — Scientific & Product-Bridge Report

Two results are kept strictly separate. Never merged into one vague success statement.

## Part A — Scientific decoder result
**Decision: `ANIMUS_P2_PERCEPTION_DECODER_VALIDATED`** (via the ANIMUS-P2-R spatial-provenance recovery;
see `results/animus_p2/ANIMUS_P2_SCIENTIFIC_DECISION.json`, `results/animus_p2/subjects/*.json`, and
`results/animus_p2r/`).

### How the earlier block was resolved
P2E real-execution reconnaissance had blocked the confirmatory as `ANIMUS_P2_BLOCKED_ROI_SPATIAL_PROVENANCE`:
the sealed primary ROI is the volumetric Wang25 MPM in MNI152NLin2009cAsym, but neither NOD (ds004496) nor
the BOLD5000 fallback publishes MNI152NLin2009cAsym-space derivatives, so the sealed atlas could not be
applied from published provenance. That block is **preserved byte-for-byte** as
`results/animus_p2e/ANIMUS_P2E_DECISION_SNAPSHOT.json`. **ANIMUS-P2-R** resolved it the only permitted way:
a fresh prospective seal authorizing **raw NOD → pinned fMRIPrep → MNI152NLin2009cAsym:res-2** re-derivation
of subject normalization. The ONLY scientific change from P2 is that preprocessing provenance; the split,
Wang25 ROI, open_clip encoder, ridge decoder, content margin, permutation/bootstrap counts, seeds, subject
gate, and dataset gate are all inherited UNCHANGED (verified by the P2-R CI guard).

### Real confirmatory (firewall-clean)
The implementation was frozen CI-green (`cc54226`) with every `real_*_inspected_before_freeze = false`
BEFORE any decoding metric was computed. The sealed `run_p2_confirmatory.py` then ran UNCHANGED on the real
6-subject cohort (raw ds004496 → fMRIPrep MNI2009c:res-2 → Wang25 ROI, 7604 vox, coverage 1.0 → frozen
LSA-GLM per-trial betas → open_clip ViT-B-32 laion2b_s34b_b79k stimulus embeddings), perm=1000, boot=1000,
seeds 20260909/20261009/20261109, grouped-by-identity 2800/600/600 split.

Frozen denominator sub-01..06 (fixed before outcomes; no performance-based selection). Result:

| Subject | Margin M | perm p | boot CI95 lo | 2AFC | cat-matched 2AFC | beats low-level | PASS |
|---------|---------:|-------:|-------------:|-----:|-----------------:|:---------------:|:----:|
| sub-01  |  0.0019  | 0.288  | −0.0049 | 0.500 | — | — | ✗ |
| sub-02  |  0.0002  | 0.394  | −0.0010 | 0.500 | — | — | ✗ |
| sub-03  |  0.0003  | 0.393  | −0.0005 | 0.501 | — | — | ✗ |
| sub-04  |  0.1217  | 0.001  |  0.1136 | 0.797 | 0.594 | yes (0.0206) | ✓ |
| sub-05  | −0.0068  | 0.971  | −0.0134 | 0.483 | — | — | ✗ |
| sub-06  |  0.0822  | 0.001  |  0.0746 | 0.719 | 0.557 | yes | ✓ |

**n_eligible 6, n_valid 6, n_pass 2 == required_passes max(2, ceil(6/3)) = 2 → VALIDATED.** The two passing
subjects show genuine, permutation-verified (p=0.001), bootstrap-lower-bound-positive, category-controlled
(within-synset 2AFC > 0.5, so not category-only), low-level-surviving (neural margin > image-statistics
margin), identity-specific content decoding on unseen ImageNet identities. The four null subjects are at
chance and are reported as such — genuine subject variability, not exclusions. Retrieval is above chance
(chance Top-1 ≈ 0.0017; sub-04 Top-5 0.053, median rank 84.5/600) but modest in absolute terms.

**A FAIL would have been equally reportable.** No post-hoc ROI/embedding/split/decoder change was made; the
result is what the frozen protocol produced.

### Capability after
`PERCEPTION_NEURAL_CONTENT = VALIDATED` (visual perception only). `IMAGERY_NEURAL_CONTENT`,
`DREAM_NEURAL_CONTENT`, `NEURAL_RECONSTRUCTION` remain `UNAUTHORIZED` — validating perception never raises
them (capability invariant, tested). Authorized claim: "Experimental validated perception-content neural
adapter (visual perception only)." Imagery requires an independent C3XRP replication + a P3 gate.

## Part B — Product-bridge result (REAL, run only because VALIDATED; no product tuning)
`results/animus_p2/product_bridge.json`. The sealed `neural_initialization_experiment` ran on the passing
subjects' real held-out perception trials, comparing UNINFORMED / NEURAL_ONLY / BEHAVIORAL_ONLY /
NEURAL_PLUS_BEHAVIORAL ANIMUS-style loops with no parameters fit to the product outcome:

| Subject | neural-init gain (median) | gain CI95 | fused ≥ both | behavioral-only | neural-only | fused |
|---------|--------------------------:|-----------|:------------:|----------------:|------------:|------:|
| sub-04  | 0.0277 | [0.0274, 0.0325] | yes | 0.194 | 0.128 | 0.227 |
| sub-06  | 0.0152 | [0.0170, 0.0222] | yes | 0.191 | 0.076 | 0.210 |

Median gain across subjects 0.0215; both positive with bootstrap CI lower bound > 0. Neural-initialized +
behavioral fusion exceeds both single modes and starts far closer to the target (initial similarity 0.128 vs
~0.001 uninformed for sub-04). **Honest limitation:** the neural start does not reduce median
iterations-to-threshold (`neural_faster = false`) — it gives a higher-quality converged estimate and a
better starting point, not faster convergence to the 0.45 cutoff. Belief fusion provably weights
higher-confidence observations more. This is a real neural-initialization result on validated perception
content; it does not extend to imagery.

## Interfaces (now live)
`ValidatedPerceptionNeuralDecoder` and `ValidatedPerceptionObservationProvider` are materialized with full
provenance (real per-subject model-weights SHA-256 in `results/animus_p2/model_manifest.json`) and are now
constructible under the VALIDATED capability — the same ANIMUS loop consumes real perception content with
zero product redesign. The same interface is what P3 would use for imagery, once (and only once) C3XRP
independent replication authorizes it. C3XAG remains unauthorized.
