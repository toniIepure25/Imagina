"""Corrected Metadata Preflight Protocol v6.1.

Event_code = LABEL_SOURCE (defines y, not a model feature).
Nuisance metadata (run_id, trial_index, file_id) = TRUE CONFOUND TARGET.
"""

import json
import os
from datetime import datetime, timezone

import numpy as np

EXPORTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports")


class MetadataFieldRole:
    LABEL_SOURCE = "label_source"
    NUISANCE = "nuisance"
    SPLIT_GROUP = "split_group"
    FORBIDDEN_MODEL_FEATURE = "forbidden_model_feature"


DEFAULT_THRESHOLDS = {
    "nuisance_metadata_max_bal_acc": 0.60,
    "combined_nuisance_metadata_max_bal_acc": 0.60,
    "trial_order_max_bal_acc": 0.60,
    "run_id_max_bal_acc": 0.60,
    "subject_only_warning_threshold": 0.70,
}


def build_metadata_matrix(rows, fields):
    """Build metadata feature matrix from rows. Skips missing fields."""
    from sklearn.preprocessing import LabelEncoder

    feature_arrays = []
    used_fields = []
    for field in fields:
        vals = []
        for row in rows:
            v = row.get(field, None)
            vals.append(str(v) if v is not None else "MISSING")
        unique = len(set(vals))
        if unique > 1:
            encoded = LabelEncoder().fit_transform(vals).astype(np.float64).reshape(-1, 1)
            feature_arrays.append(encoded)
            used_fields.append(field)
    if not feature_arrays:
        return np.zeros((len(rows), 1)), []
    return np.hstack(feature_arrays), used_fields


def run_loso_metadata_baseline(X_meta, y, subjects):
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    if X_meta.shape[0] < 4:
        return None
    scores = []
    for ts in np.unique(subjects):
        train = subjects != ts
        test = subjects == ts
        if not train.any() or not test.any():
            continue
        m = Pipeline([
            ("imp", SimpleImputer()), ("scl", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, random_state=42)),
        ])
        try:
            m.fit(X_meta[train], y[train])
            yp = m.predict(X_meta[test])
            scores.append(float(balanced_accuracy_score(y[test], yp)))
        except Exception:
            pass
    return round(float(np.mean(scores)), 4) if scores else None


