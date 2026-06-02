"""OpenMIIR Representational Analysis v4.3 — RDM, RSA, Manifold, Variance, PID-EEG.

Consolidated CLI for condition geometry analysis. Experimental only.
"""

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
FIGURES_DIR = os.path.join(EXPORTS, "figures")

CONDITIONS = ["perception", "cued_imagery", "uncued_imagery", "noise"]
BANDS = {"delta": (0.5, 4.0), "theta": (4.0, 8.0), "alpha": (8.0, 13.0),
         "beta": (13.0, 30.0), "gamma_low": (30.0, 45.0)}


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_representational_analysis")
    p.add_argument("--features-csv", default=None)
    p.add_argument("--benchmark-json", default=None)
    p.add_argument("--normalization", default="subject_zscore")
    p.add_argument("--output-prefix", default="openmiir_representational_analysis_experimental")
    return p


def _load_features(csv_path):
    rows = []
    if not csv_path or not os.path.exists(csv_path):
        return None, None
    meta = {"subject", "condition", "epoch_id", "event_code", "stimulus_group",
            "trigger_type", "sfreq", "n_channels", "epoch_duration_sec",
            "analysis_mode", "artifact_rejected"}
    with open(csv_path) as f:
        header = f.readline().strip().split(",")
        fc = [h for h in header if h not in meta]
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < len(header):
                continue
            row = dict(zip(header, parts))
            try:
                for c in fc:
                    row[c] = float(row[c])
                rows.append(row)
            except (ValueError, KeyError):
                pass
    return rows, fc


def _subject_zscore(X, subs):
    Xn = X.copy()
    for ts in np.unique(subs):
        mask = subs == ts
        m = np.mean(Xn[mask], axis=0, keepdims=True)
        s = np.std(Xn[mask], axis=0, keepdims=True) + 1e-10
        Xn[mask] = (Xn[mask] - m) / s
    return Xn


def _condition_prototypes(X, y_cond):
    prototypes = {}
    for ci, cn in enumerate(CONDITIONS):
        mask = y_cond == ci
        if mask.any():
            prototypes[cn] = np.mean(X[mask], axis=0)
    return prototypes


def _compute_rdm(prototypes):
    cond_list = [c for c in CONDITIONS if c in prototypes]
    n = len(cond_list)
    # Euclidean, cosine, correlation
    rdms = {}
    metrics = [
        ("euclidean", lambda a, b: np.linalg.norm(a - b)),
        ("cosine", lambda a, b: 1.0 - np.dot(a, b) / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-10)),
    ]
    for metric, fn in metrics:
        mat = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                mat[i, j] = fn(prototypes[cond_list[i]], prototypes[cond_list[j]])
        rdms[metric] = {"matrix": mat.tolist(), "conditions": cond_list,
                        "labels": cond_list}
    return rdms


def _model_rdm(cond_list):
    models = {}
    n = len(cond_list)
    # Condition identity: same=0, diff=1
    m = np.ones((n, n))
    np.fill_diagonal(m, 0)
    models["condition_identity"] = m.tolist()
    # Perception-imagery axis: perception close to imagery, noise far
    m = np.ones((n, n))
    for i, ci in enumerate(cond_list):
        for j, cj in enumerate(cond_list):
            if "imagery" in ci and "imagery" in cj:
                m[i, j] = 0.5
            if ci == "perception" and "imagery" in cj:
                m[i, j] = 0.6
            if cj == "perception" and "imagery" in ci:
                m[i, j] = 0.6
            if ci == "noise":
                m[i, j] = 1.0
            if cj == "noise":
                m[i, j] = 1.0
    np.fill_diagonal(m, 0)
    models["perception_imagery_axis"] = m.tolist()
    # Imagery subtype: cued and uncued close to each other
    m = np.ones((n, n))
    for i, ci in enumerate(cond_list):
        for j, cj in enumerate(cond_list):
            if ci == "cued_imagery" and cj == "uncued_imagery":
                m[i, j] = 0.3
            if ci == "uncued_imagery" and cj == "cued_imagery":
                m[i, j] = 0.3
    np.fill_diagonal(m, 0)
    models["imagery_subtype"] = m.tolist()
    return models


def _rsa_correlation(emp_rdm, model_rdm):
    e, m = np.array(emp_rdm), np.array(model_rdm)
    # Take upper triangle excluding diagonal
    n = e.shape[0]
    triu_idx = np.triu_indices(n, k=1)
    ev = e[triu_idx].flatten()
    mv = m[triu_idx].flatten()
    if np.std(ev) < 1e-10 or np.std(mv) < 1e-10:
        return 0.0
    from scipy.stats import spearmanr
    corr, p = spearmanr(ev, mv)
    return float(corr) if not np.isnan(corr) else 0.0


def _manifold_pca(X):
    from sklearn.decomposition import PCA
    pca = PCA(n_components=min(3, X.shape[1]))
    coords = pca.fit_transform(X)
    return coords[:, :2], coords[:, :3] if coords.shape[1] >= 3 else coords[:, :2]


