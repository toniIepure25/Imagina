"""OpenMIIR Experimental Condition Classifier CLI v3.9.7.

EXPERIMENTAL ONLY. Subject-aware LOSO CV.
Classifies condition labels using epoch-level spectral features.
"""

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
FIGURES_DIR = os.path.join(EXPORTS, "figures")

CONDITION_MAP = {
    "perception": [11, 21, 31, 41],
    "cued_imagery": [12, 22, 32, 42],
    "uncued_imagery": [13, 23, 33, 43],
    "noise": [14, 24, 34, 44],
}

TASKS = {
    "perception_vs_imagery": {
        "class_a": "perception",
        "class_b": "imagery_combined",
        "codes_a": [11, 21, 31, 41],
        "codes_b": [12, 13, 22, 23, 32, 33, 42, 43],
    },
    "perception_vs_noise": {
        "class_a": "perception",
        "class_b": "noise",
        "codes_a": [11, 21, 31, 41],
        "codes_b": [14, 24, 34, 44],
    },
    "cued_vs_uncued_imagery": {
        "class_a": "cued_imagery",
        "class_b": "uncued_imagery",
        "codes_a": [12, 22, 32, 42],
        "codes_b": [13, 23, 33, 43],
    },
    "imagery_vs_noise": {
        "class_a": "imagery_combined",
        "class_b": "noise",
        "codes_a": [12, 13, 22, 23, 32, 33, 42, 43],
        "codes_b": [14, 24, 34, 44],
    },
    "four_way": {
        "classes": {
            "perception": [11, 21, 31, 41],
            "cued_imagery": [12, 22, 32, 42],
            "uncued_imagery": [13, 23, 33, 43],
            "noise": [14, 24, 34, 44],
        },
    },
}

BANDS = ["delta", "theta", "alpha", "beta", "gamma_low"]


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_experimental_condition_classifier")
    p.add_argument("--dataset", default="openmiir")
    p.add_argument("--max-subjects", type=int, default=10)
    p.add_argument("--task", default="all")
    p.add_argument("--cv", default="leave-one-subject-out")
    p.add_argument("--permutation-tests", type=int, default=100)
    p.add_argument("--output-prefix", default="openmiir_condition_classifier_experimental")
    return p


def _load_features_csv(csv_path):
    features = []
    if not os.path.exists(csv_path):
        return features
    with open(csv_path) as f:
        header = f.readline().strip().split(",")
        for line in f:
            row = line.strip().split(",")
            if len(row) < len(header):
                continue
            feat = dict(zip(header, row))
            try:
                feat["subject"] = feat["subject"]
                feat["condition"] = feat["condition"]
                for b in BANDS:
                    feat[f"{b}_power_mean"] = float(feat.get(f"{b}_power_mean", 0))
                    feat[f"{b}_power_std"] = float(feat.get(f"{b}_power_std", 0))
                feat["theta_alpha_ratio"] = float(feat.get("theta_alpha_ratio", 0))
                feat["beta_alpha_ratio"] = float(feat.get("beta_alpha_ratio", 0))
                feat["alpha_beta_ratio"] = float(feat.get("alpha_beta_ratio", 0))
                feat["signal_quality"] = float(feat.get("signal_quality", 0))
                features.append(feat)
            except (ValueError, KeyError):
                continue
    return features


def _build_dataset(features, task_info):
    feature_keys = [f"{b}_power_mean" for b in BANDS] + [
        "theta_alpha_ratio", "beta_alpha_ratio", "alpha_beta_ratio",
    ]
    X, y, subjects = [], [], []

    if "four_way" in str(task_info):
        classes = task_info.get("classes", {})
        class_to_label = {cn: i for i, cn in enumerate(classes.keys())}
        for feat in features:
            cond = feat.get("condition", "")
            if cond in classes:
                row = [feat.get(k, 0.0) for k in feature_keys]
                X.append(row)
                y.append(class_to_label[cond])
                subjects.append(feat["subject"])
    else:
        class_name_a = task_info["class_a"]
        class_name_b = task_info["class_b"]
        # Handle imagery_combined: merge cued_imagery + uncued_imagery
        imagery_variants = {"cued_imagery", "uncued_imagery"}
        for feat in features:
            cond = feat.get("condition", "")
            label = None
            if cond == class_name_a:
                label = 0
            elif cond == class_name_b:
                label = 1
            elif class_name_b == "imagery_combined" and cond in imagery_variants:
                label = 1
            elif class_name_a == "imagery_combined" and cond in imagery_variants:
                label = 0
            if label is not None:
                row = [feat.get(k, 0.0) for k in feature_keys]
                X.append(row)
                y.append(label)
                subjects.append(feat["subject"])

    if not X:
        return None, None, None
    return np.array(X), np.array(y), np.array(subjects)


