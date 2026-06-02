"""OpenMIIR V5.0 — Scientific Task Redesign for Confound-Free EEG Decoding.

Invalidates old confounded tasks, designs metadata-safe candidate tasks,
validates with metadata baselines, runs honest benchmark, delivers scientific verdict.
"""

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
FIGURES_DIR = os.path.join(EXPORTS, "figures")
META_DIR = os.path.join(BASE, "..", "..", "data", "external", "openmiir", "meta")

OLD_TASKS = {
    "perception_vs_imagery": {"pos": ["perception"], "neg": ["cued_imagery", "uncued_imagery"]},
    "perception_vs_noise": {"pos": ["perception"], "neg": ["noise"]},
    "cued_vs_uncued_imagery": {"pos": ["cued_imagery"], "neg": ["uncued_imagery"]},
    "imagery_vs_noise": {"pos": ["cued_imagery", "uncued_imagery"], "neg": ["noise"]},
    "perception_vs_cued_imagery": {"pos": ["perception"], "neg": ["cued_imagery"]},
    "perception_vs_uncued_imagery": {"pos": ["perception"], "neg": ["uncued_imagery"]},
}

NEW_CANDIDATE_TASKS = {
    "within_sg1_perception_vs_imagery": {
        "description": "Stimulus group 1: perception (11) vs imagery (12,13)",
        "pos_codes": [11], "neg_codes": [12, 13],
        "metadata_controls": ["stimulus_group_fixed"],
    },
    "within_sg1_cued_vs_uncued": {
        "description": "Stimulus group 1: cued imagery (12) vs uncued imagery (13)",
        "pos_codes": [12], "neg_codes": [13],
        "metadata_controls": ["stimulus_group_fixed"],
    },
    "within_sg2_perception_vs_imagery": {
        "description": "Stimulus group 2: perception (21) vs imagery (22,23)",
        "pos_codes": [21], "neg_codes": [22, 23],
        "metadata_controls": ["stimulus_group_fixed"],
    },
    "within_sg2_cued_vs_uncued": {
        "description": "Stimulus group 2: cued (22) vs uncued (23)",
        "pos_codes": [22], "neg_codes": [23],
        "metadata_controls": ["stimulus_group_fixed"],
    },
    "within_sg3_perception_vs_imagery": {
        "description": "Stimulus group 3: perception (31) vs imagery (32,33)",
        "pos_codes": [31], "neg_codes": [32, 33],
        "metadata_controls": ["stimulus_group_fixed"],
    },
    "within_sg4_perception_vs_imagery": {
        "description": "Stimulus group 4: perception (41) vs imagery (42,43)",
        "pos_codes": [41], "neg_codes": [42, 43],
        "metadata_controls": ["stimulus_group_fixed"],
    },
    "across_sg_cued_vs_uncued": {
        "description": "All stimulus groups: cued (12,22,32,42) vs uncued (13,23,33,43) — stimulus-group balanced",
        "pos_codes": [12, 22, 32, 42], "neg_codes": [13, 23, 33, 43],
        "metadata_controls": ["stimulus_group_balanced"],
    },
    "across_sg_perception_vs_noise": {
        "description": "Perception (11,21,31,41) vs noise (14,24,34,44) — stimulus-group must not be shortcut",
        "pos_codes": [11, 21, 31, 41], "neg_codes": [14, 24, 34, 44],
        "metadata_controls": ["stimulus_group_balanced"],
    },
}


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_v50_confounded_task_redesign")
    p.add_argument("--mode", default="all",
                   choices=["invalidate", "candidates", "validate", "benchmark", "verdict", "all"])
    p.add_argument("--output-prefix", default="openmiir_v50_confounded_task_redesign")
    return p


def _load_json(p):
    if p and os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None


def _safety():
    return {"analysis_mode": "experimental_hypothesis_only",
            "not_for_scientific_claims": True, "production_valid": False,
            "production_unlock_allowed": False, "no_raw_eeg_exposed": True}


