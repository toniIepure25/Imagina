# CRT Optional Neural Extension (Stage 1E)

**Status:** optional, separate, not required for the behavioural claim.
**Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`; no neural-decoding or clinical claim.

## 1. Question

Does the active-prospective manipulation change (a) a post-outcome prediction-error component and
(b) a later source-retrieval component, relative to the yoked control? This is a **component** question,
not a decoding question.

## 2. Design

- EEG in a subset of the behavioural sample; target N=48 after exclusions.
- Same trial structure as the behavioural task, with brief delay and no feedback.
- Conditions: `active_predict`, `active_intervene`, `yoked_predict`, `yoked_intervene`.
- Primary neural quantities: pre-outcome stimulus-preceding negativity / prediction interval activity;
  post-outcome feedback-related negativity and P3; later source-retrieval old/new component.
- Behavioural primary endpoint remains the model-based source sensitivity; neural measures are
  secondary and exploratory unless separately registered.

## 3. BIDS and quality control

- BIDS-EEG with `dataset_description.json`, sidecars, events, and README.
- Line noise, bad channels, blink/muscle artifacts, and reference documented.
- Preprocessing lineage and versioned pipeline; no manual editing without a log.
- Split by participant, never by trial, for any classifier; no leakage across participants.
- Report confidence intervals and subject-level effects, not only grand averages.

## 4. Analysis

- Pre-specified ROIs/time windows; no circular window selection.
- Mixed models with participant random effects; condition, prediction, outcome, and their interactions.
- Model comparison uses the same M0–M7 logic where applicable.
- Neural-behaviour links are descriptive unless a separate preregistration fixes the direction.

## 5. Boundaries

No mind-reading, dream decoding, diagnosis, consciousness measurement, or clinical use. No raw neural
data to external APIs. A null neural result does not rescue a failed behavioural primary endpoint.
