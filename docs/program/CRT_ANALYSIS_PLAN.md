# CRT Statistical Analysis Plan (DRAFT)

## Status

- **Version:** 0.2, 2026-10-30.
- **Applies to:** `ANIMUS-CRT-v1`, Stage 0D design controls and Stage 1 measurement validation.
- **Status:** draft for independent statistical review; not yet frozen.
- **Companion documents:** [`COUNTERFACTUAL_REALITY_TESTING_SPEC.md`](../animus/COUNTERFACTUAL_REALITY_TESTING_SPEC.md),
  [`CRT_PREREGISTRATION.md`](CRT_PREREGISTRATION.md).

This plan is written before data collection. The analysis code will be frozen and hashed before the
primary analysis. Exploratory analyses are labelled as such and are not used to support confirmatory
claims.

## 1. Estimands

Let `i` index participants, `j` trials, `s_j` the true source in `(seen, imagined, described, new)`,
`a_j` a selected test, `P_j` the predicted outcome, and `O_j` the observed outcome.

### Primary estimands

1. **Prediction advantage:** the within-person difference between `active_predict` and
   `active_intervene` in source accuracy, standardized by the within-person SD.
2. **Meta-information efficiency:** `CRTE_meta_ij`, the normalized difference between the human
   cumulative meta-EIG and a random-sampling baseline, divided by the greedy meta-EIG baseline minus
   the random baseline. Both baselines sample without replacement. `CRTE_meta` is undefined for
   zero-test trials or when the full test set is sampled; those trials are reported as
   `insufficient_tests`, not imputed.
3. **Prediction calibration:** `prediction_ece` over all prediction-confidence bins.
4. **Source discrimination:** `d_prime_seen_imagined` from the 2x2 seen/imagined confusion matrix.
5. **Source calibration:** Brier score for source correctness.
6. **Specificity advantage (Stage 1C):** diagnostic minus matched non-diagnostic prediction in source
   accuracy, under a fixed test sequence. This is the primary test of whether the prediction effect is
   specific to source-diagnostic content.

### Secondary estimands

- `CRTE_eig`, `active_calibration_advantage`, `active_accuracy_advantage`.
- Active-selection advantage (Stage 1B): active minus random-passive accuracy, with algorithm-adaptive
  minus random-passive as the adaptive-design benchmark.
- Criterion `c` and externalization rate.
- ECE (10 equal-width bins) and overconfidence.
- `imagination_inflation_rate`: seen attribution after a high-confidence, prediction-consistent
  imagined experience.
- `confounded_test_rate`: proportion of fluency choices.
- Sampling quality: mean `EIG_meta_chosen / max(EIG_meta_available)`.
- Termination quality: residual posterior entropy at the decision.
- Number of tests and cost sensitivity.
- Model-free test diagnosticity: mutual information between the chosen test and the true source.
- `meta_d_prime`, only when the trial gate is met or a hierarchical model with partial pooling is used.
- Correlation of `CRTE_meta` with SIM/ART measures, VVIQ-2, SIAQ, beads-task draws, and working memory.
- Measurement invariance across device class, order, and imagery stratum.

No composite score is estimated.

## 2. Generative model

For person `i`, source `s`, test `a`, outcome `O` in `{0,1}`, and prediction `P` in `{0,1}`:

```text
P(O = 1 | s, a; d_i) = sigmoid(d_i * logit(p_as))
q_i(a) = sum_s m_i(s) * p_as
P(P = 1 | a, m_i; pi_i) = sigmoid(pi_i * logit(q_i(a)))
```

The prediction is a **belief-based posterior predictive readout**, not a likelihood conditioned on the
hidden source. The source update after an outcome is:

```text
log p(s | O, a) proportional to log prior_s + log P(O | s, a; d_i)
```

The prediction does **not** enter the source likelihood. This is the Stage 0E repair: a prediction
generated from `m_i` cannot be counted again as independent evidence. The seen-response bias `b_pi`
is applied only at the final source-choice stage, not to the sequential source posterior.

The oracle variant, retained only as a benchmark, replaces `q_i(a)` with
`P(P = 1 | s_true, a; pi_i)`. Any result from that variant is reported as an oracle upper bound, with
`oracle_inflation = advantage_oracle - advantage_belief`.

