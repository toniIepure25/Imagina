from __future__ import annotations

import numpy as np

from app.multimodal.acquisition import synthetic_signals as ss
from app.multimodal.acquisition.base import ArrayStreamProvider, FaultPlan
from app.multimodal.schemas import Capabilities, ChannelSpec, Modality, Provenance, SourceKind, StreamInfo

SYNTHETIC_NOTE = "SYNTHETIC engineering signal; not a measurement of any person."


class SyntheticProvider(ArrayStreamProvider):
    source_kind = SourceKind.SYNTHETIC
    default_rate_hz: float
    unit: str

    def __init__(
        self, rate_hz: float | None = None, duration_s: float = 300.0, seed: int = 0,
        faults: FaultPlan | None = None, blocks: list[ss.ConditionBlock] | None = None,
    ) -> None:
        super().__init__(faults=faults, seed=seed)
        self.rate_hz = rate_hz or self.default_rate_hz
        self.duration_s = duration_s
        self.blocks = blocks if blocks is not None else ss.default_blocks(duration_s)
        self.truth = ss.SyntheticTruth()
        self.provider_id = f"synthetic.{self.modality.value}"

    def capabilities(self) -> Capabilities:
        return Capabilities(
            provider_id=self.provider_id, modality=self.modality, source_kind=self.source_kind,
            available=True, realtime=True, supported_rates_hz=[self.rate_hz], support_level="IMPLEMENTED",
            reason=SYNTHETIC_NOTE,
        )

    def _rng(self) -> np.random.Generator:
        return np.random.default_rng(self.seed)

    def _time(self) -> np.ndarray:
        return np.arange(int(round(self.rate_hz * self.duration_s))) / self.rate_hz

    def _info_for(self, channels: list[ChannelSpec], **metadata) -> StreamInfo:
        return StreamInfo(
            stream_id=f"{self.provider_id}#{self.seed}",
            modality=self.modality,
            nominal_rate_hz=self.rate_hz,
            channels=channels,
            provenance=Provenance(
                source_kind=self.source_kind, provider_id=self.provider_id, provider_version=self.provider_version,
                generator_seed=self.seed, notes=SYNTHETIC_NOTE,
            ),
            metadata={"blocks": [b.__dict__ for b in self.blocks], "sync_method": "shared_clock_synthetic",
                      **metadata},
        )


class SyntheticEEG(SyntheticProvider):
    modality = Modality.EEG
    default_rate_hz = 256.0
    unit = "uV"

    def __init__(self, n_channels: int = 8, blink_times_s: tuple[float, ...] = (), **kw) -> None:
        super().__init__(**kw)
        self.n_channels = n_channels
        self.blink_times_s = blink_times_s

    def _materialize(self):
        engagement = ss.latent_timeline(self._time(), self.blocks, "engagement")
        data, names, self.truth = ss.synth_eeg(
            self.rate_hz, self.duration_s, self._rng(), self.n_channels, engagement, self.blink_times_s)
        chans = [ChannelSpec(name=n, unit="uV", kind="eeg") for n in names]
        return self._info_for(chans, reference="synthetic_common", line_freq_hz=50.0), data


class SyntheticECG(SyntheticProvider):
    modality = Modality.ECG
    default_rate_hz = 500.0
    unit = "mV"

    def __init__(self, mean_hr_bpm: float = 65.0, ectopic_indices: tuple[int, ...] = (), **kw) -> None:
        super().__init__(**kw)
        self.mean_hr_bpm = mean_hr_bpm
        self.ectopic_indices = ectopic_indices

    def _materialize(self):
        arousal = ss.latent_timeline(self._time(), self.blocks, "arousal")
        data, self.truth = ss.synth_ecg(
            self.rate_hz, self.duration_s, self._rng(), self.mean_hr_bpm,
            ectopic_indices=self.ectopic_indices, arousal=arousal)
        return self._info_for([ChannelSpec(name="ECG_II", unit="mV", kind="ecg")]), data[:, None]


class SyntheticEDA(SyntheticProvider):
    modality = Modality.EDA
    default_rate_hz = 32.0
    unit = "uS"

    def _materialize(self):
        rng = self._rng()
        onsets, amps = [], []
        for b in self.blocks:
            if b.label != "rest":
                k = 1 + int(round(2 * b.arousal))
                for j in range(k):
                    onsets.append(b.start_s + 2.0 + j * (b.duration_s - 6.0) / max(k, 1))
                    amps.append(float(0.1 + 0.3 * b.arousal * rng.uniform(0.7, 1.3)))
        data, self.truth = ss.synth_eda(self.rate_hz, self.duration_s, rng, tuple(onsets), tuple(amps))
        return self._info_for([ChannelSpec(name="EDA", unit="uS", kind="eda")]), data[:, None]


class SyntheticRespiration(SyntheticProvider):
    modality = Modality.RESPIRATION
    default_rate_hz = 50.0
    unit = "a.u."

    def __init__(self, rate_hz_breath: float = 0.25, **kw) -> None:
        super().__init__(**kw)
        self.breath_rate_hz = rate_hz_breath

    def _materialize(self):
        data, self.truth = ss.synth_respiration(self.rate_hz, self.duration_s, self._rng(), self.breath_rate_hz)
        return self._info_for([ChannelSpec(name="RESP_BELT", unit="a.u.", kind="respiration")]), data[:, None]


class SyntheticFNIRS(SyntheticProvider):
    """Raw continuous-wave intensities with explicit wavelength and optode geometry."""

    modality = Modality.FNIRS
    default_rate_hz = 10.0
    unit = "a.u."

    def __init__(self, include_short: bool = True, motion_times_s: tuple[float, ...] = (), ppf: float = 6.0,
                 **kw) -> None:
        super().__init__(**kw)
        self.include_short = include_short
        self.motion_times_s = motion_times_s
        self.ppf = ppf

    def _materialize(self):
        data, layout, self.truth = ss.synth_fnirs_raw(
            self.rate_hz, self.duration_s, self._rng(), self.blocks, include_short=self.include_short,
            ppf=self.ppf, motion_times_s=self.motion_times_s)
        chans = [
            ChannelSpec(name=c["name"], unit="a.u.", kind="fnirs_cw_amplitude", wavelength_nm=c["wavelength_nm"],
                        source_position_m=c["source_position_m"], detector_position_m=c["detector_position_m"])
            for c in layout
        ]
        return self._info_for(chans, measurement="cw_amplitude", short_channels=[
            c["name"] for c in layout if c["short_channel"]]), data


SYNTHETIC_REALTIME = {
    Modality.EEG: SyntheticEEG,
    Modality.ECG: SyntheticECG,
    Modality.EDA: SyntheticEDA,
    Modality.RESPIRATION: SyntheticRespiration,
    Modality.FNIRS: SyntheticFNIRS,
}
