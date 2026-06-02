"""V7.5 — Thesis & Demo Scientific Integration Pack.

Reads all existing artifacts, generates master status, thesis report,
project claim ledger, figure registry, dashboard summary, frontend data.
No experiments. No model training. Integration only.
"""

import json
import os
import sys
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
FIGS = os.path.join(EXPORTS, "figures")
FRONTEND = os.path.join(BASE, "..", "..", "..", "demo_thesis")


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.eeg_v75_integration")
    p.add_argument("--mode", default="all",
                   choices=["audit", "master_status", "report", "ledger", "figures", "dashboard", "frontend", "all"])
    p.add_argument("--output-prefix", default="eeg_v75_integration")
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
        "v51_status": _load("openmiir_v51_scientific_status.json"),
        "v51_report": os.path.exists(os.path.join(EXPORTS, "openmiir_v51_thesis_safe_report.md")),
        "v50_verdict": _load("openmiir_v50_scientific_verdict.json"),
        "v49_forensic": _load("openmiir_ssl_v49_forensic_conclusion.json"),
        "v74_baseline": _load("eeg_v74_final_validated_baseline.json"),
        "v74_comparison": _load("eeg_v74_final_method_comparison.json"),
        "v74_ledger": _load("eeg_v74_claim_ledger.json"),
        "v74_report": os.path.exists(os.path.join(EXPORTS, "eeg_v74_final_scientific_report.md")),
        "v74_audit": _load("eeg_v74_artifact_audit.json"),
    }
    missing = []
    required = ["v74_baseline", "v74_ledger", "v74_report", "v74_comparison"]
    for r in required:
        if not artifacts.get(r):
            missing.append(r)

    audit = {
        **_safety(), "tool": "eeg_v75_integration_audit",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "openmiir_exists": artifacts["v51_status"] is not None,
        "openmiir_invalid": (artifacts["v51_status"] or {}).get("condition_decoding_status") == "invalid_confounded",
        "physionet_baseline_exists": artifacts["v74_baseline"] is not None,
        "physionet_score": (artifacts["v74_baseline"] or {}).get("score"),
        "physionet_not_csp": (artifacts["v74_baseline"] or {}).get("not_csp", False),
        "missing_required": missing,
        "ready": len(missing) == 0,
        "impact": "Cannot produce complete integration without required artifacts." if missing else "Ready.",
    }
    _save(audit, "eeg_v75_integration_audit.json")
    _save({"missing_required": missing, "suggested_fix": "Re-run V5.1 and V7.4 to regenerate artifacts."},
          "eeg_v75_missing_artifacts.json") if missing else None
    print(f"Integration audit: ready={audit['ready']} missing={len(missing)}", file=sys.stderr)


def run_master_status():
    master = {
        **_safety(),
        "tool": "eeg_v75_master_scientific_status",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_name": "IMAGINA / EEG Motor Imagery Validation",
        "scientific_status": "valid_exploratory_baseline_with_negative_control",
        "openmiir_status": {
            "role": "negative_control", "condition_decoding": "invalid_confounded",
            "why": "Event metadata encodes labels (baseline = 1.0). V5.0: 0/8 valid.",
            "safe_use": ["confound audit methodology", "representational analysis", "metadata baseline protocol"],
        },
        "physionet_status": {
            "role": "valid_replacement_dataset",
            "task": "left/right fist motor imagery",
            "final_baseline": "V6.9 filter-bank log-power",
            "score": 0.628, "ci": [0.581, 0.677], "p_value": "<0.001",
            "validated": True, "not_csp": True, "not_fbcsp": True,
            "n_subjects": 15, "cv": "leave-one-subject-out",
        },
        "final_project_claim": (
            "IMAGINA demonstrates a rigorous EEG validation workflow: it first "
            "invalidates confounded condition-decoding on OpenMIIR using metadata "
            "baselines, then establishes a valid exploratory motor-imagery baseline "
            "on PhysioNet EEGMMI using fold-safe filter-bank log-power under LOSO."
        ),
        "forbidden_claims": ["production BCI", "clinical", "mind-reading", "dream decoding",
                             "real-time control", "publication-ready FBCSP"],
        "allowed_claims": ["exploratory MI baseline validated", "metadata confound detected",
                           "negative-control methodology", "filter-bank log-power not FBCSP"],
        "thesis_positioning": "Confound-aware EEG validation: one invalidated dataset, one validated baseline.",
        "next_step": "Integrate into thesis/demo; SSL only as exploratory comparison later.",
    }
    _save(master, "eeg_v75_master_scientific_status.json")
    print("Master status generated", file=sys.stderr)


