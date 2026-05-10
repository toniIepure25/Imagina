# LSL Integration Guide

## Overview

IMAGINA V2.1 supports optional real EEG integration via Lab Streaming Layer (LSL). This is **experimental** and not required for normal operation.

> **Disclaimer:** LSL integration is experimental. It does not decode thoughts or dreams, provide clinical neurofeedback, or clinically validate EEG biomarkers. All derived features are proxy estimates for engineering validation only.

## Prerequisites

- Python 3.10+
- liblsl system library (required by pylsl)
- An LSL-compatible stream source (e.g., Muse with a streaming app, OpenBCI, or a signal generator like `lsl.example`)

## Optional Installation

```bash
# Install IMAGINA with LSL support
pip install -e ".[dev,lsl]"

# Or just the LSL dependency alone
pip install -e ".[lsl]"
```

Without the `[lsl]` extra, the `lsl.real` provider reports as unavailable and cannot be used.

## Running the LSL Smoke Test

1. Ensure an LSL stream is active (e.g., Muse, OpenBCI, or a test signal generator).

2. Enable experimental LSL and run the smoke test:

```bash
# Enable via environment variable (recommended)
IMAGINA_ENABLE_EXPERIMENTAL_LSL=true python3 -m app.cli.lsl_smoke_test --windows 3 --allow-experimental

# Or bypass env var with just the flag
IMAGINA_ENABLE_EXPERIMENTAL_LSL=true python3 -m app.cli.lsl_smoke_test --windows 3 --allow-experimental --stream-name "Muse-ABCD"
```

3. The smoke test will:
   - Check pylsl availability
   - Discover LSL streams
   - Connect to the first EEG stream (or specified stream)
   - Collect N windows (default 3)
   - Print FeatureVector summaries
   - Write a JSON smoke report to `data/exports/lsl_smoke_test_<timestamp>.json`

4. Examine the JSON report for feature quality, artifact scores, and any errors.

## JSON Report Format

The report contains:
- Stream metadata (name, type, channel count, sampling rate)
- Provider health (before and after collection)
- Feature summaries per window (bandpower, artifacts, signal quality)
- Errors and warnings
- **No raw EEG samples** — only derived proxy features

## Privacy and Safety

- **No raw EEG persistence**: Raw samples are transient in memory and never saved to disk or SQLite.
- **Local-first**: All data stays on the local machine.
- **No external transmission**: No cloud sync, no telemetry.
- **Experimental**: Derived features are proxy estimates, not clinical EEG metrics.

## LSL Stream Discovery

LSL may discover streams on the local machine or local network depending on configuration. IMAGINA remains local-first and does not upload EEG data.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `pylsl is not installed` | Run `pip install -e ".[lsl]"` |
| `No LSL streams found` | Ensure an LSL stream is active. Try `lsl.example` or your device's streaming app. |
| `Stream timeout` | Increase timeout: `--timeout 10`. Check stream stability. |
| `Low signal quality` | Check electrode contact. Dry EEG has inherently low SNR. |
| `Window collection failed` | Stream may have disconnected. Restart the stream and retry. |
| `Experimental LSL is not enabled` | Use `--allow-experimental` or set `IMAGINA_ENABLE_EXPERIMENTAL_LSL=true`. |

## Integration Status

- **Phase 2**: Provider skeleton (discovery, health)
- **Phase 3A**: Mocked window collection + FeatureEngine DSP
- **Phase 3A.5**: End-to-end mocked flow validated
- **Phase 3B**: **Current** — smoke test CLI, manual validation
- **Future**: Frontend integration, calibration with real EEG, improved DSP
