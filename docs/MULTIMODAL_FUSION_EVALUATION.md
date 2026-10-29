# Multimodal Fusion Evaluation (Phase 2)

Gate record: `results/phase2/fusion_eegmat.json` (experiment `FUSION_EEG_ECG_EEGMAT`). Code:
`backend/app/multimodal/validation/fusion_eegmat.py`, models in `backend/app/multimodal/fusion.py`.

## Which pairings exist

Fusion was evaluated only where modalities were **recorded simultaneously from the same people**. Nothing was paired
synthetically, and no unpaired datasets were stitched together.

| Pairing | Paired public data used | Status |
|---|---|---|
| EEG + ECG | PhysioNet eegmat 1.0.0 (36 participants) | **Evaluated** |
| EEG + EDA / respiration / fNIRS | none available locally | BLOCKED |
| EEG + MEG / fMRI | none (offline modalities, different cohorts) | BLOCKED |
| Any modality + imagery labels | none with physiology besides EEG (ds005815 has EEG only) | BLOCKED |

## Task and design

- **Labels:** rest (last 60 s of the baseline recording) vs mental arithmetic (60 s), 10 s windows (12 per
  participant). This is a workload contrast, **not imagery**.
- **Features:** EEG log band power (19 channels × 5 bands). ECG heart rate and RMSSD per window from
  `processing.ecg.ecg_features`. ECG windows with quality < 0.3 were treated as missing.
- **Normalization:** per-participant z-scoring without labels.
- **Validation:** leave-one-subject-out (fold unit asserted). Balanced accuracy per held-out participant, CI =
  bootstrap over participants.
- **Models:**
  - EEG-only / ECG-only: per-modality logistic regression.
  - Early: concatenation + availability masks → logistic regression.
  - Late: quality-weighted log-odds of per-modality models.
  - Intermediate: PyTorch per-modality encoders, quality-weighted pooling, modality dropout 0.3, 40 epochs.
- **Missing-modality test:** late fusion with all ECG removed at test time.

## Predeclared criteria and verdict — PASS

| Criterion | Value | Threshold | Verdict |
|---|---|---|---|
| EEG-only balanced accuracy, CI lower bound | 0.803 | ≥ 0.55 (fail < 0.50) | PASS |
| Late fusion − EEG-only, CI lower bound | +0.023 | ≥ 0.00 (fail < −0.05) | PASS |

## Results (36 participants, LOSO)

| Model | Balanced accuracy | 95% CI | ECE |
|---|---|---|---|
| EEG-only | 0.854 | 0.803–0.900 | 0.055 |
| ECG-only | **0.926** | 0.882–0.965 | 0.067 |
| Early fusion | 0.891 | 0.831–0.942 | 0.041 |
| Late fusion | 0.914 | 0.852–0.961 | 0.037 |
| Intermediate fusion | 0.887 | 0.829–0.935 | 0.098 |
| Late fusion, ECG missing at test | 0.854 | — | — |

Fusion minus EEG-only (per participant): early +0.037 (0.009 to 0.065), late +0.060 (0.023 to 0.097),
intermediate +0.032 (−0.007 to 0.069).

**Secondary comparison (added post hoc, after seeing ECG-only > EEG-only):** fusion minus the best single
modality (ECG-only):

| Model | Δ vs ECG-only | 95% CI |
|---|---|---|
| Early | −0.035 | −0.076 to 0.007 |
| Late | −0.012 | −0.049 to 0.025 |
| Intermediate | −0.039 | −0.086 to 0.005 |

## Interpretation

- Adding ECG to EEG helps (predeclared primary criterion). **No fusion model beats ECG alone**: every CI against
  ECG-only includes zero, and the point estimates are negative. On this task the gain over EEG comes from heart
  rate, a strong workload marker. It does not show that fusion extracts complementary information.
- Late fusion degrades gracefully: with ECG removed at test time it equals EEG-only (0.854) instead of failing.
- Intermediate (neural) fusion has the worst calibration (ECE 0.098) and no accuracy advantage, so it is not
  recommended for the controller.
- One participant (M13, median ECG quality 0.68) is the worst under every model: 0.42 for EEG-only and ECG-only,
  and 0.08–0.17 for the fusion models. Fusion can amplify a participant whose two modalities disagree. Five
  participants had median ECG quality below 0.75 (M02, M13, M20, M28, M35).

## Limitations

- Rest always precedes arithmetic, so time-on-session is confounded with condition. No negative control (for
  example, decoding two halves of rest) was run. Read the absolute accuracies with that confound in mind.
- Single dataset, one binary workload contrast, 12 windows per participant.
- Workload, not imagery. These numbers do not transfer to imagery-state estimation.
- The ECG features came from the R-peak detector **before** the Phase-2 adaptive-threshold revision (code commit
  `2830dcd`; see `PHYSIOLOGICAL_VALIDATION.md`). Heart rate is robust to the missed-beat failure (HR error 0.16% in
  run 1), but RMSSD is not. The run has not been repeated with the revised detector.

## Consequence for the platform

The controller's default remains the quality-weighted late-fusion estimator, with per-modality evidence labels
shown. Fusion output must not be described as better than the best single modality.