An optional `M4` error-attribution extension may let prediction error change **later** test selection
or confidence. It must not add the prediction as a second likelihood for the current source.

The test policy uses normalized meta-EIG:

```text
u_a = beta_i * (EIG_meta(a) / max(EIG_meta) - lambda_i * cost(a) - gamma_i * complexity(a))
      + alpha_i * agency(a)
P(a) = mixture of softmax(u) and positive-testing softmax
P(stop) proportional to exp(tau_i)
```

Person-level parameters:

```text
theta_i = (d_i, pi_i, b_pi_i, beta_i, lambda_i, gamma_i, tau_i, guess_i, bias_i, mix_i, alpha_i,
           lapse_i)
```

Priors (weakly informative, sensitivity-tested):

```text
d_i             ~ Normal(1, 0.5), truncated above 0
pi_i            ~ Normal(1.2, 0.5), truncated above 0
b_pi_i          ~ Normal(0.2, 0.15), truncated above 0
beta_i          ~ Normal(2, 1), truncated above 0
lambda_i        ~ Normal(0.25, 0.25), truncated below 0
gamma_i         ~ Normal(0.2, 0.2), truncated below 0
tau_i           ~ Normal(-0.2, 0.5)
guess_i         ~ Beta(2, 18)
bias_i          ~ Beta(2, 8)
mix_i           ~ Beta(2, 2)
alpha_i         ~ Normal(0.5, 0.5), truncated above 0
lapse_i         ~ Beta(2, 18)
```

Group and device effects are partial-pooled:

```text
d_i = alpha_d + beta_group[g_i] + beta_device[dev_i] + u_i
u_i ~ Normal(0, sigma_d)
```

The normalized meta-EIG utility is fixed before registration. A sensitivity analysis will use raw
meta-EIG.

### Nested-model test

`pi = 0` makes the prediction independent of the source, so CRT reduces to ART/AgRT. The analysis
reports the posterior of `pi` and the LOO/WAIC difference between the full model and the nested model.
A non-zero `pi` is necessary but not sufficient for a prediction-specific claim.

### Model comparison

- equal versus unequal variance;
- shared versus source-specific criteria;
- SDT versus higher-order precision;
- meta-EIG versus outcome-EIG, positive-testing, fixed, heuristic, random, and agency policies;
- ideal-observer confidence versus metacognitive-noise confidence;
- with and without the `b_pi` imagination-inflation term.

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

The Stage 0C power artifact uses a two-occasion ICC(2,1) with a normal-approximation lower bound. The
Stage 0D planning check at N=240 gives power 0.949 for true ICC 0.80 with the lower bound above 0.70
([`results/crt/CRT_STAGE0D_GTHEORY.json`](../../results/crt/CRT_STAGE0D_GTHEORY.json)). The earlier
N=180 / ICC 0.75 / lower-bound 0.60 run is retained in
[`results/crt/CRT_STAGE0_POWER.json`](../../results/crt/CRT_STAGE0_POWER.json) as historical planning
evidence. Both are approximations; the registered analysis will compute the ICC confidence interval
from the observed variance components.

For the prediction contrast, N=240 gives high power for a standardized difference of 0.20; the pilot
will estimate the variance components before the main study. The Stage 0C simulation is a design
check, not a human effect-size estimate.

## 4. Reliability

- ICC(2,1): two-way random effects, absolute agreement, single measures.
- Report 95% CI, SEM, and MDC95.
- Primary occasion pair: day 0 and day 14.
- Reliability is estimated for `CRTE_meta`, `prediction_advantage`, `d_prime`, Brier score, criterion
  `c`, and sampling quality.
- `meta_d_prime` reliability is reported only if the trial gate is met; otherwise `insufficient`.

Interpretation:

- ICC >= 0.80 with lower 95% CI >= 0.70: passes for group-level use.
- ICC 0.70-0.80: provisional; requires revision and a second study before training.
- ICC < 0.70: fails; publish the psychometric null and stop the training program.
- Individual-level use requires ICC >= 0.90 and is not planned.

### Generalizability theory