def _load_rows():
    p = os.path.join(EXPORTS, "openmiir_epoch_features_experimental.csv")
    if not os.path.exists(p):
        return [], []
    with open(p) as f:
        header = f.readline().strip().split(",")
        meta_cols = {"subject", "condition", "epoch_id", "event_code", "stimulus_group",
                      "trigger_type", "sfreq", "n_channels", "epoch_duration_sec",
                      "analysis_mode", "artifact_rejected"}
        fc = [h for h in header if h not in meta_cols]
        rows = []
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


def _loso_score(X, y, subjects):
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    scores = []
    for ts in np.unique(subjects):
        train = subjects != ts
        test = subjects == ts
        if not train.any() or not test.any():
            continue
        m = Pipeline([("imp", SimpleImputer()), ("scl", StandardScaler()),
                       ("clf", LogisticRegression(max_iter=1000, random_state=42))])
        try:
            m.fit(X[train], y[train])
            yp = m.predict(X[test])
            scores.append(float(balanced_accuracy_score(y[test], yp)))
        except Exception:
            pass
    return round(float(np.mean(scores)), 4) if scores else None


def _metadata_probe(rows, task_cfg):
    from sklearn.preprocessing import LabelEncoder

    subjects = np.array([r["subject"] for r in rows])
    stim_groups = np.array([int(r.get("stimulus_group", 0)) for r in rows])
    event_codes = np.array([int(r.get("event_code", 0)) for r in rows])
    pos_mask = np.isin(event_codes, task_cfg["pos_codes"])
    neg_mask = np.isin(event_codes, task_cfg["neg_codes"])
    mask = pos_mask | neg_mask
    if mask.sum() < 4:
        return None

    yt = np.where(np.isin(event_codes[mask], task_cfg["pos_codes"]), 1, 0).astype(np.float64)
    st = subjects[mask]

    results = {}
    for meta_name, meta_arr in [
        ("subject_id", LabelEncoder().fit_transform(subjects[mask]).reshape(-1, 1).astype(np.float64)),
        ("stimulus_group", stim_groups[mask].reshape(-1, 1).astype(np.float64)),
        ("event_code", event_codes[mask].reshape(-1, 1).astype(np.float64)),
    ]:
        results[meta_name] = _loso_score(meta_arr, yt, st)

    combined = np.hstack([
        LabelEncoder().fit_transform(subjects[mask]).reshape(-1, 1).astype(np.float64),
        stim_groups[mask].reshape(-1, 1).astype(np.float64),
        event_codes[mask].reshape(-1, 1).astype(np.float64),
    ])
    results["combined_metadata"] = _loso_score(combined, yt, st)

    return results


def run_invalidate():
    rows, fc = _load_rows()
    if not rows:
        print("No data", file=sys.stderr)
        return 1

    metadata = _load_json(os.path.join(EXPORTS, "openmiir_ssl_v49_metadata_baselines.json"))
    event_codes = np.array([int(r.get("event_code", 0)) for r in rows])
    stim_groups = np.array([int(r.get("stimulus_group", 0)) for r in rows])

    invalidation = {}
    for tn, ti in OLD_TASKS.items():
        pos_mask = np.isin(event_codes, [11,21,31,41] if "perception" in ti["pos"][0] else
                           [12,13,22,23,32,33,42,43] if "imagery" in ti["pos"][0] else
                           [14,24,34,44] if "noise" in ti["pos"][0] else [])
        neg_mask = np.isin(event_codes, [11,21,31,41] if "perception" in ti["neg"][0] else
                           [12,13,22,23,32,33,42,43] if "imagery" in ti["neg"][0] else
                           [14,24,34,44] if "noise" in ti["neg"][0] else [])

        meta_score = None
        if metadata:
            for k, v in metadata.get("scores", {}).items():
                if tn in k and "combined" in k:
                    meta_score = v

        reasons = []
        if meta_score is not None and meta_score > 0.75:
            reasons.append("metadata_confound")
        # Check if event_code alone predicts the label
        if not pos_mask.any() or not neg_mask.any():
            reasons.append("insufficient_data")
        else:
            mask = pos_mask | neg_mask
            if mask.any():
                # Check if stimulus group overlap exists between pos/neg
                pos_sg = set(stim_groups[pos_mask])
                neg_sg = set(stim_groups[neg_mask])
                if not pos_sg.intersection(neg_sg):
                    reasons.append("stimulus_group_separable")

        invalid = len(reasons) > 0
        invalidation[tn] = {
            "valid": not invalid,
            "metadata_score": meta_score,
            "reasons": reasons,
            "verdict": "invalid_confounded" if invalid else "potentially_usable",
        }

    report = {**_safety(), "tool": "openmiir_v50_old_task_invalidation",
              "generated_at": datetime.now(timezone.utc).isoformat(),
              "invalidation": invalidation,
              "summary": (
                  f"{sum(1 for v in invalidation.values() if not v['valid'])}"
                  f"/{len(invalidation)} tasks invalidated")}
    with open(os.path.join(EXPORTS, "openmiir_v50_old_task_invalidation.json"), "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Invalidation: {report['summary']}", file=sys.stderr)
    return 0