def run_report():
    md = """# V7.5 — Thesis-Safe Final Scientific Report

## Executive Summary

This project began with OpenMIIR as a condition-decoding target but discovered
that condition labels were structurally encoded in event metadata (V4.9-V5.1).
OpenMIIR was invalidated and became a negative-control case study.

The project then selected PhysioNet EEGMMI as a replacement (V6.2), passed
metadata preflight, and validated a classical motor-imagery baseline using
filter-bank log-power features under LOSO (V6.9). The final locked baseline
achieves **0.628 balanced accuracy** (CI [0.581, 0.677], p<0.001) on
left/right fist motor imagery at N=15.

Multiple attempts to validate true CSP and true FBCSP were made (V7.0-V7.3)
but neither displaced the simpler frequency-domain baseline. The validated
method is explicitly NOT CSP/FBCSP.

## OpenMIIR: Negative Control

- V4.9: Metadata-only baselines achieve 1.0 accuracy across all tasks
- V5.0: 0/8 redesigned tasks pass metadata validation
- V5.1: Thesis-safe exit pack documents honest negative result
- Role: Demonstrates why metadata preflight is essential

## PhysioNet EEGMMI: Valid Baseline

- V6.2: Metadata preflight passed; train gate allowed
- V6.9: Filter-bank log-power achieves 0.628 under LOSO
- V7.3: True MNE CSP (0.482) does NOT beat the baseline
- V7.4: Final baseline locked

## What This Proves

1. Metadata baselines can invalidate confounded EEG tasks
2. Per-band frequency features capture motor-imagery signal
3. LOSO evaluation is scientifically defensible
4. The method is NOT CSP/FBCSP

## What This Does NOT Prove

1. This is NOT a production BCI
2. CSP alone does not add value over frequency features
3. True FBCSP was not validated
4. No clinical, mind-reading, or real-time control claims

## Scientific Contribution

The main contribution is the **validation methodology**: metadata preflight,
confound-safe task design, fold-safe LOSO evaluation, transparent claim
discipline, and honest reporting of negative results.

## Final Conclusion

Filter-bank log-power provides a valid exploratory classical EEG baseline
for motor imagery on PhysioNet EEGMMI. OpenMIIR serves as the negative-control
case that calibrated the validation framework. Neither result supports
production BCI claims.
"""
    with open(os.path.join(EXPORTS, "eeg_v75_final_thesis_report.md"), "w") as f:
        f.write(md)
    report_json = {**_safety(), "tool": "eeg_v75_final_thesis_report",
                   "generated_at": datetime.now(timezone.utc).isoformat()}
    _save(report_json, "eeg_v75_final_thesis_report.json")
    print("Thesis report generated", file=sys.stderr)


