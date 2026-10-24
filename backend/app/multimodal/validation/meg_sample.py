"""MEG validation on the MNE ``sample`` dataset (one participant, Elekta Neuromag 306-channel MEG).

Perception only: auditory vs visual stimuli (event codes 1-2 vs 3-4). There is no imagery condition, and one
participant means subject-independent generalization cannot be tested here (reported as BLOCKED).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from app.multimodal.acquisition.replay import read_fif
from app.multimodal.processing import meg
from app.multimodal.validation.gates import Criterion, GateResult

CRITERIA = [
    Criterion("event_count_mismatch", "<=", 0, 0, "Event import must match MNE exactly."),
    Criterion("event_sample_max_abs_offset", "<=", 0, 0, "Event sample indices must match after first_samp."),
    Criterion("auc_peak", ">=", 0.90, 0.70,
              "Auditory vs visual evoked fields differ strongly in sensor topography; >0.9 is expected."),
    Criterion("prestim_auc_abs_dev", "<=", 0.10, 0.20, "Pre-stimulus decoding must stay near chance (0.5)."),
    Criterion("bad_channel_flag_fraction", "<=", 0.05, 0.10,
              "POST HOC (added after the first run flagged 29/306 channels because magnetometers and gradiometers "
              "were pooled): a usable detector flags few channels in a curated dataset."),
    Criterion("annotated_bad_missed", "<=", 0, 0, "POST HOC: the channel the dataset authors marked bad must be "
                                                   "flagged."),
]


def run(root: Path) -> GateResult:
    import mne

    raw_path = next((root / "mne").rglob("sample_audvis_filt-0-40_raw.fif"))
    raw = mne.io.read_raw_fif(raw_path, preload=True, verbose="error")
    ref_events = mne.find_events(raw, stim_channel="STI 014", verbose="error")
    rec = read_fif(raw_path)
    ours = np.array([[e["sample"], e["code"]] for e in rec.events])
    ref = np.column_stack([ref_events[:, 0] - raw.first_samp, ref_events[:, 2]])
    count_mismatch = abs(len(ours) - len(ref))
    offset = int(np.max(np.abs(ours[:, 0] - ref[:, 0]))) if count_mismatch == 0 else None
    meg_picks = mne.pick_types(raw.info, meg=True, exclude=[])
    names = [raw.ch_names[i] for i in meg_picks]
    detected_bads = meg.detect_bad_channels(raw.get_data(picks=meg_picks), names,
                                            ch_types=raw.get_channel_types(picks=meg_picks))
    annotated_bads = [b for b in raw.info["bads"] if b.startswith("MEG")]
    event_id = {"auditory": 1, "auditory_r": 2, "visual": 3, "visual_r": 4}
    with mne.utils.use_log_level("error"):
        ep = mne.Epochs(raw, ref_events, event_id=event_id, tmin=-0.2, tmax=0.5, baseline=(None, 0),
                        picks="meg", preload=True, reject=dict(grad=4000e-13, mag=4e-12))
    y = np.where(np.isin(ep.events[:, 2], [1, 2]), "auditory", "visual")
    x = ep.get_data()
    auc = meg.time_resolved_decoding(x, y, n_splits=5)
    times = ep.times
    peak = int(np.argmax(auc))
    pre = float(np.mean(auc[times < 0]))
    rng = np.random.default_rng(0)
    perm = meg.time_resolved_decoding(x, rng.permutation(y), n_splits=5)
    g = GateResult(
        experiment="MEG_SAMPLE_AUDITORY_VS_VISUAL",
        dataset={"name": "MNE sample (sample_audvis_filt-0-40_raw)", "source": "mne.datasets.sample",
                 "mne": mne.__version__, "n_meg_channels": len(names), "sfreq": float(raw.info["sfreq"])},
        participants={"n": 1},
        task_and_labels="Perception of auditory (codes 1,2) vs visual (codes 3,4) stimuli; no imagery condition.",
        design="Stratified 5-fold CV over trials (single participant); time-resolved LDA per time point.",
        metric_definitions={"auc": "ROC AUC per time point, mean over folds",
                            "prestim_auc_abs_dev": "|mean AUC over t<0 - 0.5|"},
        criteria=CRITERIA,
        results={"events": {"ours": int(len(ours)), "mne": int(len(ref)), "max_abs_sample_offset": offset},
                 "bad_channels": {"detected": detected_bads, "annotated_in_dataset": annotated_bads,
                                  "annotated_found": [b for b in annotated_bads if b in detected_bads]},
                 "n_epochs": int(len(y)), "auc_peak": float(auc[peak]), "auc_peak_latency_s": float(times[peak]),
                 "auc_prestim_mean": pre, "permuted_label_auc_peak": float(perm.max()),
                 "auc_timecourse": {"times": times[::5].round(3).tolist(), "auc": auc[::5].round(3).tolist()}},
        negative_controls={"prestimulus_auc_mean": pre, "label_permutation_auc_max": float(perm.max())},
        generalization={"subject_independent": "BLOCKED: single participant"},
        limitations=["Single participant; perception only; source space not attempted (requires MRI/BEM).",
                     "First run pooled magnetometers and gradiometers in bad-channel detection (29 channels "
                     "flagged); fixed to per-type scoring and re-run. The two bad-channel criteria are post hoc."],
    )
    g.decide({"event_count_mismatch": count_mismatch, "event_sample_max_abs_offset": offset,
              "auc_peak": float(auc[peak]), "prestim_auc_abs_dev": abs(pre - 0.5),
              "bad_channel_flag_fraction": len(detected_bads) / len(names),
              "annotated_bad_missed": len([b for b in annotated_bads if b not in detected_bads])})
    return g
