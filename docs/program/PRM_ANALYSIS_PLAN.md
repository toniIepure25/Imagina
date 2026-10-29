# PRM Stage 1 Statistical Analysis Plan (DRAFT)

## Status

- **Version:** 0.1, 2026-10-29.
- **Applies to:** `ANIMUS-SIM-v1`, Stage 1 measurement validation.
- **Status:** draft for independent statistical review; not yet frozen.
- **Companion documents:** [`SOURCE_MONITORING_SPEC.md`](../animus/SOURCE_MONITORING_SPEC.md),
  [`PRM_PREREGISTRATION.md`](PRM_PREREGISTRATION.md).

This plan is written before data collection. The analysis code will be frozen and hashed before the
primary analysis. Exploratory analyses are labelled as such and are not used to support confirmatory
claims.

## 1. Estimands

Let `i` index participants, `j` items, and `s_j` the true source in `(new, imagined, described, seen)`.

### Primary estimands

1. **Source discrimination:** `d_prime_seen_imagined`, the standardized distance between the seen
   and imagined evidence distributions, estimated from the 2x2 seen/imagined confusion matrix.
2. **Source calibration:** Brier score for the correctness of the source choice, using the reported
   confidence.

### Secondary estimands

- Criterion `c` for the seen/imagined contrast; positive values indicate a conservative bias.
- Externalization rate: proportion of imagined trials called "seen."
- Calibration error (ECE, 10 equal-width bins) and overconfidence.
- `meta_d_prime`, only when at least 100 trials per response category are available per person or
  when a hierarchical model with partial pooling is used across occasions.
- Posterior entropy reduction per minute in the adaptive versus yoked arm.
- Correlation of source measures with VVIQ-2, SIAQ, and a working-memory composite.
- Group contrasts across imagery strata.
- Measurement invariance across groups and device classes.

No composite score is estimated.

## 2. Generative model

For person `i`, item `j`:

```text
x_ij ~ Normal(mu_s, sigma^2)
response = interval(x_ij; c_1, c_2, c_3)
mu_seen      =  d_i / 2
mu_imagined  = -d_i / 2
mu_described = -d_i / 2 - described_gap_i
mu_new       = -d_i / 2 - described_gap_i - new_gap_i
c_k          = c_k^0 + bias_i
```

Person-level parameters:

```text
theta_i = (d_i, bias_i, described_gap_i, new_gap_i, meta_d_prime_i, lapse_i)
```

Priors (weakly informative, to be sensitivity-tested):

```text
d_i             ~ Normal(0, 2)
bias_i          ~ Normal(0, 1)
described_gap_i ~ Half-Normal(0, 1)
new_gap_i       ~ Half-Normal(0, 1)
meta_d_prime_i  ~ Normal(0, 2), truncated below 0
lapse_i         ~ Beta(2, 18)
```

Group and site effects are partial-pooled:

```text
d_i = alpha_d + beta_group[g_i] + beta_site[s_i] + u_i
u_i ~ Normal(0, sigma_d)
```

Model comparison:

- equal-variance versus unequal-variance source distributions;
- shared versus source-specific criteria;
- ideal-observer confidence versus metacognitive-noise confidence;
- fixed versus adaptive selection (measurement model only; selection is randomized).

Criteria: WAIC/LOO, posterior predictive checks, and parameter recovery. A complex model is retained
only if it improves out-of-sample predictive performance and passes recovery.

## 3. Simulation-based calibration

Before fitting human data:

1. Draw 1,000 parameter sets from the prior.
2. Simulate a full session for each.
3. Fit the analysis model.
4. Compute rank statistics for each parameter.
5. Check uniformity with graphical and numerical diagnostics.

Acceptance: 95% interval coverage between 0.93 and 0.97 for the primary parameters; no systematic
rank skew. If SBC fails, the model or priors are revised before registration.

## 4. Reliability