def run_ledger():
    claims = [
        {"claim": "Metadata baselines can invalidate EEG decoding tasks",
         "status": "supported", "safe_to_show": True,
         "thesis_wording": "Metadata-only baselines are a necessary preflight for any EEG decoding claim.",
         "evidence": ["V4.9 forensic conclusion", "V5.0 task invalidation"]},
        {"claim": "OpenMIIR condition decoding is structurally confounded",
         "status": "supported", "safe_to_show": True,
         "thesis_wording": "OpenMIIR event codes structurally encode condition labels; metadata baselines achieve 1.0.",
         "evidence": ["V4.9 metadata baselines", "V5.0 scientific verdict"]},
        {"claim": "PhysioNet EEGMMI passes metadata preflight for left/right MI",
         "status": "supported", "safe_to_show": True,
         "thesis_wording": "PhysioNet EEGMMI motor imagery passes nuisance-metadata preflight under LOSO.",
         "evidence": ["V6.2 train gate", "V6.2 preflight results"]},
        {"claim": "Filter-bank log-power achieves 0.628 under LOSO",
         "status": "supported", "safe_to_show": True,
         "thesis_wording": "Filter-bank log-power: 0.628 CI [0.581,0.677] p<0.001.",
         "evidence": ["V6.9 scientific verdict", "V7.4 final baseline lock"]},
        {"claim": "The final validated method is NOT CSP/FBCSP",
         "status": "supported", "safe_to_show": True,
         "thesis_wording": "V6.9 filter-bank log-power uses per-band FFT features without CSP spatial filtering.",
         "evidence": ["V7.4 final baseline lock", "V7.1-V7.3 CSP validation history"]},
        {"claim": "True CSP does not beat filter-bank log-power",
         "status": "supported", "safe_to_show": True,
         "thesis_wording": "True MNE CSP (0.482) does NOT outperform the frequency-domain baseline (0.628).",
         "evidence": ["V7.3 fast true CSP result"]},
        {"claim": "Classical EEG features capture motor imagery signal",
         "status": "partially_supported", "safe_to_show": True,
         "thesis_wording": "Per-band frequency features capture moderate MI signal; performance is task-specific.",
         "evidence": ["V6.9 filter-bank log-power", "V7.3 CSP comparison"]},
        {"claim": "V4.8 SSL OpenMIIR 0.93-0.96 scores were valid",
         "status": "invalidated", "safe_to_show": False,
         "thesis_wording": "V4.8 SSL scores were confounded by metadata; not trustworthy condition-decoding evidence.",
         "evidence": ["V4.9 forensic audit", "V5.0 task invalidation"]},
        {"claim": "V6.7 was true FBCSP",
         "status": "invalidated", "safe_to_show": False,
         "thesis_wording": "V6.7 was filter-bank log-power, incorrectly labeled as FBCSP. Corrected in V6.9.",
         "evidence": ["V6.8 audit", "V7.4 label correction manifest"]},
        {"claim": "Production BCI / Clinical validity / Real-time control",
         "status": "forbidden", "safe_to_show": False,
         "thesis_wording": "No production, clinical, or real-time BCI claims are supported.",
         "evidence": ["All versions (V1-V7.4)"]},
        {"claim": "Mind-reading / Dream decoding / General imagery decoding",
         "status": "forbidden", "safe_to_show": False,
         "thesis_wording": "No mind-reading, dream-decoding, or general imagery-decoding claims are made.",
         "evidence": ["All versions (V1-V7.4)"]},
    ]
    ledger = {**_safety(), "tool": "eeg_v75_project_claim_ledger",
              "generated_at": datetime.now(timezone.utc).isoformat(),
              "claims": claims}
    _save(ledger, "eeg_v75_project_claim_ledger.json")
    sup = sum(1 for c in claims if c["status"] == "supported")
    inv = sum(1 for c in claims if c["status"] == "invalidated")
    print(f"Project ledger: {sup} supported, {inv} invalidated, "
          f"{sum(1 for c in claims if c['status']=='forbidden')} forbidden",
          file=sys.stderr)


def run_figures():
    fig_files = []
    if os.path.isdir(FIGS):
        fig_files = sorted([f for f in os.listdir(FIGS) if f.endswith(".png")])

    registry_entries = []
    phase_map = {"v51": "V5.1 OpenMIIR exit", "v74": "V7.4 baseline lock",
                 "v69": "V6.9", "v67": "V6.7", "v68": "V6.8"}

    for fn in fig_files:
        phase = "unknown"
        for k, v in phase_map.items():
            if k in fn:
                phase = v
                break
        registry_entries.append({
            "filename": fn, "path": f"data/exports/figures/{fn}",
            "phase": phase, "safe_to_use": True,
            "recommended_section": "Results" if "comparison" in fn else "Methodology",
        })

    registry = {**_safety(), "tool": "eeg_v75_figure_registry",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "figures": registry_entries, "n_figures": len(registry_entries)}
    _save(registry, "eeg_v75_figure_registry.json")
    print(f"Figure registry: {len(fig_files)} figures", file=sys.stderr)


