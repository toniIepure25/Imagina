"""V6.0 — EEG Dataset Replacement Search & Migration Plan.

Identifies candidate EEG datasets for confound-free mental imagery decoding,
defines metadata preflight protocol, ranks candidates, recommends V6.1 target.
"""

import json
import os
import sys
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
META_DIR = os.path.join(BASE, "..", "..", "data", "external", "openmiir", "meta")


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.eeg_dataset_replacement_search")
    p.add_argument("--mode", default="all",
                   choices=["registry", "rubric", "protocol", "openmiir_control", "rank", "recommend", "all"])
    p.add_argument("--output-prefix", default="eeg_v60_dataset_replacement")
    return p


def _safety():
    return {"analysis_mode": "experimental_hypothesis_only",
            "not_for_scientific_claims": True, "production_valid": False,
            "production_unlock_allowed": False, "no_raw_eeg_exposed": True}


def run_registry():
    datasets = [
        {
            "dataset_name": "BNCI Horizon 2020 — Motor Imagery (001-2014)",
            "domain": "motor_imagery",
            "task_type": "left_hand_vs_right_hand_vs_feet_vs_tongue_motor_imagery",
            "modalities": ["EEG"],
            "n_subjects": 9,
            "n_channels": 22,
            "sampling_rate_hz": 250,
            "conditions": ["left_hand", "right_hand", "feet", "tongue"],
            "stimulus_metadata_available": True,
            "event_metadata_available": True,
            "raw_data_available": True,
            "license_or_access_notes": "Public via BNCI Horizon / MOABB",
            "download_url_or_reference": "http://bnci-horizon-2020.eu/database/data-sets",
            "known_risks": ["event codes may encode condition directly — needs preflight"],
            "potential_target_tasks": ["left_vs_right_hand_motor_imagery", "4-class_motor_imagery"],
            "initial_suitability_score": 75,
            "recommended_priority": "high",
        },
        {
            "dataset_name": "BCI Competition IV — Dataset 2a (Graz)",
            "domain": "motor_imagery",
            "task_type": "4-class_motor_imagery",
            "modalities": ["EEG"],
            "n_subjects": 9,
            "n_channels": 22,
            "sampling_rate_hz": 250,
            "conditions": ["left_hand", "right_hand", "feet", "tongue"],
            "stimulus_metadata_available": True,
            "event_metadata_available": True,
            "raw_data_available": True,
            "license_or_access_notes": "Public via BCI Competition IV / MOABB",
            "download_url_or_reference": "https://www.bbci.de/competition/iv/",
            "known_risks": ["cue-aligned event codes — may be directly predictive"],
            "potential_target_tasks": ["left_vs_right_hand", "4-class_motor_imagery"],
            "initial_suitability_score": 70,
            "recommended_priority": "high",
        },
        {
            "dataset_name": "PhysioNet EEG Motor Movement/Imagery (eegmmidb)",
            "domain": "motor_imagery",
            "task_type": "motor_execution_vs_imagery",
            "modalities": ["EEG"],
            "n_subjects": 109,
            "n_channels": 64,
            "sampling_rate_hz": 160,
            "conditions": ["open_close_fists", "open_close_feet", "executed", "imagined"],
            "stimulus_metadata_available": True,
            "event_metadata_available": True,
            "raw_data_available": True,
            "license_or_access_notes": "Public via PhysioNet",
            "download_url_or_reference": "https://physionet.org/content/eegmmidb/",
            "known_risks": ["large dataset — need to verify event code independence"],
            "potential_target_tasks": ["executed_vs_imagined", "fists_vs_feet"],
            "initial_suitability_score": 80,
            "recommended_priority": "high",
        },
        {
            "dataset_name": "OpenBMI — Korea University Motor Imagery",
            "domain": "motor_imagery",
            "task_type": "left_vs_right_hand_motor_imagery",
            "modalities": ["EEG"],
            "n_subjects": 54,
            "n_channels": 62,
            "sampling_rate_hz": 1000,
            "conditions": ["left_hand", "right_hand"],
            "stimulus_metadata_available": True,
            "event_metadata_available": True,
            "raw_data_available": True,
            "license_or_access_notes": "Available via GigaScience",
            "download_url_or_reference": "http://gigadb.org/dataset/100542",
            "known_risks": ["event_code structure needs preflight"],
            "potential_target_tasks": ["left_vs_right_hand"],
            "initial_suitability_score": 75,
            "recommended_priority": "high",
        },
        {
            "dataset_name": "Imagined Speech EEG (Coretto et al.)",
            "domain": "imagined_speech",
            "task_type": "imagined_word_classification",
            "modalities": ["EEG"],
            "n_subjects": 15,
            "n_channels": 6,
            "sampling_rate_hz": 1024,
            "conditions": ["/\u0251/", "/i/", "/u/", "rest"],
            "stimulus_metadata_available": False,
            "event_metadata_available": False,
            "raw_data_available": True,
            "license_or_access_notes": "Published dataset — limited metadata",
            "download_url_or_reference": "https://doi.org/10.1016/j.dib.2018.11.021",
            "known_risks": ["only 6 channels — limited spatial info", "metadata sparse"],
            "potential_target_tasks": ["imagined_vowel_classification"],
            "initial_suitability_score": 40,
            "recommended_priority": "low",
        },
        {
            "dataset_name": "THINGS-EEG (Visual Object EEG)",
            "domain": "visual_perception",
            "task_type": "visual_object_viewing",
            "modalities": ["EEG", "MEG"],
            "n_subjects": 50,
            "n_channels": 64,
            "sampling_rate_hz": 1000,
            "conditions": ["1854_visual_object_concepts"],
            "stimulus_metadata_available": True,
            "event_metadata_available": True,
            "raw_data_available": True,
            "license_or_access_notes": "Public via OpenNeuro ds003825",
            "download_url_or_reference": "https://openneuro.org/datasets/ds003825",
            "known_risks": ["not imagery — perception only", "visual, not auditory"],
            "potential_target_tasks": ["object_category_classification", "perception_encoding"],
            "initial_suitability_score": 60,
            "recommended_priority": "medium",
        },
        {
            "dataset_name": "Auditory Imagery EEG (Marion & Di Liberto)",
            "domain": "auditory_imagery",
            "task_type": "imagined_music_vs_perceived_music",
            "modalities": ["EEG"],
            "n_subjects": 21,
            "n_channels": 128,
            "sampling_rate_hz": 512,
            "conditions": ["perceived_music", "imagined_music", "silence"],
            "stimulus_metadata_available": False,
            "event_metadata_available": False,
            "raw_data_available": False,
            "license_or_access_notes": "Preprint — data availability unknown",
            "download_url_or_reference": "https://www.biorxiv.org/content/10.1101/2023.11.15.567179v1",
            "known_risks": ["data may not be public", "metadata preflight impossible without data"],
            "potential_target_tasks": ["perception_vs_imagery_music"],
            "initial_suitability_score": 20,
            "recommended_priority": "reject",
        },
        {
            "dataset_name": "OpenMIIR (legacy — NEGATIVE CONTROL)",
            "domain": "auditory_perception_imagery",
            "task_type": "music_perception_vs_imagery",
            "modalities": ["EEG"],
            "n_subjects": 10,
            "n_channels": 64,
            "sampling_rate_hz": 512,
            "conditions": ["perception", "cued_imagery", "uncued_imagery", "noise"],
            "stimulus_metadata_available": True,
            "event_metadata_available": True,
            "raw_data_available": True,
            "license_or_access_notes": "Public via GitHub sstober/openmiir",
            "download_url_or_reference": "https://github.com/sstober/openmiir",
            "known_risks": ["FATAL — condition structurally encoded in event_code metadata"],
            "potential_target_tasks": ["NONE — invalid for condition decoding"],
            "initial_suitability_score": -1,
            "recommended_priority": "reject",
        },
    ]

    registry = {**_safety(), "tool": "eeg_v60_candidate_dataset_registry",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "datasets": datasets}
    with open(os.path.join(EXPORTS, "eeg_v60_candidate_dataset_registry.json"), "w") as f:
        json.dump(registry, f, indent=2, default=str)

    print(f"Registry: {len(datasets)} candidate datasets", file=sys.stderr)
    return 0


