# Offline Evaluation

The evaluation harness checks whether simulated proxy metrics behave logically before real EEG integration.

Available tools:

- `scenario_runner`: runs one scenario and emits metric timeline JSON.
- `cohort_simulator`: runs multiple seeded users and aggregates slopes, fatigue warnings, and level distribution.
- `metric_sanity`: helper summaries for expected trends.
- `replay_validator`: validates event order and replay coverage.

Expected sanity patterns:

- `improving_user`: IQI should generally increase and PID should generally decrease.
- `noisy_signal`: uncertainty should be elevated.
- `fatigue_after_half`: fatigue warnings should become more likely.

