# ANIMUS-P2 — Scientific & Product-Bridge Report

Two results are kept strictly separate. Never merged into one vague success statement.

## Part A — Scientific decoder result
**Current decision: `ANIMUS_P2_BLOCKED_CONFIRMATORY_PENDING`** (see
`results/animus_p2/ANIMUS_P2_SCIENTIFIC_DECISION.json`). Meaning:

- The prospective protocol is **sealed** (`animus_p2_protocol_seal.json`) and the entire decoding →
  evaluation → control → uncertainty → gate machinery is **validated on synthetic data**
  (`method_validation.json`): a signal cohort is correctly VALIDATED (M>0, permutation p<0.01, bootstrap CI
  lower>0, all seeds positive, beats a low-level baseline, above-chance 2AFC/retrieval), a null cohort
  correctly FAILs and collapses under permutation, normalization/splits are leakage-free, and uncertainty
  is calibrated.
- The **real confirmatory perception decode** on an independent dataset runs on the OrchestrAIQ cluster
  (fMRIPrep/GLM discipline as in C3XAT/C3XRA). **Feasibility is confirmed and real staging has begun**
  (`results/animus_p2/confirmatory_staging_status.json`): the 102 TB workspace PVC, the staged Wang25 MNI
  atlas, OpenNeuro S3 access, and CPU/GPU workers are all verified; probe + staging-inspect jobs ran and
  real BOLD5000 events were downloaded to the PVC. The confirmatory is a **multi-hour cluster pipeline**
  (both BOLD5000 and NOD publish fMRIPrep in T1w/fsnative space, so the MNI Wang25 atlas must be
  registered to each subject's T1w space, then a frozen LSA/GLM extracts per-stimulus ROI betas, plus
  CLIP embedding of the stimulus set, decode + controls across the subject subset). This exceeds a single
  session's rigorous-completion bounds. The confirmatory executor `run_p2_confirmatory.py` is committed and
  **refuses to run without staged feature bundles** (no fabrication); it consumes the exact sealed
  per-subject pipeline (`p2/pipeline.py`). Until `results/animus_p2/subjects/*.json` exist, **no
  perception-content claim is made** and `PERCEPTION_NEURAL_CONTENT` stays not usable.
- Imagery/dream/reconstruction remain **unauthorized** regardless (capability invariant, tested).

When the confirmatory completes, `run_p2_decision` produces VALIDATED / LIMITED / FAIL and updates the
capability matrix; a FAIL is an acceptable, reportable outcome and must not trigger post-hoc ROI/embedding/
split/decoder changes.

## Part B — Product-bridge result (synthetic method validation)
`results/animus_p2/bridge_validation.json`. The bridge machinery is validated on synthetic held-out trials:
initializing an ANIMUS-style loop from a decoded latent + uncertainty gives a genuine head start (median
neural-initialization gain > 0 with paired-bootstrap CI lower > 0), reaches the similarity threshold in
fewer iterations than an uninformed start, and the fused neural+behavioral mode is ≥ both single-source
modes; belief fusion provably weights higher-confidence observations more. **This is method validation of
the bridge, not a neural result, and cannot rescue a failed scientific decoder gate.** The real
neural-initialization experiment runs only after a VALIDATED decision, on real held-out perception trials.

## Interfaces ready for the real result
`ValidatedPerceptionNeuralDecoder` (implements the existing `NeuralContentDecoder` contract) and
`ValidatedPerceptionObservationProvider` are implemented and **gated off** until VALIDATED — so the same
ANIMUS loop consumes real perception content with zero product redesign. The same interface is what P3 will
use for imagery, once (and only once) C3XRP independent replication authorizes it.