def run_rubric():
    rubric = {
        **_safety(),
        "tool": "eeg_v60_dataset_safety_rubric",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scoring_dimensions": {
            "metadata_independence": {
                "weight": 0.35,
                "criteria": [
                    "condition labels NOT directly encoded in event codes (pass=25, fail=0)",
                    "event codes do not trivially reveal label (pass=25, partial=10, fail=0)",
                    "stimulus identity balanced across condition labels (pass=25, partial=10, fail=0)",
                    "metadata-only baseline <= 0.60 (pass=25, <=0.70=10, >0.70=0)",
                ],
            },
            "experimental_design": {
                "weight": 0.25,
                "criteria": [
                    "randomized trial order per subject (pass=30, unknown=10, fail=0)",
                    "balanced classes (pass=30, mild_imbalance=15, severe=0)",
                    "same/controlled stimuli across conditions (pass=20, partial=10, fail=0)",
                    "repeated conditions across subjects (pass=20, partial=10, fail=0)",
                ],
            },
            "generalization_potential": {
                "weight": 0.20,
                "criteria": [
                    ">= 10 subjects (pass=40, >=5=20, <5=0)",
                    "held-out-subject validation possible (pass=30, unknown=10, no=0)",
                    "held-out-stimulus validation possible (pass=30, unknown=10, no=0)",
                ],
            },
            "signal_quality": {
                "weight": 0.10,
                "criteria": [
                    ">= 20 channels (pass=40, >=8=20, <8=0)",
                    ">= 128 Hz sampling rate (pass=30, >=64=15, <64=0)",
                    "raw EEG available (pass=30, no=0)",
                ],
            },
            "research_alignment": {
                "weight": 0.10,
                "criteria": [
                    "aligns with IMAGINA mental imagery goal (pass=50, partial=25, no=0)",
                    "supports representational/geometry analysis (pass=50, partial=25, no=0)",
                ],
            },
        },
        "verdicts": {
            "strong_candidate": "total_score >= 75 AND metadata_independence >= 25",
            "candidate": "total_score >= 50",
            "needs_manual_review": "total_score >= 40 AND unknown_metadata == true",
            "reject": "total_score < 40 OR metadata_independence == 0",
        },
        "reject_criteria": [
            "metadata-only baseline can trivially predict labels",
            "condition is directly encoded in event code with no counterbalancing",
            "no subject-level split possible (< 3 subjects)",
            "no raw/epoch data available",
            "fewer than 5 subjects",
        ],
    }
    with open(os.path.join(EXPORTS, "eeg_v60_dataset_safety_rubric.json"), "w") as f:
        json.dump(rubric, f, indent=2, default=str)
    print("Safety rubric defined", file=sys.stderr)
    return 0


