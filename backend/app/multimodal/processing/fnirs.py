"""fNIRS: raw CW intensity -> optical density -> (optional TDDR motion repair) -> modified Beer-Lambert ->
short-channel regression -> HRF-based GLM.

The modified Beer-Lambert step is delegated to MNE and is refused unless every channel has a wavelength, both
optode positions, a plausible source-detector distance, each pair has >= 2 wavelengths, and a partial pathlength
factor is supplied explicitly. Without these, raw optical data are preserved and no hemoglobin values are produced.
Peripheral PPG is not cerebral fNIRS and is rejected outright.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from app.multimodal.acquisition.synthetic_signals import canonical_hrf
from app.multimodal.processing.common import butter_filter
from app.multimodal.schemas import Modality, StreamInfo

MAX_DISTANCE_M = 0.06
SHORT_CHANNEL_M = 0.015
HEMODYNAMIC_DELAY_S = 5.0


class FnirsMetadataError(ValueError):
    pass


@dataclass
class HemoResult:
    times: np.ndarray
    hbo: np.ndarray
    hbr: np.ndarray
    pair_names: list[str]
    short_pairs: list[str]
    sci: dict[str, float]
    motion_corrected: bool
    short_channel_regressed: bool
    log: list[str] = field(default_factory=list)


def validate_for_mbll(info: StreamInfo, ppf: float | None) -> dict[str, list[int]]:
    if info.modality != Modality.FNIRS:
        raise FnirsMetadataError(f"not an fNIRS stream: {info.modality.value}")
    kinds = {c.kind for c in info.channels}
    if kinds & {"ppg", "pulse_oximetry"}:
        raise FnirsMetadataError("peripheral PPG is not cerebral fNIRS; refusing hemoglobin conversion")
    if info.metadata.get("measurement", "cw_amplitude") != "cw_amplitude":
        raise FnirsMetadataError("only continuous-wave raw intensity is supported for mBLL")
    if ppf is None:
        raise FnirsMetadataError("partial pathlength factor must be supplied explicitly (no silent default)")
    groups: dict[str, list[int]] = defaultdict(list)
    for i, c in enumerate(info.channels):
        if c.wavelength_nm is None:
            raise FnirsMetadataError(f"channel {c.name} has no wavelength")
        if c.source_position_m is None or c.detector_position_m is None:
            raise FnirsMetadataError(f"channel {c.name} lacks source/detector geometry")
        d = float(np.linalg.norm(np.subtract(c.detector_position_m, c.source_position_m)))
        if not 0.0 < d <= MAX_DISTANCE_M:
            raise FnirsMetadataError(f"channel {c.name} source-detector distance {d:.4f} m is implausible")
        groups[c.name.split(" ")[0]].append(i)
    for pair, idx in groups.items():
        wls = {info.channels[i].wavelength_nm for i in idx}
        if len(wls) < 2:
            raise FnirsMetadataError(f"pair {pair} has {len(wls)} wavelength(s); >= 2 needed to separate HbO/HbR")
    return groups


def _to_mne_raw(info: StreamInfo, data: np.ndarray):
    import mne

    names = [c.name for c in info.channels]
    minfo = mne.create_info(names, info.nominal_rate_hz, "fnirs_cw_amplitude")
    for ch, spec in zip(minfo["chs"], info.channels):
        src = np.array(spec.source_position_m)
        det = np.array(spec.detector_position_m)
        ch["loc"][:3] = (src + det) / 2
        ch["loc"][3:6] = src
        ch["loc"][6:9] = det
        ch["loc"][9] = spec.wavelength_nm
    return mne.io.RawArray(np.asarray(data, dtype=float).T, minfo, verbose="error")


def to_hemoglobin(info: StreamInfo, data: np.ndarray, ppf: float | None, motion_correction: bool = True,
                  short_channel_regression: bool = True, band: tuple[float, float] = (0.01, 0.5)) -> HemoResult:
    import mne

    groups = validate_for_mbll(info, ppf)
    log = []
    raw = _to_mne_raw(info, data)
    with mne.utils.use_log_level("error"):
        od = mne.preprocessing.nirs.optical_density(raw)
        log.append("optical_density:-ln(I/mean)")
        sci_vals = mne.preprocessing.nirs.scalp_coupling_index(od)
        if motion_correction:
            od = mne.preprocessing.nirs.temporal_derivative_distribution_repair(od)
            log.append("motion:TDDR")
        hb = mne.preprocessing.nirs.beer_lambert_law(od, ppf=ppf)
        log.append(f"mbll:ppf={ppf}")
    hb_data = hb.get_data()
    names = hb.ch_names
    pairs = list(groups)
    hbo = np.array([hb_data[names.index(f"{p} hbo")] for p in pairs]).T
    hbr = np.array([hb_data[names.index(f"{p} hbr")] for p in pairs]).T
    fs = info.nominal_rate_hz
    hbo = butter_filter(hbo, fs, band[0], band[1], order=3)
    hbr = butter_filter(hbr, fs, band[0], band[1], order=3)
    log.append(f"bandpass:{band}")
    dist = {p: float(np.linalg.norm(np.subtract(info.channels[groups[p][0]].detector_position_m,
                                                info.channels[groups[p][0]].source_position_m))) for p in pairs}
    short = [p for p in pairs if dist[p] < SHORT_CHANNEL_M]
    regressed = False
    if short_channel_regression and short:
        for arr in (hbo, hbr):
            sc = arr[:, [pairs.index(p) for p in short]]
            design = np.column_stack([sc, np.ones(len(sc))])
            for k, p in enumerate(pairs):
                if p in short:
                    continue
                beta, *_ = np.linalg.lstsq(design, arr[:, k], rcond=None)
                arr[:, k] = arr[:, k] - design[:, :-1] @ beta[:-1]
        regressed = True
        log.append("short_channel_regression:ols")
    elif not short:
        log.append("WARNING:no_short_channels_superficial_physiology_not_removed")
    sci = {ch: float(v) for ch, v in zip(raw.ch_names, sci_vals)}
    times = np.arange(hbo.shape[0]) / fs
    return HemoResult(times, hbo, hbr, pairs, short, sci, motion_correction, regressed, log)


def hrf_design(onsets_s: list[float], durations_s: list[float], n: int, fs: float) -> np.ndarray:
    box = np.zeros(n)
    t = np.arange(n) / fs
    for o, d in zip(onsets_s, durations_s):
        box[(t >= o) & (t < o + d)] = 1.0
    reg = np.convolve(box, canonical_hrf(1.0 / fs))[:n]
    return reg / (np.max(np.abs(reg)) + 1e-12)


def glm(y: np.ndarray, regressor: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """OLS beta and t for one task regressor plus intercept and linear drift, per column of ``y``."""
    n = y.shape[0]
    x = np.column_stack([regressor, np.ones(n), np.linspace(-1, 1, n)])
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    resid = y - x @ beta
    dof = n - x.shape[1]
    sigma2 = (resid ** 2).sum(axis=0) / dof
    var_b = sigma2 * np.linalg.inv(x.T @ x)[0, 0]
    return beta[0], beta[0] / np.sqrt(var_b + 1e-30)
