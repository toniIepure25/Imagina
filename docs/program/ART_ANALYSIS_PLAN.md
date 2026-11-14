# ART Statistical Analysis Plan (DRAFT)

## Status

- **Version:** 0.1, 2026-10-29.
- **Applies to:** `ANIMUS-ART-v1`, Stage 2 measurement validation.
- **Status:** draft for independent statistical review; not yet frozen.
- **Companion documents:** [`ACTIVE_REALITY_TESTING_SPEC.md`](../animus/ACTIVE_REALITY_TESTING_SPEC.md),
  [`ART_PREREGISTRATION.md`](ART_PREREGISTRATION.md).

This plan is written before data collection. The analysis code will be frozen and hashed before the
primary analysis. Exploratory analyses are labelled as such and are not used to support confirmatory
claims.

## 1. Estimands

Let `i` index participants, `j` trials, `s_j` the true source in `(seen, imagined, described, new)`,
and `q` an evidence card.

### Primary estimands

1. **Active efficiency:** `ARTE_ij`, the normalized difference between the human cumulative EIG and a
   random-sampling baseline, divided by the greedy-EIG baseline minus the random baseline. Both
   baselines sample without replacement. `ARTE` is undefined for zero-query trials or when the full
   card set is sampled; those trials are reported as `insufficient_queries`, not imputed.
2. **Source discrimination:** `d_prime_seen_imagined` from the 2x2 seen/imagined confusion matrix.
3. **Source calibration:** Brier score for source correctness.
4. **Active benefit:** the within-person difference between active and yoked passive blocks in
   accuracy or Brier score at equal information.

### Secondary estimands

- Criterion `c` and externalization rate.
- ECE (10 equal-width bins) and overconfidence.
- Sampling quality: mean `EIG_chosen / max(EIG_available)`.
- Termination quality: residual posterior entropy at the decision.
- Number of cards sampled and cost sensitivity.
- Model-free query diagnosticity: mutual information between the chosen card and the true source.
- `meta_d_prime`, only when the trial gate is met or a hierarchical model with partial pooling is used.
- Correlation of `ARTE` with SIM, VVIQ-2, SIAQ, beads-task draws, and working memory.
- Measurement invariance across device class, order, and imagery stratum.

No composite score is estimated.

## 2. Generative model

For person `i`, source `s`, card `q`, and evidence `e_q` in `{0, 1}`:

```text
p(s | e_1..e_k) proportional to pi_s * product_q P(e_q | s, q; d_i)
P(e_q = 1 | s, q; d_i) = sigmoid(d_i * logit(p_qs))
```

The query policy uses normalized utility:

```text
u_q = beta_i * (EIG_q / max(EIG) - lambda_i * c_q)
P(q) proportional to exp(u_q)
P(stop) proportional to exp(tau_i)
```

Person-level parameters:

```text
theta_i = (d_i, bias_i, meta_d_prime_i, beta_i, lambda_i, tau_i, lapse_i)
```

Priors (weakly informative, sensitivity-tested):

```text
d_i             ~ Normal(1, 0.5), truncated above 0
bias_i          ~ Normal(0, 1)
meta_d_prime_i  ~ Normal(0, 2), truncated below 0
beta_i          ~ Normal(2, 1), truncated above 0
lambda_i        ~ Normal(0.25, 0.25), truncated below 0
tau_i           ~ Normal(-0.2, 0.5)
lapse_i         ~ Beta(2, 18)
```

Group and device effects are partial-pooled:

```text
d_i = alpha_d + beta_group[g_i] + beta_device[dev_i] + u_i
u_i ~ Normal(0, sigma_d)
```

The normalized utility is fixed before registration. A sensitivity analysis will use the raw-EIG
utility to test whether normalization drives the policy result.

### Model comparison

- equal versus unequal variance;
- shared versus source-specific criteria;
- SDT versus higher-order precision;
- EIG-cost versus fixed-threshold, heuristic, random, and confidence-in-control policies;
- ideal-observer confidence versus metacognitive-noise confidence.

Criteria: LOO/WAIC, posterior predictive checks, and parameter recovery. A complex model is retained
only if it improves out-of-sample prediction and passes recovery.

## 3. Simulation-based calibration and power

Before fitting human data:

1. Draw 1,000 parameter sets from the prior.
2. Simulate a full two-occasion session for each.
3. Fit the analysis model.
4. Compute rank statistics for each parameter.
5. Check uniformity with graphical and numerical diagnostics.

Acceptance: 95% interval coverage between 0.93 and 0.97 for the primary parameters; no systematic
rank skew. If SBC fails, the model or priors are revised before registration.

### Power

The Stage 0B power artifact uses a two-occasion ICC(2,1) with a normal-approximation lower bound. At
N=180 and 2,000 simulations, power is 0.961 for true ICC 0.75 with the lower bound above 0.60
([`results/art/ART_STAGE0_POWER.json`](../../results/art/ART_STAGE0_POWER.json)). This is a planning
approximation. The registered analysis will compute the ICC confidence interval from the observed
variance components.

