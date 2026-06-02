"""OpenMIIR V5.1 — Scientific Exit Pack & Thesis-Safe Narrative.

Transforms V4.9/V5.0 negative findings into rigorous research contributions:
audit methodology, claim ledger, thesis-safe report, valid dataset redesign spec.
"""

import json
import os
import sys
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
FIGURES_DIR = os.path.join(EXPORTS, "figures")
META_DIR = os.path.join(BASE, "..", "..", "data", "external", "openmiir", "meta")


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_v51_scientific_exit_pack")
    p.add_argument("--mode", default="all",
                   choices=["status", "report", "ledger", "dataset_spec", "figures", "all"])
    p.add_argument("--output-prefix", default="openmiir_v51_scientific_exit_pack")
    return p


def _load(p):
    if p and os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None


def _safety():
    return {"analysis_mode": "experimental_hypothesis_only",
            "not_for_scientific_claims": True, "production_valid": False,
            "production_unlock_allowed": False, "no_raw_eeg_exposed": True}


def run_status():
    forensic = _load(os.path.join(EXPORTS, "openmiir_ssl_v49_forensic_conclusion.json"))
    verdict = _load(os.path.join(EXPORTS, "openmiir_v50_scientific_verdict.json"))
    main_eval = _load(os.path.join(EXPORTS, "openmiir_condition_eval.json"))
    cond_manifest = os.path.exists(os.path.join(META_DIR, "condition_manifest.json"))

    safe_value = [
        "Confound audit methodology: metadata-only baselines can invalidate EEG decoding tasks",
        "Task invalidation framework: event_code/stimulus_group structural encoding detection",
        "Exploratory spectral feature analysis: alpha/theta bands carry moderate condition signal",
        "Representational geometry analysis: RSA, RDM, PID-EEG provide interpretable structure",
        "Honest negative result: V4.8 SSL was confounded; this finding prevents false claims",
        "Dataset suitability assessment: methodology applicable to any EEG condition-decoding dataset",
        "Leakage-free nested LOSO protocol for SSL validation",
        "Subject-adversarial training with correct gradient reversal implementation",
    ]
    invalid_artifacts = [
        "V4.8 high SSL scores (0.93-0.96): metadata-confounded",
        "V4.7 condition probe: label leakage via joint condition-head training",
        "Any condition-decoding result that can be predicted by event_code/stimulus metadata",
    ]

    status = {
        **_safety(),
        "tool": "openmiir_v51_scientific_exit_pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_status": "condition_decoding_invalid_but_exploratory_analysis_valid",
        "condition_decoding_status": "invalid_confounded",
        "metadata_confound_status": "fatal_structural_confound",
        "main_eval_status": (main_eval or {}).get("status", "unknown"),
        "main_eval_blocked": (main_eval or {}).get("status") == "blocked",
        "condition_manifest_exists": cond_manifest,
        "forensic_verdict": (forensic or {}).get("verdict"),
        "v5_verdict": (verdict or {}).get("verdict"),
        "safe_research_value": safe_value,
        "valid_artifacts": [
            "openmiir_ssl_v49_forensic_conclusion.json",
            "openmiir_v50_scientific_verdict.json",
            "openmiir_ssl_v49_frequency_sanity.json",
            "openmiir_epoch_condition_benchmark_experimental.json",
            "openmiir_representational_analysis_experimental.json",
            "openmiir_geometry_evidence_grade.json",
        ],
        "invalid_artifacts": invalid_artifacts,
        "recommended_project_framing": (
            "IMAGINA is a research prototype for EEG confound detection and "
            "representational analysis. It demonstrates that high EEG decoding "
            "scores can be invalidated by metadata baselines, and provides a "
            "framework for honest EEG benchmark auditing."
        ),
        "thesis_safe_claim": (
            "OpenMIIR is useful for exploratory EEG feature analysis and for "
            "demonstrating how metadata confounds can invalidate apparently "
            "strong EEG decoding results. It cannot support claims of reliable "
            "condition decoding, BCI-readiness, or clinical validity."
        ),
    }
    with open(os.path.join(EXPORTS, "openmiir_v51_scientific_status.json"), "w") as f:
        json.dump(status, f, indent=2, default=str)
    print(f"Status: {status['project_status']}", file=sys.stderr)
    return 0