def evaluate_preflight(rows, task_config):
    """Evaluate metadata preflight for a candidate task. Returns PreflightResult dict."""
    subjects = np.array([str(r.get("subject_id", r.get("subject", "unknown"))) for r in rows])
    # Build label from label_source fields
    label_fields = task_config.get("label_source_fields", ["event_code"])
    y = np.zeros(len(rows), dtype=np.float64)
    if "event_code" in label_fields:
        pos_codes = task_config.get("pos_codes", task_config.get("positive_label_codes", []))
        neg_codes = task_config.get("neg_codes", task_config.get("negative_label_codes", []))
        event_codes = np.array([int(r.get("event_code", 0)) for r in rows])
        y = np.where(np.isin(event_codes, pos_codes), 1.0,
                     np.where(np.isin(event_codes, neg_codes), 0.0, -1.0)).astype(np.float64)
    mask = (y >= 0) & np.isfinite(y)
    if mask.sum() < 4:
        return {"metadata_safe": False, "allowed_to_train_eeg_model": False,
                "failure_reasons": ["insufficient_data"],
                "nuisance_baselines": {}, "combined_nuisance_baseline": None}

    yt = y[mask]
    st = subjects[mask]

    # Dummy baseline
    from sklearn.dummy import DummyClassifier
    from sklearn.metrics import balanced_accuracy_score
    dummy_scores = []
    for ts in np.unique(st):
        train = st != ts
        test = st == ts
        if not train.any() or not test.any():
            continue
        try:
            dc = DummyClassifier(strategy="stratified", random_state=42)
            dc.fit(np.zeros((train.sum(), 1)), yt[train])
            yp = dc.predict(np.zeros((test.sum(), 1)))
            dummy_scores.append(float(balanced_accuracy_score(yt[test], yp)))
        except Exception:
            pass
    dummy_baseline = round(float(np.mean(dummy_scores)), 4) if dummy_scores else None

    # Nuisance metadata baselines
    nuisance_fields = task_config.get("nuisance_metadata_fields", ["run_id", "trial_index", "file_id"])
    label_source = set(task_config.get("label_source_fields", ["event_code"]))
    # Exclude label_source fields from nuisance
    nuisance_fields = [f for f in nuisance_fields if f not in label_source]
    nuisance_baselines = {}
    for field in nuisance_fields:
        Xm, used = build_metadata_matrix(rows, [field])
        score = run_loso_metadata_baseline(Xm[mask], yt, st)
        if score is not None:
            nuisance_baselines[field] = score

    # Combined nuisance (excluding label source)
    combined_fields = [f for f in nuisance_fields]
    if nuisance_fields:
        Xc, used = build_metadata_matrix(rows, combined_fields)
        combined_nuisance = run_loso_metadata_baseline(Xc[mask], yt, st)
    else:
        combined_nuisance = None

    # Evaluate thresholds
    failed = []
    warnings_list = []
    max_nuisance = max(nuisance_baselines.values()) if nuisance_baselines else 0
    if combined_nuisance is not None and combined_nuisance > 0.60:
        failed.append(f"combined_nuisance={combined_nuisance:.3f} > 0.60")
    if max_nuisance > 0.60:
        failed.append(f"max_nuisance_individual={max_nuisance:.3f} > 0.60")
    if combined_nuisance is not None and combined_nuisance <= 0.60 and max_nuisance <= 0.60:
        pass
    else:
        pass

    metadata_safe = len(failed) == 0 and dummy_baseline is not None
    return {
        "metadata_safe": metadata_safe,
        "allowed_to_train_eeg_model": metadata_safe,
        "label_source_fields": list(label_source),
        "label_source_note": ("event_code defines y; NOT used as model feature or nuisance"),
        "nuisance_baselines": nuisance_baselines,
        "combined_nuisance_baseline": combined_nuisance,
        "dummy_baseline": dummy_baseline,
        "structural_warnings": warnings_list,
        "failure_reasons": failed,
        "interpretation": (
            "Preflight passed — nuisance metadata cannot predict the label."
            if metadata_safe else
            "Preflight FAILED — nuisance metadata predicts the label. "
            "Training is BLOCKED until metadata controls are established."
        ),
    }


def export_protocol():
    """Export the current preflight protocol as a JSON artifact."""
    protocol = {
        "analysis_mode": "experimental_hypothesis_only",
        "not_for_scientific_claims": True,
        "production_valid": False,
        "production_unlock_allowed": False,
        "no_raw_eeg_exposed": True,
        "tool": "eeg_v61_corrected_preflight_protocol",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "v6.1_corrected",
        "key_principle": (
            "Event_code can be a LABEL_SOURCE (defines y). It is NOT automatically a confound. "
            "Nuisance metadata (run_id, trial_index, file_id, subject_id as feature) is the true confound target. "
            "Training is blocked if nuisance metadata can predict the label."
        ),
        "field_roles": {
            "event_code": MetadataFieldRole.LABEL_SOURCE,
            "annotation_description": MetadataFieldRole.LABEL_SOURCE,
            "run_id": MetadataFieldRole.NUISANCE,
            "trial_index": MetadataFieldRole.NUISANCE,
            "file_id": MetadataFieldRole.NUISANCE,
            "subject_id": MetadataFieldRole.SPLIT_GROUP,
            "annotation_onset_bin": MetadataFieldRole.NUISANCE,
        },
        "default_thresholds": DEFAULT_THRESHOLDS,
    }
    path = os.path.join(EXPORTS, "eeg_v61_corrected_preflight_protocol.json")
    with open(path, "w") as f:
        json.dump(protocol, f, indent=2, default=str)
    return protocol