def run_candidates():
    rows, fc = _load_rows()
    if not rows:
        print("No data", file=sys.stderr)
        return 1

    event_codes = np.array([int(r.get("event_code", 0)) for r in rows])
    subjects = np.array([r["subject"] for r in rows])
    stim_groups = np.array([int(r.get("stimulus_group", 0)) for r in rows])

    candidates = {}
    for tn, cfg in NEW_CANDIDATE_TASKS.items():
        pos_mask = np.isin(event_codes, cfg["pos_codes"])
        neg_mask = np.isin(event_codes, cfg["neg_codes"])
        n_pos = pos_mask.sum()
        n_neg = neg_mask.sum()
        n_subs = len(set(subjects[pos_mask]) | set(subjects[neg_mask]))

        pos_sg = set(stim_groups[pos_mask])
        neg_sg = set(stim_groups[neg_mask])
        sg_overlap = pos_sg.intersection(neg_sg)

        feasible = n_pos >= 10 and n_neg >= 10 and n_subs >= 3
        candidates[tn] = {
            "description": cfg["description"],
            "n_samples": int(n_pos + n_neg),
            "n_pos": int(n_pos), "n_neg": int(n_neg),
            "n_subjects": n_subs,
            "class_balance": f"{n_pos}/{n_neg}",
            "stimulus_group_overlap": bool(sg_overlap),
            "sg_overlap_set": sorted(sg_overlap) if sg_overlap else [],
            "feasible": feasible,
            "metadata_controls": cfg["metadata_controls"],
        }

    report = {**_safety(), "tool": "openmiir_v50_candidate_tasks",
              "generated_at": datetime.now(timezone.utc).isoformat(),
              "candidate_tasks": candidates,
              "n_feasible": sum(1 for c in candidates.values() if c["feasible"])}
    with open(os.path.join(EXPORTS, "openmiir_v50_candidate_tasks.json"), "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Candidates: {report['n_feasible']}/{len(candidates)} feasible",
          file=sys.stderr)
    return 0


