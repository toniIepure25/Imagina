"""OpenMIIR Event Sequence Report CLI.

Extracts ordered event sequences from all subjects, compresses repeated patterns,
identifies motifs, and builds global motif catalog.
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
FIGURES_DIR = os.path.join(EXPORTS, "figures")


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_event_sequence_report")
    p.add_argument("--dataset", default="openmiir")
    p.add_argument("--max-subjects", type=int, default=10)
    p.add_argument("--output-prefix", default="openmiir_event_sequence")
    return p


def _load_events(manifest_path, max_subjects):
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
                results.append({"subject": subj, "sequence": [], "error": "no_stim_channel"})
                continue

            events = mne.find_events(raw, stim_channel=stim_ch_name, shortest_event=1, verbose=False)
            codes = [int(ev[2]) for ev in events]
            results.append({
                "subject": subj,
                "sfreq": sfreq,
                "sequence": codes,
                "n_events": len(codes),
                "unique_codes": sorted(set(codes)),
            })
            del raw
        except Exception as e:
            results.append({"subject": subj, "sequence": [], "error": str(e)})
    return results


def _compress_runs(sequence):
    if not sequence:
        return []
    compressed = []
    prev = sequence[0]
    count = 1
    for c in sequence[1:]:
        if c == prev:
            count += 1
        else:
            compressed.append({"code": prev, "run_length": count})
            prev = c
            count = 1
    compressed.append({"code": prev, "run_length": count})
    return compressed


def _extract_motifs(sequence, min_len=2, max_len=5):
    motifs = []
    seq = list(sequence)
    n = len(seq)
    if n < min_len:
        return motifs
    for length in range(min_len, min(max_len + 1, n)):
        for start in range(n - length + 1):
            motif = tuple(seq[start:start + length])
            motifs.append(motif)
    return motifs


def _extract_block_transitions(sequence, block_codes=None):
    if block_codes is None:
        block_codes = {1000, 1111, 2000, 2001}
    blocks = []
    current_block = []
    for c in sequence:
        current_block.append(c)
        if c in block_codes:
            if len(current_block) > 1:
                blocks.append(current_block)
            current_block = []
    if len(current_block) > 1:
        blocks.append(current_block)
    return blocks


def _generate_plots(global_motifs, output_prefix):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []

    figures = []

    if global_motifs:
        top = global_motifs.most_common(20)
        labels = ["->".join(str(c) for c in m[0]) for m in top]
        counts = [m[1] for m in top]
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.barh(range(len(labels)), counts, color="steelblue", edgecolor="white")
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel("Occurrences")
        ax.set_title("OpenMIIR Event Sequence Motif Counts (Top 20)")
        ax.invert_yaxis()
        fig.tight_layout()
        path = os.path.join(FIGURES_DIR, f"{output_prefix}_motif_counts.png")
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

    subjects = _load_events(manifest_path, args.max_subjects)

    all_motifs = Counter()
    block_codes = {1000, 1111, 2000, 2001}
    subject_reports = []

    for s in subjects:
        seq = s["sequence"]
        compressed = _compress_runs(seq)
        motifs = _extract_motifs(seq, min_len=2, max_len=4)
        for m in motifs:
            all_motifs[m] += 1
        blocks = _extract_block_transitions(seq, block_codes)

        first_20 = seq[:20] if len(seq) >= 20 else seq
        last_20 = seq[-20:] if len(seq) >= 20 else seq

        code_freq = Counter(seq)

        subject_reports.append({
            "subject": s["subject"],
            "n_events": s["n_events"],
            "unique_codes": s["unique_codes"],
            "first_20_codes": first_20,
            "last_20_codes": last_20,
            "compressed_runs": compressed[:50],
            "n_blocks": len(blocks),
            "block_boundary_codes_found": sorted(set(
                c for c in seq if c in block_codes
            )),
            "most_frequent_codes": code_freq.most_common(10),
            "sequence_start_code": seq[0] if seq else None,
            "sequence_end_code": seq[-1] if seq else None,
        })

    figures = _generate_plots(all_motifs, args.output_prefix)

    report = {
        "tool": "openmiir_event_sequence_report_v3.9.3",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": args.dataset,
        "max_subjects": args.max_subjects,
        "subjects_analyzed": len(subjects),
        "total_events": sum(s["n_events"] for s in subjects),
        "block_codes": sorted(block_codes),
        "subject_reports": subject_reports,
        "global_motifs_top_50": [
            {"motif": "->".join(str(c) for c in m[0]),
             "codes": list(m[0]), "occurrences": m[1]}
            for m in all_motifs.most_common(50)
        ],
        "figures": figures,
        "motif_analysis": {
            "alls_start_with_1000": all(s["sequence"][0] == 1000 if s["sequence"] else False
                                      for s in subjects if s["sequence"]),
            "alls_end_with_2001": all(s["sequence"][-1] == 2001 if s["sequence"] else False
                                     for s in subjects if s["sequence"]),
            "most_common_single_code": sorted(
                {c: sum(1 for s in subjects if c in set(s["sequence"]))
                 for c in block_codes}.items(),
                key=lambda x: x[1], reverse=True
            )[:5] if subjects else [],
        },
        "disclaimer": "Motifs are structural patterns, not semantic labels. "
                      "No perception/imagery classification is claimed.",
        "no_raw_eeg_exposed": True,
    }

    json_path = os.path.join(EXPORTS, f"{args.output_prefix}_report.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    csv_path = os.path.join(EXPORTS, f"{args.output_prefix}_motifs.csv")
    with open(csv_path, "w") as f:
        f.write("motif,n_codes,occurrences\n")
        for m in all_motifs.most_common(100):
            f.write(f"{'->'.join(str(c) for c in m[0])},{len(m[0])},{m[1]}\n")

    md_lines = [
        "# OpenMIIR Event Sequence Report",
        f"**Subjects**: {len(subjects)} | **Total events**: {report['total_events']}",
        f"**Block codes**: {sorted(block_codes)}",
        "",
        "## Top Motifs",
    ]
    for m in all_motifs.most_common(10):
        md_lines.append(f"- `{' -> '.join(str(c) for c in m[0])}` ({m[1]} occurrences)")

    md_path = os.path.join(EXPORTS, f"{args.output_prefix}_report.md")
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))

    print(f"Event sequence: subjects={len(subjects)} total_events={report['total_events']} "
          f"motifs={len(all_motifs)}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
