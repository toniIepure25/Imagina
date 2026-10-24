# C1 Dataset Candidates — Admissibility Audit

**Audit date:** 2026-07-16
**Method:** Primary-source verification only. For every candidate below, evidence
was pulled from the official repository (OpenNeuro CRN GraphQL API and S3
mirror, GitHub, OSF, Hugging Face), the dataset's own `dataset_description.json`
and sidecar JSON/TSV files, and the associated paper's methods text — not from
abstracts or secondary blog summaries. Machine-readable form:
[`results/c1_dataset_candidates.json`](../../results/c1_dataset_candidates.json).

## Decision

```
PRIMARY_PAIRED_DATASET = FOUND
primary_confirmatory_dataset_id = ds005815 ("YOTO")
```

This determination is based on official metadata, sidecar files, a direct raw
file listing, and the paper's methods section, all verified in this audit. Two
things remain **unverified until Commit 2 ingestion** and are carried forward
as residual risk rather than blockers: (1) the exact trigger-code-to-condition
mapping in `events.tsv` (codes 21–47 observed, not self-documenting — the paper
describes the trial structure but not the numeric code table), and (2)
independent confirmation that the "weighted randomization" the authors describe
actually avoids a block/stimulus-category confound at the trial level.

## Tier A — Primary confirmatory

### ds005815 — YOTO: A Human EEG Dataset for Multisensory Perception and Mental Imagery — **SELECTED**

