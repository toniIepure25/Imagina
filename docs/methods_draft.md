# IMAGINA Methods Section — Draft

> **Status:** DRAFT — synthetic validation complete, not ready for submission.
> **Not for distribution.** This is a working draft to guide implementation.
>
> **Critical disclaimers:**
> - The primary outcome is now objective imagery reconstruction error (Gate C0).
> - A confirmatory hierarchical analysis is executable on synthetic data (statsmodels MixedLM).
> - Biosignal acquisition foundations exist (ring buffer, marker sync) but real EEG collection is not implemented.
> - Full synthetic end-to-end experiments have been executed with falsification testing.
> - No human data collection is authorized.
> - Randomization uses a balanced Williams crossover design (6 sequences).
> - All results are synthetic-only; no human construct validity is established.

---

## Participants

[N] participants (age range, recruitment method) were recruited from [source]. Inclusion criteria: normal or corrected-to-normal vision, no history of epilepsy or photosensitive conditions, ability to follow written instructions in [language]. Exclusion criteria: current psychotropic medication affecting cognitive function, inability to commit to the full study protocol.

All participants provided informed consent via the IMAGINA electronic consent system. The study was approved by [ethics board] (reference: [number]).

## Design

A within-subjects design with three feedback conditions was employed:

1. **Adaptive (closed-loop):** Visual scene parameters (clarity, blur, wall distortion, light stability, texture detail, particle stability, fog density, color saturation, breathing cue) were updated every 2 seconds based on the system's real-time estimate of imagery quality (IQI) and perception-imagination distance (PID).

2. **Fixed (non-contingent control):** Visual scene parameters were held constant at moderate values regardless of the participant's estimated imagery state. The visual display was identical in appearance to the adaptive condition but did not respond to the participant's state.

3. **Yoked (sham control):** Visual scene parameters replayed the trajectory recorded from a previous participant's adaptive session, providing dynamic visual changes that were not contingent on the current participant's imagery state.

Condition order was counterbalanced using a Latin square design with block randomization. Each participant completed all three conditions with [washout period] between conditions. Within each condition, participants completed [N] sessions on separate days.

## Materials

### IMAGINA Platform
The IMAGINA platform (version 0.5.0, [commit SHA]) is a local-first research prototype consisting of a FastAPI backend and Next.js frontend. The 3D Dream Corridor visualization was rendered using React Three Fiber. All data was stored locally in SQLite (no cloud transmission).

### Stimuli
Five corridor imagery stimuli of increasing complexity were used: Simple Corridor, Detailed Corridor, Corridor with Doors, Garden at End, and Memory Room. Stimulus descriptions and content hashes are registered in the IMAGINA stimulus registry.

### Instruments
- **VVIQ-2** (Marks, 1995): 16-item questionnaire assessing visual imagery vividness. Administered pre- and post-study.
- **Trial-level vividness:** Single item per trial (1-7 Likert, 1=no image, 7=perfectly vivid).
- **Trial-level confidence:** Single item per trial (1-7 Likert).
- **Trial-level effort:** Single item per trial (1-7 Likert).
- **Post-session perceived contingency:** Single item (1-7 Likert, "To what extent did you feel the visual feedback responded to your mental imagery?").
- **Post-session fatigue:** Single item (1-7 Likert).
- **Post-session discomfort:** Single item (1-7 Likert).

### Proxy Metrics (Exploratory)
Two composite proxy metrics were computed in real time:
- **IQI (Imagery Quality Index):** Weighted combination of attention stability (0.35), imagery engagement (0.30), behavioral consistency (0.20), and relaxation (0.15), scaled by confidence. Range 0-1, higher is better. These are experimental proxies, not validated neuroscientific measures.
- **PID (Perception-Imagination Distance):** Weighted combination of neural proxy distance (0.45), behavioral distance (0.35), and uncertainty (0.20). Range 0-1, lower is better.

Both metrics are derived from the system's internal signal processing pipeline (simulated or, if available, EEG-derived features) combined with self-report inputs. They serve as adaptive feedback drivers, not as primary outcome measures.

## Procedure

Each session followed this sequence:

1. **Consent verification** (first session only or re-verification)
2. **Baseline calibration** (60-second eyes-closed resting state)
3. **Practice trial** (1 familiarization trial, excluded from analysis)
4. **Experimental trials** ([N] trials per session):
   - 3-second fixation cross
   - Imagery phase (participant signals when image is formed)
   - Self-report ratings (vividness, confidence, effort)
   - 30-second inter-trial interval
5. **Post-session ratings** (perceived contingency, fatigue, discomfort)

The safety monitor automatically checked for estimated fatigue (threshold: 0.80), overeffort, dissociation-related keywords in free-text responses, and session duration (maximum: 20 minutes). Sessions exceeding safety thresholds were terminated with a rest recommendation.

## Data Analysis

### Primary Analysis

**Primary endpoint:** Standardized multi-feature objective imagery reconstruction error (composite of orientation, hue, spatial frequency, position, and size errors). Lower is better. See `docs/science/objective_measurement_spec.md`.

**Primary estimand:** Within-participant ATE of adaptive vs. yoked on objective reconstruction error.

A trial-level hierarchical linear mixed-effects model was fitted using Python statsmodels MixedLM:

```
objective_error ~ condition + period + session_index + baseline_precision + task_family
                + (1 | participant)
```

**Primary contrast:** Adaptive vs. Yoked (one test).

**Key secondary contrasts** (Holm-Bonferroni corrected):
1. Adaptive vs. Fixed
2. Fixed vs. Yoked

Subjective vividness is analyzed as a secondary endpoint only.

### Blinding Check
Perceived contingency ratings were compared across conditions to assess blinding success.

### Exploratory Analyses
1. Convergent validity of IQI and PID with self-reported vividness
2. VVIQ-2 moderation of the training effect
3. Incremental validity of behavioral and proxy metrics (hierarchical model comparison)

### Missing Data
Full Information Maximum Likelihood (FIML) within the LMM framework.

### Software
- IMAGINA platform: version 0.5.0 (Python 3.10+, Node 20+)
- Statistical analysis: R 4.x with lme4, ggplot2, emmeans
- Data preparation: Python with pandas

---

## Limitations (to be included in Discussion)

1. IQI and PID are hand-tuned composite proxies with no independent psychometric validation.
2. Default signal processing uses simulated features; real EEG integration requires further validation.
3. The 3D corridor paradigm limits generalizability to other imagery domains.
4. Single-blind design (operator aware of condition).
5. Self-report vividness is a subjective measure subject to demand characteristics.
6. The adaptive algorithm's responsiveness is constrained by the 2-second update cycle.

---

*This methods draft should be revised with actual values after pilot testing and before submission.*