def run_report():
    md_lines = [
        "# OpenMIIR Condition Decoding — Thesis-Safe Scientific Report",
        "",
        ":warning: **Experimental only — not validated BCI, clinical, or production-ready.**",
        "",
        "## 1. Executive Summary",
        "",
        "This project evaluated whether OpenMIIR EEG can support confound-free condition decoding "
        "(perception vs imagery vs noise). After rigorous forensic auditing, we conclude that **OpenMIIR "
        "cannot support confound-free condition decoding** because condition labels are structurally "
        "encoded in event metadata (event_code, stimulus_group). Metadata-only baselines achieve perfect "
        "accuracy (1.0) across all task designs, invalidating any EEG-based condition-decoding claim.",
        "",
        "However, the project provides significant research value:",
        "- A reusable confound audit methodology",
        "- A task invalidation framework applicable to any EEG dataset",
        "- Exploratory spectral feature and representational geometry analyses",
        "- An honest negative result that prevents false scientific claims",
        "- A specification for valid future dataset design",
        "",
        "## 2. What We Tried",
        "",
        "- Imported OpenMIIR: 10 subjects, 64-channel EEG, 512 Hz",
        "- Extracted 52 unique stim-channel event codes",
        "- Recovered MATLAB trigger semantics: 1=perception, 2=cued, 3=uncued, 4=noise",
        "- Built handcrafted spectral features (32 features per epoch)",
        "- Trained self-supervised EEG encoders (ResNet1D + MAE)",
        "- Implemented nested LOSO leakage-free evaluation",
        "- Achieved V4.8 SSL scores of 0.93-0.96 (later invalidated)",
        "",
        "## 3. Why the Original Task Looked Promising",
        "",
        "- MATLAB confirmed trigger/code meaning",
        "- StimTracker encoding empirically validated (score 0.862)",
        "- SSL produced competitive embeddings",
        "- Subject-adversarial training reduced subject predictability",
        "- All above-chance with permutation p < 0.05",
        "",
        "## 4. What the Forensic Audit Found (V4.9)",
        "",
        "- **Combined metadata (subject + stimulus_group + event_code) achieves 1.0 accuracy "
        "across ALL 6 tasks under LOSO.**",
        "- Event_code alone achieves 1.0 on within-stimulus-group tasks",
        "- Stimulus_group alone = chance (0.50) — but combined with event_code = 1.0",
        "- Alpha/theta features carry real signal (0.58), but this includes metadata-confounded structure",
        "- Quality features near chance (0.52) — no artifact confound",
        "",
        "## 5. Why V4.8 Was Invalid",
        "",
        "- The encoder learned to exploit stimulus/event metadata structure",
        "- Condition labels are encoded in the experimental paradigm design",
        "- Metadata baselines prove the task is trivially solvable without EEG",
        "- A valid EEG decoding task requires metadata baselines to remain near chance",
        "",
        "## 6. Why V5.0 Could Not Find a Confound-Free Task",
        "",
        "- All 8 candidate redesigned tasks (within-stimulus-group, balanced) failed metadata validation",
        "- Event codes directly encode the condition per stimulus group",
        "- Example: within stimulus group 1, code 11=perception, 12=cued, 13=uncued",
        "- No task design can decouple condition from event_code in OpenMIIR",
        "",
        "## 7. What Still Remains Scientifically Useful",
        "",
        "1. **Confound audit methodology**: reusable for any EEG decoding study",
        "2. **Task invalidation framework**: formal criteria for labeling tasks as confounded",
        "3. **Exploratory spectral analysis**: alpha/theta bands carry real neural signal",
        "4. **Representational geometry**: RSA, RDM, PID-EEG provide interpretable structure",
        "5. **Leakage-free nested LOSO protocol**: correct SSL evaluation without label leakage",
        "6. **Subject-adversarial training**: correct gradient reversal implementation",
        "7. **Honest negative result**: prevents false claims in EEG decoding literature",
        "8. **Dataset redesign specification**: requirements for valid future experiments",
        "",
        "## 8. What Cannot Be Claimed (Forbidden)",
        "",
        "- ❌ We can decode imagined perception or mental imagery from EEG",
        "- ❌ We achieved 95% EEG decoding accuracy",
        "- ❌ This is BCI-ready or production-ready",
        "- ❌ Mind-reading, dream decoding, clinical diagnosis",
        "- ❌ Validated condition decoding",
        "- ❌ Confound-free perception/imagery classification",
        "",
        "## 9. What Can Be Claimed (Allowed)",
        "",
        "- ✔ OpenMIIR is useful for exploratory EEG feature analysis",
        "- ✔ Metadata baselines can invalidate confounded EEG decoding tasks",
        "- ✔ This project demonstrates how to avoid false claims in EEG research",
        "- ✔ Representational geometry provides interpretable EEG structure",
        "- ✔ Subject-adversarial training reduces subject identity signal",
        "",
        "## 10. Future Work: How to Build a Valid Dataset",
        "",
        "A valid confound-free EEG condition-decoding dataset requires:",
        "- Randomized trial order per subject",
        "- Condition labels not encoded in event codes",
        "- Same stimulus identity across multiple conditions",
        "- Metadata-only baselines near chance (≤ 0.55)",
        "- Held-out subject validation",
        "- Held-out stimulus validation",
        "- Pre-registered exclusion rules",
        "",
        "## 11. Final Thesis-Safe Conclusion",
        "",
        "OpenMIIR cannot support confound-free condition decoding. However, this negative result is "
        "a rigorous scientific contribution: it demonstrates that high EEG decoding scores can be "
        "invalidated by simple metadata baselines, and it provides a reusable framework for honest "
        "EEG benchmark auditing. The project contributes methodology, not hype.",
        "",
        "---",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "Analysis mode: experimental_hypothesis_only",
        "Not for scientific claims about condition decoding.",
    ]

    md_path = os.path.join(EXPORTS, "openmiir_v51_thesis_safe_report.md")
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))

    report_json = {**_safety(), "tool": "openmiir_v51_thesis_safe_report",
                   "generated_at": datetime.now(timezone.utc).isoformat(),
                   "sections": [line.lstrip("## ") for line in md_lines
                                if line.startswith("##")]}
    with open(os.path.join(EXPORTS, "openmiir_v51_thesis_safe_report.json"), "w") as f:
        json.dump(report_json, f, indent=2, default=str)

    print("Thesis-safe report generated", file=sys.stderr)
    return 0