def run_protocol():
    protocol = {
        **_safety(),
        "tool": "eeg_v60_metadata_preflight_protocol",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": (
            "Universal metadata-confound screening protocol. "
            "MUST run before any model training on any EEG dataset."
        ),
        "metadata_baselines_required": [
            {"name": "subject_id_only", "description": "Encode only subject identity"},
            {"name": "event_code_only", "description": "Encode only event/trigger codes"},
            {"name": "stimulus_id_only", "description": "Encode only stimulus identity if available"},
            {"name": "trial_index_only", "description": "Encode only trial temporal order"},
            {"name": "block_or_session_id", "description": "Encode block/session identifier"},
            {"name": "combined_metadata", "description": "All non-EEG metadata combined"},
            {"name": "dummy_baseline", "description": "Stratified DummyClassifier"},
        ],
        "acceptance_thresholds": {
            "event_code_baseline_max": 0.55,
            "combined_metadata_baseline_max": 0.60,
            "eeg_model_beats_metadata_by": "statistically significant margin (p < 0.05)",
            "requires_loso": True,
            "requires_stimulus_holdout_if_available": True,
        },
        "output_schema": {
            "dataset_name": "", "task_name": "",
            "metadata_baselines": {}, "metadata_safe": False,
            "failure_reasons": [], "allowed_to_train_eeg_model": False,
        },
        "usage": (
            "Run on EVERY candidate dataset before training. "
            "If metadata_safe is False, do NOT train. "
            "Report the preflight result as the first experimental finding."
        ),
    }
    with open(os.path.join(EXPORTS, "eeg_v60_metadata_preflight_protocol.json"), "w") as f:
        json.dump(protocol, f, indent=2, default=str)
    print("Preflight protocol defined", file=sys.stderr)
    return 0