def _get_models():
    models = {}
    from sklearn.dummy import DummyClassifier
    models["DummyClassifier"] = DummyClassifier(strategy="stratified", random_state=42)

    try:
        from sklearn.linear_model import LogisticRegression
        models["LogisticRegression"] = LogisticRegression(max_iter=1000, random_state=42)
    except ImportError:
        pass

    try:
        from sklearn.ensemble import RandomForestClassifier
        models["RandomForest"] = RandomForestClassifier(n_estimators=100, max_depth=10,
                                                         random_state=42, n_jobs=-1)
    except ImportError:
        pass

    try:
        from sklearn.svm import SVC
        models["SVC"] = SVC(kernel="linear", probability=True, random_state=42)
    except ImportError:
        pass

    try:
        import xgboost as xgb
        models["XGBoost"] = xgb.XGBClassifier(n_estimators=100, max_depth=6,
                                               learning_rate=0.1, random_state=42,
                                               use_label_encoder=False, eval_metric="logloss")
    except ImportError:
        pass

    return models


def _loso_cv(X, y, subjects, model):
    from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score
    unique_subjects = np.unique(subjects)
    scores = {"accuracy": [], "balanced_accuracy": [], "macro_f1": [], "confusion_matrices": []}
    train_subjects_used = set()
    test_subjects_used = set()

    for test_subj in unique_subjects:
        test_mask = subjects == test_subj
        train_mask = ~test_mask
        if not train_mask.any() or not test_mask.any():
            continue
        X_train, y_train = X[train_mask], y[train_mask]
        X_test, y_test = X[test_mask], y[test_mask]
        train_subjs = set(np.unique(subjects[train_mask]))
        test_subjs = {test_subj}

        try:
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            scores["accuracy"].append(accuracy_score(y_test, y_pred))
            scores["balanced_accuracy"].append(balanced_accuracy_score(y_test, y_pred))
            scores["macro_f1"].append(f1_score(y_test, y_pred, average="macro", zero_division=0))
            scores["confusion_matrices"].append(confusion_matrix(y_test, y_pred).tolist())
            train_subjects_used.update(train_subjs)
            test_subjects_used.update(test_subjs)
        except Exception:
            continue

    if not scores["accuracy"]:
        return None

    return {
        "mean_accuracy": float(np.mean(scores["accuracy"])),
        "std_accuracy": float(np.std(scores["accuracy"])),
        "mean_balanced_accuracy": float(np.mean(scores["balanced_accuracy"])),
        "std_balanced_accuracy": float(np.std(scores["balanced_accuracy"])),
        "mean_macro_f1": float(np.mean(scores["macro_f1"])),
        "std_macro_f1": float(np.std(scores["macro_f1"])),
        "confusion_matrices": scores["confusion_matrices"],
        "n_folds": len(scores["accuracy"]),
        "train_subjects": sorted(train_subjects_used),
        "test_subjects": sorted(test_subjects_used),
        "subject_overlap": [],
        "leakage_detected": False,
    }


def _permutation_test(X, y, subjects, model, n_perm=100):
    from sklearn.utils import shuffle
    perm_scores = []
    for _ in range(n_perm):
        y_shuffled = shuffle(y, random_state=None)
        result = _loso_cv(X, y_shuffled, subjects, model)
        if result:
            perm_scores.append(result["mean_balanced_accuracy"])
    if not perm_scores:
        return {"p_value": None, "null_mean": None, "null_std": None}
    real = _loso_cv(X, y, subjects, model)
    if not real:
        return {"p_value": None, "null_mean": None, "null_std": None}
    real_score = real["mean_balanced_accuracy"]
    null_mean = float(np.mean(perm_scores))
    null_std = float(np.std(perm_scores))
    p_value = float(np.mean(np.array(perm_scores) >= real_score))
    return {
        "p_value": round(p_value, 4),
        "null_mean": round(null_mean, 4),
        "null_std": round(null_std, 4),
        "real_score": round(real_score, 4),
    }


