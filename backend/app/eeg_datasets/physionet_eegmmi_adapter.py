"""PhysioNet EEGMMI Adapter v6.2 — Corrected for real dataset, no Cho2017.

Uses MOABB PhysionetMI when available, MNE eegbci for metadata fallback.
"""

import os
from datetime import datetime, timezone

EXPORTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports")

CANDIDATE_TASKS = [
    {
        "task_name": "left_fist_vs_right_fist_imagery",
        "description": "Motor imagery: left fist (T1) vs right fist (T2) — runs 3,7,11",
        "positive_label": "left_fist_imagery",
        "negative_label": "right_fist_imagery",
        "pos_codes": [2],
        "neg_codes": [3],
        "label_source_fields": ["event_code", "annotation_description"],
        "nuisance_metadata_fields": ["run_id", "trial_index", "file_id", "annotation_onset_bin"],
        "split_group_fields": ["subject_id"],
        "forbidden_model_feature_fields": [
            "event_code", "annotation_description", "subject_id", "run_id", "trial_index", "file_id",
        ],
        "split_strategy": "leave_one_subject_out",
    },
    {
        "task_name": "task_vs_rest_imagery",
        "description": "Any motor imagery task (T1,T2) vs rest (T0) — runs 3,7,11",
        "positive_label": "task",
        "negative_label": "rest",
        "pos_codes": [2, 3],
        "neg_codes": [1],
        "label_source_fields": ["event_code", "annotation_description"],
        "nuisance_metadata_fields": ["run_id", "trial_index", "file_id", "annotation_onset_bin"],
        "split_group_fields": ["subject_id"],
        "forbidden_model_feature_fields": [
            "event_code", "annotation_description", "subject_id", "run_id", "trial_index", "file_id",
        ],
        "split_strategy": "leave_one_subject_out",
    },
]


def _check_deps():
    deps = {"moabb": False, "mne": False, "has_physionet_loader": False}
    try:
        importlib = __import__("importlib")
        importlib.import_module("moabb.datasets")
        deps["moabb"] = True
    except ImportError:
        pass
    try:
        importlib.import_module("mne.datasets.eegbci")
        deps["mne"] = True
    except ImportError:
        pass
    if deps["moabb"] or deps["mne"]:
        deps["has_physionet_loader"] = True
    return deps


def export_manifest():
    deps = _check_deps()
    loader_backend = "unavailable"
    if deps["moabb"]:
        loader_backend = "moabb"
    elif deps["mne"]:
        loader_backend = "mne"

    missing = []
    if not deps["moabb"]:
        missing.append("moabb")
    if not deps["mne"]:
        missing.append("mne")

    return {
        "analysis_mode": "experimental_hypothesis_only",
        "not_for_scientific_claims": True,
        "production_valid": False,
        "production_unlock_allowed": False,
        "no_raw_eeg_exposed": True,
        "tool": "eeg_v62_physionet_adapter_manifest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_name": "PhysioNet EEG Motor Movement/Imagery (eegmmidb)",
        "adapter_status": "available" if deps["has_physionet_loader"] else "data_unavailable",
        "data_available": deps["has_physionet_loader"],
        "loader_backend": loader_backend,
        "dependency_missing": missing,
        "install_suggestion": (
            "pip install moabb" if not deps["moabb"] else "All dependencies satisfied"
        ),
        "candidate_tasks": CANDIDATE_TASKS,
        "recommended_first_task": "movement_vs_imagery_all",
        "notes": (
            "Uses MOABB PhysionetMI class (NOT Cho2017/OpenBMI). "
            "MNE eegbci provides PhysioNet motor imagery data as fallback. "
            f"Current status: {loader_backend}. "
            "Cho2017/OpenBMI is a separate dataset and is NOT used here."
        ),
    }