def _manifold_umap(X):
    try:
        import umap
        reducer = umap.UMAP(n_components=2, random_state=42)
        return reducer.fit_transform(X)
    except ImportError:
        return None


def _manifold_tsne(X):
    from sklearn.manifold import TSNE
    tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, X.shape[0] - 1))
    return tsne.fit_transform(X)


def _silhouette(X, labels):
    from sklearn.metrics import silhouette_score
    unique = set(labels)
    if len(unique) < 2 or len(unique) >= len(X):
        return 0.0
    return float(silhouette_score(X, labels))


def _variance_decomposition(X, cond_y, subj_y, stim_y):
    results = {}
    for factor_name, y in [("condition", cond_y), ("subject", subj_y),
                            ("stimulus_group", stim_y)]:
        ss_total = np.sum((X - np.mean(X, axis=0)) ** 2)
        ss_factor = 0.0
        for val in np.unique(y):
            mask = y == val
            if mask.sum() > 1:
                group_mean = np.mean(X[mask], axis=0)
                ss_factor += mask.sum() * np.sum((group_mean - np.mean(X, axis=0)) ** 2)
        eta_sq = ss_factor / max(ss_total, 1e-10)
        results[factor_name] = round(float(eta_sq), 4)
    residual = 1.0 - sum(results.values())
    results["residual"] = round(max(0.0, residual), 4)
    return results


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    csv_path = args.features_csv or os.path.join(EXPORTS, "openmiir_epoch_features_experimental.csv")
    rows, fc = _load_features(csv_path)
    if not rows:
        print("No features", file=sys.stderr)
        return 1

    X = np.array([[r.get(f, 0.0) for f in fc] for r in rows], dtype=np.float64)
    cond_y = np.array([CONDITIONS.index(r["condition"]) if r["condition"] in CONDITIONS else -1
                       for r in rows])
    subj_y = np.array([r["subject"] for r in rows])
    stim_y = np.array([int(r.get("stimulus_group", 0)) for r in rows])

    valid = cond_y >= 0
    X, cond_y, subj_y, stim_y = X[valid], cond_y[valid], subj_y[valid], stim_y[valid]

    # Subject normalize
    X_norm = _subject_zscore(X, subj_y)

    print(f"Data: {X.shape[0]} epochs, {X.shape[1]} features, {len(np.unique(cond_y))} conditions",
          file=sys.stderr)

    # === RDM ===
    prototypes = _condition_prototypes(X_norm, cond_y)
    rdms = _compute_rdm(prototypes)
    cond_list = [c for c in CONDITIONS if c in prototypes]

    # === RSA ===
    model_rdms = _model_rdm(cond_list)
    rsa_results = {}
    for metric, rdm_dict in rdms.items():
        emp_mat = np.array(rdm_dict["matrix"])
        for model_name, model_mat in model_rdms.items():
            corr = _rsa_correlation(emp_mat, model_mat)
            rsa_results[f"{metric}_{model_name}"] = {
                "metric": metric, "model": model_name, "spearman_r": round(corr, 4),
            }

    best_rsa = max(rsa_results.items(), key=lambda x: x[1]["spearman_r"]) if rsa_results else None

    # === Manifold ===
    manifold = {}
    # PCA
    coords_2d, coords_3d = _manifold_pca(X_norm)
    manifold["pca_2d"] = {
        "coords": coords_2d.tolist(),
        "silhouette_condition": _silhouette(coords_2d, cond_y),
        "silhouette_subject": _silhouette(coords_2d, subj_y),
    }

    # UMAP
    umap_coords = _manifold_umap(X_norm[:2000])
    if umap_coords is not None:
        n_umap = min(2000, len(X_norm))
        manifold["umap_2d"] = {
            "coords": umap_coords[:n_umap].tolist(),
            "silhouette_condition": _silhouette(umap_coords[:n_umap], cond_y[:n_umap]),
            "silhouette_subject": _silhouette(umap_coords[:n_umap], subj_y[:n_umap]),
        }

    # t-SNE
    n_tsne = min(1000, len(X_norm))
    tsne_coords = _manifold_tsne(X_norm[:n_tsne])
    manifold["tsne_2d"] = {
        "coords": tsne_coords.tolist(),
        "silhouette_condition": _silhouette(tsne_coords, cond_y[:n_tsne]),
        "silhouette_subject": _silhouette(tsne_coords, subj_y[:n_tsne]),
    }

    # === Variance Decomposition ===
    var_decomp = _variance_decomposition(X_norm, cond_y, subj_y, stim_y)

    # === PID-EEG ===
    pid = {}
    if "perception" in prototypes and "cued_imagery" in prototypes:
        p_vec = prototypes["perception"]
        ci_vec = prototypes["cued_imagery"]
        ui_vec = prototypes.get("uncued_imagery")
        n_vec = prototypes.get("noise")
        pid["perception_to_cued_imagery"] = float(np.linalg.norm(p_vec - ci_vec))
        if ui_vec is not None:
            pid["perception_to_uncued_imagery"] = float(np.linalg.norm(p_vec - ui_vec))
            pid["cued_imagery_advantage"] = round(
                pid["perception_to_uncued_imagery"] - pid["perception_to_cued_imagery"], 4)
        if n_vec is not None:
            pid["perception_to_noise"] = float(np.linalg.norm(p_vec - n_vec))
            pid["imagery_to_noise"] = float(np.linalg.norm(ci_vec - n_vec))
            pid["imagery_closeness_ratio"] = round(
                pid.get("perception_to_cued_imagery", 0) / max(pid["perception_to_noise"], 1e-10), 4)

    # === Subject manifold consistency ===
    subj_consistency = []
    for ts in np.unique(subj_y):
        mask = subj_y == ts
        if mask.sum() < 10:
            continue
        sproto = _condition_prototypes(X_norm[mask], cond_y[mask])
        # Compute RDM for this subject and correlate with group RDM
        if "euclidean" in rdms:
            group_mat = np.array(rdms["euclidean"]["matrix"])
            subj_mat = np.zeros((len(cond_list), len(cond_list)))
            for i, ci in enumerate(cond_list):
                for j, cj in enumerate(cond_list):
                    if ci in sproto and cj in sproto:
                        subj_mat[i, j] = np.linalg.norm(sproto[ci] - sproto[cj])
            triu = np.triu_indices(len(cond_list), k=1)
            from scipy.stats import spearmanr
            corr, _ = spearmanr(group_mat[triu].flatten(), subj_mat[triu].flatten())
            subj_consistency.append({
                "subject": ts, "spearman_r": round(float(corr) if not np.isnan(corr) else 0, 4),
            })

    # === Save ===
    report = {
        "tool": "openmiir_representational_analysis_v4.3",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_mode": "experimental_hypothesis_only",
        "not_for_scientific_claims": True,
        "production_valid": False,
        "production_unlock_allowed": False,
        "no_raw_eeg_exposed": True,
        "n_subjects": len(np.unique(subj_y)),
        "n_epochs": len(X_norm),
        "n_features": X_norm.shape[1],
        "condition_rdm": rdms,
        "rsa_results": rsa_results,
        "best_rsa_model": {"name": best_rsa[0], **best_rsa[1]} if best_rsa else None,
        "manifold": manifold,
        "variance_decomposition": var_decomp,
        "pid_eeg": pid,
        "subject_consistency": subj_consistency,
        "subject_dominance_warning": (
            manifold.get("pca_2d", {}).get("silhouette_subject", 0) >
            manifold.get("pca_2d", {}).get("silhouette_condition", 0)
            if "pca_2d" in manifold else False
        ),
    }

    for prefix, data in [
        ("openmiir_condition_rdm_experimental", {"condition_rdm": rdms}),
        ("openmiir_rsa_experimental", {"rsa_results": rsa_results, "best_rsa_model": report["best_rsa_model"]}),
        ("openmiir_condition_manifold_experimental", {"manifold": manifold}),
        ("openmiir_variance_decomposition_experimental", {"variance_decomposition": var_decomp}),
        ("openmiir_perception_imagery_distance_experimental", {"pid_eeg": pid}),
        ("openmiir_subject_manifold_consistency_experimental", {"subject_consistency": subj_consistency}),
    ]:
        p = os.path.join(EXPORTS, f"{prefix}.json")
        sub = {**report, **data}
        sub["tool"] = prefix
        with open(p, "w") as f:
            json.dump(sub, f, indent=2, default=str)

    # Master report
    json_path = os.path.join(EXPORTS, f"{args.output_prefix}.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Summary
    pca_cond_sil = manifold.get("pca_2d", {}).get("silhouette_condition", 0)
    pca_subj_sil = manifold.get("pca_2d", {}).get("silhouette_subject", 0)
    print(f"Representational: RDM={len(rdms)} RSA={len(rsa_results)} "
          f"manifold={len(manifold)} var_decomp={var_decomp} pid={len(pid)} "
          f"subj_consistency={len(subj_consistency)}", file=sys.stderr)
    print(f"  PCA silhouette: cond={pca_cond_sil:.3f} subj={pca_subj_sil:.3f}", file=sys.stderr)
    if best_rsa:
        print(f"  Best RSA: {best_rsa[0]} (r={best_rsa[1]['spearman_r']:.3f})", file=sys.stderr)
    print(f"  Top variance: {max(var_decomp.items(), key=lambda x: x[1])}", file=sys.stderr)
    if pid:
        print(f"  PID: P->CI={pid.get('perception_to_cued_imagery',0):.3f} "
              f"P->UI={pid.get('perception_to_uncued_imagery',0):.3f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
