# EEG, MEG and fMRI Validation (Phase 2)

Gate records in `results/phase2/`. Code: `backend/app/multimodal/validation/{eeg_yoto,meg_sample,fmri_haxby}.py`.
Criteria were declared in code before each run. Post-hoc additions are labelled. Participant IDs in outputs are
pseudonymous (salted SHA-256 prefix for ds005815; public dataset numbers elsewhere).

| Experiment | Dataset | Verdict |
|---|---|---|
| EEG Protocol A — perception vs imagery phase | OpenNeuro ds005815 (YOTO) | EEG_A_VERDICT |
| EEG imagery content (face vs square) | ds005815 | EEG_CONTENT_VERDICT |
| EEG Protocol B — vividness prediction | ds005815 | EEG_B_VERDICT |
| MEG events, bad channels, auditory vs visual decoding | MNE `sample` | **PASS** |
| fMRI GLM agreement + VT category decoding (perception only) | Haxby 2001 (nilearn) | FMRI_VERDICT |
| fMRI imagery decoding | — | **BLOCKED** |

OpenMIIR (music imagery EEG) was not available locally, so ds005815 was used as the specification's fallback.

EEG_SECTION

## MEG — MNE `sample` (one participant) — PASS

`sample_audvis_filt-0-40_raw.fif`: auditory and visual stimuli, left and right (event codes 1–4).

| Check | Value | Criterion |
|---|---|---|
| Events found (ours vs `mne.find_events`) | 319 vs 319 | count mismatch ≤ 0 |
| Max event sample offset | 0 samples | ≤ 0 |
| Auditory (1, 2) vs visual (3, 4): peak time-resolved AUC (LDA per time point, stratified 5-fold over 286 epochs) | 0.995 at 93 ms | ≥ 0.90 (fail < 0.70) |
| Pre-stimulus AUC (mean over t < 0) | 0.499 | \|AUC − 0.5\| ≤ 0.10 |
| Permuted-label peak AUC (negative control) | 0.596 | (reported) |
| Bad channels flagged | MEG 2443 only | flagged fraction ≤ 0.05; annotated bad missed ≤ 0 (both **post hoc**) |

The first run pooled magnetometers and gradiometers and flagged 29 channels (kept as
`meg_sample.run1_pooled_badchannels.json`). The detector now scores each sensor type separately and also requires a
variance ratio of at least 4× (or a flat channel). The two bad-channel criteria were written after that first run.

Limits: one participant, one session, offline only. The decoding contrast is sensory modality, not imagery. No
real-time MEG path exists or is claimed.

FMRI_SECTION
