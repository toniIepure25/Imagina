# C3 Protocol Provenance Audit — Perception Split

## Question

Two split descriptions exist in the repository history:

1. `docs/research/C3_REALDATA_INFERENCE_SPEC.md` (frozen at commit `1680ea9`, 2026-07-24 18:48:58 +0300):
   describes an approximate "~9000 train / 1000 shared1000 test" design, with inner CV inside the
   9000-image training pool for alpha selection.
2. `results/c3_split_manifest.json` (first appears with explicit 8000/1000/1000 counts at commit
   `9aa7b4e`, 2026-07-25 14:27:13 +0300; hash-locked with full image-ID lists at `996bb4d`,
   2026-07-25 17:49:24 +0300, `manifest_hash = 3ea066638ee94568275f119fb0cd737821932e4aa2ee78f31854e765028a3b78`):
   splits the 10,000-image participant pool into 8000 train / 1000 validation / 1000 test, with the
   1000 test images identified with the shared1000 set.

This audit determines whether the 8000/1000/1000 manifest was frozen *before* any test-set result
existed (a legitimate prospective protocol refinement), or whether it was chosen *after* seeing
performance under some other split (which would be undisclosed multiplicity / p-hacking).

## Method

Git history was inspected directly (`git log --oneline --follow`, `git show --stat`, `git log
--reverse --format='%h %ci %s'`) for every commit on `research/fmri-imagery-transfer-c3-realdata`
that touches `results/c3_split_manifest.json`, `docs/research/C3_REALDATA_INFERENCE_SPEC.md`, or any
file containing a perception decoding/pilot/retrieval result. No commit history was rewritten,
squashed, or reordered for this audit — the sequence below is the actual, unmodified commit
chronology, `--not-forged`.

## Chronology (all times +0300, branch `research/fmri-imagery-transfer-c3-realdata`)

| Order | Commit | Date/time | Event |
|---|---|---|---|
| 1 | `1680ea9` | 2026-07-24 18:48:58 | Inference spec frozen — describes ~9000/1000 design, inner CV |
| 2 | `6bccaea` | 2026-07-24 20:17:49 | Real-data acquisition infra added |
| 3 | `5225b00` | 2026-07-24 20:19:07 | Acquisition documented as in-progress/blocked |
| 4 | `9aa7b4e` | 2026-07-25 14:27:13 | Split manifest first appears with 8000/1000/1000 counts |
| 5 | `2fa27b7` | 2026-07-25 15:33:20 | Storage-budget fix |
| 6 | `996bb4d` | 2026-07-25 17:49:24 | Split manifest hash-locked with full explicit train/val/test image-ID lists (`manifest_hash = 3ea066638ee94568...`) |
| 7 | `0593a16` | 2026-07-25 17:55:40 | Pilot decoder *module* (`perception_pilot.py`) added — readiness explicitly states acquisition still incomplete: **"23/40 sessions complete, 454/10000 stimuli downloaded"**. No test-set (or any-set) result exists in this commit. |
| 8 | `2c5be36` | 2026-07-25 18:30:18 | Session log update, no results |
| 9 | `6a838f4` | 2026-07-26 12:55:14 | Full 40/40 perception beta acquisition certified |
| 10 | `d9d9bc3` | 2026-07-26 12:57:01 | Stimulus reconstruction / CLIP target certification |
| 11 | `006f3d2` | 2026-08-20 21:47:15 | **First and only commit containing an executed perception-decoding result** (`results/c3_subj01_perception_pilot.json`, MRR = 0.0827) |

## Findings

- `total_mapped_trials` / split counts of exactly 8000/1000/1000 (`n_excluded_imagery_targets: 0`)
  were fixed at commit **4** (`9aa7b4e`, 2026-07-25 14:27:13) and hash-locked with the complete,
  auditable image-ID assignment at commit **6** (`996bb4d`, 2026-07-25 17:49:24).
- Real-data acquisition was **not even complete** at the time the split was hash-locked — commit
  **7** (six minutes after the hash-lock) explicitly records only 23/40 beta sessions and 454/10000
  stimulus images present. It is not physically possible to have evaluated test-set performance
  under an alternative split at this point, because the data required to do so did not exist yet.
- **No commit prior to `006f3d2`** contains any perception-decoding result file, MRR value, or any
  other test-derived metric, for either the 8000/1000/1000 split or the ~9000/1000 design described
  in the inference spec. `git log --diff-filter=A -- 'results/c3_*perception*' 'results/c3_*pilot*'
  'results/c3_*decoding*'` confirms `results/c3_subj01_perception_pilot.json` was added for the
  first time in `006f3d2`, on 2026-08-20 — **26 days** after the split was hash-locked.
- The only other perception-decoding result in the repository (`9487c69`, "establish perception
  decoding foundation") lives on the sibling branch `research/fmri-imagery-transfer-c3` and was run
  against deterministic synthetic fixtures for CI smoke-testing, not real subj01 data. It is
  unrelated to this split-selection question.

## Determination

**The 8000/1000/1000 split is a prospective protocol amendment relative to the original
`C3_REALDATA_INFERENCE_SPEC.md` design, frozen and hash-locked 26 days before the first (and only)
test-set evaluation, at a point when full evaluation was not yet technically possible.** There is no
evidence of split selection informed by outcome. The amendment is accepted as the frozen primary
split for all subsequent H1/H2 work.

This audit does **not** retroactively bless the perception-decoding result computed under this split
(`006f3d2`) as final — that result is separately reopened for a leakage-free, frozen-decoder-spec
strict replay (see `results/c3_subj01_perception_strict_replay.json` and the corresponding session
log entry). The split itself, independent of the leaky preprocessing used to evaluate it, is
certified prospective.

## Machine-readable companion

See `results/c3_protocol_provenance_audit.json` for the structured version of this chronology,
including commit SHAs, ISO timestamps, and the determination field
`split_provenance = "PROSPECTIVE_AMENDMENT_VERIFIED"`.
