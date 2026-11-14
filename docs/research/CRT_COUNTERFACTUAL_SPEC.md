# CRT Dual-Hypothesis Counterfactual Specification

## Status

- **Date:** 2026-10-30.
- **Scope:** `ANIMUS-CRT-v1`, simulation-only Stage 0E.
- **Claim status:** `LIMITED`; the label "counterfactual" is provisional.
- **Fallback name if the gate remains `REVIEW`:** **prospective reality testing**.

## 1. Construct

A single prediction asks: "what will happen?" A dual prediction asks: "what would happen if the source
were seen, and what would happen if it were imagined?" The second form makes the alternative explicit
and yields a measurable **perceived diagnosticity**:

```text
p_seen(a) = P(P = 1 | a, s = seen)
p_imagined(a) = P(P = 1 | a, s = imagined)
D(a) = |p_seen(a) - p_imagined(a)|
```

`D(a)` is not the same as the model's objective `counterfactual_discrimination`. The former is the
participant's represented difference; the latter is the experimenter's likelihood difference.

## 2. Reports

For each test, the participant reports:

- a binary prediction under `seen`;
- confidence under `seen`;
- a binary prediction under `imagined`;
- confidence under `imagined`.

Derived fields:

| Field | Definition |
| --- | --- |
| `prediction_correct_seen` | `predicted_seen == outcome` |
| `prediction_correct_imagined` | `predicted_imagined == outcome` |
| `prediction_error` | `abs(p_seen - outcome)` for the primary hypothesis |
| `counterfactual_discrepancy` | `abs(p_seen - p_imagined)` |

The current implementation stores these on `TestRecord` and aggregates them in `CrtSummary`.

## 3. Model space

| Model | Prediction | Source update | Free parameters | Distinguishing signature |
| --- | --- | --- | --- | --- |
| `M0` | None | Outcome | `d`, bias, confidence | No prediction effect |
| `M1` | Precision readout only | Outcome | `d`, precision | Confidence explains attribution |
| `M2` | Single belief readout | Outcome | `d`, `pi` | Prediction tracks `q_i`; no dual advantage |
| `M3` | Dual | Outcome | `d`, `pi`, dual coupling | Discrepancy predicts test choice or accuracy |
| `M4` | Dual + error attribution | Outcome + attribution | `M3` plus attribution weights | Prediction error changes later behaviour |

The Stage 0E simulator implements the **generative** side of `M3`; it does not yet fit `M3` or estimate
its parameters.

## 4. Decision rule

The dual-prediction gate passes only if all three hold on the same fixed test sequence:

1. dual diagnostic accuracy exceeds single diagnostic accuracy by at least 0.02;
2. dual diagnostic accuracy exceeds dual non-diagnostic accuracy by at least 0.02;
3. mean counterfactual discrepancy is at least 0.05.

If any condition fails, the gate is `REVIEW` and the construct is called **prospective reality
testing** in manuscripts.

## 5. Stage 0E result

From [`CRT_STAGE0E_COUNTERFACTUAL.json`](../../results/crt/CRT_STAGE0E_COUNTERFACTUAL.json):

- Mean discrepancy: `0.475993` (large).
- Dual gain over single: `0.000000`.
- Specificity gain over dual non-diagnostic: `0.036806`.
- Decision: `CRT_STAGE0E_COUNTERFACTUAL_REVIEW`.

Interpretation: participants can represent two hypotheses, but the dual report does not change source
accuracy on the fixed sequence. The discrepancy is a **report-level** variable, not yet a behavioural
advantage.

## 6. Why the fixed sequence matters

The fixed-sequence design isolates prediction content from test selection. If dual prediction improves
accuracy only by changing which tests are selected, the fixed-sequence gate will miss it. That is why
the next experiment must add a **policy-level** dual manipulation:

- dual prediction before choosing a test;
- single prediction before choosing a test;
- non-diagnostic prediction before choosing a test;
- same test menu and cost structure.

The policy-level test asks whether counterfactual representation changes inquiry, not just report
content.

## 7. Measurement model

A future hierarchical model should include:

```text
D_ij = D_true,j + e_ij
logit(P(correct_seen_ij)) = alpha_j + beta * D_ij + ...
logit(P(correct_imagined_ij)) = alpha_j - beta * D_ij + ...
```

where `j` indexes participants and `i` indexes tests. The key parameter is whether `D` predicts
out-of-sample source accuracy or test choice after controlling for `d'`, confidence, and working
memory. The current simulation does not estimate this model.

## 8. Limitations

- The dual report may be a demand characteristic: asking for two predictions can induce a strategy that
  is not used spontaneously.
- The fixed sequence removes the policy channel.
- The simulation uses the same likelihood table for both hypotheses; human participants may use
  different forward models for seen and imagined sources.
- No parameter recovery or model comparison has been run for `M3`/`M4`.
- The label "counterfactual" is not earned by a large discrepancy alone.

## 9. Next step

Implement `M3`/`M4` fitting, run parameter and model recovery, and test a policy-level dual
manipulation. Only then decide whether to keep the counterfactual label.
