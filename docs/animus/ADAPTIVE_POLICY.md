# Adaptive Policy — coverage floor, then expected information gain

**Status:** experimental heuristic, `ANIMUS-ADAPTIVE-v1`.
**Scope:** local practice task selection. Not a validated computerized-adaptive-testing model and not a
learning-rate estimate.

## Selection order

1. **Trial 0:** `object_reconstruction` (stability) as a reconstruction warmup.
2. **Trial 1:** `attribute_recall` (stability) as a confidence warmup.
3. **Coverage floor:** if any selectable dimension has `n < 2`, choose the sparsest one.
4. **Information gain:** otherwise choose the dimension with the highest expected reduction in outcome
   entropy, using the Beta posterior and the current difficulty.
5. **Difficulty:** independent challenge-point controller; moves by at most `0.08` and stays within
   `[0.1, 0.9]`.

Calibration is **not** a selectable dimension. Every trial updates it because confidence is recorded before
feedback. This prevents the policy from spending trials on “calibration practice” while ability dimensions
remain unmeasured.

## Expected information gain

For Beta parameters `(alpha, beta)`:

```text
p = sigmoid(logit(alpha / (alpha + beta)) + (0.5 - difficulty) * 2)
H(p) = -p ln p - (1-p) ln(1-p)
p_correct = (alpha + 1) / (alpha + beta + 1)
p_incorrect = alpha / (alpha + beta + 1)
gain = H(p) - [p * H(p_correct) + (1-p) * H(p_incorrect)]
```

The mean is clamped to `[0.02, 0.98]` so the logarithm is defined. The result ranks dimensions; it is not
shown as a score in the UI. `adaptive.expected_gain` is available for audit and tests.

## Why not a fixed curriculum

A fixed cycle guarantees coverage but may spend trials on dimensions whose posterior is already narrow.
Pure information gain can neglect a dimension with little evidence. The coverage floor is the guardrail;
information gain is the efficiency step. The design analogy is multidimensional adaptive testing with
uncertainty (Fink, König & Frey, 2026), but that simulation is not evidence that this policy improves human
measurement.

## Difficulty controller

```text
mean = average of the last up to five scores
if mean >= 0.8: +0.08
if mean <= 0.5: -0.08
otherwise: unchanged
clamp to [0.1, 0.9]
```

Scores are reconstruction F1 or spatial accuracy on `[0, 1]`. The controller is deliberately conservative;
it is not a staircase with a target success threshold.

## Failure handling

- If a reconstruction task cannot be generated, the server falls back to a legacy task for that dimension.
- If the next task cannot be built after a saved trial, the trial remains saved and `next_task` is null.
- If a client retries the same `client_trial_id`, the saved trial is returned and `next_task` is null; the
  client can request a new start rather than duplicating evidence.

## Simulation

`backend/app/evaluation/animus_instrument_sim.py` compares:

- `coverage_first`: least-sampled dimension;
- `information_gain`: the policy above;
- `fixed_cycle`: round-robin.

It reports RMSE against known synthetic probabilities, coverage, mean uncertainty, and Brier score. Results
are synthetic policy mechanics only. They must not be presented as human validation or as a training effect.

## Open questions

- Is `n < 2` the right coverage floor?
- Should difficulty be optimized jointly with dimension selection?
- Does information gain improve precision when task scores are noisy or multidimensional?
- Do reconstruction trials show practice effects that the controller would misinterpret as ability change?
- Does the policy behave fairly across users with different baseline performance? No norms or fairness
  claim is made.
