# Reproducibility

- Simulated providers use deterministic seeds.
- Replay sessions persist event envelopes in SQLite.
- JSONL exports preserve event order and payloads.
- CSV exports expose metric timelines and self-report rows.
- Offline evaluation CLIs can rerun scenario and cohort simulations.
- Session metadata records profile id, task id, signal provider id, simulated scenario, experiment run id, and consent acknowledgement.
- Calibration profiles record quality score, warnings, provider/scenario normalization metadata, and baseline self-report values.
- Experiment summaries aggregate linked session summaries and expose catch-trial metadata.

Example:

```bash
cd backend
python3 -m app.evaluation.scenario_runner --scenario improving_user --windows 20
python3 -m app.evaluation.cohort_simulator --n 10 --windows 20
```

Limitations: deterministic simulation is useful for engineering validation, but does not validate real imagery or EEG claims.

## Recommended Reproducible Workflow

1. Record the protocol id and experiment run id.
2. Use a named simulated scenario and deterministic seed where possible.
3. Export event JSONL and timeline CSV for every session.
4. Export the experiment summary JSON after all linked sessions complete.
5. Include the data dictionary with any shared dataset bundle.

All exported PID/IQI values remain experimental derived proxies.
