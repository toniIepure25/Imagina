# IMAGINA V23 — Imagery Protocol Studio + Personal Benchmark Standard

## What V23 Adds

V23 turns IMAGINA into a reusable protocol design and benchmarking framework for mental imagery training. It allows users to instantiate standardized protocols, run guided blocks, analyze results, compare protocols, and export safe benchmark packs.

## V22 vs V23

| | V22 | V23 |
|---|-----|-----|
| **Tasks** | Individual guided sessions | Protocol blocks (sequences of sessions) |
| **Design** | None | 8 built-in protocols + custom protocol creator |
| **Execution** | Manual per-session | Automated block-by-block runs |
| **Analysis** | Per-session replay | Protocol-level benchmarks |
| **Comparison** | None | Multi-protocol comparison |
| **Export** | Session replay | Benchmark export pack (5-9 files) |

## Built-in Protocol Library (8)

| Protocol | Type | Days | Focus |
|----------|------|------|-------|
| baseline_imagery_assessment_7d | assessment | 7 | Balanced across all dimensions |
| vividness_foundation_7d | training | 7 | Vividness + color control |
| stability_under_load_7d | training | 7 | Spatial stability + motion |
| detail_builder_7d | training | 7 | Detail generation |
| multisensory_integration_7d | training | 7 | Multisensory integration |
| meta_control_7d | training | 7 | Blur/refocus/switch control |
| recovery_low_fatigue_5d | recovery | 5 | Calm, low-intensity scenes |
| plateau_breaker_7d | recovery | 7 | Category switching, lower difficulty |

## Protocol Run Lifecycle

```
Instantiate → Start Run → Start Block (creates guided session)
           → Run guided session (check-ins, scene, complete)
           → Complete Block → Start Next Block → ...
           → Complete Run → Analyze Benchmark → Compare → Export
```

## Test Results

```
V23 PROTOCOL STUDIO: 8 built-in protocols ✓
  Baseline protocol: 7 blocks, 3 completed ✓
  Benchmark: IQI=0.70, fatigue=2.5, rec=stability_under_load ✓
  Comparison: 2 runs ranked ✓
  Export: 9 files, no raw EEG ✓

V13/V20/V21/V22 regression: ALL PASSED
ruff: clean, frontend: compiled, verify.sh: 7/8 pass
```

## API Endpoints Added

17 endpoints: built-in protocol library, custom protocol CRUD, run lifecycle, benchmark, comparison, export.

## Final Claim

> IMAGINA V23 turns the project into a reusable mental imagery protocol studio and benchmark framework: it defines standardized protocols, runs guided task blocks, analyzes protocol-level results, compares protocols, and exports safe benchmark packs containing protocol summaries and self-report proxy metrics only. It remains non-clinical, non-diagnostic, non-BCI, and not mind-reading.
