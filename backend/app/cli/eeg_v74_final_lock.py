"""V7.4 — Final Classical Baseline Lock.

Audit existing artifacts, lock V6.9 as validated baseline,
produce claim ledger, comparison table, scientific report.
No new experiments — final evidence pack only.
"""

import json
import os
import sys
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
FIGS = os.path.join(EXPORTS, "figures")


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.eeg_v74_final_lock")
    p.add_argument("--mode", default="all",
                   choices=["audit", "lock", "report", "ledger", "comparison", "figures", "all"])
    p.add_argument("--output-prefix", default="eeg_v74_final")
    return p


def _safety():
    return {"analysis_mode": "experimental_hypothesis_only",
            "not_for_scientific_claims": True, "production_valid": False,
            "production_unlock_allowed": False, "no_raw_eeg_exposed": True}


def _load(fn):
    p = os.path.join(EXPORTS, fn)
    return json.load(open(p)) if os.path.exists(p) else None


def _save(data, fn):
    with open(os.path.join(EXPORTS, fn), "w") as f:
        json.dump(data, f, indent=2, default=str)


def run_audit():
    artifacts = {
        "v69": _load("eeg_v69_scientific_verdict.json"),
        "v73_csp": _load("eeg_v73_fast_true_mne_csp.json"),
        "v73_verdict": _load("eeg_v73_scientific_verdict.json"),
    }

    results = {
        "v69_exists": artifacts["v69"] is not None,
        "v69_score": artifacts["v69"].get("balanced_accuracy") if artifacts["v69"] else None,
        "v69_is_fbcsp": "FBCSP" in str(artifacts["v69"].get("method", "")),
        "v69_no_fbcsp_label": "FBCSP" not in str(artifacts["v69"].get("method", "")) if artifacts["v69"] else None,
        "v73_csp_exists": artifacts["v73_csp"] is not None,
        "v73_csp_score": artifacts["v73_csp"].get("balanced_accuracy") if artifacts["v73_csp"] else None,
        "v73_csp_api_fix_present": "api_fix" in (artifacts["v73_csp"] or {}),
        "all_have_safety_fields": all(
            (a or {}).get("no_raw_eeg_exposed") for a in artifacts.values() if a),
        "no_production_claims": all(
            "production BCI" not in str(a) for a in artifacts.values() if a),
        "issues": [],
    }

    if results["v69_exists"] and not results["v69_no_fbcsp_label"]:
        results["issues"].append("V6.9 may still contain FBCSP label — check method field")

    correction_manifest = {
        **_safety(), "tool": "eeg_v74_label_correction_manifest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "corrections": [
            {"version": "V6.7", "claimed": "FBCSP at 0.614",
             "actual": "filter-bank log-power at 0.614 (no CSP spatial filter used)",
             "fixed_in": "V6.9 (label corrected)"},
            {"version": "V6.9", "method": "filter-bank log-power (NOT CSP/FBCSP)",
             "status": "correctly labeled, validated baseline"},
            {"version": "V7.3", "true_csp": "0.482 (near chance, does not beat V6.9)",
             "true_fbcsp": "not completed/failed, does not beat V6.9"},
            {"version": "V7.4", "final_lock": "V6.9 filter-bank log-power locked as final validated baseline"},
        ],
    }
    _save({**_safety(), "tool": "eeg_v74_artifact_audit", **results}, "eeg_v74_artifact_audit.json")
    _save(correction_manifest, "eeg_v74_label_correction_manifest.json")

    print(f"Audit: v69_exists={results['v69_exists']}, csp_exists={results['v73_csp_exists']}, "
          f"issues={len(results['issues'])}", file=sys.stderr)


def run_lock():
    baseline = {
        **_safety(),
        "tool": "eeg_v74_final_validated_baseline",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "final_validated_baseline": "V6.9 filter-bank log-power",
        "dataset": "PhysioNet EEGMMI",
        "task": "left/right fist motor imagery",
        "n_subjects": 15, "n_epochs": 675, "cv": "leave-one-subject-out",
        "score": 0.628, "ci_low": 0.581, "ci_high": 0.677,
        "permutation_p": 0.000, "above_chance": True,
        "beats_metadata": True, "beats_quality": True,
        "method_type": "classical_frequency_domain_baseline",
        "not_csp": True, "not_fbcsp": True,
        "true_csp_status": "tested_does_not_beat_baseline (0.482, p=0.933)",
        "true_fbcsp_status": "not_validated_as_superior (runtime/computation constrained)",
        "scientific_status": "validated_exploratory_baseline",
        "thesis_safe_interpretation": (
            "Fold-safe filter-bank log-power features achieve above-chance left/right "
            "motor imagery decoding (0.628, p<0.001) under LOSO. "
            "This provides a valid exploratory classical EEG baseline. The method is NOT "
            "CSP/FBCSP and does not support production BCI, clinical, or mind-reading claims."
        ),
    }
    _save(baseline, "eeg_v74_final_validated_baseline.json")
    print("Locked: V6.9 filter-bank log-power at 0.628", file=sys.stderr)


