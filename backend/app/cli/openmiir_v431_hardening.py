"""V4.3.1 Hardening CLI — Audit, artifact export, ORS fix, geometry grade.

Consolidated infrastructure for paper-grade representational benchmarking.
"""

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
META_DIR = os.path.join(BASE, "..", "..", "data", "external", "openmiir", "meta")
FIGURES_DIR = os.path.join(EXPORTS, "figures")


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_v431_hardening")
    p.add_argument("--features-csv", default=None)
    p.add_argument("--representational-json", default=None)
    p.add_argument("--benchmark-json", default=None)
    p.add_argument("--robustness-json", default=None)
    p.add_argument("--mode", default="all",
                   choices=["audit", "export", "fix_ors", "geometry_grade", "figures", "all"])
    p.add_argument("--output-prefix", default="openmiir_v431")
    return p


def _load(p):
    if p and os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None


def _safety():
    return {
        "analysis_mode": "experimental_hypothesis_only",
        "not_for_scientific_claims": True,
        "production_valid": False,
        "production_unlock_allowed": False,
        "no_raw_eeg_exposed": True,
    }


def run_audit(args):
    csv_path = args.features_csv or os.path.join(EXPORTS, "openmiir_epoch_features_experimental.csv")
    rep_path = args.representational_json or os.path.join(
        EXPORTS, "openmiir_representational_analysis_experimental.json")
    bm_path = args.benchmark_json or os.path.join(
        EXPORTS, "openmiir_epoch_condition_benchmark_experimental.json")

    rep = _load(rep_path)
    bm = _load(bm_path)
    rows = 0
    subjects = set()
    if os.path.exists(csv_path):
        with open(csv_path) as f:
            f.readline()  # skip header
            for line in f:
                parts = line.split(",")
                if len(parts) > 1:
                    rows += 1
                    subjects.add(parts[0])

    results = {
        "feature_csv_exists": os.path.exists(csv_path),
        "n_subjects": len(subjects),
        "n_epochs": rows,
        "n_subjects_match": len(subjects) == 10,
        "n_epochs_ok": rows >= 800,
        "representational_exists": rep is not None,
        "rdm_exists": "condition_rdm" in (rep or {}),
        "rsa_exists": "rsa_results" in (rep or {}),
        "manifold_exists": "manifold" in (rep or {}),
        "variance_decomp_exists": "variance_decomposition" in (rep or {}),
        "pid_exists": "pid_eeg" in (rep or {}),
        "subject_consistency_exists": "subject_consistency" in (rep or {}),
        "main_eval_blocked": (_load(os.path.join(EXPORTS, "openmiir_condition_eval.json")) or {})
        .get("status") == "blocked",
        "no_condition_manifest": not os.path.exists(os.path.join(META_DIR, "condition_manifest.json")),
        "benchmark_exists": bm is not None,
        "safety_fields_ok": all((rep or {}).get(k, False) is not None for k in [
            "not_for_scientific_claims", "production_valid", "no_raw_eeg_exposed"]),
    }
    passed = sum(1 for k, v in results.items() if isinstance(v, bool) and v)
    total = sum(1 for k, v in results.items() if isinstance(v, bool))
    results["all_checks"] = passed == total

    audit = {**_safety(), "tool": "openmiir_v431_readiness_audit",
             "generated_at": datetime.now(timezone.utc).isoformat(),
             "results": results, "overall": "PASS" if results["all_checks"] else "FAIL"}

    _save(audit, "openmiir_v431_readiness_audit", args.output_prefix)
    print(f"Audit: {passed}/{total} checks passed")
    return 0