def load_metadata_rows(max_subjects=None):
    """Load metadata rows from PhysioNet EEGMMI via MOABB or MNE."""
    deps = _check_deps()
    rows = []

    if deps["moabb"]:
        try:
            from moabb.datasets import PhysionetMI
            dataset = PhysionetMI()
            subject_list = dataset.subject_list
            if max_subjects:
                subject_list = subject_list[:max_subjects]
            for subj in subject_list:
                try:
                    data = dataset.get_data(subjects=[subj])
                    if data is None:
                        continue
                    raw_all = data[subj]
                    if not raw_all:
                        continue
                    for run_id, run_dict in raw_all.items():
                        for sess_id, raw in run_dict.items():
                            events = raw[1] if isinstance(raw, tuple) and len(raw) > 1 else []
                            if hasattr(raw, "annotations") and raw.annotations:
                                for ann in raw.annotations:
                                    code_desc = ann.get("description", "")
                                    rows.append({
                                        "subject_id": str(subj),
                                        "run_id": str(run_id),
                                        "file_id": f"{subj}_{run_id}",
                                        "trial_index": len(rows),
                                        "event_code": code_desc,
                                        "annotation_description": code_desc,
                                        "annotation_onset": float(ann.get("onset", 0)),
                                        "annotation_duration": float(ann.get("duration", 0)),
                                        "annotation_onset_bin": int(float(ann.get("onset", 0)) // 2),
                                    })
                            elif len(events) > 0:
                                for ev in events:
                                    code = int(ev[2]) if ev.ndim > 1 else int(ev)
                                    rows.append({
                                        "subject_id": str(subj),
                                        "run_id": str(run_id),
                                        "file_id": f"{subj}_{run_id}",
                                        "trial_index": len(rows),
                                        "event_code": str(code),
                                        "annotation_description": f"event_{code}",
                                        "annotation_onset": float(ev[0]) / 160.0 if ev.ndim > 1 else 0,
                                        "annotation_duration": 4.0,
                                        "annotation_onset_bin": int(0) // 2,
                                    })
                except Exception:
                    continue
            return rows
        except Exception:
            pass

    # MNE fallback: load eegbci data and extract metadata
    if deps["mne"] and not deps["moabb"]:
        try:
            import mne
            from mne.datasets import eegbci

            subjects = list(range(1, 110))
            if max_subjects:
                subjects = subjects[:max_subjects]
            for subj in subjects:
                try:
                    runs = [3, 7, 11]
                    paths = eegbci.load_data(subj, runs, path=None, update_path=False,
                                              verbose=False)
                    for ri, path in enumerate(paths):
                        raw = mne.io.read_raw_edf(str(path), preload=False, verbose=False)
                        events, event_id = mne.events_from_annotations(raw, verbose=False)
                        row_count = len(rows)
                        for ei, ev in enumerate(events):
                            code = int(ev[2])
                            desc = [k for k, v in event_id.items() if v == code]
                            desc_str = desc[0] if desc else f"event_{code}"
                            rows.append({
                                "subject_id": str(subj),
                                "run_id": str(runs[ri]),
                                "file_id": f"{subj}_{runs[ri]}",
                                "trial_index": row_count + ei,
                                "event_code": str(code),
                                "annotation_description": desc_str,
                                "annotation_onset": float(ev[0]) / raw.info["sfreq"],
                                "annotation_duration": 4.0,
                                "annotation_onset_bin": int(float(ev[0]) / raw.info["sfreq"]) // 2,
                            })
                        del raw
                except Exception:
                    continue
            return rows
        except Exception:
            pass

    return rows


def build_task_labels(rows, task_config):
    """Build binary labels from metadata rows using event_code."""
    import numpy as np
    pos_codes = set(task_config.get("pos_codes", []))
    neg_codes = set(task_config.get("neg_codes", []))
    y = np.zeros(len(rows), dtype=np.float64)
    for i, row in enumerate(rows):
        code = str(row.get("event_code", "")).strip()
        if code in [str(c) for c in pos_codes]:
            y[i] = 1.0
        elif code in [str(c) for c in neg_codes]:
            y[i] = 0.0
        else:
            y[i] = -1.0
    return y, (y >= 0)


def validate_task_sample_counts(rows, task_config):
    y, mask = build_task_labels(rows, task_config)
    pos_count = int((y[mask] == 1.0).sum())
    neg_count = int((y[mask] == 0.0).sum())
    subj_set = set(r["subject_id"] for i, r in enumerate(rows) if mask[i])
    return {
        "task_name": task_config["task_name"],
        "n_subjects": len(subj_set),
        "n_total": int(mask.sum()),
        "n_positive": pos_count,
        "n_negative": neg_count,
        "class_balance": f"{pos_count}/{neg_count}",
        "sufficient": pos_count >= 10 and neg_count >= 10 and len(subj_set) >= 3,
    }
