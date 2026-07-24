# C2 Final Decision — Neural Content–State Disentanglement and Perception-to-Imagery Transfer

**Status:** Gate decision issued. Machine-readable version:
[`results/c2_final_decision.json`](../../results/c2_final_decision.json).
Frozen per [`C2_PROTOCOL.md`](C2_PROTOCOL.md) and
[`C2_ANALYSIS_SPEC.md`](C2_ANALYSIS_SPEC.md).

## Decision

```
C2_NEURAL_CONTENT               = NULL_SUPPORTED_WITHIN_SENSITIVITY
C2_PERCEPTION_IMAGERY_TRANSFER  = NULL_SUPPORTED_WITHIN_SENSITIVITY
C2_STATE_SEPARATION             = NULL_SUPPORTED_QUALITATIVE
C2_SUBJECT_INVARIANCE           = NOT_APPLICABLE_NO_POSITIVE_SIGNAL_TO_ASSESS
C2                                = COMPLETE_WITH_NULL_RESULT
```

`C2_STATE_SEPARATION` and `C2_SUBJECT_INVARIANCE` go beyond the gate's
minimal decision template (which only names the first two fields for the
valid-null branch), added for completeness given the task's own H3/H4/H5
hypotheses — see rationale below.

## Relationship to C1

C1 asked and answered a narrower question: do prespecified classical EEG
features improve cross-subject prediction of subjective imagery vividness?
The answer was a real, adequately-powered negative result
(`C1 = COMPLETE_WITH_NULL_RESULT_MECHANISM_UNRESOLVED`). C2 asked a
structurally different question: does EEG encode stimulus content and
cognitive state in reproducible representations at all, independent of
whether that representation improves a behavioral covariate? **C2 does not
rescue or reinterpret C1** — it is an independent line of evidence that
also, honestly, came back null.

## The evidence, commit by commit

**Commit 3 (classical baselines, 14 participants).** Content decoding:
chance/majority, order-only, block/session-only, quality-only, and
classical-feature-decoder baselines all sit at or slightly below chance
(class-weighted log loss 1.16–1.18; chance = log(3) = 1.099). State
decoding: order-only and block/session-only sit at *exact* chance
(log loss = ln(2) = 0.693); quality-only and classical-feature-decoder
show only a marginal elevation (AUC 0.57 and 0.52).

**Commit 4 (compact encoders, 15 participants).** None of EEGNet, TCN, or
a contrastive encoder + linear probe shows above-chance cross-subject
content decoding under LOSO:

| Architecture | Mean log loss | Balanced accuracy |
|---|---|---|
| EEGNet | 4.42 (std 1.68) | 0.342 |
| TCN | 1.04 | **0.3333 on every one of 15 folds** |
| Contrastive + probe | 1.17 | 0.324 |

EEGNet's high log loss reflects severe overfitting (confidently wrong on
held-out participants, ~13 participants' worth of training data, no
explicit regularization) — a training-capacity limitation, not evidence of
a *negative* content signal. TCN's exact, unvarying 0.3333 across every
single fold is the signature of a model that converged to a trivial
constant-output solution and never engaged with the input at all.

**Commit 5 (perception-to-imagery transfer, 14 participants).** The
primary C2-H2 evaluation (perception train → imagery test, using the
equal-duration common window so epoch length itself cannot leak state)
shows no transfer for any architecture. Critically, the negative controls
are **statistically indistinguishable from the real evaluation** for every
architecture:

| Architecture | Real eval | Label-shuffle control | Pre-cue control |
|---|---|---|---|
| EEGNet | 7.25 | 7.21 | 7.21 |
| TCN | 1.0404 | 1.0404 | 1.0398 |
| Contrastive | 1.1847 | 1.1793 | 1.1918 |

This means even EEGNet's large, non-chance-looking log loss is not
tracking genuine label correspondence at all — a convergent null across
every architecture and every control, not merely an absent effect.

**Commit 6 (disentanglement probes, 15 participants).** TCN and the
contrastive encoder show essentially no probe-recoverable signal for
*any* target — content, state, participant identity, or signal-quality
bin all sit near chance. EEGNet shows a different, carefully-interpreted
pattern: within-sample content decoding reaches balanced accuracy 0.68,
but this uses stratified K-fold *within* the same pooled training data the
encoder saw, not the strict cross-subject LOSO already shown null — most
likely trial-level memorization, not genuine content structure. EEGNet
also shows real, modest participant-identity leakage (0.185 vs. 0.067
chance) and quality-bin leakage (0.457). Session-identity probing was
honestly reported as untestable: every included participant used session 1
only, so the label has zero variance.

