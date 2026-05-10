# Real Data Readiness Checklist

Before running IMAGINA with real EEG data, verify each item.

## File Verification
- [ ] Real EEG file exists (`.fif`, `.edf`, `.bdf`, `.vhdr`, or `.set`)
- [ ] File size is below disk budget (recommended < 3 GB)
- [ ] File extension is supported by IMAGINA loaders
- [ ] MNE can open the file: `python3 -c "import mne; mne.io.read_raw_fif('file.fif', preload=False).info"`
- [ ] File is NOT in a git-tracked directory
- [ ] `data/external/` is gitignored (confirmed in `.gitignore`)

## Import
- [ ] Run: `python3 -m app.cli.dataset_manager import-local --dataset <name> --path <file> --copy --overwrite`
- [ ] Import exits with code 0
- [ ] Manifest at `data/external/<name>/manifest.json` exists
- [ ] Manifest `real_signal` is `true`
- [ ] Manifest `raw_persisted` is `false`
- [ ] Import report at `data/external/<name>/import_report.json` exists
- [ ] Import report `success` is `true`
- [ ] Sampling rate, channel count, and duration are populated

## Evaluation
- [ ] Run: `python3 -m app.cli.dataset_eval --dataset <name> --max-windows 50 --compute-pid-iqi --compare fixture --distribution-report --export-features-csv`
- [ ] Eval exits cleanly
- [ ] Eval report has `fallback_used: false`
- [ ] Eval report has `real_signal: true`
- [ ] Distribution report generated
- [ ] CSV export generated
- [ ] Comparison report shows differences vs fixture

## Signal Quality
- [ ] Run: `python3 -m app.cli.dataset_quality --dataset <name> --max-windows 50`
- [ ] Quality score is within reasonable range
- [ ] Warnings reviewed: `low_signal_quality`, `high_missing_data`, `high_clipping`, `high_muscle_noise`

## Privacy
- [ ] CSV export contains NO raw EEG samples
- [ ] Distribution report contains NO raw EEG samples
- [ ] Eval report contains NO raw EEG samples
- [ ] All reports use derived proxy features only
- [ ] Raw EEG file remains only in `data/external/<name>/raw/` (gitignored)

## Scientific Boundaries
- [ ] No clinical claims in any output
- [ ] No mind-reading, dream-decoding, diagnosis, or treatment claims
- [ ] All outputs use "experimental proxy features" language
- [ ] Reports include scientific disclaimer

## Acceptance
- [ ] 162+ tests pass: `cd backend && python3 -m pytest app/tests/ -q`
- [ ] `scripts/verify.sh` passes
- [ ] All evaluation CLIs run without error