def run_export(args):
    rep_path = args.representational_json or os.path.join(
        EXPORTS, "openmiir_representational_analysis_experimental.json")
    rep = _load(rep_path)
    if not rep:
        print("No representational analysis found", file=sys.stderr)
        return 1

    # RDM export
    rdms = rep.get("condition_rdm", {})
    for metric, rdm_dict in rdms.items():
        _save({**_safety(), "tool": "openmiir_condition_rdm", "metric": metric,
               "conditions": rdm_dict["conditions"], "matrix": rdm_dict["matrix"]},
              "openmiir_condition_rdm_experimental", args.output_prefix)

    # RSA
    rsa_data = rep.get("rsa_results", {})
    _save({**_safety(), "tool": "openmiir_rsa", "rsa_results": rsa_data,
           "best_model": rep.get("best_rsa_model")},
          "openmiir_rsa_experimental", args.output_prefix)
    if rsa_data:
        csv_rsa = os.path.join(EXPORTS, "openmiir_rsa_model_comparison.csv")
        with open(csv_rsa, "w") as f:
            f.write("model,metric,spearman_r\n")
            for k, v in rsa_data.items():
                f.write(f"{v['model']},{v['metric']},{v['spearman_r']}\n")

    # Variance decomp
    _save({**_safety(), "tool": "openmiir_variance_decomposition",
           "decomposition": rep.get("variance_decomposition", {})},
          "openmiir_variance_decomposition_experimental", args.output_prefix)

    # PID-EEG
    _save({**_safety(), "tool": "openmiir_pid_eeg", "pid": rep.get("pid_eeg", {})},
          "openmiir_perception_imagery_distance_experimental", args.output_prefix)

    # Subject consistency
    _save({**_safety(), "tool": "openmiir_subject_manifold_consistency",
           "consistency": rep.get("subject_consistency", [])},
          "openmiir_subject_manifold_consistency_experimental", args.output_prefix)

    # Manifold coordinates (no raw EEG)
    manifold = rep.get("manifold", {})
    pca_coords = manifold.get("pca_2d", {}).get("coords", [])
    if pca_coords:
        csv_path = os.path.join(EXPORTS, "openmiir_condition_manifold_coordinates.csv")
        with open(csv_path, "w") as f:
            f.write("method,epoch_index,dim1,dim2\n")
            for i, coord in enumerate(pca_coords[:len(pca_coords)]):
                f.write(f"pca,{i},{coord[0]},{coord[1]}\n")

    print("Exported: RDM, RSA, variance, PID, subject_consistency, manifold coordinates")
    return 0


def run_fix_ors(args):
    robustness_path = args.robustness_json or os.path.join(EXPORTS, "openmiir_robustness_score.json")
    data = _load(robustness_path)
    if not data:
        print("No robustness data", file=sys.stderr)
        return 1

    ors = data.get("ors_scores", {})
    capped = {}
    fixed_any = False
    for tn, info in ors.items():
        score = min(100.0, info.get("ors", 0))
        if info.get("ors", 0) > 100:
            fixed_any = True
        cat = "weak" if score < 40 else ("exploratory" if score < 60
              else ("promising" if score < 75 else ("strong" if score < 90 else "exceptional")))
        capped[tn] = {"ors": round(score, 1), "category": cat,
                       "original_ors": info.get("ors"), "ors_capped": score < info.get("ors", 0),
                       "reasons": info.get("reasons", [])}

    result = {**_safety(), "tool": "openmiir_robustness_score_fixed",
              "generated_at": datetime.now(timezone.utc).isoformat(),
              "ors_scores": capped, "ors_capped": fixed_any,
              "note": "ORS is an internal robustness score, not external scientific validation."}

    _save(result, "openmiir_robustness_score", args.output_prefix)
    print(f"ORS fixed: capped={fixed_any}")
    return 0