- ICC(2,1): two-way random effects, absolute agreement, single measures.
- Report 95% CI, SEM, and MDC95.
- Primary occasion pair: day 0 and day 7.
- Day 28 is reported descriptively for stability; it is not a second primary test.
- Reliability is estimated for `d_prime`, Brier score, criterion `c`, and calibration error.
- `meta_d_prime` reliability is reported only if the trial gate is met; otherwise it is marked
  `insufficient`.

Interpretation:

- ICC >= 0.75 with lower 95% CI >= 0.60: passes.
- ICC 0.60-0.75: provisional; requires a revision and a second study before training.
- ICC < 0.60: fails; publish the psychometric null and stop the training program.

## 5. Validity

### Convergent and discriminant

- Pearson correlations with VVIQ-2, SIAQ, and the working-memory composite.
- Fisher-z confidence intervals; no directional significance test for the primary pattern.
- Expected pattern: small-to-moderate associations with imagery questionnaires; weaker associations
  with working memory.
- A correlation above 0.70 with a generic source-memory task is a redundancy warning.

### Known groups

- Primary analysis: continuous VVIQ-2 association with `d_prime` and `c`.
- Secondary: group contrasts with 95% CIs and Bayes factors.
- No diagnostic classification; no cutoff optimization.

### Measurement invariance

- Questionnaire comparators: multigroup CFA with configural, metric, and scalar constraints.
- Behavioural model: group-specific parameters with ROPE; compare marginal likelihood or LOO.
- Criteria: Delta CFI < 0.01; Delta RMSEA < 0.015; ROPE excludes a group difference larger than
  0.20 SD.
- Device class: same procedure; if invariance fails, restrict to a single device class and report
  the restriction.

## 6. Adaptive efficiency

- Unit: participant-occasion.
- Outcome: posterior SD of `d_prime` per minute after 60 trials.
- Model: linear mixed-effects model with random intercepts for participant and item family; fixed
  effects for arm, order, and their interaction.
- Primary contrast: adaptive minus yoked, expressed as a percentage of the yoked mean.
- Equivalence: final `d_prime` difference within +/-0.20 (TOST).
- Sensitivity: exclude sessions with >20% missing trials; repeat with all sessions.
- If the adaptive arm is better on precision but not equivalent on `d_prime`, the construct is
  considered drifted and the adaptive claim is not made.

## 7. Missing data and exclusions

- Pre-specified trial exclusions: response time <150 ms or >10 s; no response; technical failure.
- Participant exclusions: failed practice; <50% completed trials; protocol deviation.
- Missing data: FIML for the hierarchical model; multiple imputation (m=50) as a sensitivity
  analysis.
- Report the flow diagram and all exclusions (STROBE).
- Do not impute the primary reliability endpoints from incomplete pairs; report pairwise and
  available-case estimates.

## 8. Multiplicity

- Two primary hypotheses (H1, H2); each tested at alpha = 0.05 with a confidence-interval decision.
- Secondary hypotheses are labelled exploratory and reported with confidence intervals; no
  family-wise claims.
- If a secondary family is treated as confirmatory in a revision, Holm correction is applied and the
  change is registered before analysis.

## 9. Blinding and multiverse

- The analyst receives de-identified data with arm and group labels masked until the primary
  analysis is locked.
- The analysis script is hashed and archived before unblinding.
- Pre-specified multiverse: smoothing correction (0.5 vs 1.0), trial exclusion threshold, prior
  scale, and ICC model. Report a specification curve; the primary specification is fixed in advance.
- Any post hoc analysis is labelled and reported separately.

## 10. Reporting

- STROBE for the observational design.
- GRRAS for reliability and agreement.
- COSMIN domains in a table with evidence and risk of bias.
- CONSORT only for the conditional training RCT, not this study.
- Open data and code statement; synthetic benchmark DOI.
- Negative or null results are reported with the same detail as positive results.

## 11. Software and reproducibility

- Python 3.12, locked environment; analysis code in `backend/app/research/prm/`.
- Deterministic seeds recorded per participant and per simulation.
- Raw trial tables preserved separately from derived summaries.
- Every reported number is recomputable from a documented command.
- A fresh-worktree reproduction is required before submission.
