# C2 Protocol — Neural Content–State Disentanglement and Perception-to-Imagery Transfer

**Status:** Frozen prior to any confirmatory model training. This document,
together with [`C2_ANALYSIS_SPEC.md`](C2_ANALYSIS_SPEC.md) and
[`C2_DATASET_ROLE_MATRIX.md`](C2_DATASET_ROLE_MATRIX.md), constitutes the
pre-registration for Scientific Gate C2. Confirmatory analyses may not
deviate from this document once training begins; any deviation is
exploratory by definition. Source commit for this branch:
`defd964381a2abf424105e558b0f24f5fc7e4c13` (the final CI-tested C1 closure
commit on `research/neural-behavioral-alignment-c1`).

## 1. Relationship to C1 — read this first

C1 asked and answered a narrower, different question: *do prespecified
classical EEG features improve cross-subject prediction of subjective
imagery vividness?* The answer, for the tested pipeline, was a real,
adequately-powered **negative** result, with the falsification closure
raising an unresolved mechanism concern (temporal/spatial non-specificity,
partial frontal-proxy reproduction) — see
[`C1_FINAL_DECISION.md`](C1_FINAL_DECISION.md).

C2 is **not** an attempt to rescue, reinterpret, or overturn C1. C1's
negative result stands as a frozen, valid finding regardless of what C2
finds. C2 asks a structurally different question that C1's design cannot
answer: *does EEG encode stimulus content and cognitive state (perception
vs. imagery) in reproducible representations at all* — independent of
whether that representation happens to improve a behavioral vividness
rating. A representation can carry real, decodable content information
while still being useless (or actively harmful, as C1 found) as an
incremental predictor of a specific behavioral covariate. These are not in
tension.

## 2. Scope and non-goals

Not an EEG-to-image reconstruction project, not a real-time BCI, not a
claim of thought-reading or exact recovery of private mental content, not a
clinical or efficacy claim. See §9, Scientific claim boundaries.

## 3. Primary factorization target

Every analysis in C2 explicitly separates:

- **content** — the visual stimulus category (square / male face / female
  face);
- **cognitive state** — perception vs. imagery;
- **participant identity**;
- **session identity**;
- **block/trial order**;
- **signal quality**.

A model that classifies content by exploiting participant, session, or
block structure does not pass C2 — see the nuisance-probe requirement in
§7 and the disentanglement commit (Commit 6).

## 4. Primary dataset and class audit