def run_ledger():
    claims = [
        {"claim": "Metadata baselines can invalidate confounded EEG decoding tasks",
         "status": "supported",
         "evidence": "V4.9 metadata-only baselines achieve 1.0 accuracy across all tasks",
         "safe_to_show": True},
        {"claim": "OpenMIIR condition labels are structurally recoverable from event metadata",
         "status": "supported",
         "evidence": "Event_code alone achieves 1.0 accuracy within stimulus groups",
         "safe_to_show": True},
        {"claim": "V4.8 SSL scores are confounded and not trustworthy",
         "status": "supported",
         "evidence": "Forensic audit found metadata confound; scores invalidated in V5.0",
         "safe_to_show": True},
        {"claim": "Alpha/theta spectral features carry moderate condition-related structure",
         "status": "partially_supported",
         "evidence": "Alpha/theta features achieve ~0.58 bal_acc, above chance but metadata-confounded",
         "safe_to_show": True},
        {"claim": "Cued imagery is closer to perception than uncued imagery",
         "status": "partially_supported",
         "evidence": "PID-EEG shows cued imagery advantage=0.73; exploratory but not validated",
         "safe_to_show": True},
        {"claim": "Subject-adversarial training reduces subject identity signal in EEG embeddings",
         "status": "partially_supported",
         "evidence": "Subject predictability dropped from 0.445 to 0.349 in V4.8 OOF",
         "safe_to_show": True},
        {"claim": "V4.8 SSL reliably decodes imagined condition from EEG",
         "status": "invalidated",
         "evidence": "Metadata baselines achieve 1.0; SSL scores are confounded",
         "safe_to_show": False},
        {"claim": "OpenMIIR supports confound-free condition decoding",
         "status": "invalidated",
         "evidence": "V5.0 found 0/8 tasks pass metadata validation",
         "safe_to_show": False},
        {"claim": "We can decode imagined perception or mental imagery from EEG",
         "status": "forbidden",
         "evidence": "All condition decoding tasks are metadata-confounded",
         "safe_to_show": False},
        {"claim": "This system is BCI-ready or production-ready",
         "status": "forbidden",
         "evidence": "Experimental prototype only; no production validation",
         "safe_to_show": False},
        {"claim": "Mind-reading, dream decoding, or clinical EEG analysis",
         "status": "forbidden",
         "evidence": "No clinical validation; explicit scientific boundaries",
         "safe_to_show": False},
    ]
    ledger = {**_safety(), "tool": "openmiir_v51_claim_ledger",
              "generated_at": datetime.now(timezone.utc).isoformat(),
              "claims": claims}
    with open(os.path.join(EXPORTS, "openmiir_v51_claim_ledger.json"), "w") as f:
        json.dump(ledger, f, indent=2, default=str)
    print(f"Claim ledger: {len(claims)} claims classified", file=sys.stderr)
    return 0