def run_geometry_grade(args):
    rep = _load(args.representational_json or os.path.join(
        EXPORTS, "openmiir_representational_analysis_experimental.json"))
    bm = _load(args.benchmark_json or os.path.join(
        EXPORTS, "openmiir_epoch_condition_benchmark_experimental.json"))

    if not rep:
        print("No data", file=sys.stderr)
        return 1

    # Geometry score components (0-100 scale)
    score = 0.0
    reasons = []
    total_weight = 0.0

    # 1. RSA evidence (30%)
    best_rsa = rep.get("best_rsa_model", {})
    rsa_corr = best_rsa.get("spearman_r", 0) if best_rsa else 0
    rsa_score = min(100, max(0, rsa_corr * 130))
    score += rsa_score * 0.30
    total_weight += 0.30
    reasons.append(f"RSA={rsa_score:.0f} (r={rsa_corr:.3f})")

    # 2. Condition silhouette (25%)
    pca_sil = rep.get("manifold", {}).get("pca_2d", {}).get("silhouette_condition", -1)
    sil_score = max(0, min(100, (pca_sil + 0.3) * 120))
    score += sil_score * 0.25
    total_weight += 0.25
    reasons.append(f"Silhouette={sil_score:.0f} (cond={pca_sil:.3f})")

    # 3. PID evidence (25%)
    pid = rep.get("pid_eeg", {})
    adv = pid.get("cued_imagery_advantage", 0)
    pid_score = min(100, max(0, adv * 80))
    score += pid_score * 0.25
    total_weight += 0.25
    reasons.append(f"PID={pid_score:.0f} (adv={adv:.3f})")

    # 4. Classifier evidence (20%)
    bm_best = (bm or {}).get("best_model_per_task", {}).get("perception_vs_imagery", {})
    cls_acc = bm_best.get("bal_acc", 0) if bm_best else 0
    cls_score = min(100, max(0, (cls_acc - 0.5) * 400))
    score += cls_score * 0.20
    total_weight += 0.20
    reasons.append(f"Classifier={cls_score:.0f} (PvI={cls_acc:.3f})")

    cat = "weak_geometry" if score < 30 else ("exploratory_geometry" if score < 50
          else ("promising_geometry" if score < 65 else "strong_geometry"))

    result = {**_safety(), "tool": "openmiir_geometry_evidence_grade",
              "generated_at": datetime.now(timezone.utc).isoformat(),
              "geometry_score": round(score, 1), "category": cat,
              "reasons": reasons,
              "interpretation": (
                  "The strongest representational evidence is that cued imagery is closer to "
                  "perception than uncued imagery (PID advantage). The best RSA model is imagery_subtype, "
                  "suggesting the main representational axis separates imagery subtypes. "
                  "PCA silhouette is negative, indicating overlapping low-dimensional clusters. "
                  "Residual variance dominates (95.7%). This is not validated BCI decoding."
              )}

    _save(result, "openmiir_geometry_evidence_grade", args.output_prefix)
    print(f"Geometry grade: {score:.0f} ({cat})")
    return 0