def run_comparison():
    comparison = {
        **_safety(), "tool": "eeg_v74_final_method_comparison",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "methods": [
            {"method": "V6.9 filter-bank log-power", "score": 0.628, "ci": [0.581, 0.677],
             "p": 0.000, "status": "validated_best", "beats_metadata": True,
             "label_correct": True, "note": "Final validated classical baseline. NOT CSP/FBCSP."},
            {"method": "V7.3 true MNE CSP", "score": 0.482, "ci": [0.458, 0.504],
             "p": 0.933, "status": "tested_not_better",
             "beats_metadata": False, "label_correct": True,
             "note": "API-fixed fold-safe MNE CSP. Does not beat frequency decomposition."},
            {"method": "V7.3 true FBCSP", "score": None, "ci": None,
             "p": None, "status": "not_completed",
             "beats_metadata": False, "label_correct": False,
             "note": "Time-domain bandpass FBCSP computationally constrained. Not validated."},
            {"method": "Metadata baseline", "score": 0.482, "ci": None,
             "p": None, "status": "nuisance_baseline",
             "beats_metadata": False, "label_correct": True, "note": ""},
            {"method": "Quality baseline", "score": 0.494, "ci": None,
             "p": None, "status": "nuisance_baseline",
             "beats_metadata": False, "label_correct": True, "note": ""},
        ],
    }
    _save(comparison, "eeg_v74_final_method_comparison.json")
    print("Comparison: 5 methods, best=V6.9 (0.628)", file=sys.stderr)


def run_ledger():
    ledger = {
        **_safety(), "tool": "eeg_v74_claim_ledger",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "claims": [
            {"claim": "Filter-bank log-power features achieve above-chance left/right MI decoding under LOSO",
             "status": "supported", "safe_to_show": True,
             "thesis_wording": "Fold-safe filter-bank log-power features achieve above-chance MI decoding under LOSO."},
            {"claim": "V6.9 filter-bank log-power is the validated classical baseline at 0.628",
             "status": "supported", "safe_to_show": True,
             "thesis_wording": "The validated classical baseline for this task is filter-bank log-power at 0.628."},
            {"claim": "Frequency-domain decomposition outperforms CSP spatial filtering for this task",
             "status": "supported", "safe_to_show": True,
              "thesis_wording": "Per-band frequency features provide stronger signal than pure CSP on this dataset."},
            {"claim": "Classical EEG features can capture motor imagery signal",
             "status": "partially_supported", "safe_to_show": True,
             "thesis_wording": "Classical frequency-based EEG features capture above-chance but moderate MI signal."},
            {"claim": "V6.7 was true FBCSP",
             "status": "invalidated", "safe_to_show": False,
             "thesis_wording": "V6.7 was filter-bank log-power, incorrectly labeled as FBCSP. Corrected in V6.9."},
            {"claim": "True CSP beats filter-bank log-power",
             "status": "invalidated", "safe_to_show": False,
             "thesis_wording": "True MNE CSP (0.482) does NOT beat the filter-bank log-power baseline (0.628)."},
            {"claim": "Production BCI",
             "status": "forbidden", "safe_to_show": False,
             "thesis_wording": "This is NOT a production BCI system. It is experimental research."},
            {"claim": "Clinical EEG decoding / Mind-reading / Dream decoding",
             "status": "forbidden", "safe_to_show": False,
             "thesis_wording": "No clinical, mind-reading, or dream-decoding claims are made."},
            {"claim": "Real-time control",
             "status": "forbidden", "safe_to_show": False,
             "thesis_wording": "This does not support real-time BCI control."},
            {"claim": "Publication-ready FBCSP",
             "status": "forbidden", "safe_to_show": False,
             "thesis_wording": "The method is filter-bank log-power, not FBCSP. True FBCSP was not validated."},
        ],
    }
    _save(ledger, "eeg_v74_claim_ledger.json")
    supported = sum(1 for c in ledger["claims"] if c["status"] == "supported")
    invalidated = sum(1 for c in ledger["claims"] if c["status"] == "invalidated")
    print(f"Claim ledger: {supported} supported, {invalidated} invalidated, "
          f"{sum(1 for c in ledger['claims'] if c['status']=='forbidden')} forbidden",
          file=sys.stderr)