- Design: persons crossed with occasions; report person, occasion, and residual variance components.
- Compute relative and absolute reliability, SEM, and MDC95 for one to four occasions.
- The decision study asks whether two occasions meet the group-level target and how many occasions would
  be needed for individual-level use.
- Negative variance components are set to zero for reporting but flagged; a zero occasion component is
  not evidence that occasion effects are absent.
- Stage 0D is a simulation illustration. The human study estimates the components from observed data.

## 5. Primary contrasts

### Prediction advantage

- Unit: participant-occasion.
- Outcome: source accuracy and Brier score.
- Model: linear mixed-effects model with random intercepts for participant and item; fixed effects for
  prediction condition, agency condition, order, and their interaction.
- Primary contrast: `active_predict` minus `active_intervene`, standardized by the within-person SD.
- Equivalence: final `d_prime` difference within +/-0.20 (TOST) to check that prediction did not change
  the source construct.
- Sensitivity: exclude sessions with >20% missing trials; repeat with all sessions.
- If prediction improves accuracy but not calibration, report the dissociation; do not combine into a
  single benefit claim.

### Meta-EIG policy

- Fit the hierarchical policy model with LOO/WAIC.
- Compare meta-EIG, outcome-EIG, positive-testing, fixed, heuristic, random, and agency policies.
- Primary evidence: out-of-sample expected log predictive density advantage of meta-EIG over the best
  alternative.
- Report the posterior of `pi` and the nested-model comparison.

### Prediction calibration

- `prediction_ece` with 10 equal-width bins and bootstrap CI.
- Reliability diagram and overconfidence by condition.
- Sensitivity: equal-mass bins; logit-scaled calibration slope and intercept.

### Specificity analysis

- Contrast: `active_predict_diagnostic` minus `active_predict_nondiagnostic`.
- Unit: participant-occasion; outcome: source accuracy.
- The non-diagnostic arm is matched on prediction format, confidence report, fixed test sequence, test
  count, cost, and time. The fixed sequence prevents a test-selection difference from masquerading as a
  prediction-specificity effect.
- Supported specificity requires a positive accuracy contrast with a 95% CI excluding zero and a
  diagnostic prediction accuracy above chance.
- A null or negative contrast rejects the counterfactual-prediction interpretation, even if the generic
  prediction arm beats outcome-only testing.
- Brier score and ECE are descriptive secondary outcomes; they are not used to rescue a failed accuracy
  specificity contrast.

### Test-likelihood calibration

- Before the confirmatory study, a separate calibration sample estimates the six test likelihoods with a
  hierarchical Beta-Binomial model.
- The fitted table is frozen and hashed. The confirmatory analysis uses the frozen table, not
  participant-specific re-estimation.
- Tests with a seen-versus-imagined likelihood ratio inside `[0.75, 1.33]` are dropped or redesigned.
- The fluency test must remain non-diagnostic; a strong fluency likelihood ratio is a calibration
  failure and triggers a task review.
- Stage 0D is a simulated calibration design only; it does not replace the human calibration sample.

### Imagination inflation

- Outcome: seen attribution on imagined trials with a prediction-consistent high-confidence outcome.
- Model: mixed-effects logistic regression with random intercepts for participant and item; fixed
  effects for prediction consistency, prediction confidence, source confidence, guessing, and response
  bias.
- Primary contrast: prediction-consistent minus prediction-inconsistent imagined trials.
- Report the `b_pi` posterior and a sensitivity analysis that fixes `b_pi = 0`.

## 6. Active selection and controls

- Unit: participant-occasion.
- Outcome: accuracy, Brier score, and `CRTE_meta`.
- Model: linear mixed-effects model with random intercepts for participant and item; fixed effects for
  condition, order, and their interaction.
- **Primary selection contrast:** active prediction minus random-passive exposure, standardized by the
  within-person SD.
- **Adaptive-design contrast:** algorithm-adaptive selection minus random-passive exposure. This
  separates the value of adaptive test choice from the value of human choice.
- **Identification limitation:** matched-sequence yoking gives both arms the same test distribution.
  Accuracy and calibration differences are expected to be near zero. Yoked contrasts are retained as a
  manipulation check, not as the selection estimand.