def run_openmiir_control():
    control = {
        **_safety(),
        "tool": "eeg_v60_openmiir_negative_control",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_name": "OpenMIIR",
        "dataset_status": "invalid_for_condition_decoding",
        "metadata_safe": False,
        "failure_reason": "event_code_structurally_encodes_condition",
        "evidence": (
            "V4.9 forensic audit: combined metadata = 1.0 accuracy across all tasks. "
            "V5.0 task redesign: 0/8 candidate tasks passed metadata validation. "
            "Event codes (11-14, 21-24, 31-34, 41-44) directly encode stimulus group + condition. "
        ),
        "allowed_uses": [
            "exploratory spectral analysis",
            "representational geometry demonstration (RSA, RDM, PID-EEG)",
            "confound audit methodology demonstration",
            "negative-control dataset for preflight protocol validation",
            "subject-identity encoding analysis",
            "leakage-free nested LOSO protocol development",
        ],
        "forbidden_uses": [
            "condition decoding claims",
            "imagery decoding claims",
            "BCI-ready claims",
            "production or clinical claims",
            "mind-reading or dream-decoding claims",
            "reliable perception vs imagery classification",
        ],
        "role": (
            "OpenMIIR served as the primary dataset for V1-V5 development. "
            "It demonstrated the research pipeline (loading, epoching, SSL, representational analysis) "
            "and ultimately revealed the importance of metadata confound screening. "
            "It is now retired from condition-decoding and serves as the negative-control "
            "dataset proving the preflight protocol correctly rejects confounded tasks."
        ),
    }
    with open(os.path.join(EXPORTS, "eeg_v60_openmiir_negative_control.json"), "w") as f:
        json.dump(control, f, indent=2, default=str)
    print("OpenMIIR negative-control artifact generated", file=sys.stderr)
    return 0


def run_rank():
    registry = [
        {"name": "PhysioNet EEG Motor Movement/Imagery", "tier": 1, "score": 80,
         "reason": "109 subjects, 64 channels, execution vs imagery task, large public dataset",
         "checks_needed": ["verify event code independence", "check execution/imagery event overlap"]},
        {"name": "BNCI 2014-001 Motor Imagery", "tier": 1, "score": 75,
         "reason": "Standard MI benchmark, well-documented, MOABB-compatible",
         "checks_needed": ["verify cue-event codes don't trivially encode condition"]},
        {"name": "BCI Competition IV 2a", "tier": 1, "score": 70,
         "reason": "Classic MI benchmark, 4-class, widely used",
         "checks_needed": ["check if class label is embedded in event code"]},
        {"name": "OpenBMI Motor Imagery", "tier": 1, "score": 75,
         "reason": "54 subjects, 62 channels, left/right hand MI",
         "checks_needed": ["verify metadata independence"]},
        {"name": "THINGS-EEG", "tier": 2, "score": 60,
         "reason": "Large visual perception dataset, not imagery but useful for encoding models",
         "checks_needed": ["verify object category can be decoded without metadata leakage"]},
        {"name": "Imagined Speech EEG", "tier": 3, "score": 40,
         "reason": "Only 6 channels, small n, limited metadata — insufficient for robust validation",
         "checks_needed": ["too many limitations — reject for V6.x"]},
        {"name": "Auditory Imagery EEG (Marion)", "tier": 3, "score": 20,
         "reason": "Data may not be public, metadata unknown, cannot preflight",
         "checks_needed": ["reject until data becomes publicly available"]},
        {"name": "OpenMIIR", "tier": 3, "score": -1,
         "reason": "CONFOUNDED — negative control only. Do not use for condition decoding.",
         "checks_needed": ["N/A — permanently rejected for condition decoding"]},
    ]
    ranked = {**_safety(), "tool": "eeg_v60_ranked_dataset_candidates",
              "generated_at": datetime.now(timezone.utc).isoformat(),
              "ranked_datasets": registry}
    with open(os.path.join(EXPORTS, "eeg_v60_ranked_dataset_candidates.json"), "w") as f:
        json.dump(ranked, f, indent=2, default=str)

    md_lines = ["# Ranked Dataset Candidates", "",
                "## Tier 1 — Strongest Candidates",
                "| Dataset | Score | Reason |",
                "|---------|-------|--------|"]
    for d in registry:
        if d["tier"] == 1:
            md_lines.append(f"| {d['name']} | {d['score']} | {d['reason']} |")
    md_lines += ["", "## Tier 2 — Usable with Caveats"]
    for d in registry:
        if d["tier"] == 2:
            md_lines.append(f"| {d['name']} | {d['score']} | {d['reason']} |")
    md_lines += ["", "## Tier 3 — Reject / Not Suitable"]
    for d in registry:
        if d["tier"] == 3:
            md_lines.append(f"| {d['name']} | {d['score']} | {d['reason']} |")
    with open(os.path.join(EXPORTS, "eeg_v60_ranked_dataset_candidates.md"), "w") as f:
        f.write("\n".join(md_lines))

    print(f"Ranked: {sum(1 for d in registry if d['tier']==1)} Tier-1, "
          f"{sum(1 for d in registry if d['tier']==2)} Tier-2, "
          f"{sum(1 for d in registry if d['tier']==3)} Tier-3",
          file=sys.stderr)
    return 0