**Primary paired dataset:** OpenNeuro `ds005815` (YOTO v2.0.1), the same
dataset C1 used, reusing C1's provenance-locked ingestion
(`app/research/neural/adapters/yoto.py`) and the same 16-participant usable
set established in C1 (`sub-01, sub-02, sub-08, sub-09, sub-11, sub-12,
sub-13, sub-16, sub-18, sub-19, sub-21, sub-22, sub-23, sub-24, sub-25,
sub-26`) as the starting point for C2's own independent inclusion audit
(C2 preprocessing/QC may exclude a different subset than C1 did, since the
content-decoding task's artifact sensitivity differs from C1's vividness-
regression task — any such difference is recorded, never silently forced
to match C1's set).

**Primary visual subset (3-class content target):**

```
visual_square
visual_face_male
visual_face_female
```

**Real class-count audit (results/c2_protocol_decision.json), performed
before freezing this inclusion rule, per-participant manifest counts across
all 16 C1-usable participants, perception phase:**

| Participant | square | face_male | face_female |
|---|---|---|---|
| every one of the 16 | 24 | 12 | 12 |

The design is **perfectly balanced across participants** at the manifest
level (before QC-driven artifact rejection): every participant has exactly
24 square trials and 12 trials of each face identity, a fixed 2:1:1 ratio.
This ratio is a property of the experimental design, not sampling noise —
it is retained as a known class imbalance, not treated as a data error.
Consequences for the analysis spec: the primary metric (multiclass log
loss) is class-weighted; balanced accuracy and macro F1 are reported as
secondary metrics specifically because they are insensitive to this fixed
2:1:1 imbalance. Post-preprocessing/artifact-rejection counts will differ
slightly per participant and are reported per-participant in
`results/c2_data_eligibility.json` (Commit 2), never used to justify
excluding a participant from the LOSO analysis unless a participant drops
below a prespecified minimum per-class trial floor (defined in
`C2_ANALYSIS_SPEC.md` §3).

Perception and imagery phases of the SAME physical trials are used for both
states — C2 never treats perception-only and imagery-only trials as
unrelated samples; every content-decoding analysis over imagery data is
paired with the same trial's perception-phase counterpart wherever the
cross-state transfer analysis (Commit 5) requires it.

## 5. Dataset roles

```
ds005815 (YOTO v2.0.1):
  primary paired perception-imagery dataset — confirmatory H1-H5

ds004306:
  external exploratory perception-imagery replication, IF access and
  metadata permit (audited in Commit 7; never allowed to change the
  primary ds005815 decision)

THINGS-EEG2:
  perception-only representation pretraining / benchmarking (exploratory,
  optional; never a source of confirmatory content or state labels for
  ds005815 trials)

OpenMIIR:
  auditory modality-general control only (exploratory; never used to
  support a visual-content claim)
```

EEG-ImageNet is explicitly excluded (not audited, not used) per the task's
own instruction. Full admissibility/role reasoning:
[`C2_DATASET_ROLE_MATRIX.md`](C2_DATASET_ROLE_MATRIX.md).

## 6. Prespecified hypotheses

### C2-H1 — Cross-subject content information (PRIMARY)
Visual stimulus category (3-class: square / face_male / face_female) can be
decoded above a valid participant/block-preserving null in held-out
participants (LOSO). Confirmatory.

### C2-H2 — Perception-to-imagery transfer
A representation trained ONLY on perception predicts or retrieves content
during imagery above a matched null. Imagery labels never enter perception
encoder fitting or hyperparameter selection at any point (frozen perception
encoder, per Commit 5). Confirmatory, secondary to H1.

### C2-H3 — Cognitive-state information
Perception vs. imagery can be decoded after matching/controlling for
stimulus category, participant, session, trial identity, epoch duration,
block, trial order, and signal quality. Uses an EQUAL-DURATION common
analysis window for both states (the first `PERCEPTION_PHASE_DURATION_S`
= 2.0s of each phase — perception's own full 2.0s window, and the first
2.0s of imagery's 4.0s window — so epoch length itself cannot trivially
reveal the state; see `C2_ANALYSIS_SPEC.md` §4). Confirmatory, secondary.

### C2-H4 — Subject-invariant content representation
Content information (H1) remains above null under LOSO evaluation
specifically — not merely within-subject. Within-subject decoding is
reported as a distinct, secondary quantity and never presented as
participant-general performance.

### C2-H5 — Disentanglement
The learned representation retains content information while reducing the
recoverability of participant identity, session identity, and
signal-quality status, relative to a raw/unconstrained baseline
representation. Reported as SEPARATE content and nuisance-probe metrics
(participant leakage, session leakage, quality leakage) — never combined
into one opaque "disentanglement score." Exploratory/secondary.

## 7. Nuisance-confound requirement (applies to every hypothesis)

Every confirmatory content or state claim must survive comparison against:
order-only, block/session-only, signal-quality-only, and participant-only
models achieving comparable performance — if any of these nuisance-only
models matches the full model's performance, the content/state claim is
not supported regardless of the full model's own p-value. See
`C2_ANALYSIS_SPEC.md` §7 for the exact falsification battery.

## 8. Validation hierarchy

1. **Within-subject reliability** (exploratory) — same participant, split
   or session comparisons.
2. **Subject-dependent held-out-trial** (exploratory, secondary) — trials
   held out within an otherwise-seen participant.
3. **Leave-one-subject-out (LOSO)** (confirmatory, primary) — the
   participant-general claim; inferential unit is the participant
   throughout, never the trial.

Participant is the inferential unit for every population-level claim,
matching C1's convention (`C1_PROTOCOL.md` §5).

## 9. Scientific claim boundaries

**Allowed:** visual content categories were or were not decodable under the
tested protocol; perception-trained representations transferred or failed
to transfer to imagery; perception and imagery were or were not separable
after matched controls; representations generalized or failed to
generalize across participants; participant/session information remained
or was reduced in the representation.

**Forbidden:** thought reading; reconstruction of private mental images;
exact recovery of what a participant imagined; real-time BCI capability;
imagery enhancement; causal modulation; clinical efficacy.

## 10. Stopping conditions

If the class-count audit (§4) had revealed a participant with a
class-collapsed or missing category, that participant would be excluded
from the confirmatory content-decoding analysis with the reason recorded
(none were — see §4). If ds005815's perception/imagery phase timing were
found inconsistent with C1's already-verified trigger codebook, this
protocol would be revised before Commit 2; C1's trigger semantics are
reused as-is (already independently verified against the authors' own
analysis code in C1 Commit 2).

## 11. No-efficacy boundary

C2 makes no claim about clinical utility, imagery training efficacy, or
real-time feasibility. Compact-architecture and CPU/short-training-time
constraints (Commit 4) are for methodological rigor and reproducibility
within this project's compute budget, not evidence of real-time
practicality.
