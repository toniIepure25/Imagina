# C3 NSD-Imagery Row Mapping — Provenance Amendment

## Status change

```
previous_status  = BLOCKED_IMAGERY_ROW_PROVENANCE   (preserved, not deleted)
resolution_status = AUTHORITATIVELY_RESOLVED_BY_NSD_DATA_MANUAL_V1_6
```

The prior blocker (`results/c3_nsdimagery_row_mapping.json`, git history at commit `7e6c945`)
correctly reported that the 144-row gap between the 720 raw `betas_nsdimagery.hdf5` rows and the
576 behaviorally-logged task trials could not be explained from any source this session could
independently locate (raw HDF5 metadata, the official NSD S3 bucket listing, or either
HuggingFace dataset repository the MedARC-AI/MIRAGE reference implementation depends on). That
determination was correct given the evidence available at the time and is preserved unmodified
below — this amendment supersedes it with new evidence, it does not retract it as having been
wrong to issue.

## New evidence

**Source (as provided by the user for this task):** Natural Scenes Dataset Data Manual, version
1.6, snapshot 2025-08-31. The manual itself is gated behind the NSD Data Access Agreement form
(`https://forms.gle/eT4jHxaWwYUDEf2i9`, confirmed via `naturalscenesdataset.org`) and is not
independently fetchable by this session — **this session could not itself retrieve or read the
manual text** and is recording the user-provided explanation of its contents rather than a
first-hand citation. What follows is therefore treated as an authoritative claim to be verified
empirically against the actual data this session has access to, not as independently confirmed
primary-source text.

**Claimed explanation:** vision trials produce one beta weight each; imagery trials produce one
beta weight each; attention trials produce **two** beta weights each, because the cue epoch and
the detection epoch of an attention trial are modeled as two temporally distinct GLM events.

```
vision:    3 runs x 48 trials x 1 beta = 144
imagery:   6 runs x 48 trials x 1 beta = 288
attention: 3 runs x 48 trials x 2 beta = 288
total = 144 + 288 + 288 = 720
```

## Independent empirical verification performed this session

The claim was **not** accepted on citation alone. `nsddata/experiments/nsdimagery/
designmatrixGLMsingle.mat` (sha256 `803f0399a746eeff1d402b808dc9d910c6345285d5388cfe192262671c7948f8`,
already hashed during the prior blocked investigation) was re-inspected programmatically:

For each of the 12 per-run design-matrix cells, the number of GLM regressor columns with at least
one nonzero (event-onset) entry, and the total count of nonzero entries, was computed directly:

| Run | TR count | Active columns | Total onset events |
|---|---|---|---|
| visA | 240 | 6 | **48** |
| attA | 480 | 12 | **96** |
| imgA_1 | 240 | 6 | **48** |
| visB | 240 | 6 | **48** |
| attB | 480 | 12 | **96** |
| imgB_1 | 240 | 6 | **48** |
| visC | 240 | 6 | **48** |
| attC | 480 | 12 | **96** |
| imgC_1 | 240 | 6 | **48** |
| imgA_2 | 240 | 6 | **48** |
| imgB_2 | 240 | 6 | **48** |
| imgC_2 | 240 | 6 | **48** |

Sum: 3x48 (vis) + 6x48 (img) + 3x96 (att) = 144 + 288 + 288 = **720**, matching the claimed
accounting and the actual `betas_nsdimagery.hdf5` row count exactly. The attention runs' 480-TR
length (vs. 240 for vision/imagery) and doubled active-column count (12 vs. 6) is independent,
data-derived structural evidence consistent with each attention trial being modeled as two
distinct events rather than one — it does not merely repeat the manual's claim, it corroborates it
from the raw design-matrix geometry, which was already on disk and hashed before this task began.

This is accepted as **empirically corroborated**, not merely cited.

## Authoritative run order and beta-row blocks (0-based, half-open)

Run order (agreed by the behavioral logs' `RUN` column and the claimed manual):

```
1  visA     2  attA     3  imgA_1    4  visB     5  attB     6  imgB_1
7  visC     8  attC     9  imgC_1   10  imgA_2  11  imgB_2  12  imgC_2
```

| Run | Rows |
|---|---|
| visA | 0:48 |
| attA | 48:144 |
| imgA_1 | 144:192 |
| visB | 192:240 |
| attB | 240:336 |
| imgB_1 | 336:384 |
| visC | 384:432 |
| attC | 432:528 |
| imgC_1 | 528:576 |
| imgA_2 | 576:624 |
| imgB_2 | 624:672 |
| imgC_2 | 672:720 |

These offsets are derived programmatically from the run-order + per-run-beta-count specification
(`backend/app/research/fmri/nsdimagery_row_mapping.py::compute_run_blocks`), not hardcoded as a
literal table — the table above is this session's rendering of that function's output for
documentation, and CI asserts the function's output matches it.

## What remained to certify after this amendment

The block-level structure (which 48- or 96-row span belongs to which run) is now on solid footing.
The **internal ordering within each block** (does beta row 0 of the visA block correspond to
behavioral trial 1, or some other permutation of the 48?) required separate, direct proof — see
`results/c3_nsdimagery_beta_event_manifest.json` and the vision cross-session validation in
`results/c3_subj01_nsdimagery_vision_validation.json` for that certification, performed in the
following commit.
