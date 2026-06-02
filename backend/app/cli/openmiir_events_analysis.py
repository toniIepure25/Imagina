"""OpenMIIR event/annotation-aware analysis — honest inventory and condition detection."""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone


def _exports_path(fn):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports", fn)


def _figures_path(fn):
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports", "figures")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, fn)


def build_parser():
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_events_analysis")
    p.add_argument("--dataset", default="openmiir")
    p.add_argument("--max-subjects", type=int, default=10)
    p.add_argument("--tmin", type=float, default=0.0)
    p.add_argument("--tmax", type=float, default=3.0)
    p.add_argument("--output-prefix", default="openmiir_events")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    manifest_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..",
        "data", "external", args.dataset, "manifest.json",
    )
    if not os.path.exists(manifest_path):
        print(f"No manifest for dataset '{args.dataset}'.", file=sys.stderr)
        return 1

    with open(manifest_path) as f:
        manifest = json.load(f)
    files = manifest.get("files", [])[: args.max_subjects]
    if not files:
        print("No files in manifest.", file=sys.stderr)
        return 1

    import numpy as np
    from scipy.signal import welch as scipy_welch

    inventory = []
    has_any_annotations = False

    for fif in files:
        subj = os.path.splitext(os.path.basename(fif))[0]
        entry = {
            "subject": subj, "file": fif, "annotations_found": False,
            "events_found": False, "events": [], "annotations": [],
        }
        try:
            import mne
            raw = mne.io.read_raw_fif(fif, preload=False, verbose=False)
            if raw.annotations and len(raw.annotations) > 0:
                has_any_annotations = True
                entry["annotations_found"] = True
                descs = set()
                for a in raw.annotations:
                    descs.add(str(a["description"]))
                    entry["annotations"].append({
                        "onset": float(a["onset"]),
                        "duration": float(a["duration"]),
                        "description": str(a["description"]),
                    })
                entry["unique_descriptions"] = sorted(descs)
            elif hasattr(raw, "events") and raw.events is not None:
                entry["events_found"] = True
                entry["event_count"] = len(raw.events)
        except Exception as e:
            entry["error"] = str(e)
        inventory.append(entry)

    condition_mapping = {}
    if has_any_annotations:
        for inv in inventory:
            for desc in inv.get("unique_descriptions", []):
                condition_mapping[desc] = f"condition_{len(condition_mapping)}"

    condition_bandpower = []
    if has_any_annotations and condition_mapping:
        for fif in files:
            subj = os.path.splitext(os.path.basename(fif))[0]
            try:
                raw = mne.io.read_raw_fif(fif, preload=False, verbose=False)
                dur = min(raw.n_times / raw.info["sfreq"], 30.0)
                raw.crop(tmax=dur).load_data()
                data = raw.get_data()
                sfreq = raw.info["sfreq"]
                chs = min(data.shape[0], 8)
                psds = []
                for ch in range(chs):
                    f, pxx = scipy_welch(data[ch], fs=sfreq, nperseg=min(1024, data.shape[1] // 2))
                    psds.append(pxx)
                avg = np.mean(psds, axis=0)
                total = np.trapezoid(avg, f)
                for band, (lo, hi) in (("theta", (4, 8)), ("alpha", (8, 13)), ("beta", (13, 30))):
                    m = (f >= lo) & (f <= hi)
                    val = float(np.trapezoid(avg[m], f[m]) / max(total, 1e-9)) if m.any() else 0
                    condition_bandpower.append({
                        "subject": subj, "condition": "unknown", "band": band, "value": round(val, 6),
                    })
            except Exception:
                pass

    report = {
        "tool": "imagina_openmiir_events_analysis",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": args.dataset,
        "subjects_scanned": len(inventory),
        "has_annotations": has_any_annotations,
        "has_condition_labels": len(condition_mapping) > 0,
        "condition_mapping": condition_mapping,
        "inventory": inventory,
        "condition_bandpower": condition_bandpower,
        "recommendation": (
            "No MNE annotations found in OpenMIIR FIF files. "
            "The dataset's event structure is documented in the OpenMIIR paper: "
            "12 music fragments (7-16s each) with perception and imagery conditions. "
            "To use condition-aware analysis, add a metadata file mapping file names "
            "to condition labels (perception/imagery/rest) and onset times."
        ) if not has_any_annotations else "Annotations found. Condition mapping available.",
        "disclaimer": "Experimental proxy features. Not clinical validation. Does not decode thoughts.",
    }

    jp = _exports_path(f"{args.output_prefix}_inventory.json")
    ap = _exports_path(f"{args.output_prefix}_analysis.json")
    mp = _exports_path(f"{args.output_prefix}_analysis.md")
    bc = _exports_path(f"{args.output_prefix}_condition_bandpower.csv")
    sc = _exports_path(f"{args.output_prefix}_subject_condition_summary.csv")
    with open(jp, "w") as f:
        json.dump(report, f, indent=2, default=str)
    with open(ap, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # CSVs
    with open(bc, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["subject", "condition", "band", "value"])
        w.writeheader()
        for r in condition_bandpower:
            w.writerow(r)
    with open(sc, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["subject", "annotations_found", "events_found", "unique_descriptions"])
        w.writeheader()
        for inv in inventory:
            desc_str = ",".join(inv.get("unique_descriptions", []))
            w.writerow({
                "subject": inv["subject"],
                "annotations_found": inv["annotations_found"],
                "events_found": inv["events_found"],
                "unique_descriptions": desc_str,
            })

    # Markdown
    lines = [
        "# OpenMIIR Event & Condition Analysis",
        f"**Dataset**: {args.dataset} | **Subjects**: {len(inventory)}",
        "",
        "## Annotation Status",
        f"**Annotations found**: {'YES' if has_any_annotations else 'NO'}",
        f"**Condition labels inferred**: {'YES' if condition_mapping else 'NO'}",
        "",
    ]
    if not has_any_annotations:
        lines.extend([
            "OpenMIIR FIF files do not contain MNE-readable annotations or event markers.",
            "This is expected: the dataset documentation describes 12 music fragments per subject",
            "with perception and imagery conditions, but this metadata was stored separately",
            "in the repository's `meta/` directory, not embedded in the FIF files.",
            "",
            "**Recommended next steps:**",
            "1. Obtain the OpenMIIR metadata from the GitHub repository (`sstober/openmiir/meta/`)",
            "2. Create a `meta/condition_labels.json` mapping file names to condition/trial info",
            "3. Re-run this analysis with `--metadata-path meta/condition_labels.json`",
            "4. Then run `app.cli.openmiir_events_analysis` for condition-aware evaluation",
        ])
    lines.extend([
        "",
        "## Subject Inventory",
        "| Subject | Annotations | Events |",
        "|---------|------------|--------|",
    ])
    for inv in inventory:
        lines.append(f"| {inv['subject']} | {inv['annotations_found']} | {inv['events_found']} |")
    lines.extend([
        "",
        "## Limitations",
        "- No embedded annotation/event markers available in current FIF files",
        "- Condition-aware analysis requires external metadata",
        "- This is an engineering evaluation, not clinical validation",
    ])
    with open(mp, "w") as f:
        f.write("\n".join(lines))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        subjects = [inv["subject"] for inv in inventory]
        ann = [1 if inv["annotations_found"] else 0 for inv in inventory]
        ax.bar(subjects, ann, color=["green" if a else "gray" for a in ann])
        ax.set_title("OpenMIIR Annotation Status")
        fig.savefig(_figures_path(f"{args.output_prefix}_event_counts.png"), dpi=100)
        plt.close(fig)
    except Exception:
        pass

    print(f"Event inventory: {jp}", file=sys.stderr)
    print(f"  Annotations found: {has_any_annotations} | Conditions: {len(condition_mapping)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