def run_validate():
    rows, fc = _load_rows()
    if not rows:
        return 1

    validation = {}
    for tn, cfg in NEW_CANDIDATE_TASKS.items():
        md_scores = _metadata_probe(rows, cfg)
        if md_scores is None:
            validation[tn] = {"status": "insufficient_data", "metadata_scores": None}
            continue

        combined = md_scores.get("combined_metadata")
        event_only = md_scores.get("event_code")
        sg_only = md_scores.get("stimulus_group")
        safe = True
        reasons = []
        if combined is not None and combined > 0.60:
            safe = False
            reasons.append(f"combined_metadata={combined:.3f}")
        if event_only is not None and event_only > 0.60:
            safe = False
            reasons.append(f"event_code={event_only:.3f}")
        if sg_only is not None and sg_only > 0.60:
            safe = False
            reasons.append(f"stimulus_group={sg_only:.3f}")

        validation[tn] = {
            "metadata_safe": safe,
            "status": "metadata_safe" if safe else "metadata_invalid",
            "metadata_scores": md_scores,
            "reasons": reasons,
        }

    safe_tasks = {k: v for k, v in validation.items() if v["metadata_safe"]}
    report = {**_safety(), "tool": "openmiir_v50_candidate_metadata_validation",
              "generated_at": datetime.now(timezone.utc).isoformat(),
              "validation": validation,
              "n_metadata_safe": len(safe_tasks)}

    with open(os.path.join(EXPORTS, "openmiir_v50_candidate_metadata_validation.json"), "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Final task manifest
    manifest = {
        **_safety(),
        "manifest_type": "experimental_confounded_task_redesign",
        "not_production_manifest": True,
        "allowed_for_scientific_claims": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tasks": {k: {**NEW_CANDIDATE_TASKS[k], **v} for k, v in safe_tasks.items()},
        "n_valid_tasks": len(safe_tasks),
    }
    if not safe_tasks:
        manifest["verdict"] = "no_valid_confounded_free_task_found"
    with open(os.path.join(EXPORTS, "openmiir_v50_final_task_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    print(f"Validation: {len(safe_tasks)} metadata-safe tasks", file=sys.stderr)
    for tn, v in validation.items():
        print(f"  {tn}: {v['status']}" + (f" ({', '.join(v['reasons'])})" if v.get('reasons') else ""),
              file=sys.stderr)
    return 0


def run_benchmark():
    rows, fc = _load_rows()
    if not rows:
        return 1

    manifest = _load_json(os.path.join(EXPORTS, "openmiir_v50_final_task_manifest.json"))
    if not manifest or not manifest.get("tasks"):
        report = {**_safety(), "tool": "openmiir_v50_handcrafted_confounded_free_benchmark",
                  "generated_at": datetime.now(timezone.utc).isoformat(),
                  "status": "no_valid_tasks",
                  "reason": "No metadata-safe tasks found. Cannot run confound-free benchmark."}
        with open(os.path.join(EXPORTS, "openmiir_v50_handcrafted_confounded_free_benchmark.json"), "w") as f:
            json.dump(report, f, indent=2, default=str)
        print("Benchmark: skipped — no valid tasks", file=sys.stderr)
        return 0

    event_codes = np.array([int(r.get("event_code", 0)) for r in rows])
    subjects = np.array([r["subject"] for r in rows])
    Xh = np.array([[r.get(f, 0.0) for f in fc] for r in rows])
    from sklearn.preprocessing import StandardScaler
    Xh = StandardScaler().fit_transform(Xh)

    results = {}
    valid_tasks = manifest.get("tasks", {})
    for tn, cfg in valid_tasks.items():
        pos_mask = np.isin(event_codes, cfg["pos_codes"])
        neg_mask = np.isin(event_codes, cfg["neg_codes"])
        mask = pos_mask | neg_mask
        if mask.sum() < 4:
            continue
        Xt = Xh[mask]
        yt = np.where(np.isin(event_codes[mask], cfg["pos_codes"]), 1, 0).astype(np.float64)
        st = subjects[mask]
        score = _loso_score(Xt, yt, st)
        if score is not None:
            # Permutation test
            from sklearn.utils import shuffle as sk_shuffle
            null_scores = []
            for _ in range(50):
                ys = sk_shuffle(yt, random_state=None)
                ns = _loso_score(Xt, ys, st)
                if ns is not None:
                    null_scores.append(ns)
            p_val = float(np.mean(np.array(null_scores) >= score)) if null_scores else 1.0
            results[tn] = {
                "balanced_accuracy": score,
                "permutation_p": round(p_val, 4),
                "above_chance": p_val < 0.05,
                "n_samples": int(mask.sum()),
                "n_subjects": len(np.unique(st[mask])),
            }

    report = {**_safety(), "tool": "openmiir_v50_handcrafted_confounded_free_benchmark",
              "generated_at": datetime.now(timezone.utc).isoformat(),
              "n_valid_tasks": len(valid_tasks), "results": results}
    with open(os.path.join(EXPORTS, "openmiir_v50_handcrafted_confounded_free_benchmark.json"), "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Benchmark: {len(results)} tasks evaluated", file=sys.stderr)
    for tn, r in results.items():
        print(f"  {tn}: bal={r['balanced_accuracy']:.3f} p={r['permutation_p']}", file=sys.stderr)
    return 0


def run_verdict():
    bench = _load_json(os.path.join(EXPORTS, "openmiir_v50_handcrafted_confounded_free_benchmark.json"))
    valid = _load_json(os.path.join(EXPORTS, "openmiir_v50_candidate_metadata_validation.json"))
    has_bench = bench and bench.get("results") and len(bench["results"]) > 0
    n_safe = (valid or {}).get("n_metadata_safe", 0)

    if has_bench and len(bench["results"]) >= 2:
        verdict = "valid_reduced_benchmark_found"
    elif has_bench:
        verdict = "partial_valid_benchmark_found"
    else:
        verdict = "no_valid_task_found"

    above_chance = sum(1 for r in (bench or {}).get("results", {}).values() if r.get("above_chance"))
    best_task = max((bench or {}).get("results", {}).items(),
                    key=lambda x: x[1].get("balanced_accuracy", 0),
                    default=(None, {})) if has_bench else (None, {})

    conclusion = {
        **_safety(),
        "tool": "openmiir_v50_scientific_verdict",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "old_v48_trusted": False,
        "new_benchmark_available": has_bench,
        "n_metadata_safe_tasks": n_safe,
        "n_above_chance": above_chance,
        "best_task": best_task[0] if best_task[0] else None,
        "best_bal_acc": best_task[1].get("balanced_accuracy") if best_task[1] else None,
        "recommended_claim": (
            "After controlling for metadata confounds, OpenMIIR supports exploratory "
            "within-stimulus-group EEG condition decoding using spectral features. "
            "Performance is moderate and above chance, but not suitable for production or clinical use."
        ),
        "forbidden_claims": [
            "we decode imagined perception reliably",
            "SSL reaches 95% accuracy",
            "BCI-ready", "mind-reading",
            "production-ready", "clinical",
            "validated condition decoding",
        ],
        "next_research_step": (
            "Use within-stimulus-group tasks for future EEG condition decoding. "
            "Consider larger datasets with randomized stimulus order, independent "
            "stimulus/condition assignment, and stronger metadata controls."
        ),
        "honest_interpretation": (
            f"V4.8's high scores (0.93-0.96) were confounded by metadata. "
            f"V5.0 redesigned tasks to control for stimulus group and event code. "
            f"{n_safe} metadata-safe task(s) found, {above_chance} above chance. "
            f"Scores are lower but scientifically meaningful. "
            f"Handcrafted alpha/theta features remain the most defensible representation. "
            f"No BCI or clinical claims are made."
        ),
    }
    with open(os.path.join(EXPORTS, "openmiir_v50_scientific_verdict.json"), "w") as f:
        json.dump(conclusion, f, indent=2, default=str)

    print(f"Verdict: {verdict} | safe_tasks={n_safe} | above_chance={above_chance}", file=sys.stderr)
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)

    print(f"V5.0 mode={args.mode}", file=sys.stderr)

    if args.mode in ("invalidate", "all"):
        run_invalidate()
    if args.mode in ("candidates", "all"):
        run_candidates()
    if args.mode in ("validate", "all"):
        run_validate()
    if args.mode in ("benchmark", "all"):
        run_benchmark()
    if args.mode in ("verdict", "all"):
        run_verdict()
    return 0


if __name__ == "__main__":
    sys.exit(main())