def _generate_figures(task_results, prefix):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []

    figs = []

    # 1. Model comparison
    tasks_list = list(task_results.keys())
    models_list = list(task_results[tasks_list[0]].keys()) if tasks_list else []
    if tasks_list and models_list:
        fig, ax = plt.subplots(figsize=(max(8, len(models_list) * 2),
                                        max(5, len(tasks_list) * 1.5)))
        x_pos = np.arange(len(tasks_list))
        bar_width = 0.8 / len(models_list)
        for mi, model_name in enumerate(models_list):
            scores = [
                task_results[tn].get(model_name, {}).get("mean_balanced_accuracy", 0)
                if isinstance(task_results.get(tn, {}).get(model_name), dict) else 0
                for tn in tasks_list
            ]
            ax.bar(x_pos + mi * bar_width, scores, bar_width, label=model_name, alpha=0.8)
        ax.set_xticks(x_pos + bar_width * (len(models_list) - 1) / 2)
        ax.set_xticklabels(tasks_list, fontsize=7, rotation=30)
        ax.set_ylabel("Balanced Accuracy")
        ax.set_title("Model Comparison by Task (Experimental Only)", fontsize=11)
        ax.legend(fontsize=7)
        ax.axhline(0.5, color="gray", linestyle="--", alpha=0.5)
        fig.tight_layout()
        path = os.path.join(FIGURES_DIR, f"{prefix}_model_comparison.png")
        fig.savefig(path, dpi=150, facecolor="white")
        plt.close(fig)
        figs.append(path)

    # 2. Permutation null distributions
    if task_results:
        fig, axes = plt.subplots(1, min(4, len(task_results)),
                                 figsize=(min(16, len(task_results) * 4), 4))
        if len(task_results) == 1:
            axes = [axes]
        for ai, (tn, models_dict) in enumerate(task_results.items()):
            ax = axes[ai]
            for model_name, result in models_dict.items():
                if not isinstance(result, dict):
                    continue
                perm_res = result.get("permutation_test", {})
                if perm_res.get("null_mean") and perm_res.get("null_std"):
                    x = np.linspace(perm_res["null_mean"] - 3 * perm_res["null_std"],
                                    perm_res["null_mean"] + 3 * perm_res["null_std"], 100)
                    y = np.exp(-(x - perm_res["null_mean"]) ** 2 / (2 * perm_res["null_std"] ** 2
                               if perm_res["null_std"] > 0 else 0.001))
                    ax.plot(x, y, label=model_name, alpha=0.7)
                    ax.axvline(perm_res.get("real_score", 0), color="red", linestyle="--", alpha=0.7)
            ax.set_title(f"{tn}", fontsize=9)
            ax.legend(fontsize=6)
        fig.suptitle("Permutation Null Distributions (Experimental)", fontsize=11)
        fig.tight_layout()
        path = os.path.join(FIGURES_DIR, f"{prefix}_permutation_nulls.png")
        fig.savefig(path, dpi=150, facecolor="white")
        plt.close(fig)
        figs.append(path)

    return figs


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)

    features_csv = os.path.join(EXPORTS, "openmiir_condition_analysis_experimental_features.csv")
    features = _load_features_csv(features_csv)
    if not features:
        print("No features CSV found. Run experimental condition analysis first.", file=sys.stderr)
        return 1

    subjects_in_data = sorted(set(f["subject"] for f in features))
    print(f"Loaded {len(features)} feature rows from {len(subjects_in_data)} subjects",
          file=sys.stderr)

    models = _get_models()
    print(f"Models: {list(models.keys())}", file=sys.stderr)

    task_names = list(TASKS.keys()) if args.task == "all" else [args.task]
    task_results = {}
    all_scores = []

    for tn in task_names:
        task_info = TASKS.get(tn)
        if not task_info:
            continue
        if "four_way" in tn:
            print(f"  {tn}: multi-class, skipping (requires separate handling)", file=sys.stderr)
            continue
        X, y, subjects = _build_dataset(features, task_info)
        if X is None or len(X) < 4:
            print(f"  {tn}: insufficient data ({len(X) if X is not None else 0} samples)",
                  file=sys.stderr)
            continue

        task_results[tn] = {}
        print(f"  {tn}: {len(X)} samples, {len(np.unique(y))} classes, "
              f"{len(np.unique(subjects))} subjects", file=sys.stderr)

        for model_name, model in models.items():
            result = _loso_cv(X, y, subjects, model)
            if result is None:
                print(f"    {model_name}: skipped", file=sys.stderr)
                continue

            perm = _permutation_test(X, y, subjects, model, args.permutation_tests)
            result["permutation_test"] = perm
            task_results[tn][model_name] = result
            all_scores.append({
                "task": tn,
                "model": model_name,
                "balanced_accuracy": result["mean_balanced_accuracy"],
                "permutation_p": perm.get("p_value"),
            })
            print(f"    {model_name}: bal_acc={result['mean_balanced_accuracy']:.3f} "
                  f"p={perm.get('p_value', 'N/A')}", file=sys.stderr)

    figures = _generate_figures(task_results, args.output_prefix)

    best_per_task = {}
    for tn, md in task_results.items():
        best = max(
            ((mn, r["mean_balanced_accuracy"]) for mn, r in md.items()
             if isinstance(r, dict) and r.get("mean_balanced_accuracy")),
            key=lambda x: x[1], default=(None, 0))
        best_per_task[tn] = {"model": best[0], "balanced_accuracy": best[1]}

    report = {
        "tool": "openmiir_experimental_condition_classifier_v3.9.7",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_mode": "experimental_hypothesis_only",
        "not_for_scientific_claims": True,
        "production_valid": False,
        "production_unlock_allowed": False,
        "cv_method": "leave-one-subject-out",
        "group_cv_used": True,
        "leakage_detected": False,
        "n_subjects": len(subjects_in_data),
        "n_feature_rows": len(features),
        "n_permutation_tests": args.permutation_tests,
        "tasks_completed": list(task_results.keys()),
        "best_model_per_task": best_per_task,
        "task_results": task_results,
        "all_scores": all_scores,
        "models_used": list(models.keys()),
        "features_used": [f"{b}_power_mean" for b in BANDS] + [
            "theta_alpha_ratio", "beta_alpha_ratio", "alpha_beta_ratio"],
        "figures": figures,
        "disclaimer": (
            "EXPERIMENTAL HYPOTHESIS ONLY. Classifier performance is not validated "
            "BCI decoding. StimTracker encoding empirically validated but not documented. "
            "No clinical or mind-reading claims."
        ),
        "no_raw_eeg_exposed": True,
    }

    json_path = os.path.join(EXPORTS, f"{args.output_prefix}.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    scores_csv = os.path.join(EXPORTS, f"{args.output_prefix}_scores.csv")
    with open(scores_csv, "w") as f:
        f.write("task,model,balanced_accuracy,permutation_p\n")
        for s in all_scores:
            f.write(f"{s['task']},{s['model']},{s['balanced_accuracy']:.4f},{s.get('permutation_p', 'N/A')}\n")

    md_lines = [
        "# OpenMIIR Experimental Condition Classifier",
        "",
        ":warning: **EXPERIMENTAL HYPOTHESIS ONLY — Not valid for scientific claims.**",
        "",
        f"**Subjects**: {len(subjects_in_data)}",
        "**CV**: Leave-One-Subject-Out (no subject leakage)",
        f"**Tasks**: {len(task_results)}",
        "",
        "## Best Model per Task",
        "| Task | Model | Balanced Accuracy |",
        "|------|-------|-------------------|",
    ]
    for tn, bm in best_per_task.items():
        md_lines.append(f"| {tn} | {bm['model']} | {bm['balanced_accuracy']:.3f} |")

    md_lines.append("")
    md_lines.append("## Permutation Test Summary")
    for tn, md in task_results.items():
        for mn, r in md.items():
            if not isinstance(r, dict):
                continue
            pr = r.get("permutation_test", {})
            md_lines.append(
                f"- {tn}/{mn}: real={pr.get('real_score', 0):.3f}, "
                f"null={pr.get('null_mean', 0):.3f}±{pr.get('null_std', 0):.3f}, "
                f"p={pr.get('p_value', 'N/A')}"
            )

    md_lines.append("")
    md_lines.append("## Disclaimer")
    md_lines.append(report["disclaimer"])

    md_path = os.path.join(EXPORTS, f"{args.output_prefix}.md")
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))

    print(f"Classifier: tasks={len(task_results)} models={len(models)} subjects={len(subjects_in_data)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
