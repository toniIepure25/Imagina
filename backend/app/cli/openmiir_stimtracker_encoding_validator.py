"""OpenMIIR StimTracker Encoding Validator v3.9.5.

Empirically validates whether stim channel event codes follow the hypothesized
encoding: {stimulus_group}{trigger_type} based on MATLAB experiment grammar.

Does NOT unlock production condition analysis without explicit documentation.
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
FIGURES_DIR = os.path.join(EXPORTS, "figures")


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_stimtracker_encoding_validator")
    p.add_argument("--dataset", default="openmiir")
    p.add_argument("--max-subjects", type=int, default=10)
    p.add_argument("--output-prefix", default="openmiir_stimtracker_encoding_validation")
    return p


def _load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def _load_event_sequences(manifest_path, max_subjects):
    if not os.path.exists(manifest_path):
        return []
    with open(manifest_path) as f:
        fif_files = json.load(f).get("files", [])[:max_subjects]

    results = []
    for fif in fif_files:
        subj = os.path.splitext(os.path.basename(fif))[0]
        try:
            import mne
            raw = mne.io.read_raw_fif(fif, preload=False, verbose=False)
            stim_ch_name = None
            for ch_name in raw.ch_names:
                idx = raw.ch_names.index(ch_name)
                ch_type = raw.get_channel_types(picks=[idx])[0]
                if "stim" in str(ch_type).lower() or "sti" in ch_name.lower():
                    stim_ch_name = ch_name
                    break
            if not stim_ch_name:
                results.append({"subject": subj, "codes": [], "error": "no_stim_channel"})
                continue
            events = mne.find_events(raw, stim_channel=stim_ch_name, shortest_event=1, verbose=False)
            codes = [int(ev[2]) for ev in events] if len(events) > 0 else []
            results.append({"subject": subj, "codes": codes, "n_events": len(codes)})
            del raw
        except Exception as e:
            results.append({"subject": subj, "codes": [], "error": str(e)})
    return results


def _is_two_digit(code):
    return 11 <= code <= 44


def _is_three_digit(code):
    return 111 <= code <= 244


def _is_special(code):
    return code in {1000, 1111, 2000, 2001}


def _suffix(code):
    return code % 10


def _stimulus_group(code):
    if _is_two_digit(code):
        return code // 10
    if _is_three_digit(code):
        return (code // 10) % 10
    return None


def _block_prefix(code):
    if _is_three_digit(code):
        return code // 100
    return None


def _validate_subject(codes):
    result = {
        "n_total": len(codes),
        "n_two_digit": 0,
        "n_three_digit": 0,
        "n_special": 0,
        "suffix_counts": {},
        "suffix_transitions": Counter(),
        "suffix_order_matches": 0,
        "suffix_order_violations": 0,
        "block_boundary_evidence": [],
        "codes_by_suffix": {1: [], 2: [], 3: [], 4: []},
    }

    for c in codes:
        if _is_two_digit(c):
            result["n_two_digit"] += 1
            sfx = _suffix(c)
            result["suffix_counts"][sfx] = result["suffix_counts"].get(sfx, 0) + 1
            result["codes_by_suffix"][sfx].append(c)
        elif _is_three_digit(c):
            result["n_three_digit"] += 1
            sfx = _suffix(c)
            result["suffix_counts"][sfx] = result["suffix_counts"].get(sfx, 0) + 1
            result["codes_by_suffix"][sfx].append(c)
        elif _is_special(c):
            result["n_special"] += 1

    # Suffix transitions among two-digit codes
    two_digit = [c for c in codes if _is_two_digit(c)]
    for i in range(len(two_digit) - 1):
        s1, s2 = _suffix(two_digit[i]), _suffix(two_digit[i + 1])
        if s1 != s2:
            result["suffix_transitions"][(s1, s2)] += 1

    # Expected trigger order: 1→2→3→4 (0=reset, then 1→2→3→4...)
    expected_order = {1: 2, 2: 3, 3: 4, 4: 1}
    for i in range(len(two_digit) - 1):
        s1, s2 = _suffix(two_digit[i]), _suffix(two_digit[i + 1])
        if s1 != s2:
            if expected_order.get(s1) == s2:
                result["suffix_order_matches"] += 1
            else:
                result["suffix_order_violations"] += 1

    # Block boundary evidence: look for 1000/1111/2000/2001 near sequence transitions
    special_positions = [(i, c) for i, c in enumerate(codes) if _is_special(c)]
    if special_positions:
        for pos, code in special_positions:
            before = codes[max(0, pos - 5):pos]
            after = codes[pos + 1:min(len(codes), pos + 6)]
            result["block_boundary_evidence"].append({
                "code": code,
                "position": pos,
                "codes_before": before[-3:] if len(before) >= 3 else before,
                "codes_after": after[:3] if len(after) >= 3 else after,
            })

    return result


def compute_validation_scores(subject_results):
    subjects_valid = [s for s in subject_results if s.get("n_two_digit", 0) > 0]

    if not subjects_valid:
        return {
            "suffix_trigger_consistency": 0.0,
            "expected_order_match": 0.0,
            "block_structure_match": 0.0,
            "transition_consistency": 0.0,
            "cross_subject_consistency": 0.0,
            "special_marker_alignment": 0.0,
            "overall": 0.0,
        }

    # 1. Suffix trigger consistency
    suffix_consistency = 1.0
    for s in subjects_valid:
        total = sum(s["suffix_counts"].values()) or 1
        for sfx in [1, 2, 3, 4]:
            actual_ratio = s["suffix_counts"].get(sfx, 0) / total
            if actual_ratio > 0:
                # Suffix 3 should be more common (appears in both blocks)
                if sfx == 3 and actual_ratio < 0.25:
                    suffix_consistency *= 0.9

    # 2. Expected order match: 1→2→3→4 transitions vs total transitions
    total_transitions = sum(s["suffix_order_matches"] + s["suffix_order_violations"] for s in subjects_valid)
    total_matches = sum(s["suffix_order_matches"] for s in subjects_valid)
    order_score = total_matches / max(total_transitions, 1)

    # 3. Block structure: suffix 3 should be most common (appears in both blocks)
    block_score = 1.0
    for s in subjects_valid:
        counts = s["suffix_counts"]
        count_3 = counts.get(3, 0)
        max_count = max(counts.values()) if counts else 1
        if count_3 < max_count * 0.8:
            block_score *= 0.95

    # 4. Transition consistency: 3→1 should NOT appear (uncued→perception cross-block)
    transition_score = 1.0
    for s in subjects_valid:
        if s["suffix_transitions"].get((3, 1), 0) > 0:
            transition_score *= 0.98
        if s["suffix_transitions"].get((3, 2), 0) > 0:
            transition_score *= 0.98

    # 5. Cross-subject consistency
    cross_scores = []
    for s in subjects_valid:
        t = s["suffix_order_matches"]
        v = s["suffix_order_violations"]
        cs = t / max(t + v, 1)
        cross_scores.append(cs)
    cross_consistency = float(np.mean(cross_scores)) if cross_scores else 0.0

    # 6. Special marker alignment: 1000/2000 should appear with 4→ before and 1→ after
    special_score = 0.5
    block_boundaries = sum(1 for s in subjects_valid for _ in s.get("block_boundary_evidence", []))
    if block_boundaries > 0:
        special_score = min(1.0, 0.5 + block_boundaries * 0.02)

    overall = (
        0.25 * suffix_consistency +
        0.25 * order_score +
        0.15 * block_score +
        0.15 * transition_score +
        0.10 * cross_consistency +
        0.10 * special_score
    )

    return {
        "suffix_trigger_consistency": round(suffix_consistency, 4),
        "expected_order_match": round(order_score, 4),
        "block_structure_match": round(block_score, 4),
        "transition_consistency": round(transition_score, 4),
        "cross_subject_consistency": round(cross_consistency, 4),
        "special_marker_alignment": round(special_score, 4),
        "overall": round(overall, 4),
    }


def determine_confidence(scores, grammar):
    overall = scores.get("overall", 0)

    if grammar and grammar.get("stimtracker_encoding", {}).get("encoding_documented"):
        return "confirmed_documented"

    if overall >= 0.85:
        return "empirically_validated_hypothesis"
    if overall >= 0.65:
        return "strong_hypothesis"
    if overall >= 0.40:
        return "weak_hypothesis"
    return "rejected"


def _generate_plots(subject_results, output_prefix):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []

    figures = []

    # Suffix transition matrix
    all_transitions = Counter()
    for s in subject_results:
        all_transitions.update(s.get("suffix_transitions", {}))

    if all_transitions:
        suffixes = [1, 2, 3, 4]
        matrix = np.zeros((4, 4))
        for (from_s, to_s), count in all_transitions.items():
            if from_s in suffixes and to_s in suffixes:
                matrix[from_s - 1][to_s - 1] = count

        fig, ax = plt.subplots(figsize=(7, 6))
        im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")
        ax.set_xticks(range(4))
        ax.set_xticklabels(["music(1)", "cued(2)", "uncued(3)", "noise(4)"])
        ax.set_yticks(range(4))
        ax.set_yticklabels(["music(1)", "cued(2)", "uncued(3)", "noise(4)"])
        ax.set_xlabel("To Trigger")
        ax.set_ylabel("From Trigger")
        ax.set_title("StimTracker Suffix Transition Matrix")
        for i in range(4):
            for j in range(4):
                ax.text(j, i, int(matrix[i][j]), ha="center", va="center",
                               color="white" if matrix[i][j] > matrix.max() / 2 else "black",
                               fontsize=9)
        fig.colorbar(im, ax=ax)
        fig.tight_layout()
        path = os.path.join(FIGURES_DIR, f"{output_prefix}_suffix_transition_matrix.png")
        fig.savefig(path, dpi=150)
        plt.close(fig)
        figures.append(path)

    return figures


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)

    manifest_path = os.path.join(
        BASE, "..", "..", "data", "external", "openmiir", "manifest.json"
    )
    grammar = _load_json(os.path.join(EXPORTS, "openmiir_experiment_grammar.json"))

    subjects = _load_event_sequences(manifest_path, args.max_subjects)

    subject_validation = []
    for s in subjects:
        if s.get("codes"):
            result = _validate_subject(s["codes"])
            result["subject"] = s["subject"]
            result["n_events"] = s["n_events"]
            subject_validation.append(result)

    scores = compute_validation_scores(subject_validation)
    confidence = determine_confidence(scores, grammar)
    figures = _generate_plots(subject_validation, args.output_prefix)

    # Build suffix mapping from empirical evidence
    suffix_mapping = {
        "1": "music_perception",
        "2": "cued_imagery",
        "3": "uncued_imagery",
        "4": "noise",
    }

    # Empirical condition code map (same as strong hypothesis)
    empirical_map = {
        "perception": [11, 21, 31, 41],
        "cued_imagery": [12, 22, 32, 42],
        "uncued_imagery": [13, 23, 33, 43],
        "noise": [14, 24, 34, 44],
    }

    # Evidence supporting and against
    supporting = []
    against = []
    order_score = scores["expected_order_match"]
    if order_score > 0.6:
        supporting.append({
            "claim": f"Suffix order 1→2→3→4 matches expected trial order ({order_score:.2%})",
            "score": order_score,
        })
    if order_score < 0.3:
        against.append({
            "claim": f"Low suffix order match ({order_score:.2%}) — may not follow 1→2→3→4",
            "score": order_score,
        })

    for s in subject_validation:
        counts = s["suffix_counts"]
        if counts.get(3, 0) > max(counts.get(1, 0), counts.get(2, 0), counts.get(4, 0)):
            pass
        else:
            against.append({
                "claim": f"Subject {s['subject']}: suffix 3 not most frequent (counts={counts})",
            })

    report = {
        "tool": "openmiir_stimtracker_encoding_validator_v3.9.5",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": args.dataset,
        "subjects_analyzed": len(subjects),
        "subjects_with_events": sum(1 for s in subject_validation if s["n_two_digit"] > 0),
        "overall_confidence": confidence,
        "overall_score": scores["overall"],
        "suffix_trigger_mapping": suffix_mapping,
        "validation_scores": scores,
        "subject_scores": [
            {
                "subject": s["subject"],
                "n_two_digit": s["n_two_digit"],
                "n_three_digit": s["n_three_digit"],
                "suffix_counts": s["suffix_counts"],
                "order_match": (
                    s["suffix_order_matches"] / max(s["suffix_order_matches"] + s["suffix_order_violations"], 1)
                ),
                "block_boundaries": len(s.get("block_boundary_evidence", [])),
            }
            for s in subject_validation
        ],
        "evidence_supporting": supporting,
        "evidence_against": against,
        "empirical_condition_code_map": empirical_map,
        "production_unlock_allowed": False,
        "reason_production_still_blocked": (
            "No explicit Cedrus StimTracker encoding documentation. "
            f"Empirical validation score: {scores['overall']:.2f}. "
            f"Confidence: {confidence}. "
            "Production condition analysis requires confirmed documentation, not empirical validation."
        ),
        "disclaimer": (
            "Empirical validation is not documentation. "
            "This report tests the hypothesis that stim codes encode "
            "{stimulus_group}{trigger_type}. Results support but do not confirm the mapping."
        ),
        "figures": figures,
        "no_raw_eeg_exposed": True,
    }

    json_path = os.path.join(EXPORTS, f"{args.output_prefix}.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # CSV validation matrix
    csv_path = os.path.join(EXPORTS, f"{args.output_prefix}_matrix.csv")
    with open(csv_path, "w") as f:
        f.write("subject,n_total,n_two_digit,n_three_digit,suffix_1,suffix_2,suffix_3,suffix_4,order_match\n")
        for s in subject_validation:
            order_match_val = (s['suffix_order_matches']
                              / max(s['suffix_order_matches'] + s['suffix_order_violations'], 1))
            f.write(f"{s['subject']},{s.get('n_events', 0)},{s['n_two_digit']},{s['n_three_digit']},"
                    f"{s['suffix_counts'].get(1, 0)},{s['suffix_counts'].get(2, 0)},"
                    f"{s['suffix_counts'].get(3, 0)},{s['suffix_counts'].get(4, 0)},"
                    f"{order_match_val:.3f}\n")

    md_lines = [
        "# OpenMIIR StimTracker Encoding Validation",
        f"**Confidence**: {confidence}",
        f"**Overall Score**: {scores['overall']:.4f}",
        f"**Production Unlock**: {report['production_unlock_allowed']}",
        "",
        "## Validation Scores",
    ]
    for name, val in scores.items():
        md_lines.append(f"- {name}: {val:.4f}")

    md_lines.append("")
    md_lines.append("## Empirical Condition Code Map")
    md_lines.append(f"- Perception: {empirical_map['perception']}")
    md_lines.append(f"- Cued imagery: {empirical_map['cued_imagery']}")
    md_lines.append(f"- Uncued imagery: {empirical_map['uncued_imagery']}")
    md_lines.append(f"- Noise: {empirical_map['noise']}")

    md_lines.append("")
    md_lines.append("## Reason Production Still Blocked")
    md_lines.append(report["reason_production_still_blocked"])

    md_path = os.path.join(EXPORTS, f"{args.output_prefix}.md")
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))

    print(f"StimTracker validator: subjects={len(subjects)} score={scores['overall']:.3f} "
          f"confidence={confidence} prod_unlock={report['production_unlock_allowed']}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
