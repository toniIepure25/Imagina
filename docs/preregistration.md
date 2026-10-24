# IMAGINA Preregistration Template

> **Status:** SYNTHETIC PROTOCOL FROZEN — preregistration-ready for synthetic validation.
> **Target registry:** OSF Preregistrations or AsPredicted.
>
> **Critical disclaimers:**
> - Primary outcome: objective imagery reconstruction error (composite, frozen).
> - Objective behavioral task battery implemented (4 task families, Gate C0).
> - Sample size estimated via simulation-based power analysis (Monte Carlo).
> - No human data collection is authorized.
> - Confirmatory analysis is executable on synthetic data (statsmodels MixedLM).
> - Counterbalancing uses balanced Williams crossover sequences.
> - All validation is synthetic-only; no human construct validity is established.

---

## Study Information

### Title
Closed-Loop Adaptive Visual Feedback for Mental Imagery Training: A Within-Subjects Controlled Study

### Authors
[To be completed]

### Research Questions

**Primary:**
Does adaptive feedback improve objective visual-imagery precision and control beyond fixed feedback, yoked feedback, practice effects, expectancy effects, fatigue, and period/order effects?

**Secondary:**
1. Does adaptive feedback improve imagery control (manipulation accuracy)?
2. Does adaptive feedback improve imagery stability (delayed reconstruction)?
3. Is there a dissociation between objective and subjective improvement?
4. Do negative controls (perceptual matching) remain stable?

### Hypotheses

**H1 (Primary):** Adaptive feedback produces lower standardized objective imagery reconstruction error than yoked feedback (E[Y(adaptive) - Y(yoked)] < 0).

**H2 (Key Secondary):** Adaptive vs. fixed contrast is present but smaller than adaptive vs. yoked, indicating contingency drives improvement.

**H3 (Key Secondary):** Imagery manipulation accuracy improves more under adaptive than yoked.

**H4 (Exploratory):** Subjective vividness improvement may occur without corresponding objective improvement.

**H5 (Negative Control):** Perceptual matching error does not show condition-specific improvement.

### Falsification Criteria

The scientific hypothesis is considered unsupported when:
- Adaptive vs. yoked objective effect is absent
- Only subjective outcomes improve
- Effect is explained by perceptual negative control
- Effect disappears under carryover sensitivity
- Type-I error is inflated
- Endpoint reliability is inadequate
- Model convergence is unacceptable
- Effect is driven by a small number of participants
- Result exists only in exploratory endpoints

---

## Design Plan

### Study Type
Within-subjects experimental design with counterbalancing.

### Conditions
1. **Adaptive:** Scene parameters respond to estimated imagery state (IQI/PID-driven feedback).
2. **Fixed:** Scene parameters are held constant regardless of imagery state.
3. **Yoked:** Scene parameters replay the trajectory of a previous adaptive participant (non-contingent).

### Counterbalancing
Latin square (3! = 6 orders) with block randomization. Participants experience all three conditions in counterbalanced order with washout periods.

### Blinding
- Participants are blind to condition assignment.
- Operator is aware of condition (single-blind).
- All conditions use the same visual interface.
- Perceived contingency is measured post-session to check blinding success.

---

## Sampling Plan

### Sample Size Rationale
Based on approximate within-subjects F-test power analysis:
- Effect size: Cohen's d = 0.50 (medium)
- Alpha: 0.05 (two-tailed)
- Power: 0.80
- Assumed correlation between conditions: rho = 0.50
- Dropout rate: 15%

Estimated N = [computed by `power_analysis.required_sample_size()`]

### Stopping Rule
Data collection continues until the target N is reached or the study period ends.

---

## Variables

### Independent Variable
Feedback condition (adaptive, fixed, yoked) — within subjects.

### Primary Dependent Variable
Standardized multi-feature objective imagery reconstruction error (composite). Range 0–1, lower is better.

### Key Secondary Dependent Variables
- Feature-specific reconstruction errors (orientation, hue, spatial frequency, position, size)
- Imagery manipulation accuracy
- Delayed stability degradation
- Metacognitive calibration (confidence-resolution slope)

### Subjective Secondary Variables (not primary outcomes)
- Self-reported trial-level vividness (1-7 Likert)
- Self-reported effort (1-7 Likert)

### Negative Control Variables
- Perceptual matching error (target visible)
- Simple motor response latency

### Covariates
- Baseline imagery precision (calibration)
- Period (counterbalancing position)
- Session index (within-condition progression)
- Task family

---

## Analysis Plan

### Primary Analysis
Trial-level hierarchical linear mixed-effects model (Python statsmodels MixedLM):

```
objective_error ~ condition + period + session_index + baseline_precision + task_family
                + (1 | participant)
```

### Primary Contrast
Adaptive vs. Yoked (one test, negative effect = adaptive better).

### Key Secondary Contrasts
Holm-Bonferroni corrected:
1. Adaptive vs. Fixed
2. Fixed vs. Yoked

### Sensitivity Analyses
1. Model without carryover indicator
2. Model with carryover indicator
3. Complete-case only (exclude incomplete participants)
4. Negative-control outcome analysis (perceptual matching)
5. Subjective-only analysis (labeled secondary)

### Missing Data
Full Information Maximum Likelihood (FIML) within the LMM framework.
Complete-case sensitivity analysis as robustness check.

### Calibration
3-down/1-up transformed staircase, condition-independent, frozen before experimental sessions.

### Counterbalancing
Balanced Williams crossover sequences (6 orders for 3 conditions).

### Stopping Rule
Data collection continues until target N (simulation-derived) is reached.

### Sample Size
Determined by simulation-based power analysis (Monte Carlo, not formula).
See `docs/science/simulation_report.md`.

---

## Data and Code Availability

### Data Availability
Anonymized trial-level data will be shared via [repository/platform] after publication.
No raw EEG data will be shared (if collected, data remains local per ethics protocol).

### Code Availability
Full analysis code, synthetic dataset, and IMAGINA platform source code will be available at [repository URL].

### Software Versions
- IMAGINA backend: `0.5.0.dev1`
- IMAGINA frontend: `0.5.0-research`
- Python: 3.10+
- R: [version for LMM analysis]
- Key packages: FastAPI, pydantic, aiosqlite, lme4, ggplot2

---

## Ethics

### Approval
[Ethics board reference number — to be obtained before data collection]

### Consent
Informed consent obtained electronically via the IMAGINA consent gate.
Participants may withdraw at any time without penalty.

### Risk Management
- Session time limit: 20 minutes
- Fatigue monitoring with automatic session termination
- No deceptive practices beyond condition blinding
- Debriefing includes condition explanation

---

## Timeline

1. **Preregistration:** Before any participant data collection
2. **Pilot testing:** N=3-5 to verify protocol and platform
3. **Data collection:** Target N participants
4. **Analysis:** Following the registered plan
5. **Publication:** After analysis complete

---

*This preregistration template follows the OSF standard format. Complete all [bracketed] sections before registering.*
