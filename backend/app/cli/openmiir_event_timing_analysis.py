"""OpenMIIR Event Timing Analysis CLI.

Analyzes stim channel event timing patterns across all subjects:
- Inter-event interval distributions
- Code-wise timing statistics
- Code transition matrices
- Block boundary / trial onset detection
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
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_event_timing_analysis")
    p.add_argument("--dataset", default="openmiir")
    p.add_argument("--max-subjects", type=int, default=10)
    p.add_argument("--output-prefix", default="openmiir_event_timing")
    return p


def _load_stim_events(manifest_path, max_subjects):
    fif_files = []
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            fif_files = json.load(f).get("files", [])[:max_subjects]

    results = []
    for fif in fif_files:
        subj = os.path.splitext(os.path.basename(fif))[0]
        try:
            import mne
            raw = mne.io.read_raw_fif(fif, preload=False, verbose=False)
            sfreq = raw.info["sfreq"]
            stim_ch_name = None
            for ch_name in raw.ch_names:
                idx = raw.ch_names.index(ch_name)
                ch_type = raw.get_channel_types(picks=[idx])[0]
                if "stim" in str(ch_type).lower() or "sti" in ch_name.lower():
                    stim_ch_name = ch_name
                    break
            if not stim_ch_name:
                results.append({"subject": subj, "events": [], "error": "no_stim_channel"})
                continue

            events = mne.find_events(raw, stim_channel=stim_ch_name, shortest_event=1, verbose=False)
            event_list = []
            for ev in events:
                code = int(ev[2])
                time_sec = float(ev[0]) / sfreq
                event_list.append({
                    "sample": int(ev[0]),
                    "time_sec": round(time_sec, 6),
                    "code": code,
                })

            # Compute inter-event intervals
            times = [e["time_sec"] for e in event_list]
            ieis = [times[i + 1] - times[i] for i in range(len(times) - 1)] if len(times) > 1 else []
            codes = [e["code"] for e in event_list]

            # Code-wise timing
            code_timing = {}
            for e in event_list:
                c = e["code"]
                if c not in code_timing:
                    code_timing[c] = {"count": 0, "times": []}
                code_timing[c]["count"] += 1
                code_timing[c]["times"].append(e["time_sec"])

            # Code transitions
            transitions = Counter()
            if len(codes) > 1:
                for i in range(len(codes) - 1):
                    transitions[(codes[i], codes[i + 1])] += 1

            # Block boundary detection (long IEIs)
            if ieis:
                iei_median = float(np.median(ieis))
                iei_mad = float(np.median(np.abs(np.array(ieis) - iei_median)))
                boundary_threshold = iei_median + 5 * iei_mad
                boundaries = [
                    {"index": i, "time_sec": times[i], "iei_sec": round(ieis[i], 4),
                     "from_code": codes[i], "to_code": codes[i + 1]}
                    for i in range(len(ieis))
                    if ieis[i] > boundary_threshold
                ]
            else:
                boundaries = []
                iei_median = None

            results.append({
                "subject": subj,
                "sfreq": sfreq,
                "n_events": len(event_list),
                "unique_codes": sorted(set(codes)),
                "time_span_sec": round(times[-1] - times[0], 2) if times else None,
                "event_times_sec": [round(t, 4) for t in times],
                "inter_event_intervals_sec": [round(i, 4) for i in ieis],
                "iei_stats": {
                    "mean": round(float(np.mean(ieis)), 4) if ieis else None,
                    "median": round(float(np.median(ieis)), 4) if ieis else None,
                    "std": round(float(np.std(ieis)), 4) if ieis else None,
                    "min": round(float(np.min(ieis)), 4) if ieis else None,
                    "max": round(float(np.max(ieis)), 4) if ieis else None,
                } if ieis else None,
                "code_wise_timing": {
                    str(k): {
                        "count": v["count"],
                        "mean_interval": round(v["count"] / (times[-1] - times[0]), 2) if times else None,
                        "first_sec": round(min(v["times"]), 4),
                        "last_sec": round(max(v["times"]), 4),
                    }
                    for k, v in code_timing.items()
                },
                "block_boundaries": boundaries,
                "likely_markers": {
                    "block_boundaries": len(boundaries),
                    "dense_codes": sorted([k for k, v in code_timing.items() if v["count"] > len(event_list) * 0.1]),
                    "sparse_codes": sorted([k for k, v in code_timing.items() if v["count"] < 10]),
                },
                "event_list": event_list,
                "top_transitions": [
                    {"from": int(t[0]), "to": int(t[1]), "count": c}
                    for t, c in transitions.most_common(50)
                ],
            })
            del raw

        except Exception as e:
            results.append({"subject": subj, "events": [], "error": str(e)})

    return results


def _build_transition_matrix(subject_results):
    all_transitions = Counter()
    for r in subject_results:
        if not r.get("event_list"):
            continue
        codes = [e["code"] for e in r["event_list"]]
        for i in range(len(codes) - 1):
            all_transitions[(codes[i], codes[i + 1])] += 1
    return all_transitions


def _generate_plots(subject_results, output_prefix):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []

    figures = []

    # Code counts plot
    all_codes = Counter()
    for r in subject_results:
        for e in r.get("event_list", []):
            all_codes[e["code"]] += 1

    if all_codes:
        codes = sorted(all_codes.keys())
        counts = [all_codes[c] for c in codes]
        fig, ax = plt.subplots(figsize=(14, 5))
        ax.bar(range(len(codes)), counts, color="steelblue", edgecolor="white")
        ax.set_xticks(range(len(codes)))
        ax.set_xticklabels(codes, rotation=90, fontsize=7)
        ax.set_xlabel("Event Code")
        ax.set_ylabel("Total Count (All Subjects)")
        ax.set_title("OpenMIIR Event Code Counts")
        fig.tight_layout()
        path = os.path.join(FIGURES_DIR, f"{output_prefix}_code_counts.png")
        fig.savefig(path, dpi=150)
        plt.close(fig)
        figures.append(path)

    # IEI distribution plot
    all_ieis = []
    for r in subject_results:
        all_ieis.extend(r.get("inter_event_intervals_sec", []))
    if all_ieis:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.hist(all_ieis, bins=100, color="steelblue", edgecolor="white", alpha=0.8)
        ax.set_xlabel("Inter-Event Interval (seconds)")
        ax.set_ylabel("Frequency")
        ax.set_title("OpenMIIR Inter-Event Interval Distribution")
        ax.axvline(np.median(all_ieis), color="red", linestyle="--", label=f"Median: {np.median(all_ieis):.3f}s")
        ax.legend()
        fig.tight_layout()
        path = os.path.join(FIGURES_DIR, f"{output_prefix}_inter_event_intervals.png")
        fig.savefig(path, dpi=150)
        plt.close(fig)
        figures.append(path)

    return figures


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    manifest_path = os.path.join(
        BASE, "..", "..", "data", "external", "openmiir", "manifest.json"
    )

    if not os.path.exists(manifest_path):
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    subject_results = _load_stim_events(manifest_path, args.max_subjects)

    n_with_events = sum(1 for r in subject_results if r.get("n_events", 0) > 0)
    total_events = sum(r.get("n_events", 0) for r in subject_results)
    all_codes = set()
    for r in subject_results:
        all_codes.update(r.get("unique_codes", []))

    transitions = _build_transition_matrix(subject_results)

    figures = _generate_plots(subject_results, args.output_prefix)

    analysis = {
        "tool": "openmiir_event_timing_analysis_v3.9.2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": args.dataset,
        "max_subjects": args.max_subjects,
        "subjects_with_events": n_with_events,
        "total_events": total_events,
        "unique_event_codes": sorted(all_codes),
        "unique_code_count": len(all_codes),
        "inter_event_interval_stats": {
            "mean": round(float(np.mean([r.get("iei_stats", {}).get("mean", 0) or 0 for r in subject_results
                                         if r.get("iei_stats")])), 4) if n_with_events > 0 else None,
            "median": round(float(np.median([r.get("iei_stats", {}).get("median", 0) or 0 for r in subject_results
                                              if r.get("iei_stats")])), 4) if n_with_events > 0 else None,
        },
        "subject_results": [
            {k: v for k, v in r.items() if k != "event_list"}
            for r in subject_results
        ],
        "code_family_hypotheses": {
            "block_boundary_candidates": [
                c for c in all_codes if c >= 1000
            ],
            "high_frequency_trial_codes": [
                c for c in all_codes
                if sum(1 for r in subject_results
                       for e in r.get("event_list", [])
                       if e["code"] == c) > total_events * 0.02
            ][:20],
        },
        "top_transitions": [
            {"from": int(t[0]), "to": int(t[1]), "count": c}
            for t, c in transitions.most_common(50)
        ],
        "figures": figures,
        "disclaimer": "Timing patterns are observational, not semantic labels. "
                      "No perception/imagery classification is claimed.",
        "no_raw_eeg_exposed": True,
    }

    json_path = os.path.join(EXPORTS, f"{args.output_prefix}_analysis.json")
    with open(json_path, "w") as f:
        json.dump(analysis, f, indent=2, default=str)

    # CSV transition matrix
    csv_path = os.path.join(EXPORTS, f"{args.output_prefix}_transition_matrix.csv")
    with open(csv_path, "w") as f:
        f.write("from_code,to_code,count\n")
        for t, c in transitions.most_common(200):
            f.write(f"{t[0]},{t[1]},{c}\n")

    # MD report
    md_lines = [
        "# OpenMIIR Event Timing Analysis",
        f"**Subjects with events**: {n_with_events}/{args.max_subjects}",
        f"**Total events**: {total_events}",
        f"**Unique codes**: {len(all_codes)}",
        f"**Codes**: {sorted(all_codes)}",
        "",
        "## Block Boundary Candidates (codes >= 1000)",
    ]
    for c in sorted(all_codes):
        if c >= 1000:
            count = sum(1 for r in subject_results for e in r.get("event_list", []) if e["code"] == c)
            md_lines.append(f"- Code {c}: {count} occurrences")

    md_lines.append("")
    md_lines.append("## Top Event Code Transitions")
    for t, c in transitions.most_common(20):
        md_lines.append(f"- {t[0]} -> {t[1]}: {c} times")

    md_lines.append("")
    md_lines.append(f"## Figures: {len(figures)}")

    md_path = os.path.join(EXPORTS, f"{args.output_prefix}_analysis.md")
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))

    print(f"Event timing: subjects={n_with_events} total_events={total_events} codes={len(all_codes)}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