- If active is better on accuracy but not calibration, report the dissociation; do not combine into a
  single benefit claim. If algorithm-adaptive selection beats active choice, report that human choice is
  suboptimal rather than treating the control as failed.

## 7. Cost, complexity, and reliability manipulations

- Outcome: number of tests, sampling quality, and meta-EIG efficiency.
- Model: mixed-effects model with cost condition, complexity condition, reliability condition, and
  their interactions.
- Expected: more sampling under low cost; better test choice under high reliability; lower choice of
  high-complexity tests under high complexity.
- A null manipulation check blocks the "adaptive control" interpretation but not the measurement
  paper.

## 8. Model-free robustness

To avoid circularity:

- Compute `CRTE_meta` with the model-based meta-EIG;
- compute `sampling_quality` with mutual information between test and source, independent of the fitted
  policy;
- compute `termination_quality` from posterior entropy under the known likelihood table;
- compute `confounded_test_rate` from the fluency trap;
- report all four; if they diverge, the model-based result is not the sole basis for the claim.

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

- Primary analysis blinded to cell order and group labels.
- Pre-specified multiverse: model priors (three), trial exclusions (two), and `CRTE_meta` baseline
  (greedy versus raw meta-EIG).
- Report the specification curve; the primary specification is the one in this plan.
- All deviations are logged with date, reason, and blinding status.

## 12. Decision rules

| Decision | Rule |
| --- | --- |
| Measurement pass | ICC >=0.80, lower CI >=0.70; prediction advantage; incremental validity; discriminant r<0.70 |
| Provisional | ICC 0.70-0.80, or prediction advantage without calibration; revise and replicate |
| Fail | ICC <0.70 or no prediction advantage; publish null; stop training |
| Prediction support | Standardized difference >=0.20 or calibration advantage with CI excluding 0 |
| Policy support | Meta-EIG model beats alternatives out of sample |
| Specificity support | Diagnostic prediction beats matched non-diagnostic prediction; 95% CI excludes zero |
| Active selection | Active beats random-passive; algorithm-adaptive is a benchmark, not a failed control |
| Training | Only after measurement pass and separate RCT registration |
| Clinical | Blocked; separate IRB and registration |

## 13. Stage 0C, 0D, and 0E caveats

- The Stage 0C simulation fixes `alpha`, `d`, `guess`, and `bias` for recovery. The human analysis
  estimates them hierarchically.
- Prediction-precision recovery in Stage 0C used the known simulated source as an oracle
  identifiability check. The Stage 0E repair replaces that with a belief-based posterior predictive
  readout and an outcome-only source update. The oracle path is retained only as a benchmark.
- Stage 0E shows the Stage 0D specificity result does not survive belief-based prediction: diagnostic
  prediction accuracy is 0.505 (below the 0.55 floor) and the source accuracy gain is 0.026 over a
  0.374 non-diagnostic baseline. The specificity gate is downgraded to `LIMITED`.
- Stage 0E dual prediction has a large discrepancy (0.476) but no accuracy gain over single prediction
  on the fixed sequence. The "counterfactual" label is provisional.
- Stage 0E meta-EIG beats cost-only by 0.060 but loses to the best competing policy by 0.012. The
  normative policy claim is downgraded to descriptive.
- The Stage 0E posterior PIT check is not full hierarchical SBC. It tests the assumed generative model,
  not the human likelihood table.
- `b_pi` is the least precisely recovered Stage 0C parameter (full-run bias 0.010, RMSE 0.105). It is
  a secondary parameter and must be interpreted with SBC and sensitivity analyses.
- The Stage 0C active-versus-yoked calibration contrast is near zero under matched-sequence yoking.
  This is a design identification result, not a human null.
- Stage 0D model signatures are design hypotheses, not human model evidence. The tournament does not fit
  the models to human data.
- Stage 0D specificity Brier and calibration gains are negative because the non-diagnostic arm is
  constructed to be source-neutral, not confidence-matched. Accuracy is the gate; Brier and ECE are
  descriptive.
- Stage 0D algorithm-adaptive selection beats active choice in simulation. That is a benchmark result,
  not evidence that human choice is useless.
- No Stage 0C or Stage 0D result is human evidence, and no claim is upgraded by a simulation PASS or
  REVIEW.