For the active-versus-yoked within-person contrast, N=180 gives high power for a standardized
difference of 0.20; the pilot will estimate the variance components before the main study.

## 4. Reliability

- ICC(2,1): two-way random effects, absolute agreement, single measures.
- Report 95% CI, SEM, and MDC95.
- Primary occasion pair: day 0 and day 14.
- Reliability is estimated for `ARTE`, `d_prime`, Brier score, criterion `c`, and sampling quality.
- `meta_d_prime` reliability is reported only if the trial gate is met; otherwise `insufficient`.

Interpretation:

- ICC >= 0.75 with lower 95% CI >= 0.60: passes.
- ICC 0.60-0.75: provisional; requires revision and a second study before training.
- ICC < 0.60: fails; publish the psychometric null and stop the training program.

## 5. Validity

### Convergent and discriminant

- Pearson correlations with SIM `d_prime`, SIM `meta_d_prime`, VVIQ-2, SIAQ, and working memory.
- Fisher-z confidence intervals.
- Expected pattern: `ARTE` shows small-to-moderate associations with SIM and imagery measures;
  weaker associations with working memory; r < 0.70 with beads-task draws.
- A correlation above 0.70 with a generic source-memory task is a redundancy warning.

### Known groups

- Primary: continuous VVIQ-2 association with `ARTE`, `d_prime`, and `c`.
- Secondary: group contrasts with 95% CIs and Bayes factors.
- Exploratory: continuous LSHS-E association; no diagnostic classification, no cutoff optimization.

### Measurement invariance

- Questionnaire comparators: multigroup CFA with configural, metric, and scalar constraints.
- Behavioural model: group-specific parameters with ROPE; compare LOO or marginal likelihood.
- Criteria: Delta CFI < 0.01; Delta RMSEA < 0.015; ROPE excludes a group difference larger than
  0.20 SD.
- Device class: same procedure; if invariance fails, restrict to a single device class and report the
  restriction.

## 6. Active versus yoked

- Unit: participant-occasion.
- Outcome: accuracy, Brier score, and `ARTE`.
- Model: linear mixed-effects model with random intercepts for participant and item; fixed effects for
  block type, order, and their interaction.
- Primary contrast: active minus yoked, standardized by the within-person SD.
- Equivalence: final `d_prime` difference within +/-0.20 (TOST) to check that active selection did not
  change the construct.
- Sensitivity: exclude sessions with >20% missing trials; repeat with all sessions.
- If active is better on accuracy but not calibration, report the dissociation; do not combine into a
  single benefit claim.

## 7. Cost and reliability manipulations

- Outcome: number of cards sampled and sampling quality.
- Model: mixed-effects model with cost condition, reliability condition, and their interaction.
- Expected: more sampling under low cost; better card choice under high reliability.
- A null manipulation check blocks the "adaptive control" interpretation but not the measurement
  paper.

## 8. Model-free robustness

To avoid circularity:

- Compute `ARTE` with the model-based EIG;
- compute `sampling_quality` with mutual information between card and source, independent of the
  fitted policy;
- compute `termination_quality` from posterior entropy under the known likelihood table;
- report all three; if they diverge, the model-based result is not the sole basis for the claim.

## 9. Missing data and exclusions

- Pre-specified trial exclusions: response time <150 ms or >10 s; no response; technical failure.
- Participant exclusions: failed practice; <50% completed trials; protocol deviation.
- Missing data: FIML for the hierarchical model; multiple imputation (m=50) as a sensitivity analysis.
- Report the flow diagram and all exclusions (STROBE).
- Do not impute the primary reliability endpoints from incomplete pairs; report pairwise and
  available-case estimates.

## 10. Multiplicity

- Three primary hypotheses (H1, H2, H3); each tested at alpha = 0.05 with a confidence-interval
  decision.
- Secondary hypotheses are labelled exploratory and reported with confidence intervals; no
  family-wise claims.
- If a secondary family is treated as confirmatory in a revision, Holm correction is applied and the
  change is registered before analysis.

## 11. Blinding and multiverse

- Primary analysis blinded to block order and group labels.
- Pre-specified multiverse: model priors (three), trial exclusions (two), and ARTE baseline (greedy
  versus raw EIG).
- Report the specification curve; the primary specification is the one in this plan.
- All deviations are logged with date, reason, and blinding status.

## 12. Decision rules

| Decision | Rule |
| --- | --- |
| Measurement pass | ICC >=0.75, lower CI >=0.60; incremental validity; discriminant r<0.70 |
| Provisional | ICC 0.60-0.75; revise and replicate before training |
| Fail | ICC <0.60 or no incremental validity; publish null; stop training |
| Active benefit | Standardized difference >=0.20 or calibration advantage with CI excluding 0 |
| Policy support | EIG-cost model beats alternatives out of sample |
| Training | Only after measurement pass and separate RCT registration |
| Clinical | Blocked; separate IRB and registration |
