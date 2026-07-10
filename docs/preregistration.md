# IMAGINA Preregistration Template

> **Status:** Draft template. Complete before data collection begins.
> **Target registry:** OSF Preregistrations or AsPredicted.

---

## Study Information

### Title
Closed-Loop Adaptive Visual Feedback for Mental Imagery Training: A Within-Subjects Controlled Study

### Authors
[To be completed]

### Research Questions

**Primary:**
Does closed-loop adaptive visual feedback produce measurable improvements in voluntary visual mental-imagery vividness beyond practice effects, fixed feedback, and non-contingent feedback?

**Secondary:**
1. Do proxy metrics (IQI, PID) show convergent validity with self-reported vividness?
2. Does baseline imagery ability (VVIQ-2) moderate the training effect?
3. What is the relationship between perceived contingency and actual feedback contingency?

### Hypotheses

**H1 (Primary):** Participants in the adaptive condition will show greater improvement in self-reported vividness across sessions compared to the fixed-feedback and yoked-feedback conditions.

**H2:** The adaptive-vs-yoked contrast will be larger than the adaptive-vs-fixed contrast, indicating that contingency (not mere feedback presence) drives improvement.

**H3 (Exploratory):** IQI and PID will show moderate correlation with self-reported vividness (|r| > 0.3), supporting convergent validity.

**H4 (Exploratory):** Participants with lower baseline VVIQ-2 scores will show larger improvements than those with higher scores.

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
Self-reported trial-level vividness (1-7 Likert scale).

### Secondary Dependent Variables
- VVIQ-2 change score (pre/post)
- Perceived contingency rating (1-7 Likert)
- Response time for imagery formation
- Post-session fatigue and discomfort ratings

### Exploratory Variables (not outcomes)
- IQI (Imagery Quality Index) — experimental proxy, 0-1
- PID (Perception-Imagination Distance) — experimental proxy, 0-1
- Behavioral consistency — 0-1
- Safety events count

### Covariates
- Pre-study VVIQ-2 score (baseline imagery ability)
- Session order (counterbalancing check)

---

## Analysis Plan

### Primary Analysis
Linear Mixed-Effects Model (LMM):

```
vividness ~ condition * session + (1 + session | participant_id)
```

With pre-study VVIQ-2 as covariate and session order as a nuisance variable.

### Planned Contrasts
1. Adaptive vs. Fixed (tests contingency beyond practice)
2. Adaptive vs. Yoked (tests contingency beyond non-contingent feedback)
3. Fixed vs. Yoked (tests feedback presence vs. sham)

Correction: Holm-Bonferroni for 3 contrasts.

### Effect Size
Cohen's d computed from LMM contrast estimates.

### Missing Data
Full Information Maximum Likelihood (FIML) within the LMM framework.

### Assumption Checks
- Residual normality (Q-Q plot)
- Homoscedasticity (residual vs. fitted)
- Random effects normality

### Exploratory Analyses
1. Convergent validity of IQI/PID with vividness (Pearson correlation)
2. VVIQ-2 moderation (condition x VVIQ-2 interaction)
3. Perceived contingency by condition (blinding check)
4. Incremental validity (hierarchical model comparison)
5. Group-aware analysis (median split by VVIQ-2, exploratory only)

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