def run_dataset_spec():
    spec = {
        **_safety(),
        "tool": "openmiir_v51_valid_dataset_redesign_spec",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "question": "If OpenMIIR is structurally confounded, how would we collect or choose a valid dataset?",
        "requirements": [
            "1. Randomized trial order per subject — condition labels not predictable from trial position",
            "2. Condition labels not trivially encoded in event_code or channel labels",
            "3. Same stimulus presented across multiple conditions (perception + imagery of same audio)",
            "4. Balanced stimulus groups across condition labels",
            "5. Metadata-only baseline must stay near chance (balanced accuracy <= 0.55)",
            "6. Held-out-subject validation (LOSO or group K-fold)",
            "7. Held-out-stimulus validation where feasible",
            "8. Pre-registered exclusion rules",
            "9. Separate train/test subjects to prevent any form of subject leakage",
            "10. No condition-dependent preprocessing (filtering, epoching, artifact rejection)",
        ],
        "valid_experimental_designs": [
            {
                "name": "Same-Stimulus Perception vs Imagery",
                "description": "Present same audio clip, randomly instruct participant to perceive or imagine. "
                "Event code marks stimulus onset; condition is an orthogonal label.",
            },
            {
                "name": "Active vs Passive Imagination with Matched Cues",
                "description": "Cued vs uncued imagery with identical pre-trial cue metadata. "
                "Conditional randomization within subject.",
            },
            {
                "name": "Imagined Category Decoding",
                "description": "Subjects imagine different categories (faces, places, objects). "
                "Categories balanced across stimulus blocks. Random event codes.",
            },
            {
                "name": "Cross-Subject Stimulus-Held-Out Generalization",
                "description": "Train on N-1 subjects, test on held-out subject with held-out stimuli. "
                "Tests whether EEG encodes condition beyond stimulus familiarity.",
            },
        ],
        "acceptance_criteria": [
            "Metadata-only baseline balanced accuracy <= 0.55",
            "DummyClassifier baseline near chance",
            "EEG model > metadata baseline by statistically significant margin (permutation p < 0.05)",
            "Effect remains under LOSO and held-out-stimulus validation",
            "Confound-free verification via V4.9/V5.0 forensic methodology",
        ],
    }
    with open(os.path.join(EXPORTS, "openmiir_v51_valid_dataset_redesign_spec.json"), "w") as f:
        json.dump(spec, f, indent=2, default=str)

    md_lines = [
        "# Valid EEG Dataset Redesign Specification",
        "",
        spec["question"], "",
        "## Requirements",
    ] + spec["requirements"] + [
        "", "## Valid Experimental Designs",
    ]
    for d in spec["valid_experimental_designs"]:
        md_lines.append(f"### {d['name']}")
        md_lines.append(d["description"])
    md_lines += ["", "## Acceptance Criteria"] + spec["acceptance_criteria"]
    with open(os.path.join(EXPORTS, "openmiir_v51_valid_dataset_redesign_spec.md"), "w") as f:
        f.write("\n".join(md_lines))
    print("Dataset redesign spec generated", file=sys.stderr)
    return 0


