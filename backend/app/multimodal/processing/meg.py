"""Offline MEG: FIF import, filtering, bad-channel detection, epoching, sensor-space features, time-resolved decoding.

Source-space modelling requires individual anatomy (MRI) and head-coregistration; it is not attempted here.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

SOURCE_SPACE_AVAILABLE = False
SOURCE_SPACE_REASON = "requires subject MRI, BEM and coregistration (not available in this repository)"


@dataclass
class MegEpochs:
    data: np.ndarray
    labels: np.ndarray
    times: np.ndarray
    ch_names: list[str]
    bads: list[str]
    sfreq: float


def detect_bad_channels(data: np.ndarray, ch_names: list[str], z_thresh: float = 5.0,
                        ch_types: list[str] | None = None, min_ratio: float = 4.0) -> list[str]:
    """Robust log-variance outliers and flat channels, scored separately per sensor type (magnetometers and
    gradiometers have different units and scales and must not share one distribution). A channel must exceed the
    robust z threshold AND differ from the median variance by ``min_ratio`` (guards against tiny MADs)."""
    types = np.array(ch_types if ch_types is not None else ["meg"] * len(ch_names))
    var = np.var(data, axis=1)
    bad = []
    for t in np.unique(types):
        m = types == t
        lv = np.log(var[m] + 1e-40)
        med = np.median(lv)
        mad = np.median(np.abs(lv - med)) * 1.4826 + 1e-12
        z = (lv - med) / mad
        for n, zz, v in zip(np.array(ch_names)[m], z, var[m]):
            if (abs(zz) > z_thresh and abs(np.log(v + 1e-40) - med) > np.log(min_ratio)) or v < 1e-34:
                bad.append(str(n))
    return [n for n in ch_names if n in set(bad)]


def load_epochs(path: Path, event_id: dict[str, int], tmin: float = -0.2, tmax: float = 0.8,
                l_freq: float | None = 1.0, h_freq: float | None = 40.0) -> MegEpochs:
    import mne

    with mne.utils.use_log_level("error"):
        raw = mne.io.read_raw_fif(path, preload=True)
        raw.filter(l_freq, h_freq, picks="meg")
        picks = mne.pick_types(raw.info, meg=True)
        names = [raw.ch_names[p] for p in picks]
        bads = detect_bad_channels(raw.get_data(picks=picks), names, ch_types=raw.get_channel_types(picks=picks))
        raw.info["bads"] = bads
        events = mne.find_events(raw)
        ep = mne.Epochs(raw, events, event_id=event_id, tmin=tmin, tmax=tmax, baseline=(None, 0), picks="meg",
                        preload=True, reject=None)
    inv = {v: k for k, v in event_id.items()}
    labels = np.array([inv[c] for c in ep.events[:, 2]])
    return MegEpochs(ep.get_data(), labels, ep.times, ep.ch_names, bads, float(ep.info["sfreq"]))


def sensor_features(ep: MegEpochs, windows: list[tuple[float, float]]) -> np.ndarray:
    feats = []
    for a, b in windows:
        m = (ep.times >= a) & (ep.times < b)
        feats.append(ep.data[:, :, m].mean(axis=2))
    return np.concatenate(feats, axis=1)


def time_resolved_decoding(x: np.ndarray, y: np.ndarray, groups: np.ndarray | None = None, n_splits: int = 5,
                           seed: int = 0) -> np.ndarray:
    """Per-time-point AUC. With ``groups`` uses leave-one-group-out (subject-independent)."""
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import LeaveOneGroupOut, StratifiedKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    yb = (y == np.unique(y)[1]).astype(int)
    cv = (LeaveOneGroupOut().split(x, yb, groups) if groups is not None
          else StratifiedKFold(n_splits, shuffle=True, random_state=seed).split(x, yb))
    folds = list(cv)
    scores = np.zeros((len(folds), x.shape[2]))
    for f, (tr, te) in enumerate(folds):
        for t in range(x.shape[2]):
            clf = make_pipeline(StandardScaler(), LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"))
            clf.fit(x[tr, :, t], yb[tr])
            scores[f, t] = roc_auc_score(yb[te], clf.decision_function(x[te, :, t]))
    return scores.mean(axis=0)
