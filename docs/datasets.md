# Dataset Integration

## Overview

IMAGINA V2.2 adds dataset-backed validation using public EEG datasets. This is **experimental** — not clinical, not thought decoding.

> **Disclaimer:** Dataset-derived features are experimental proxy estimates. They do not represent clinical EEG interpretation, decoded mental content, or validated biomarkers.

## Available Datasets

| ID | Name | Source | Status |
|----|------|--------|--------|
| `yoto` | YOTO ds005815 | OpenNeuro | metadata available (manual download required) |
| `openmiir` | OpenMIIR | GitHub (sstober/openmiir) | metadata available (manual download required, ~0.7 GB/subject) |
| `fixture` | IMAGINA Synthetic Fixture | local | available |

> **Note:** Previous V2.2 implementation incorrectly marked YOTO and OpenMIIR as permanently unreachable due to brittle/incorrect URL checks. V2.2.1 corrects this: both datasets are now known to exist with reachable metadata pages, but automated subset download requires additional tooling (OpenNeuro API, direct file URLs, or manual acquisition).

## Fixture Fallback

Both real datasets are available for manual acquisition but cannot be auto-downloaded in this environment. A **synthetic 4-channel 256Hz fixture** is provided for pipeline validation. Run `--dataset yoto --fallback fixture` to request a real dataset but fall back to synthetic data when it's unavailable.

### Fixture manifest

The fixture manifest (in `data/external/fixture_manifest.json`) records:
- dataset name, source
- fallback reason (exact HTTP 404 details)
- acquisition method: "fixture"
- windows generated, sampling rate, channel count

## Real Dataset Acquisition (V2.3)

Automatic acquisition was attempted for YOTO and OpenMIIR. All mirrors failed (HTTP 404, timeout, torrent-only). See `data/external/openmiir/acquisition_report.json` for details.

**Current status**: Fixture fallback is used. Real EEG must be manually acquired.

### Manual Import (Recommended Path)

1. Download one OpenMIIR subject via Academic Torrents:
   ```
   Magnet: magnet:?xt=urn:btih:c18c04a9f18ff7d133421012978c4a92f57f6b9c
   ```
2. Place `.fif` file in `backend/data/external/openmiir/raw/`
3. Import:
   ```bash
   python3 -m app.cli.dataset_manager import-local \
     --dataset openmiir --path data/external/openmiir/raw/<file>.fif \
     --copy --overwrite --notes "manual OpenMIIR import"
   ```
4. Evaluate:
   ```bash
   python3 -m app.cli.dataset_eval --dataset openmiir --max-windows 50 \
     --compute-pid-iqi --compare fixture --distribution-report --export-features-csv
   ```
5. See `docs/real_data_readiness_checklist.md` for full verification.

## Dataset Replay Provider

Provider ID: `dataset.replay`

Replays pre-loaded dataset windows through the closed-loop pipeline. Works with fixture data now; will work with real datasets when available.

## Evaluation CLI

```bash
# Evaluate fixture
python3 -m app.cli.dataset_eval --dataset fixture --max-windows 50

# Evaluate with PID/IQI proxies
python3 -m app.cli.dataset_eval --dataset fixture --max-windows 50 --compute-pid-iqi

# Output: data/exports/dataset_eval_fixture.json
```

## Privacy

- Dataset files are stored in `data/external/` (gitignored).
- No raw EEG samples are persisted to the event store or reports.
- FeatureVectors contain derived bandpower/artifact features only.
- Reports/exports use proxy/estimate language.