def run_dashboard():
    dashboard = {
        **_safety(), "tool": "eeg_v75_dashboard_summary",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "headline": "Confound-aware EEG validation: OpenMIIR invalidated, PhysioNet baseline validated",
        "openmiir_card": {"status": "negative_control", "reason": "metadata confounded",
                          "score": "N/A (invalid)"},
        "physionet_card": {"status": "valid_exploratory", "task": "left/right MI",
                           "score": 0.628, "ci": [0.581, 0.677], "method": "filter-bank log-power (NOT CSP/FBCSP)"},
        "final_baseline_card": {"method": "V6.9", "score": 0.628, "not_fbcsp": True},
        "claim_discipline_card": {"supported": 6, "partially": 1, "invalidated": 2, "forbidden": 2},
        "next_steps_card": "SSL as exploratory comparison only; no further CSP/FBCSP",
    }
    _save(dashboard, "eeg_v75_dashboard_summary.json")
    print("Dashboard summary generated", file=sys.stderr)


def run_frontend():
    if not os.path.isdir(FRONTEND):
        print("Frontend directory not found — skipping frontend export", file=sys.stderr)
        return

    data_dir = os.path.join(FRONTEND, "src", "data")
    os.makedirs(data_dir, exist_ok=True)

    ts_content = """// V7.5 Generated
// Do not edit manually.
export const eegScientificStatus = {{
  projectName: "IMAGINA / EEG Motor Imagery Validation",
  status: "valid_exploratory_baseline_with_negative_control",
  generatedAt: \"""" + datetime.now(timezone.utc).isoformat() + """\",
}};

export const openmiirNegativeControl = {{
  role: "negative_control",
  conditionDecoding: "invalid_confounded",
  reason: "Event metadata encodes condition labels (metadata baseline = 1.0 accuracy)",
  safeUses: ["confound audit", "representational analysis", "metadata preflight protocol"],
}};

export const physionetFinalBaseline = {{
  role: "valid_replacement_dataset",
  task: "left/right fist motor imagery",
  method: "filter-bank log-power (NOT CSP/FBCSP)",
  score: 0.628,
  ci: [0.581, 0.677],
  pValue: "<0.001",
  subjects: 15,
  cv: "leave-one-subject-out",
  validated: true,
  notCspOrFbcsp: true,
}};

export const finalClaimLedger = {{
  supported: 6, partiallySupported: 1, invalidated: 2, forbidden: 2,
}};

export const forbiddenClaims = [
  "Production BCI", "Clinical EEG decoding", "Mind-reading",
  "Dream decoding", "Real-time control", "Publication-ready FBCSP",
];

export const allowedClaims = [
  "Metadata baselines invalidate confounded EEG tasks",
  "OpenMIIR condition decoding is structurally confounded",
  "PhysioNet EEGMMI passes metadata preflight",
  "Filter-bank log-power achieves 0.628 under LOSO",
  "Method is NOT CSP/FBCSP", "True CSP does not beat baseline",
];
"""

    ts_path = os.path.join(data_dir, "eegScientificStatus.ts")
    with open(ts_path, "w") as f:
        f.write(ts_content)
    print(f"Frontend data exported: {ts_path}", file=sys.stderr)


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)
    print(f"V7.5 mode={args.mode}", file=sys.stderr)

    if args.mode in ("audit", "all"):
        run_audit()
    if args.mode in ("master_status", "all"):
        run_master_status()
    if args.mode in ("report", "all"):
        run_report()
    if args.mode in ("ledger", "all"):
        run_ledger()
    if args.mode in ("figures", "all"):
        run_figures()
    if args.mode in ("dashboard", "all"):
        run_dashboard()
    if args.mode in ("frontend", "all"):
        run_frontend()
    return 0


if __name__ == "__main__":
    sys.exit(main())
