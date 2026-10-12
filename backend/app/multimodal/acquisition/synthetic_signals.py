"""Deterministic synthetic waveform generators with ground truth.

These produce SYNTHETIC engineering test signals. They are not models of any participant and carry no
neuroscientific meaning; the ground truth they return exists only to verify processing pipelines.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import signal as sps


@dataclass
class ConditionBlock:
    label: str
    start_s: float
    duration_s: float
    arousal: float = 0.0
    engagement: float = 0.0


@dataclass
class SyntheticTruth:
    values: dict[str, np.ndarray | float | list] = field(default_factory=dict)


def default_blocks(duration_s: float) -> list[ConditionBlock]:
    pattern = [("rest", 0.0, 0.0), ("perception", 0.4, 0.6), ("imagery", 0.5, 0.8)]
    blocks, t, i = [], 0.0, 0
    while t < duration_s:
        label, arousal, engagement = pattern[i % len(pattern)]
        d = min(20.0, duration_s - t)
        blocks.append(ConditionBlock(label, t, d, arousal, engagement))
        t += d
        i += 1
    return blocks


def latent_timeline(t: np.ndarray, blocks: list[ConditionBlock], key: str, tau_s: float = 3.0) -> np.ndarray:
    raw = np.zeros_like(t)
    for b in blocks:
        raw[(t >= b.start_s) & (t < b.start_s + b.duration_s)] = getattr(b, key)
    if len(t) < 2:
        return raw
    dt = float(t[1] - t[0])
    alpha = 1.0 - np.exp(-dt / tau_s)
    return sps.lfilter([alpha], [1.0, alpha - 1.0], raw, zi=[raw[0] * (1 - alpha)])[0]


def _pink(n: int, rng: np.random.Generator) -> np.ndarray:
    white = rng.standard_normal(n)
    spec = np.fft.rfft(white)
    f = np.arange(spec.size, dtype=float)
    f[0] = 1.0
    out = np.fft.irfft(spec / np.sqrt(f), n)
    return out / (np.std(out) + 1e-12)


def synth_ecg(
    fs: float, duration_s: float, rng: np.random.Generator, mean_hr_bpm: float = 65.0,
    rsa_fraction: float = 0.04, resp_rate_hz: float = 0.25, ectopic_indices: tuple[int, ...] = (),
    noise_mv: float = 0.02, arousal: np.ndarray | None = None,
) -> tuple[np.ndarray, SyntheticTruth]:
    n = int(round(fs * duration_s))
    t = np.arange(n) / fs
    r_times, rr = [0.5], []
    while r_times[-1] < duration_s - 1.0:
        tc = r_times[-1]
        hr = mean_hr_bpm
        if arousal is not None:
            hr = mean_hr_bpm + 10.0 * float(arousal[min(int(tc * fs), n - 1)])
        base = 60.0 / hr
        interval = base * (1.0 + rsa_fraction * np.sin(2 * np.pi * resp_rate_hz * tc)) + rng.normal(0, 0.01)
        if len(rr) in ectopic_indices:
            interval *= 0.6
        rr.append(interval)
        r_times.append(tc + interval)
    r_times_arr = np.array(r_times)
    waves = [(-0.2, 0.025, 0.12), (-0.03, 0.008, -0.12), (0.0, 0.01, 1.2), (0.03, 0.008, -0.25), (0.25, 0.04, 0.3)]
    ecg = np.zeros(n)
    for rt in r_times_arr:
        lo, hi = int(max(0, (rt - 0.4) * fs)), int(min(n, (rt + 0.5) * fs))
        seg = t[lo:hi] - rt
        for mu, sigma, amp in waves:
            ecg[lo:hi] += amp * np.exp(-0.5 * ((seg - mu) / sigma) ** 2)
    ecg += 0.05 * np.sin(2 * np.pi * 0.15 * t) + rng.normal(0, noise_mv, n)
    rr_arr = np.diff(r_times_arr)
    normal = np.ones(rr_arr.size, dtype=bool)
    for k in ectopic_indices:
        if k < normal.size:
            normal[k] = False
            if k + 1 < normal.size:
                normal[k + 1] = False
    nn = rr_arr[normal]
    truth = SyntheticTruth({
        "r_peak_times_s": r_times_arr,
        "rr_s": rr_arr,
        "mean_hr_bpm": 60.0 / float(np.mean(nn)),
        "rmssd_ms": float(np.sqrt(np.mean(np.diff(nn * 1000.0) ** 2))),
        "sdnn_ms": float(np.std(nn * 1000.0, ddof=1)),
        "ectopic_indices": list(ectopic_indices),
    })
    return ecg, truth


def synth_eda(
    fs: float, duration_s: float, rng: np.random.Generator, scr_onsets_s: tuple[float, ...] = (),
    scr_amplitudes_us: tuple[float, ...] = (), tonic_us: float = 4.0, drift_us_per_min: float = 0.2,
    noise_us: float = 0.003,
) -> tuple[np.ndarray, SyntheticTruth]:
    n = int(round(fs * duration_s))
    t = np.arange(n) / fs
    tonic = tonic_us + drift_us_per_min * t / 60.0
    phasic = np.zeros(n)
    tau_rise, tau_decay = 0.75, 2.0
    peak_lag = tau_rise * tau_decay / (tau_decay - tau_rise) * np.log(tau_decay / tau_rise)
    kernel_peak = np.exp(-peak_lag / tau_decay) - np.exp(-peak_lag / tau_rise)
    latency = 1.5
    for onset, amp in zip(scr_onsets_s, scr_amplitudes_us):
        start = onset + latency
        mask = t >= start
        dt = t[mask] - start
        phasic[mask] += amp * (np.exp(-dt / tau_decay) - np.exp(-dt / tau_rise)) / kernel_peak
    eda = tonic + phasic + rng.normal(0, noise_us, n)
    truth = SyntheticTruth({
        "scr_stimulus_onsets_s": np.array(scr_onsets_s, dtype=float),
        "scr_response_onsets_s": np.array(scr_onsets_s, dtype=float) + latency,
        "scr_peak_times_s": np.array(scr_onsets_s, dtype=float) + latency + peak_lag,
        "scr_amplitudes_us": np.array(scr_amplitudes_us, dtype=float),
        "tonic_start_us": tonic_us,
    })
    return eda, truth


def synth_respiration(
    fs: float, duration_s: float, rng: np.random.Generator, rate_hz: float = 0.25,
    rate_jitter: float = 0.03, ie_ratio: float = 0.7, noise: float = 0.02,
) -> tuple[np.ndarray, SyntheticTruth]:
    n = int(round(fs * duration_s))
    sig = np.zeros(n)
    onsets, peaks, periods = [], [], []
    tc = 0.3
    while tc < duration_s:
        period = (1.0 / rate_hz) * (1.0 + rng.normal(0, rate_jitter))
        ti = period * ie_ratio / (1.0 + ie_ratio)
        te = period - ti
        i0 = int(tc * fs)
        ni, ne = int(ti * fs), int(te * fs)
        if i0 + ni + ne > n:
            break
        sig[i0:i0 + ni] = 0.5 - 0.5 * np.cos(np.pi * np.arange(ni) / ni)
        sig[i0 + ni:i0 + ni + ne] = 0.5 + 0.5 * np.cos(np.pi * np.arange(ne) / ne)
        onsets.append(tc)
        peaks.append(tc + ti)
        periods.append(period)
        tc += period
    sig = sig - 0.5 + rng.normal(0, noise, n)
    periods_arr = np.array(periods)
    truth = SyntheticTruth({
        "inspiration_onsets_s": np.array(onsets),
        "inspiration_peaks_s": np.array(peaks),
        "rate_bpm": 60.0 / float(np.mean(periods_arr)) if periods_arr.size else float("nan"),
        "ti_te_ratio": ie_ratio,
    })
    return sig, truth


EEG_MONTAGE_16 = ["Fp1", "Fp2", "F3", "F4", "Fz", "C3", "C4", "Cz", "P3", "P4", "Pz", "O1", "O2", "Oz", "T7", "T8"]


def synth_eeg(
    fs: float, duration_s: float, rng: np.random.Generator, n_channels: int = 8,
    engagement: np.ndarray | None = None, blink_times_s: tuple[float, ...] = (), line_hz: float = 50.0,
) -> tuple[np.ndarray, list[str], SyntheticTruth]:
    if not 1 <= n_channels <= 16:
        raise ValueError("synthetic EEG supports 1-16 channels")
    names = EEG_MONTAGE_16[:n_channels]
    n = int(round(fs * duration_s))
    t = np.arange(n) / fs
    data = np.empty((n, n_channels))
    alpha_env = np.ones(n) if engagement is None else 1.0 - 0.5 * engagement
    for c, name in enumerate(names):
        posterior = name[0] in "PO"
        bg = 8.0 * _pink(n, rng)
        alpha = (6.0 if posterior else 2.0) * alpha_env * np.sin(2 * np.pi * 10.0 * t + rng.uniform(0, 2 * np.pi))
        data[:, c] = bg + alpha + 1.5 * np.sin(2 * np.pi * line_hz * t)
    for bt in blink_times_s:
        blink = 120.0 * np.exp(-0.5 * ((t - bt) / 0.08) ** 2)
        for c, name in enumerate(names):
            if name.startswith("Fp"):
                data[:, c] += blink
            elif name.startswith("F"):
                data[:, c] += 0.4 * blink
    truth = SyntheticTruth({"alpha_hz": 10.0, "line_hz": line_hz, "blink_times_s": list(blink_times_s)})
    return data, names, truth


def canonical_hrf(dt: float, length_s: float = 32.0) -> np.ndarray:
    from scipy.stats import gamma
    tt = np.arange(0, length_s, dt)
    h = gamma.pdf(tt, 6) - gamma.pdf(tt, 16) / 6.0
    return h / np.max(h)


def synth_fnirs_raw(
    fs: float, duration_s: float, rng: np.random.Generator, blocks: list[ConditionBlock],
    wavelengths_nm: tuple[float, float] = (760.0, 850.0), n_long: int = 4, include_short: bool = True,
    ppf: float = 6.0, motion_times_s: tuple[float, ...] = (),
) -> tuple[np.ndarray, list[dict], SyntheticTruth]:
    from mne.preprocessing.nirs._beer_lambert_law import _load_absorption

    n = int(round(fs * duration_s))
    t = np.arange(n) / fs
    task = np.zeros(n)
    for b in blocks:
        if b.label == "imagery":
            task[(t >= b.start_s) & (t < b.start_s + b.duration_s)] = 1.0
    hrf = canonical_hrf(1.0 / fs)
    evoked = np.convolve(task, hrf)[:n]
    evoked /= max(np.max(np.abs(evoked)), 1e-12)
    systemic = 0.5 * np.sin(2 * np.pi * 1.1 * t) + 0.8 * np.sin(2 * np.pi * 0.1 * t + 0.3)
    abs_coef = _load_absorption(list(wavelengths_nm))
    layout, cols = [], []
    truth_hbo, truth_hbr = [], []
    configs = [(f"S{k + 1}_D{k + 1}", 0.03, 1.0) for k in range(n_long)]
    if include_short:
        configs.append((f"S{n_long + 1}_D{n_long + 1}", 0.008, 0.0))
    for idx, (pair, dist, brain_gain) in enumerate(configs):
        src = np.array([0.02 * idx, 0.05, 0.08])
        det = src + np.array([dist, 0.0, 0.0])
        hbo = 1e-6 * (brain_gain * 0.6 * evoked + 0.4 * systemic) + rng.normal(0, 2e-8, n)
        hbr = 1e-6 * (brain_gain * -0.2 * evoked - 0.1 * systemic) + rng.normal(0, 1e-8, n)
        truth_hbo.append(hbo)
        truth_hbr.append(hbr)
        for w_i, wl in enumerate(wavelengths_nm):
            ext_hbo, ext_hbr = abs_coef[w_i]
            od = (ext_hbo * hbo + ext_hbr * hbr) * dist * ppf * 1e3
            intensity = 1.0 * np.exp(-od) * (1.0 + rng.normal(0, 1e-4, n))
            for mt in motion_times_s:
                intensity *= 1.0 + 0.15 * ((t >= mt) & (t < mt + 0.5))
            cols.append(intensity)
            layout.append({
                "name": f"{pair} {int(wl)}", "pair": pair, "wavelength_nm": float(wl),
                "source_position_m": tuple(float(x) for x in src),
                "detector_position_m": tuple(float(x) for x in det),
                "short_channel": dist < 0.015,
            })
    truth = SyntheticTruth({
        "hbo_M": np.array(truth_hbo).T, "hbr_M": np.array(truth_hbr).T, "task_regressor": task,
        "evoked": evoked, "ppf": ppf, "motion_times_s": list(motion_times_s),
    })
    return np.array(cols).T, layout, truth