**Commit 7 (falsification + sensitivity, 14 participants).** All 12
required controls pass — temporal shift, channel-label permutation,
order-only, block/session-only, signal-quality-only, participant-only,
within-block label shuffle, paired-trial leakage, outer-test-blind
hyperparameter selection, random-noise comparison, pre-cue, and the
equal-duration state control. None of them exposes a confound explaining
the (null) result, because there is no positive result requiring
explanation. The fixed-sample sensitivity analysis, reusing C1's
`sensitivity.py` machinery unchanged against the classical-feature-decoder's
real per-participant effect distribution (n=14, observed mean delta vs.
chance = −0.079, observed SD = 0.030), shows **power = 1.0000** at the
prespecified minimum effect of interest (0.05). The null is not a symptom
of an underpowered study.

## Why `COMPLETE_WITH_NULL_RESULT`, not `FAILED_BY_CONFOUNDING_OR_LEAKAGE`

The failure branch applies when order, block, signal quality, duration,
participant, or session structure *explains* an apparent positive result.
Here there is no positive result to explain away — every negative control
behaves exactly as it should for a genuine, adequately-powered null, and
the pipeline mechanics (leakage, hyperparameter-blindness, replay
determinism) are independently verified sound.

## Why the extra `C2_STATE_SEPARATION` and `C2_SUBJECT_INVARIANCE` fields

The gate's minimal decision template for a valid null only specifies
`C2_NEURAL_CONTENT` and `C2_PERCEPTION_IMAGERY_TRANSFER`. Given the task's
own H3 (state) and H4/H5 (subject invariance, disentanglement) hypotheses,
omitting any statement about them risked looking like they were never
assessed. `C2_STATE_SEPARATION = NULL_SUPPORTED_QUALITATIVE` is explicitly
qualified as *not* power-verified (no dedicated state-target sensitivity
analysis was run — an honest scope limitation). `C2_SUBJECT_INVARIANCE =
NOT_APPLICABLE_NO_POSITIVE_SIGNAL_TO_ASSESS` reflects that subject
invariance is a property of a *real* signal generalizing across people —
since no representation here ever showed above-chance content decoding
in the first place, asking whether that (non-existent) signal generalizes
is not a meaningful question to force a PASS/FAIL answer to.

## Honest limitations

- State-target sensitivity was not formally computed; only content
  decoding's per-participant effect distribution was used for the
  fixed-sample power analysis.
- Only session 1 was used for every participant throughout this pipeline;
  session-identity leakage is genuinely untestable with this data
  construction.
- `ds004306` exploratory replication and `THINGS-EEG2` optional
  pretraining were not pursued this session (documented from Commit 1
  onward); per the task's own instruction, their absence cannot change
  this primary decision.
- EEGNet's overfitting reflects the specific hyperparameters used here
  (100 epochs, no explicit regularization, ~13 participants' worth of
  per-fold training data), not a claim that no compact architecture could
  ever decode content from this dataset.
- C2's own inclusion floor (minimum 6 trials per content class) excludes
  sub-02 and sub-22 from every C2 analysis, an honest divergence from C1's
  16-participant set, documented from `C2_PROTOCOL.md` Section 4 onward
  and never adjusted after seeing results.

## Claim boundaries upheld

No thought-reading, real-time BCI, or clinical efficacy claim is made. No
claim of exact recovery of what a participant imagined or perceived. The
null result is not overclaimed as "EEG cannot encode visual content in
general" — only that the tested compact architectures and classical
features, under this protocol, did not show above-chance cross-subject
decoding. Image generation, causal modulation, and closed-loop
neurofeedback were not started.

## What this decision does and does not authorize

This closes Scientific Gate C2 with a real, honestly-reported, adequately-
powered null result across content decoding, perception-to-imagery
transfer, and (qualitatively) state separation. It does **not** authorize
C3, image reconstruction, real-time BCI, or closed-loop neurofeedback
work — per the task's explicit stop condition, work stops here.