| Field | Value |
|---|---|
| Official source | [OpenNeuro ds005815](https://openneuro.org/datasets/ds005815) (S3 mirror verified directly) |
| Paper | *Scientific Data* 2025, doi:10.1038/s41597-025-05881-1; preprint doi:10.1101/2025.04.17.645384 |
| Dataset DOI | doi:10.18112/openneuro.ds005815.v2.0.1 |
| License | **CC0 1.0** (public domain; relicensed from CC-BY-4.0 on 2025-01-12 — verified via the dataset's own `CHANGES` file) |
| Participants / sessions | 20 participants × 2 sessions |
| Channels / sampling rate | 30-channel 10-20 montage, 1000 Hz raw (verified via `eeg.json`); ASR+ICA-cleaned derivatives at 250 Hz also present |
| Trial structure | Per trial: fixation (2s) → **stimulus presentation / perception** (2s) → **mental imagery of the same stimulus** (4s) → **self-reported vividness, 1–5, per trial** |
| Modalities | Visual-only (gray square, male face, female face), auditory-only (vowels, piano tones), and audiovisual multimodal — visual condition is clearly separable |
| Trial count | 384 trials/participant (2 sessions × 4 blocks × 48 trials) |
| Randomization | Paper reports a "weighted randomization strategy" interleaving conditions within blocks — not simple blocking, but not yet independently re-verified from raw data |
| Raw data | BrainVision format (`.eeg`/`.vhdr`/`.vmrk`), confirmed reachable at `s3://openneuro.org/ds005815/sub-*/ses-*/eeg/` |
| Checksums | S3 object ETag + CRC64NVME per file; independent SHA-256 will be computed on ingestion per this project's provenance convention |
| BIDS status | 1.10.0 compliant |

**Why selected:** this is the only candidate found with (a) a visual condition,
(b) perception and imagery recorded in the **same trial, same stimulus, same
participant**, and (c) a **trial-level, observed (not synthesized) behavioral
target** — vividness — satisfying acceptance criteria 1, 2, and 6 directly. All
ten acceptance criteria are addressed in the table below.

| # | Acceptance criterion | Status |
|---|---|---|
| 1 | EEG + behavioral target, same participant/trial | ✅ vividness rated immediately after each trial's imagery phase |
| 2 | Imagery vs. perception clearly distinguishable | ✅ separate, time-locked trial phases |
| 3 | Stimulus/state/participant/session identifiers | ✅ BIDS subject/session; stimulus category via trigger code (decode pending) |
| 4 | Trial ordering doesn't confound content/condition with time/block | ⚠️ partial — interleaving reported, not yet independently confirmed; flagged for QC in Commit 3 |
| 5 | Leakage-safe train/test construction possible | ✅ participant/session/trial IDs present |
| 6 | Behavioral target observed, not synthesized | ✅ self-report, not derived from EEG or class label |
| 7 | Data-use terms permit analysis and publication | ✅ CC0 |
| 8 | Files checksummable | ✅ S3 ETag/CRC64NVME; independent hash on ingest |
| 9 | Missingness/artifact rejection quantifiable | ✅ per-subject/session `removed_component.txt` logs present in derivatives |
| 10 | Adequate subject count for exploratory subject-level inference | ✅ 20 (adequate for exploratory Level 2/3; modest for high-powered LOSO — addressed by the fixed-sample sensitivity analysis) |

### ds004306 — EEG-based BCI Dataset of Semantic Concepts for Imagination and Perception Tasks — near miss, exploratory only

Same-subject perception + imagination, visual (pictorial and orthographic) and
auditory modalities, 12 participants, 124 channels, BIDS/CC-BY-4.0, hosted on
[OpenNeuro ds004306](https://openneuro.org/datasets/ds004306). **Rejected as
the primary confirmatory dataset**: it records only participant-level VVIQ/
BAIS-V questionnaire scores, not any trial-level behavioral target — there is
nothing observed at the trial level to serve as the H2 behavioral endpoint.
Condition is also cycled in ~7-minute per-modality blocks rather than
confirmed randomized. Retained as a secondary, exploratory-only dataset for H1
(reliability) and H3/H4 (perception–imagery representational transfer)
robustness checks, never for the primary incremental-validity estimand.

## Tier B — Neural representation pretraining and benchmark

| Dataset | Source | N | Imagery? | Use |
|---|---|---|---|---|
| THINGS-EEG2 | [OSF 3jk45](https://osf.io/3jk45/) | 10, 82,160 trials | No | Perception-side encoder pretraining, external replication of H1/H3 |
| Alljoined-1.6M | [GitHub](https://github.com/Alljoined/Alljoined-1.6M) / [HF](https://huggingface.co/datasets/Alljoined/Alljoined-1.6M) | 20, 1.6M trials | No | Large-scale, consumer-hardware pretraining and cross-hardware generalization checks (CC BY-NC-SA 4.0 — share-alike obligation on any derived artifact) |
| EEG-ImageNet (Spampinato et al.) | [GitHub](https://github.com/perceivelab/eeg_visual_classification) | 6 | No | **Excluded even for pretraining.** [Li et al. 2018](https://arxiv.org/abs/1812.07697) demonstrated the dataset's block-presented design let published classifiers exploit temporal drift rather than stimulus content — a documented instance of exactly the leakage this project's admissibility criteria (#4) are designed to exclude. Retained in the candidates file only as the canonical negative-control citation for `C1_ANALYSIS_SPEC.md`. |

Neither perception-only dataset may be used as evidence for imagery-specific
behavioral validity; both lack an imagery condition entirely.

## Tier C — Auxiliary state-transfer control

**OpenMIIR** ([GitHub](https://github.com/sstober/openmiir), PDDL public
domain): 10 participants, auditory (music) perception and imagery, same
subject/trial. Usable only as an independent, modality-general test of the
perception–imagery alignment infrastructure built in Commit 6 (H4 machinery).
Cannot support the primary visual-imagery claim — auditory modality only, out
of scope per the task's explicit restriction.

## Datasets investigated and excluded from further consideration

- **VEPCON** (OpenNeuro ds003505): high-density visual EEG + fMRI/DWI, but
  perception-only (face/scrambled discrimination, coherent/incoherent motion)
  — no imagery condition at all.
- Several 2025 "visual imagery BCI" datasets surfaced in search (e.g. the
  Figshare visual-imagery-only dataset, DOI 10.6084/m9.figshare.30227503) were
  investigated and rejected: imagery-only design (no separate perception
  condition), only participant-level VVIQ (no trial-level behavior), and a
  CC BY-NC-ND license whose No-Derivatives clause conflicts with this
  project's need to publish derived/preprocessed artifacts.

## Residual risks carried into C1_PROTOCOL.md

1. ~~ds005815's trigger-code table has not yet been decoded from raw data.~~
   **Resolved in Commit 2.** The real `sub-01/ses-1` task recording (114MB,
   BrainVision format) was downloaded and read with MNE, confirming 30 real
   channels at 1000Hz (30949466-sample / 951.466s duration — independently
   contradicting the `eeg.json` sidecar's `RecordingDuration: 122.48`, which
   is now confirmed copy-pasted from a resting-state run, a genuine metadata
   authoring bug, not a hypothesis). The 27 distinct trigger codes (21-47)
   observed in `events.tsv`, with exact per-code occurrence counts ({21:12,
   22:12, 23:24, 24-35:8 each, 36-47:4 each}), were cross-checked against the
   dataset authors' own analysis code
   (`python/Event-Related Potential (ERP) Analysis/config.py` in
   [CECNL/YOTO_You_Only_Think_Once](https://github.com/CECNL/YOTO_You_Only_Think_Once),
   commit `5789a37`) — an authoritative primary source, not inference. See
   `backend/app/research/neural/trigger_codebook.py` for the full transcribed
   table. The same repository's `python/Behavioral Analysis/
   Trigger_Vividness_Data.csv` provides genuine per-trial vividness ratings
   (1-5, zero missing, for 26 enrolled participants — 20 of whom have public
   EEG on OpenNeuro) whose per-(subject, session, trigger-code) occurrence
   *counts* match the public BIDS release exactly, though the *within-code
   instance order* does not match the raw chronological event stream
   byte-for-byte — see the alignment-assumption caveat documented in
   `backend/app/research/neural/adapters/yoto.py`. That repository carries no
   detected LICENSE file, so the CSV is downloaded for provenance-tracked
   analysis only (pinned to the commit SHA above) and is never committed to
   this repository or redistributed; the underlying behavioral data
   ultimately traces back to the CC0-licensed OpenNeuro dataset itself.
2. Block/stimulus-category confound in ds005815 requires empirical QC, not
   just the authors' description, before confirmatory use (Commit 3).
3. ds005815 has no dedicated EOG channels — the ocular-only negative control
   (falsification test 5) will use frontal EEG channels as a documented proxy,
   a weaker control than true EOG.
4. **New, from Commit 2:** the vividness behavioral target's within-trigger-
   code instance alignment (see item 1) is a documented assumption, not a
   certainty. Commit 3 QC should attempt an independent cross-check (e.g. via
   the finer-grained `derivatives/*/task_event.mat` marker stream) before
   this is relied upon for the H2 primary estimand; if it cannot be
   corroborated, H2 falls back to a code-conservative aggregate target per
   `C1_PROTOCOL.md` Section 10.
5. **New, from Commit 5:** `sub-07`'s task-run raw `.eeg` file returns
   HTTP 404 from the OpenNeuro S3 mirror — only its `.vhdr`/`.json`/events
   sidecars are present; the actual signal file is absent from the public
   release. This subject cannot be used at all. The effective usable
   participant count is therefore below the nominal 20 and must be verified
   per-subject (not assumed) before Commit 7's fixed-sample sensitivity
   analysis. Per-participant artifact-rejection severity also varies more
   than expected: a 3-subject smoke test (`results/c1_encoder_smoke.json`)
   found `sub-05` retained only 17/192 perception trials (91% rejected) at
   the standard 150uV threshold, versus 87/192 and 80/192 for `sub-01` and
   `sub-02`. Commit 7 must track and report this heterogeneity explicitly,
   not average it away.