def run_figures():
    os.makedirs(FIGURES_DIR, exist_ok=True)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return 1

    # 1. Project status flow (simple text-based figure)
    fig, ax = plt.subplots(figsize=(10, 5))
    steps = [
        "V4.8 High Scores\n(0.93-0.96)", "V4.9 Forensic Audit\n(metadata=1.0 → CONFOUNDED)",
        "V5.0 Task Redesign\n(0/8 tasks safe)", "V5.1 Safe Conclusion\n(thesis-safe negative)",
    ]
    colors = ["#F44336", "#FF9800", "#FF9800", "#4CAF50"]
    for i, (step, color) in enumerate(zip(steps, colors)):
        ax.fill_between([i, i + 1], 0, 1, alpha=0.3, color=color)
        ax.text(i + 0.5, 0.5, step, ha="center", va="center", fontsize=9, fontweight="bold",
                bbox=dict(boxstyle="round", facecolor=color, alpha=0.3))
    ax.set_xlim(0, len(steps))
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("Project Status Flow — Thesis-Safe Interpretation Only", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "openmiir_v51_project_status_flow.png"),
                dpi=150, facecolor="white")
    plt.close(fig)

    # 2. Old scores vs metadata baseline
    fig, ax = plt.subplots(figsize=(8, 5))
    jobs = ["PvI", "PvN", "CvU", "IvN", "PvCI", "PvUI"]
    old_scores = [0.941, 0.958, 0.955, 0.954, 0.940, 0.933]
    meta_scores = [1.0] * 6
    x = range(len(jobs))
    ax.bar([i - 0.2 for i in x], old_scores, 0.35, label="Old V4.8 SSL", color="#F44336", alpha=0.8)
    ax.bar([i + 0.2 for i in x], meta_scores, 0.35, label="Metadata baseline", color="#4CAF50", alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(jobs)
    ax.set_ylabel("Balanced Accuracy")
    ax.legend(fontsize=8)
    ax.set_title("Old Scores vs Metadata Baseline — Experimental Only", fontsize=10)
    ax.axhline(0.75, color="red", linestyle="--", label="Confound threshold")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "openmiir_v51_old_vs_metadata_baseline.png"),
                dpi=150, facecolor="white")
    plt.close(fig)

    # 3. Allowed vs forbidden claims
    fig, ax = plt.subplots(figsize=(10, 6))
    allowed = ["Confound audit\nmethodology", "EEG feature\nanalysis", "Representational\ngeometry",
               "Dataset suitability\nassessment", "Honest negative\nresult"]
    forbidden = ["Reliable imagery\ndecoding", "BCI-ready", "Mind-reading/\ndream decoding",
                 "Clinical\nvalidity", "Production-ready"]
    for i, text in enumerate(allowed):
        ax.text(0.2, 1 - (i + 0.5) / 6, f"✔ {text}", fontsize=9, color="#4CAF50",
                bbox=dict(boxstyle="round", facecolor="#4CAF5020"))
    for i, text in enumerate(forbidden):
        ax.text(0.6, 1 - (i + 0.5) / 6, f"✘ {text}", fontsize=9, color="#F44336",
                bbox=dict(boxstyle="round", facecolor="#F4433620"))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("Allowed vs Forbidden Claims — Thesis-Safe Only", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "openmiir_v51_allowed_vs_forbidden_claims.png"),
                dpi=150, facecolor="white")
    plt.close(fig)

    print("Figures generated: 3", file=sys.stderr)
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    print(f"V5.1 mode={args.mode}", file=sys.stderr)

    if args.mode in ("status", "all"):
        run_status()
    if args.mode in ("report", "all"):
        run_report()
    if args.mode in ("ledger", "all"):
        run_ledger()
    if args.mode in ("dataset_spec", "all"):
        run_dataset_spec()
    if args.mode in ("figures", "all"):
        run_figures()

    return 0


if __name__ == "__main__":
    sys.exit(main())
