"""EEG representation similarity analysis — subject-level embeddings, cosine similarity, PCA."""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np


def _exports_path(fn):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports", fn)


def _figures_path(fn):
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports", "figures")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, fn)


def build_parser():
    p = argparse.ArgumentParser(prog="python3 -m app.cli.eeg_representation_analysis")
    p.add_argument("--dataset", default="openmiir")
    p.add_argument("--features", default="bandpower,covariance,psd")
    p.add_argument("--max-subjects", type=int, default=10)
    p.add_argument("--output-prefix", default="openmiir_representation")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    mp = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..",
        "data", "external", args.dataset, "manifest.json",
    )
    if not os.path.exists(mp):
        print(f"No manifest for '{args.dataset}'", file=sys.stderr)
        return 1

    from app.datasets.loaders import safe_read_raw
    from app.datasets.windowing import windows_from_raw
    from app.services.feature_engine import FeatureEngine

    with open(mp) as f:
        files = json.load(f).get("files", [])[: args.max_subjects]
    if len(files) < 2:
        print("Need >=2 subjects", file=sys.stderr)
        return 1

    subject_embeddings = {}
    all_feature_maps = {}
    engine = FeatureEngine()

    for fif in files:
        subj = os.path.splitext(os.path.basename(fif))[0]
        try:
            raw = safe_read_raw(fif)
            dur = min(raw.n_times / raw.info["sfreq"], 30)
            raw.crop(tmax=dur)
            windows = windows_from_raw(raw, max_windows=30)
            fvs = [engine.process_eeg_window(w) for w in windows]
            bp_vecs = []
            for fv in fvs:
                bp_vecs.append([
                    fv.theta_power, fv.alpha_power, fv.beta_power,
                    fv.theta_beta_ratio, fv.alpha_stability, fv.signal_quality,
                ])
            bp_mean = np.mean(bp_vecs, axis=0) if bp_vecs else np.zeros(6)
            subject_embeddings[subj] = bp_mean
            all_feature_maps[subj] = {"bandpower": bp_vecs}
        except Exception:
            pass

    if len(subject_embeddings) < 2:
        print("Not enough subjects", file=sys.stderr)
        return 1

    subjects = list(subject_embeddings.keys())
    n = len(subjects)
    emb_matrix = np.array([subject_embeddings[s] for s in subjects])

    # Cosine similarity
    norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    emb_norm = emb_matrix / norms
    sim_matrix = emb_norm @ emb_norm.T

    # Correlation matrix
    np.corrcoef(emb_matrix)

    # PCA
    from sklearn.decomposition import PCA
    pca = PCA(n_components=2)
    pca_coords = pca.fit_transform(emb_matrix)

    report = {
        "tool": "imagina_representation_analysis",
        "release_candidate": "V3.5",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": args.dataset,
        "subjects_analyzed": n,
        "features_used": ["bandpower"],
        "similarity_matrix_shape": [n, n],
        "cosine_similarity_range": [round(float(sim_matrix.min()), 4), round(float(sim_matrix.max()), 4)],
        "interpretation": (
            "Subject-level bandpower embeddings were computed and compared via cosine similarity. "
            "Higher similarity near the diagonal indicates within-subject consistency. "
            "Cross-subject similarity can be used to assess EEG feature stability. "
            "This is a foundation for future perception-vs-imagery similarity analysis."
        ),
        "condition_labels_available": False,
        "disclaimer": (
            "Experimental representation analysis using derived EEG proxy features. "
            "Not clinical validation. Does not decode thoughts."
        ),
    }

    prefix = args.output_prefix
    jp = _exports_path(f"{prefix}_analysis.json")
    rp = _exports_path(f"{prefix}_analysis.md")
    ep = _exports_path(f"{prefix}_subject_embeddings.csv")
    sp = _exports_path(f"{prefix}_similarity_matrix.csv")
    with open(jp, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # CSV: embeddings
    with open(ep, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject", "theta", "alpha", "beta", "tb_ratio", "alpha_stab", "signal_quality"])
        for s in subjects:
            w.writerow([s] + [round(v, 6) for v in subject_embeddings[s]])

    # CSV: similarity
    with open(sp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([""] + subjects)
        for i, s in enumerate(subjects):
            w.writerow([s] + [round(float(sim_matrix[i, j]), 4) for j in range(n)])

    # Markdown
    lines = [
        "# EEG Representation Similarity Analysis",
        f"**Subjects**: {n} | **Features**: bandpower",
        "",
        "## Cosine Similarity Matrix",
    ]
    for i, s in enumerate(subjects):
        vals = " ".join(f"{sim_matrix[i, j]:.3f}" for j in range(n))
        lines.append(f"  {s}: {vals}")
    lines.extend([
        "",
        "## Interpretation",
        report["interpretation"],
        "",
        "## Limitations",
        "- No condition labels — subject-level analysis only",
        "- Bandpower features only (no time-frequency or connectivity features)",
        "- Small subject count for robust similarity estimation",
        "- Experimental proxy features, not clinical biomarkers",
    ])
    with open(rp, "w") as f:
        f.write("\n".join(lines))

    # Figures
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.matshow(sim_matrix, cmap="RdYlBu_r", vmin=0.5, vmax=1.0)
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(subjects, rotation=45, ha="left", fontsize=7)
        ax.set_yticklabels(subjects, fontsize=7)
        ax.set_title("Subject Cosine Similarity")
        fig.colorbar(im)
        fig.savefig(_figures_path(f"{prefix}_subject_similarity_heatmap.png"), dpi=100)
        plt.close(fig)

        fig2, ax2 = plt.subplots()
        for i, s in enumerate(subjects):
            ax2.scatter(pca_coords[i, 0], pca_coords[i, 1], label=s, s=60)
        ax2.set_title("PCA Subject Embedding")
        ax2.legend(fontsize=7)
        fig2.savefig(_figures_path(f"{prefix}_embedding_pca.png"), dpi=100)
        plt.close(fig2)
    except Exception:
        pass

    print(f"Representation analysis: {jp}", file=sys.stderr)
    print(f"  Subjects: {n} | Cosine sim range: [{sim_matrix.min():.3f}, {sim_matrix.max():.3f}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
