"""Imagery State Estimator (multimodal, individually calibrated).

Each output dimension states where it comes from:
- SUBJECTIVE_REPORT: the participant's own rating (vividness, immersion, control, reality orientation).
- DERIVED_METRIC: direct physiological summaries relative to the participant's baseline (arousal/regulation).
- EXPERIMENTAL_PROXY: unvalidated composites (attention, effort, fatigue, stability).
- VALIDATED_ESTIMATE: only produced by a registered predictor whose card says it passed validation.

No physiological signal is turned into a vividness number unless such a validated predictor exists.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np
from pydantic import BaseModel, Field

from app.multimodal.processing.common import FeatureSet
from app.multimodal.schemas import EvidenceClass, Modality

IQI_WEIGHTS = {"attention": 0.35, "engagement": 0.30, "behavioral": 0.20, "relaxation": 0.15}

DIMENSIONS = ["vividness", "spatial_detail", "representational_stability", "sustained_attention",
              "voluntary_control", "subjective_immersion", "mental_effort", "fatigue", "physiological_arousal",
              "reality_orientation"]

BASELINE_FEATURES = {
    Modality.EEG: ["theta_beta_ratio", "posterior_rel_alpha", "rel_theta"],
    Modality.ECG: ["heart_rate", "rmssd"],
    Modality.EDA: ["tonic_scl", "scr_rate"],
    Modality.RESPIRATION: ["resp_rate", "breath_regularity"],
}


class SelfReport(BaseModel):
    time: float
    vividness: float | None = Field(default=None, ge=0, le=1)
    spatial_detail: float | None = Field(default=None, ge=0, le=1)
    voluntary_control: float | None = Field(default=None, ge=0, le=1)
    immersion: float | None = Field(default=None, ge=0, le=1)
    effort: float | None = Field(default=None, ge=0, le=1)
    fatigue: float | None = Field(default=None, ge=0, le=1)
    discomfort: float | None = Field(default=None, ge=0, le=1)
    reality_orientation: float | None = Field(default=None, ge=0, le=1)
    free_text: str = ""


class DimensionEstimate(BaseModel):
    name: str
    value: float | None = Field(default=None, ge=0, le=1)
    uncertainty: float | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)
    evidence_class: EvidenceClass
    inputs: list[str] = Field(default_factory=list)
    calibrated: bool = False
    reason: str = ""


class ImageryState(BaseModel):
    t: float
    dimensions: dict[str, DimensionEstimate]
    iqi: float | None = None
    iqi_confidence: float = 0.0
    overall_confidence: float = 0.0
    modalities_used: list[str] = Field(default_factory=list)
    source_kinds: list[str] = Field(default_factory=list)
    estimator_version: str = "mm-estimator-1.0"

    def value(self, name: str) -> float | None:
        return self.dimensions[name].value


@dataclass
class CalibrationProfile:
    participant_pseudo_id: str
    stats: dict[str, tuple[float, float]] = field(default_factory=dict)
    perception_centroid: dict[str, float] = field(default_factory=dict)
    n_windows: int = 0

    def z(self, key: str, value: float | None) -> float | None:
        if value is None or key not in self.stats:
            return None
        mu, sd = self.stats[key]
        return (value - mu) / sd if sd > 1e-9 else 0.0

    def to_dict(self) -> dict:
        return {"participant_pseudo_id": self.participant_pseudo_id, "n_windows": self.n_windows,
                "stats": {k: list(v) for k, v in self.stats.items()},
                "perception_centroid": self.perception_centroid}


def calibrate(participant_pseudo_id: str, baseline_windows: list[dict[Modality, FeatureSet]],
              perception_windows: list[dict[Modality, FeatureSet]] | None = None, min_windows: int = 3,
              ) -> CalibrationProfile:
    prof = CalibrationProfile(participant_pseudo_id, n_windows=len(baseline_windows))
    for m, names in BASELINE_FEATURES.items():
        for n in names:
            vals = [w[m].value(n) for w in baseline_windows if m in w and w[m].quality >= 0.5]
            vals = [v for v in vals if v is not None]
            if len(vals) >= min_windows:
                prof.stats[f"{m.value}.{n}"] = (float(np.mean(vals)), float(np.std(vals, ddof=1)) + 1e-6)
    if perception_windows:
        for key in prof.stats:
            m, n = key.split(".", 1)
            vals = [w[Modality(m)].value(n) for w in perception_windows if Modality(m) in w]
            vals = [v for v in vals if v is not None]
            if vals:
                prof.perception_centroid[key] = float(np.mean(vals))
    return prof


def _sig(z: float) -> float:
    return float(1.0 / (1.0 + np.exp(-z)))


@dataclass
class PIDConfig:
    features: list[str] = field(default_factory=lambda: ["eeg.posterior_rel_alpha", "eeg.theta_beta_ratio"])
    metric: str = "euclidean"
    objective_allowed: bool = False


def perception_imagination_distance(fs: dict[Modality, FeatureSet], prof: CalibrationProfile,
                                    cfg: PIDConfig | None = None) -> dict:
    """Research metric only: standardized distance of the current window from the participant's perception
    centroid. ``objective_allowed`` stays False until validated and safety-reviewed; controllers must not
    minimize it."""
    cfg = cfg or PIDConfig()
    cur, ref = [], []
    for key in cfg.features:
        m, n = key.split(".", 1)
        v = fs[Modality(m)].value(n) if Modality(m) in fs else None
        if v is None or key not in prof.perception_centroid or key not in prof.stats:
            continue
        sd = prof.stats[key][1]
        cur.append(v / sd)
        ref.append(prof.perception_centroid[key] / sd)
    if not cur:
        return {"value": None, "reason": "no calibrated features available", "objective_allowed": False}
    a, b = np.array(cur), np.array(ref)
    if cfg.metric == "cosine":
        d = 1 - float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))
    else:
        d = float(np.linalg.norm(a - b) / np.sqrt(len(a)))
    return {"value": d, "n_features": len(cur), "metric": cfg.metric, "evidence_class": "EXPERIMENTAL_PROXY",
            "objective_allowed": False, "note": "Not validated; not a neurofeedback target."}


class ImageryStateEstimator:
    def __init__(self, profile: CalibrationProfile | None = None, validated_predictors: dict | None = None,
                 stale_report_s: float = 120.0, history: int = 6) -> None:
        self.profile = profile
        self.validated = {k: v for k, v in (validated_predictors or {}).items()
                          if getattr(v, "card", {}).get("validation_status") == "VALIDATED"}
        self.stale_report_s = stale_report_s
        self._eeg_hist: deque[float] = deque(maxlen=history)
        self._tbr_hist: deque[float] = deque(maxlen=60)

    def _zf(self, fs: dict[Modality, FeatureSet], m: Modality, name: str) -> tuple[float | None, float]:
        if m not in fs or fs[m].quality < 0.3:
            return None, 0.0
        v = fs[m].value(name)
        if v is None:
            return None, 0.0
        if self.profile is not None:
            z = self.profile.z(f"{m.value}.{name}", v)
            if z is not None:
                return z, fs[m].quality
        return None, 0.0

    def estimate(self, t: float, fs: dict[Modality, FeatureSet], report: SelfReport | None = None,
                 behavioral_consistency: float | None = None) -> ImageryState:
        dims: dict[str, DimensionEstimate] = {}
        fresh = report if report is not None and t - report.time <= self.stale_report_s else None
        calibrated = self.profile is not None and bool(self.profile.stats)

        def subjective(name, attr):
            v = getattr(fresh, attr) if fresh else None
            dims[name] = DimensionEstimate(
                name=name, value=v, evidence_class=EvidenceClass.SUBJECTIVE_REPORT,
                confidence=0.9 if v is not None else 0.0, uncertainty=0.1 if v is not None else None,
                inputs=["self_report"] if v is not None else [],
                reason="" if v is not None else "no fresh self-report")

        for name in ("vividness", "spatial_detail"):
            if name in self.validated:
                dims[name] = self.validated[name].estimate(fs)
            else:
                subjective(name, name)
                dims[name].reason = (dims[name].reason + "; " if dims[name].reason else "") + \
                    "no validated physiological predictor registered"
        subjective("voluntary_control", "voluntary_control")
        subjective("subjective_immersion", "immersion")
        subjective("reality_orientation", "reality_orientation")

        tbr, q_eeg = self._zf(fs, Modality.EEG, "theta_beta_ratio")
        if tbr is not None:
            dims["sustained_attention"] = DimensionEstimate(
                name="sustained_attention", value=_sig(-tbr), uncertainty=0.25, confidence=0.5 * q_eeg,
                evidence_class=EvidenceClass.EXPERIMENTAL_PROXY, inputs=["eeg.theta_beta_ratio(z)"], calibrated=True)
        else:
            dims["sustained_attention"] = DimensionEstimate(
                name="sustained_attention", evidence_class=EvidenceClass.EXPERIMENTAL_PROXY,
                reason="EEG unavailable, low quality, or uncalibrated")

        alpha = fs[Modality.EEG].value("posterior_rel_alpha") if Modality.EEG in fs else None
        if alpha is not None and fs[Modality.EEG].quality >= 0.3:
            self._eeg_hist.append(alpha)
        if len(self._eeg_hist) >= 3:
            arr = np.array(self._eeg_hist)
            cv = float(np.std(arr) / (np.mean(arr) + 1e-9))
            dims["representational_stability"] = DimensionEstimate(
                name="representational_stability", value=float(np.clip(1 - 3 * cv, 0, 1)), uncertainty=0.3,
                confidence=0.3, evidence_class=EvidenceClass.EXPERIMENTAL_PROXY,
                inputs=[f"eeg.posterior_rel_alpha window-to-window CV (n={len(arr)})"],
                reason="Feature stability is not shown to track imagery stability.")
        else:
            dims["representational_stability"] = DimensionEstimate(
                name="representational_stability", evidence_class=EvidenceClass.EXPERIMENTAL_PROXY,
                reason="fewer than 3 usable EEG windows")

        ar_parts, ar_inputs, ar_q = [], [], []
        for m, n, sign in [(Modality.ECG, "heart_rate", 1), (Modality.ECG, "rmssd", -1),
                           (Modality.EDA, "tonic_scl", 1), (Modality.EDA, "scr_rate", 1),
                           (Modality.RESPIRATION, "resp_rate", 1)]:
            z, q = self._zf(fs, m, n)
            if z is not None:
                ar_parts.append(sign * z)
                ar_inputs.append(f"{m.value}.{n}(z)")
                ar_q.append(q)
        if ar_parts:
            dims["physiological_arousal"] = DimensionEstimate(
                name="physiological_arousal", value=_sig(float(np.mean(ar_parts))),
                uncertainty=float(0.4 / np.sqrt(len(ar_parts))), confidence=float(np.mean(ar_q)),
                evidence_class=EvidenceClass.DERIVED_METRIC, inputs=ar_inputs, calibrated=True)
        else:
            dims["physiological_arousal"] = DimensionEstimate(
                name="physiological_arousal", evidence_class=EvidenceClass.DERIVED_METRIC,
                reason="no calibrated cardiac/EDA/respiration features")

        eff_parts, eff_inputs = [], []
        for m, n in [(Modality.ECG, "heart_rate"), (Modality.EDA, "scr_rate")]:
            z, _ = self._zf(fs, m, n)
            if z is not None:
                eff_parts.append(_sig(z))
                eff_inputs.append(f"{m.value}.{n}(z)")
        if fresh and fresh.effort is not None:
            eff_parts.append(fresh.effort)
            eff_inputs.append("self_report.effort")
        dims["mental_effort"] = DimensionEstimate(
            name="mental_effort", value=float(np.mean(eff_parts)) if eff_parts else None,
            uncertainty=0.3 if eff_parts else None, confidence=0.4 if eff_parts else 0.0,
            evidence_class=EvidenceClass.EXPERIMENTAL_PROXY, inputs=eff_inputs,
            reason="" if eff_parts else "no effort inputs")

        fat_parts, fat_inputs = [], []
        raw_tbr = fs[Modality.EEG].value("theta_beta_ratio") if Modality.EEG in fs else None
        if raw_tbr is not None:
            self._tbr_hist.append(raw_tbr)
        if len(self._tbr_hist) >= 10:
            h = np.array(self._tbr_hist)
            slope = float(np.polyfit(np.arange(len(h)), h, 1)[0] / (np.mean(h) + 1e-9))
            fat_parts.append(_sig(slope * 50))
            fat_inputs.append("eeg.theta_beta_ratio trend")
        if fresh and fresh.fatigue is not None:
            fat_parts.append(fresh.fatigue)
            fat_inputs.append("self_report.fatigue")
        dims["fatigue"] = DimensionEstimate(
            name="fatigue", value=float(max(fat_parts)) if fat_parts else None,
            uncertainty=0.3 if fat_parts else None, confidence=0.5 if fat_parts else 0.0,
            evidence_class=EvidenceClass.EXPERIMENTAL_PROXY, inputs=fat_inputs,
            reason="" if fat_parts else "no fatigue inputs")

        att = dims["sustained_attention"].value
        eng = dims["vividness"].value
        relax = 1 - dims["physiological_arousal"].value if dims["physiological_arousal"].value is not None else None
        comps = {"attention": att, "engagement": eng, "behavioral": behavioral_consistency, "relaxation": relax}
        present = {k: v for k, v in comps.items() if v is not None}
        iqi, iqi_conf = None, 0.0
        if len(present) >= 2:
            wsum = sum(IQI_WEIGHTS[k] for k in present)
            iqi = float(sum(IQI_WEIGHTS[k] * v for k, v in present.items()) / wsum)
            iqi_conf = float(wsum * np.mean([d.confidence for d in dims.values() if d.value is not None]))
        confs = [d.confidence for d in dims.values() if d.value is not None]
        return ImageryState(
            t=t, dimensions=dims, iqi=iqi, iqi_confidence=min(iqi_conf, 1.0),
            overall_confidence=float(np.mean(confs)) * (1.0 if calibrated else 0.5) if confs else 0.0,
            modalities_used=sorted(m.value for m in fs), source_kinds=sorted({f.source_kind.value for f in fs.values()}),
        )