def run_recommend():
    recommendation = {
        **_safety(),
        "tool": "eeg_v60_next_dataset_recommendation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manual_review_required_before_selection": True,
        "primary_candidate": {
            "dataset_name": "PhysioNet EEG Motor Movement/Imagery (eegmmidb)",
            "why": [
                "109 subjects — largest public motor imagery/execution dataset",
                "64 channels — sufficient for spatial/representational analysis",
                "Execution vs imagery task maps well to IMAGINA goal",
                "Publicly accessible via PhysioNet",
                "Well-documented, widely cited",
                "Supports LOSO with many folds",
            ],
            "target_task": "motor_execution_vs_imagery (fists and feet)",
            "expected_challenges": [
                "Event codes need metadata preflight before training",
                "Execution may have larger ERP/artifacts that must be controlled",
                "Need to verify condition labels are not encoded in metadata",
            ],
            "preflight_checks_required": [
                "event_code metadata baseline <= 0.55",
                "combined metadata baseline <= 0.60",
                "LOSO CV with 10+ folds",
                "Permutation test p < 0.05",
                "Check if execution ERPs confound the classification",
            ],
            "implementation_plan": [
                "V6.1: Download dataset via MOABB or PhysioNet",
                "V6.1: Run metadata preflight protocol",
                "V6.1: If metadata-safe, build epoch dataset",
                "V6.2: Handcrafted feature benchmark",
                "V6.3: SSL encoder training",
                "V6.4: Representational analysis",
            ],
        },
        "backup_candidate": {
            "dataset_name": "BNCI 2014-001 Motor Imagery",
            "why": [
                "Classic MI benchmark, 4-class (left/right hand, feet, tongue)",
                "MOABB-compatible for easy loading",
                "Well-studied — many published baselines available",
                "22 channels, 250 Hz",
            ],
        },
    }
    with open(os.path.join(EXPORTS, "eeg_v60_next_dataset_recommendation.json"), "w") as f:
        json.dump(recommendation, f, indent=2, default=str)

    md_lines = [
        "# V6.1 Recommended Dataset",
        "",
        "## Primary: PhysioNet EEG Motor Movement/Imagery",
        "",
        "**Why**: 109 subjects, 64 channels, execution vs imagery, public, well-documented.",
        "**Target task**: Motor execution vs imagery (fists + feet)",
        "**Preflight required**: Yes — must pass metadata screening before any model training.",
        "",
        "## Backup: BNCI 2014-001 Motor Imagery",
        "",
        "Classic 4-class MI benchmark, MOABB-compatible.",
    ]
    with open(os.path.join(EXPORTS, "eeg_v60_next_dataset_recommendation.md"), "w") as f:
        f.write("\n".join(md_lines))

    print(f"Recommendation: primary={recommendation['primary_candidate']['dataset_name']}",
          file=sys.stderr)
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)

    print(f"V6.0 mode={args.mode}", file=sys.stderr)

    if args.mode in ("registry", "all"):
        run_registry()
    if args.mode in ("rubric", "all"):
        run_rubric()
    if args.mode in ("protocol", "all"):
        run_protocol()
    if args.mode in ("openmiir_control", "all"):
        run_openmiir_control()
    if args.mode in ("rank", "all"):
        run_rank()
    if args.mode in ("recommend", "all"):
        run_recommend()
    return 0


if __name__ == "__main__":
    sys.exit(main())
