"""EEG preprocessing and features.

Band-power features are DERIVED_METRIC values. They are not evidence of imagery vividness on their own; any link
between spectral power and imagery must be established by validated, individually calibrated predictors.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import signal as sps

from app.multimodal.processing.common import Feature, FeatureSet, butter_filter
from app.multimodal.schemas import Modality, SourceKind

BANDS = {"delta": (1.0, 4.0), "theta": (4.0, 8.0), "alpha": (8.0, 13.0), "beta": (13.0, 30.0),
         "gamma": (30.0, 45.0)}
POSTERIOR_PREFIXES = ("P", "O")
PTP_REJECT_UV = 150.0


@dataclass
class PreprocessConfig:
    reference: str | None = "average"
    notch_hz: float | None = 50.0
    band_hz: tuple[float, float] | None = (1.0, 45.0)


@dataclass
class PreprocessLog:
    steps: list[str] = field(default_factory=list)


def preprocess(data: np.ndarray, fs: float, ch_names: list[str], cfg: PreprocessConfig | None = None,
               ) -> tuple[np.ndarray, PreprocessLog]:
    cfg = cfg or PreprocessConfig()
    x = np.asarray(data, dtype=float).copy()
    log = PreprocessLog()
    if cfg.reference == "average":
        x = x - x.mean(axis=1, keepdims=True)
        log.steps.append("reference:average")
    elif cfg.reference:
        if cfg.reference not in ch_names:
            raise ValueError(f"reference channel {cfg.reference} not present")
        x = x - x[:, [ch_names.index(cfg.reference)]]
        log.steps.append(f"reference:{cfg.reference}")
    if cfg.notch_hz and cfg.notch_hz < fs / 2:
        b, a = sps.iirnotch(cfg.notch_hz, 30.0, fs)
        x = sps.filtfilt(b, a, x, axis=0)
        log.steps.append(f"notch:{cfg.notch_hz}")
    if cfg.band_hz:
        x = butter_filter(x, fs, cfg.band_hz[0], min(cfg.band_hz[1], fs / 2 * 0.9), order=4)
        log.steps.append(f"bandpass:{cfg.band_hz[0]}-{cfg.band_hz[1]}")
    return x, log


def channel_quality(x: np.ndarray, fs: float, ch_names: list[str], raw: np.ndarray | None = None) -> dict:
    out = {}
    f, p = sps.welch(x, fs=fs, nperseg=min(x.shape[0], int(2 * fs)), axis=0)
    total = np.trapezoid(p[(f >= 1) & (f <= 45)], f[(f >= 1) & (f <= 45)], axis=0) + 1e-12
    hf = np.trapezoid(p[(f >= 30) & (f <= 45)], f[(f >= 30) & (f <= 45)], axis=0)
    line = None
    if raw is not None:
        fr, pr = sps.welch(raw, fs=fs, nperseg=min(raw.shape[0], int(2 * fs)), axis=0)
        near = lambda hz: (fr > hz - 1) & (fr < hz + 1)  # noqa: E731
        line = np.max([pr[near(50)].sum(axis=0), pr[near(60)].sum(axis=0)], axis=0) / (pr.sum(axis=0) + 1e-12)
    for c, name in enumerate(ch_names):
        flags = []
        ptp = float(np.ptp(x[:, c]))
        sd = float(np.std(x[:, c]))
        if sd < 0.1:
            flags.append("flat")
        if ptp > PTP_REJECT_UV:
            flags.append("high_amplitude")
        emg = float(hf[c] / total[c])
        if emg > 0.4:
            flags.append("emg_like_hf_power")
        if line is not None and line[c] > 0.5:
            flags.append("line_noise")
        score = 1.0
        score *= 0.0 if "flat" in flags else 1.0
        score *= 0.4 if "high_amplitude" in flags else 1.0
        score *= 0.6 if "emg_like_hf_power" in flags else 1.0
        score *= 0.7 if "line_noise" in flags else 1.0
        out[name] = {"score": score, "flags": flags, "ptp_uv": ptp, "hf_ratio": emg}
    return out


def bandpowers(x: np.ndarray, fs: float) -> dict[str, np.ndarray]:
    f, p = sps.welch(x, fs=fs, nperseg=min(x.shape[0], int(2 * fs)), axis=0)
    out = {}
    for name, (lo, hi) in BANDS.items():
        m = (f >= lo) & (f < min(hi, fs / 2))
        out[name] = np.trapezoid(p[m], f[m], axis=0) if m.any() else np.zeros(x.shape[1])
    return out


def time_frequency(x: np.ndarray, fs: float, freqs: np.ndarray, n_cycles: float = 5.0) -> np.ndarray:
    """Morlet power, shape (n_channels, n_freqs, n_times)."""
    from mne.time_frequency import tfr_array_morlet

    arr = np.asarray(x, dtype=float).T[None]
    return tfr_array_morlet(arr, sfreq=fs, freqs=freqs, n_cycles=n_cycles, output="power", verbose="error")[0]


def epoch(x: np.ndarray, times: np.ndarray, events: list[tuple[float, str]], fs: float, tmin: float, tmax: float,
          baseline: tuple[float, float] | None = (None, 0.0), reject_ptp_uv: float | None = PTP_REJECT_UV,
          ) -> tuple[np.ndarray, list[str], list[int]]:
    """Returns (epochs[n, ch, t], labels, rejected_event_indices)."""
    n_t = int(round((tmax - tmin) * fs))
    rel = np.arange(n_t) / fs + tmin
    eps, labels, rejected = [], [], []
    for k, (t_ev, label) in enumerate(events):
        i0 = int(np.searchsorted(times, t_ev + tmin))
        if i0 < 0 or i0 + n_t > x.shape[0] or abs(times[i0] - (t_ev + tmin)) > 1.5 / fs:
            rejected.append(k)
            continue
        ep = x[i0:i0 + n_t].T.copy()
        if baseline is not None:
            b0 = rel[0] if baseline[0] is None else baseline[0]
            bm = (rel >= b0) & (rel <= baseline[1])
            if bm.any():
                ep -= ep[:, bm].mean(axis=1, keepdims=True)
        if reject_ptp_uv is not None and np.ptp(ep, axis=1).max() > reject_ptp_uv:
            rejected.append(k)
            continue
        eps.append(ep)
        labels.append(label)
    return (np.array(eps) if eps else np.empty((0, x.shape[1], n_t))), labels, rejected


def ica_remove_ocular(x: np.ndarray, fs: float, ch_names: list[str], eog_proxies: tuple[str, ...] = ("Fp1", "Fp2"),
                      n_components: int | None = None, seed: int = 0) -> tuple[np.ndarray, dict]:
    """Optional ICA ocular-artifact removal using frontal channels as EOG proxies (no dedicated EOG)."""
    import mne

    proxies = [c for c in eog_proxies if c in ch_names]
    if not proxies:
        return x, {"applied": False, "reason": "no frontal EOG proxy channels"}
    info = mne.create_info(ch_names, fs, "eeg")
    raw = mne.io.RawArray(np.asarray(x, dtype=float).T * 1e-6, info, verbose="error")
    raw_hp = raw.copy().filter(1.0, None, verbose="error")
    ica = mne.preprocessing.ICA(n_components=n_components or min(len(ch_names) - 1, 15), random_state=seed,
                                max_iter="auto", verbose="error")
    ica.fit(raw_hp, verbose="error")
    bads, _ = ica.find_bads_eog(raw_hp, ch_name=proxies, measure="correlation", threshold=0.7, verbose="error")
    ica.exclude = bads
    cleaned = ica.apply(raw.copy(), verbose="error").get_data().T * 1e6
    return cleaned, {"applied": True, "excluded_components": [int(b) for b in bads],
                     "note": "EOG proxies are scalp channels; ocular/neural separation is approximate."}


def eeg_features(x_raw: np.ndarray, fs: float, ch_names: list[str], stream_id: str = "eeg",
                 source_kind: SourceKind = SourceKind.SYNTHETIC, t_start: float = 0.0,
                 cfg: PreprocessConfig | None = None) -> FeatureSet:
    x_raw = np.asarray(x_raw, dtype=float)
    x, log = preprocess(x_raw, fs, ch_names, cfg)
    q = channel_quality(x, fs, ch_names, raw=x_raw)
    good = [i for i, n in enumerate(ch_names) if q[n]["score"] >= 0.5]
    fsets = FeatureSet(modality=Modality.EEG, stream_id=stream_id, source_kind=source_kind, t_start=t_start,
                       t_end=t_start + x.shape[0] / fs, quality=float(np.mean([q[n]["score"] for n in ch_names])))
    if len(good) < max(2, len(ch_names) // 2):
        fsets.flags.append("insufficient_good_channels")
    for n in ch_names:
        if q[n]["flags"]:
            fsets.flags.append(f"{n}:{','.join(q[n]['flags'])}")
    method = "welch_2s;" + ";".join(log.steps)
    if not good:
        return fsets
    bp = bandpowers(x[:, good], fs)
    total = sum(v for v in bp.values()) + 1e-12
    for name, v in bp.items():
        fsets.add(Feature(name=f"rel_{name}", value=float(np.mean(v / total)), unit="ratio",
                          confidence=fsets.quality, method=method))
    post = [i for i, gi in enumerate(good) if ch_names[gi].startswith(POSTERIOR_PREFIXES)]
    if post:
        fsets.add(Feature(name="posterior_rel_alpha", value=float(np.mean((bp["alpha"] / total)[post])),
                          unit="ratio", confidence=fsets.quality, method=method))
    fsets.add(Feature(name="theta_beta_ratio", value=float(np.mean(bp["theta"]) / (np.mean(bp["beta"]) + 1e-12)),
                      unit="ratio", confidence=fsets.quality, method=method))
    if "F3" in ch_names and "F4" in ch_names:
        i3, i4 = ch_names.index("F3"), ch_names.index("F4")
        if i3 in good and i4 in good:
            a = bandpowers(x[:, [i3, i4]], fs)["alpha"]
            fsets.add(Feature(name="frontal_alpha_asymmetry", value=float(np.log(a[1]) - np.log(a[0])),
                              unit="ln(uV2)", confidence=fsets.quality, method=method))
    return fsets