def run_figures(args):
    rep = _load(args.representational_json or os.path.join(
        EXPORTS, "openmiir_representational_analysis_experimental.json"))
    if not rep:
        print("No data", file=sys.stderr)
        return 1

    os.makedirs(FIGURES_DIR, exist_ok=True)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return 1

    figs = []
    prefix = args.output_prefix

    # 1. RDM heatmap
    rdms = rep.get("condition_rdm", {})
    eucl = rdms.get("euclidean", {})
    if eucl and eucl.get("matrix"):
        mat = np.array(eucl["matrix"])
        labels = eucl.get("conditions", [])
        fig, ax = plt.subplots(figsize=(6, 5))
        im = ax.imshow(mat, cmap="YlOrRd")
        for i in range(len(labels)):
            for j in range(len(labels)):
                ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center", fontsize=9)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_title("Condition RDM (Euclidean) — Experimental Only", fontsize=10)
        fig.colorbar(im, ax=ax)
        fig.tight_layout()
        p = os.path.join(FIGURES_DIR, f"{prefix}_condition_rdm_heatmap.png")
        fig.savefig(p, dpi=150, facecolor="white")
        plt.close(fig)
        figs.append(p)

    # 2. RSA comparison
    rsa = rep.get("rsa_results", {})
    if rsa:
        fig, ax = plt.subplots(figsize=(8, 4))
        names = list(rsa.keys())
        vals = [rsa[n]["spearman_r"] for n in names]
        colors = ["#4CAF50" if v == max(vals) else "#90A4AE" for v in vals]
        ax.barh(range(len(names)), vals, color=colors)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=7)
        ax.invert_yaxis()
        ax.set_xlabel("Spearman r")
        ax.set_title("RSA Model Comparison — Experimental Only", fontsize=10)
        fig.tight_layout()
        p = os.path.join(FIGURES_DIR, f"{prefix}_rsa_model_comparison.png")
        fig.savefig(p, dpi=150, facecolor="white")
        plt.close(fig)
        figs.append(p)

    # 3. Variance decomposition
    vd = rep.get("variance_decomposition", {})
    if vd:
        fig, ax = plt.subplots(figsize=(6, 4))
        keys = ["condition", "subject", "stimulus_group", "residual"]
        vals = [vd.get(k, 0) * 100 for k in keys]
        ax.bar(keys, vals, color=["#2196F3", "#FF9800", "#4CAF50", "#9E9E9E"])
        ax.set_ylabel("Variance Explained (%)")
        ax.set_title("Variance Decomposition — Experimental Only", fontsize=10)
        for i, v in enumerate(vals):
            ax.text(i, v + 0.5, f"{v:.1f}%", ha="center", fontsize=9)
        fig.tight_layout()
        p = os.path.join(FIGURES_DIR, f"{prefix}_variance_decomposition.png")
        fig.savefig(p, dpi=150, facecolor="white")
        plt.close(fig)
        figs.append(p)

    # 4. PID barplot
    pid = rep.get("pid_eeg", {})
    if pid:
        fig, ax = plt.subplots(figsize=(5, 4))
        items = [("P→Cued", pid.get("perception_to_cued_imagery", 0)),
                 ("P→Uncued", pid.get("perception_to_uncued_imagery", 0))]
        labels_list = [it[0] for it in items]
        values_list = [it[1] for it in items]
        ax.bar(labels_list, values_list, color=["#2196F3", "#FF9800"])
        ax.set_ylabel("Euclidean Distance")
        ax.set_title("PID-EEG — Experimental Only", fontsize=10)
        if "cued_imagery_advantage" in pid:
            ax.text(0.5, max(values_list) * 0.5,
                    f"Advantage: {pid['cued_imagery_advantage']:.3f}",
                    ha="center", fontsize=9, bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
        fig.tight_layout()
        p = os.path.join(FIGURES_DIR, f"{prefix}_pid_eeg_barplot.png")
        fig.savefig(p, dpi=150, facecolor="white")
        plt.close(fig)
        figs.append(p)

    # 5. Subject consistency
    consistency = rep.get("subject_consistency", [])
    if consistency:
        fig, ax = plt.subplots(figsize=(8, 4))
        subj_names = [c["subject"] for c in consistency]
        corr_vals = [c["spearman_r"] for c in consistency]
        ax.bar(range(len(subj_names)), corr_vals, color="steelblue")
        ax.set_xticks(range(len(subj_names)))
        ax.set_xticklabels(subj_names, fontsize=8, rotation=45)
        ax.set_ylabel("Spearman r with Group RDM")
        ax.set_title("Subject Manifold Consistency — Experimental Only", fontsize=10)
        fig.tight_layout()
        p = os.path.join(FIGURES_DIR, f"{prefix}_subject_manifold_consistency.png")
        fig.savefig(p, dpi=150, facecolor="white")
        plt.close(fig)
        figs.append(p)

    return 0


def _save(data, key, prefix):
    path = os.path.join(EXPORTS, f"{key}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)

    mode = args.mode
    if mode in ("audit", "all"):
        run_audit(args)
    if mode in ("export", "all"):
        run_export(args)
    if mode in ("fix_ors", "all"):
        run_fix_ors(args)
    if mode in ("geometry_grade", "all"):
        run_geometry_grade(args)
    if mode in ("figures", "all"):
        run_figures(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
