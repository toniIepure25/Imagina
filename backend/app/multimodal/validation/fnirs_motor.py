"""fNIRS validation on the MNE ``fnirs_motor`` dataset (NIRx, one participant, finger tapping vs control).

Checks: SNIRF round-trip of real geometry/wavelengths through our reader; our OD -> mBLL path vs MNE's reference
path; channel-wise GLM t-values vs MNE-NIRS; block-averaged HbO peak latency; scalp coupling index; refusal on
missing metadata. The data have no short-separation channels, so superficial physiology cannot be regressed.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from app.multimodal.acquisition.replay import read_snirf
from app.multimodal.processing.common import butter_filter
from app.multimodal.processing.fnirs import FnirsMetadataError, glm, hrf_design, to_hemoglobin
from app.multimodal.schemas import ChannelSpec, Modality, Provenance, SourceKind, StreamInfo
from app.multimodal.validation.gates import Criterion, GateResult

PPF = 6.0
CRITERIA = [
    Criterion("geometry_max_abs_error_m", "<=", 1e-6, 1e-3,
              "SNIRF round-trip must preserve optode positions exactly (float precision)."),
    Criterion("hbo_corr_vs_mne_min", ">=", 0.999, 0.99,
              "Same equations; anything below 0.99 means channel pairing or wavelength handling is wrong."),
    Criterion("glm_t_corr_vs_mne_nirs", ">=", 0.80, 0.50,
              "Different HRF/drift models give similar but not identical channel maps."),
    Criterion("hbo_peak_latency_s_dev_from_6", "<=", 3.0, 6.0,
              "A 5 s motor block typically peaks ~5-8 s after onset; |latency-6| <= 3 s accepted."),
]


def _load(root: Path):
    import mne

    base = next((root / "mne").rglob("Participant-1"))
    raw = mne.io.read_raw_nirx(base, verbose="error").load_data()
    raw.annotations.set_durations(5)
    raw.annotations.rename({"1.0": "Control", "2.0": "Tapping/Left", "3.0": "Tapping/Right"})
    raw.annotations.delete(np.where(raw.annotations.description == "15.0")[0])
    return raw


def _info_from_mne(raw) -> StreamInfo:
    chans = [ChannelSpec(name=ch["ch_name"], unit="a.u.", kind="fnirs_cw_amplitude", wavelength_nm=float(ch["loc"][9]),
                         source_position_m=tuple(float(v) for v in ch["loc"][3:6]),
                         detector_position_m=tuple(float(v) for v in ch["loc"][6:9])) for ch in raw.info["chs"]]
    return StreamInfo(stream_id="fnirs_motor", modality=Modality.FNIRS, nominal_rate_hz=float(raw.info["sfreq"]),
                      channels=chans, realtime_capable=False,
                      provenance=Provenance(source_kind=SourceKind.REPLAY, provider_id="replay.fnirs",
                                            provider_version="1.0", file_path="mne.datasets.fnirs_motor"),
                      metadata={"measurement": "cw_amplitude"})


def run(root: Path) -> GateResult:
    import mne
    from mne_nirs.experimental_design import make_first_level_design_matrix
    from mne_nirs.io import write_raw_snirf
    from mne_nirs.statistics import run_glm

    raw = _load(root)
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "motor.snirf"
        write_raw_snirf(raw, str(p))
        rec = read_snirf(p)
    orig = {ch["ch_name"]: ch["loc"] for ch in raw.info["chs"]}
    geo_err = max(max(np.max(np.abs(np.subtract(c.source_position_m, orig[c.name][3:6]))),
                      np.max(np.abs(np.subtract(c.detector_position_m, orig[c.name][6:9]))))
                  for c in rec.channels)
    wl_ok = all(abs(c.wavelength_nm - orig[c.name][9]) < 1e-6 for c in rec.channels)

    info = _info_from_mne(raw)
    data = raw.get_data().T
    ours = to_hemoglobin(info, data, ppf=PPF, motion_correction=False, short_channel_regression=False)
    od = mne.preprocessing.nirs.optical_density(raw)
    hb = mne.preprocessing.nirs.beer_lambert_law(od, ppf=PPF)
    fs = float(raw.info["sfreq"])
    corrs = []
    for k, pair in enumerate(ours.pair_names):
        ref = butter_filter(hb.get_data(picks=[f"{pair} hbo"])[0], fs, 0.01, 0.5, order=3)
        corrs.append(float(np.corrcoef(ours.hbo[:, k], ref)[0, 1]))

    full = to_hemoglobin(info, data, ppf=PPF, motion_correction=True, short_channel_regression=True)
    ann = raw.annotations
    tap = [o for o, desc in zip(ann.onset, ann.description) if desc.startswith("Tapping")]
    reg = hrf_design(tap, [5.0] * len(tap), full.hbo.shape[0], fs)
    _, t_ours = glm(full.hbo, reg)

    hb_f = hb.copy().filter(0.01, 0.5, verbose="error")
    hb_f.annotations.rename({"Tapping/Left": "Tapping", "Tapping/Right": "Tapping"})
    dm = make_first_level_design_matrix(hb_f, hrf_model="spm", stim_dur=5.0, drift_model="cosine",
                                        high_pass=0.01)
    res = run_glm(hb_f, dm).to_dataframe()
    res = res[(res.Condition == "Tapping") & (res.Chroma == "hbo")]
    t_ref = {r.ch_name.split(" ")[0]: r.t for r in res.itertuples()}
    paired = [(t_ours[k], t_ref[p]) for k, p in enumerate(full.pair_names) if p in t_ref]
    t_corr = float(np.corrcoef(*zip(*paired))[0, 1]) if len(paired) > 3 else None

    top = np.argsort(t_ours)[-max(3, len(t_ours) // 4):]
    pre, post = int(2 * fs), int(20 * fs)
    blocks = []
    for o in tap:
        i = int(o * fs)
        if i - pre >= 0 and i + post < full.hbo.shape[0]:
            seg = full.hbo[i - pre:i + post, top].mean(axis=1)
            blocks.append(seg - seg[:pre].mean())
    avg = np.mean(blocks, axis=0)
    lat_t = np.arange(-pre, post) / fs
    peak_latency = float(lat_t[pre + int(np.argmax(avg[pre:]))])
    hbr_blocks = []
    for o in tap:
        i = int(o * fs)
        if i - pre >= 0 and i + post < full.hbr.shape[0]:
            seg = full.hbr[i - pre:i + post, top].mean(axis=1)
            hbr_blocks.append(seg - seg[:pre].mean())
    hbr_avg = np.mean(hbr_blocks, axis=0)

    refusals = {}
    for label, mutate in (("missing_wavelength", {"wavelength_nm": None}),
                          ("missing_geometry", {"detector_position_m": None}),
                          ("ppg_kind", {"kind": "ppg"})):
        bad = info.model_copy(deep=True)
        bad.channels[0] = ChannelSpec(**{**bad.channels[0].model_dump(), **mutate})
        try:
            to_hemoglobin(bad, data, ppf=PPF)
            refusals[label] = "NOT REFUSED"
        except FnirsMetadataError as e:
            refusals[label] = f"refused: {e}"
    try:
        to_hemoglobin(info, data, ppf=None)
        refusals["missing_ppf"] = "NOT REFUSED"
    except FnirsMetadataError as e:
        refusals["missing_ppf"] = f"refused: {e}"

    sci = np.array(list(full.sci.values()))
    g = GateResult(
        experiment="FNIRS_MOTOR_MNE",
        dataset={"name": "MNE fnirs_motor (NIRx)", "source": "mne.datasets.fnirs_motor", "mne": mne.__version__,
                 "n_channels": len(raw.ch_names), "sfreq": fs},
        participants={"n": 1, "note": "single participant; validation of processing, not of a population effect"},
        task_and_labels="Finger tapping (left/right, combined) vs control, 5 s blocks.",
        design="No training; fixed pipelines compared with MNE / MNE-NIRS references.",
        metric_definitions={"hbo_corr": "per pair Pearson r between our HbO and MNE beer_lambert_law HbO (same "
                                        "band-pass), minimum over pairs",
                            "glm_t_corr": "Pearson r over channels of tapping HbO t (ours: boxcar*SPM-like HRF + "
                                          "drift; reference: MNE-NIRS run_glm, SPM HRF, cosine drift)",
                            "peak_latency": "block-averaged HbO over the top-25% channels by our t"},
        criteria=CRITERIA,
        results={"snirf_roundtrip": {"geometry_max_abs_error_m": float(geo_err), "wavelengths_preserved": wl_ok},
                 "hbo_corr_vs_mne": {"min": float(min(corrs)), "median": float(np.median(corrs))},
                 "glm": {"t_corr_vs_mne_nirs": t_corr, "n_channels": len(paired),
                         "n_channels_t_gt_3": int(np.sum(t_ours > 3))},
                 "hemodynamics": {"hbo_peak_latency_s": peak_latency, "hbo_peak_uM": float(avg.max() * 1e6),
                                  "hbr_min_uM": float(hbr_avg[pre:].min() * 1e6),
                                  "hbr_anticorrelated": bool(hbr_avg[pre:].min() < 0 < avg.max())},
                 "signal_quality": {"sci_median": float(np.median(sci)),
                                    "fraction_sci_ge_0.8": float(np.mean(sci >= 0.8))},
                 "metadata_refusal": refusals, "processing_log": full.log},
        baseline={"reference": "MNE optical_density + beer_lambert_law; MNE-NIRS run_glm"},
        limitations=["One participant; no short channels, so scalp/systemic physiology is not removed.",
                     "Our pipeline delegates OD and mBLL to MNE, so agreement there tests integration (pairing, "
                     "wavelengths, geometry), not independent physics.",
                     "PPF = 6 is a conventional constant, not measured for this participant."],
    )
    g.decide({"geometry_max_abs_error_m": float(geo_err), "hbo_corr_vs_mne_min": float(min(corrs)),
              "glm_t_corr_vs_mne_nirs": t_corr, "hbo_peak_latency_s_dev_from_6": abs(peak_latency - 6.0)})
    if any(v == "NOT REFUSED" for v in refusals.values()):
        g.verdict = "FAIL"
        g.verdicts["metadata_refusal"] = "FAIL"
    return g