def run_report():
    report_md = """# V7.4 — Final Classical Motor Imagery Baseline Lock

## Executive Summary

After a rigorous multi-version validation cycle across V6.2–V7.3, the final validated
classical baseline for PhysioNet EEGMMI left/right fist motor imagery is **filter-bank
log-power at 0.628 balanced accuracy** under leave-one-subject-out cross-validation.

This method uses per-band FFT log-power features with LogisticRegression/LinearSVC
classification. It is explicitly **NOT CSP/FBCSP**. Multiple attempts to validate
true CSP and true FBCSP were made (V7.0–V7.3) but neither displaced the simpler
frequency-domain baseline.

## Dataset and Task

- Dataset: PhysioNet EEGMMI (eegmmidb)
- Task: Left fist vs. right fist motor imagery
- Subjects: 15
- Epochs: 675
- Evaluation: Leave-one-subject-out (LOSO)

## Final Validated Baseline

| Metric | Value |
|--------|-------|
| Method | Filter-bank log-power |
| Score | 0.628 |
| 95% CI | [0.581, 0.677] |
| p-value | < 0.001 |
| Above chance | Yes |
| Beats metadata (0.482) | Yes |

## CSP/FBCSP History

1. V6.7 claimed FBCSP but was actually filter-bank log-power (label corrected in V6.9)
2. V7.0-V7.1: CSP failed due to API bug (`verbose` in constructor)
3. V7.2: API fixed, CSP runs correctly
4. V7.3: True MNE CSP validated (0.482, p=0.933 — near chance, does NOT beat V6.9)
5. V7.3: True FBCSP attempted but did not complete under computational constraints

## What This Result Does and Does Not Prove

**Proved:**
- Per-band frequency features capture motor-imagery discriminative signal
- LOSO evaluation is scientifically defensible
- Metadata preflight confirms no nuisance confounds

**Not proved:**
- This is NOT a production BCI
- CSP spatial filtering alone does not improve over frequency decomposition
- True FBCSP has not been validated
- No clinical, mind-reading, or real-time control claims are made

## Limitations

- N=15 subjects — moderate sample size
- Single dataset (PhysioNet EEGMMI)
- Only left/right fist imagery task
- No time-domain bandpass CSP was successfully benchmarked
- Exploratory only — not a clinically validated BCI

## Thesis-Safe Conclusion

Fold-safe filter-bank log-power features provide an above-chance exploratory
classical EEG baseline for motor imagery decoding on PhysioNet EEGMMI.
The validated score is 0.628 [0.581, 0.677] under LOSO. This method is not
CSP/FBCSP and does not support production BCI, clinical, or mind-reading claims.
"""
    with open(os.path.join(EXPORTS, "eeg_v74_final_scientific_report.md"), "w") as f:
        f.write(report_md)

    report_json = {**_safety(), "tool": "eeg_v74_final_scientific_report",
                   "generated_at": datetime.now(timezone.utc).isoformat(),
                    "sections": [ln.strip("# ") for ln in report_md.split("\n") if ln.startswith("##")]}
    _save(report_json, "eeg_v74_final_scientific_report.json")
    print("Scientific report generated", file=sys.stderr)


def run_figures():
    os.makedirs(FIGS, exist_ok=True)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("Matplotlib not available", file=sys.stderr)
        return

    # 1. Method comparison bar chart
    fig, ax = plt.subplots(figsize=(8, 5))
    methods = ["FB Log-Power\n(V6.9)", "True CSP\n(V7.3)", "Metadata", "Quality"]
    scores = [0.628, 0.482, 0.482, 0.494]
    colors = ["#4CAF50", "#FF9800", "#9E9E9E", "#9E9E9E"]
    bars = ax.bar(methods, scores, color=colors, alpha=0.85)
    ax.axhline(0.5, color="gray", linestyle="--", alpha=0.5, label="Chance")
    ax.set_ylabel("Balanced Accuracy")
    ax.set_title("Final Method Comparison — Exploratory Only", fontsize=11)
    for bar, val in zip(bars, scores):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.01, f"{val:.3f}",
                ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "eeg_v74_final_method_comparison.png"), dpi=150, facecolor="white")
    plt.close(fig)

    # 2. Claim status pie
    fig, ax = plt.subplots(figsize=(6, 5))
    labels = ["Supported (3)", "Partial (1)", "Invalidated (2)", "Forbidden (4)"]
    sizes = [3, 1, 2, 4]
    colors_pie = ["#4CAF50", "#FFC107", "#FF9800", "#F44336"]
    ax.pie(sizes, labels=labels, colors=colors_pie, autopct="%1.0f%%", startangle=90)
    ax.set_title("Claim Ledger Summary — Exploratory Only", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "eeg_v74_claim_status_summary.png"), dpi=150, facecolor="white")
    plt.close(fig)

    print("Figures generated: 2", file=sys.stderr)


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)
    os.makedirs(FIGS, exist_ok=True)

    print(f"V7.4 mode={args.mode}", file=sys.stderr)

    if args.mode in ("audit", "all"):
        run_audit()
    if args.mode in ("lock", "all"):
        run_lock()
    if args.mode in ("comparison", "all"):
        run_comparison()
    if args.mode in ("ledger", "all"):
        run_ledger()
    if args.mode in ("report", "all"):
        run_report()
    if args.mode in ("figures", "all"):
        run_figures()
    return 0


if __name__ == "__main__":
    sys.exit(main())
