# Analysis Specification — IMAGINA

> **Status:** Executable synthetic analysis. Not validated on human data.

## Primary Model

Trial-level hierarchical linear mixed-effects model (frequentist, statsmodels MixedLM):

```
objective_error ~ condition + period + session_index + baseline_precision + task_family
                + (1 | participant)
```

### Fallback Model

When full model fails to converge:

```
objective_error ~ condition + period + session_index
                + (1 | participant)
```

Fallback models are labeled as exploratory.

## Multiplicity Control

1. **Primary contrast:** Adaptive vs. Yoked (one test, no correction needed)
2. **Key secondary:** Holm-Bonferroni correction across secondary endpoints
3. **Exploratory:** No confirmatory language applied

## Sensitivity Analyses

| Analysis | Purpose |
|----------|---------|
| No-carryover model | Remove carryover indicator |
| With-carryover model | Include carryover indicator |
| Complete-case only | Exclude participants with missing sessions |
| Negative-control outcome | Run model on perceptual control endpoint |
| Subjective-only | Run model on vividness (labeled secondary) |

## Required Result Fields

- Estimand ID
- Effect estimate
- Standard error
- 95% CI
- Test statistic
- p-value
- Standardized effect
- Convergence status
- Singularity warning
- Participant and trial counts
- Missingness count
- Analysis population
- Model specification hash

## Diagnostics

- Residual normality
- Random effects variance
- Convergence information
- Model comparison (primary vs. fallback)
