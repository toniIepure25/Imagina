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

## Research Reproducibility (v0.5.0+)

### Synthetic Dataset Generation

Generate a deterministic synthetic dataset for analysis pipeline development:

```bash
python scripts/generate_synthetic_dataset.py --n-participants 24 --seed 42 --output data/synthetic/
```

This produces `participants.csv`, `trials.csv`, and `metadata.json` with deterministic, seeded data matching the expected research schema.

### Provenance Tracking

Every trial in research mode records:
- Software version and git commit SHA
- Study ID, participant ID, session ID
- Condition assignment and trial index
- Stimulus ID and content hash
- Signal provider ID and protocol version

### Preregistration

See `docs/preregistration.md` for the study preregistration template. Complete before any data collection.

### Analysis Pipeline

The confirmatory hierarchical analysis is **executable** on synthetic data using `backend/app/research/statistics/confirmatory.py` (Python statsmodels MixedLM). The primary model formula is:

```
objective_error ~ condition + period + session_index + baseline_precision + task_family + (1 | participant)
```

The analysis pipeline includes:
- Design matrix construction (`statistics/design_matrix.py`)
- Primary confirmatory model with fallback (`statistics/confirmatory.py`)
- Holm-Bonferroni multiplicity correction (`statistics/multiplicity.py`)
- Sensitivity analyses (`statistics/sensitivity.py`)

**Status:** Executable on synthetic data. Human data analysis requires: ethics approval, human data collection, and validated psychometric properties.

### Environment Reproducibility

```bash
# Backend
cd backend
pip install -e ".[dev]"
python -m pytest app/tests/ -q

# Frontend
cd frontend
npm ci
npm run typecheck
npm test
npm run build
```

### Version Pinning

- Backend dependencies: `backend/pyproject.toml`
- Frontend dependencies: `frontend/package-lock.json`
- Python version: >= 3.10
- Node version: >= 20

## LSL Smoke Test (Experimental)

For real EEG hardware validation, a manual smoke test CLI is available:

```bash
cd backend
IMAGINA_ENABLE_EXPERIMENTAL_LSL=true python3 -m app.cli.lsl_smoke_test \
  --windows 3 --allow-experimental --output data/exports/lsl_smoke.json
```

This requires pylsl (`pip install -e ".[lsl]"`) and an active LSL stream. See `docs/lsl_integration.md` for full setup instructions. The output JSON contains no raw EEG samples — only derived proxy features.
