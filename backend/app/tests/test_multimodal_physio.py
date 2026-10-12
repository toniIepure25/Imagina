import numpy as np
import pytest

from app.multimodal.acquisition import synthetic_signals as ss
from app.multimodal.processing.ecg import analyze_rpeaks, ecg_features
from app.multimodal.processing.eda import calibrate_baseline, eda_features, event_related_scr
from app.multimodal.processing.respiration import detect_cycles, respiration_features, rsa_peak_to_trough
from app.multimodal.schemas import EvidenceClass, Marker


class TestECG:
    @pytest.fixture(scope="class")
    def fixture_180(self):
        return ss.synth_ecg(500, 180, np.random.default_rng(1))

    def test_r_peaks_match_ground_truth(self, fixture_180):
        ecg, truth = fixture_180
        det = analyze_rpeaks(ecg, 500).peaks / 500
        tp = truth.values["r_peak_times_s"]
        tp = tp[(tp > 0.3) & (tp < 179.7)]
        assert len(det) == len(tp)
        assert max(np.min(np.abs(det - t)) for t in tp) < 0.005

    def test_hrv_matches_ground_truth(self, fixture_180):
        ecg, truth = fixture_180
        f = ecg_features(ecg, 500)
        assert f.value("heart_rate") == pytest.approx(truth.values["mean_hr_bpm"], rel=0.005)
        assert f.value("rmssd") == pytest.approx(truth.values["rmssd_ms"], rel=0.03)
        assert f.value("sdnn") == pytest.approx(truth.values["sdnn_ms"], rel=0.03)
        assert f.features["heart_rate"].evidence_class == EvidenceClass.DERIVED_METRIC
        assert f.quality > 0.9

    def test_lf_hf_only_with_adequate_window(self, fixture_180):
        ecg, _ = fixture_180
        short = ecg_features(ecg[: 500 * 60], 500)
        assert short.value("lf_hf_ratio") is None
        assert "120s" in short.features["lf_hf_ratio"].reason
        long = ecg_features(ecg, 500)
        assert long.value("hf_power") > long.value("lf_power")

    def test_ectopic_beats_excluded(self):
        ecg, truth = ss.synth_ecg(500, 120, np.random.default_rng(2), ectopic_indices=(20, 60))
        f = ecg_features(ecg, 500)
        assert f.value("fraction_normal_beats") < 1.0
        assert f.value("rmssd") == pytest.approx(truth.values["rmssd_ms"], rel=0.05)

    def test_noise_gives_low_quality(self):
        f = ecg_features(np.random.default_rng(0).normal(0, 1, 500 * 30), 500)
        assert f.quality < 0.5

    def test_flatline_flagged(self):
        f = ecg_features(np.zeros(500 * 30), 500)
        assert "flatline" in f.flags and f.value("heart_rate") is None


class TestEDA:
    ONSETS = (10.0, 40.0, 70.0, 100.0)
    AMPS = (0.3, 0.1, 0.5, 0.05)

    def _fixture(self, seed=0):
        return ss.synth_eda(32, 120, np.random.default_rng(seed), self.ONSETS, self.AMPS)

    @pytest.mark.parametrize("seed", [0, 1, 2])
    def test_scrs_recovered(self, seed):
        eda, truth = self._fixture(seed)
        _, dec = eda_features(eda, 32)
        for peak_t, amp in zip(truth.values["scr_peak_times_s"], truth.values["scr_amplitudes_us"]):
            match = [s for s in dec.scrs if abs(s.peak_s - peak_t) < 0.5]
            assert match, f"missed SCR at {peak_t}"
            assert match[0].amplitude_us == pytest.approx(amp, rel=0.2)
        spurious = [s for s in dec.scrs
                    if min(abs(s.peak_s - p) for p in truth.values["scr_peak_times_s"]) >= 0.5]
        assert all(s.amplitude_us < 0.02 for s in spurious)

    def test_tonic_traceable(self):
        eda, truth = self._fixture()
        f, dec = eda_features(eda, 32)
        assert dec.tonic[0] == pytest.approx(truth.values["tonic_start_us"], abs=0.1)
        assert f.features["tonic_scl"].method

    def test_contact_artifact_masked(self):
        eda, _ = self._fixture()
        eda = eda.copy()
        eda[32 * 50:32 * 55] = 0.0
        f, dec = eda_features(eda, 32)
        assert "artifact_segments" in f.flags and f.quality < 1.0
        assert not any(50 <= s.onset_s <= 56 for s in dec.scrs)

    def test_event_related_and_baseline(self):
        eda, _ = self._fixture()
        markers = [Marker(label="cue", local_time=t) for t in self.ONSETS] + [Marker(label="null", local_time=25.0)]
        f, dec = eda_features(eda, 32, markers=markers, baseline=calibrate_baseline(eda[: 32 * 9], 32))
        er = event_related_scr(dec, markers, 0.0)
        assert [e["responded"] for e in er] == [True, True, True, True, False]
        assert f.value("event_response_rate") == pytest.approx(0.8)
        assert f.value("tonic_scl_z_vs_baseline") is not None


class TestRespiration:
    def test_rate_and_timing(self):
        resp, truth = ss.synth_respiration(50, 120, np.random.default_rng(0), rate_hz=0.25, ie_ratio=0.7)
        f = respiration_features(resp, 50)
        assert f.value("resp_rate") == pytest.approx(truth.values["rate_bpm"], rel=0.02)
        assert f.value("ti_te_ratio") == pytest.approx(0.7, abs=0.1)
        assert f.value("breath_regularity") > 0.9

    def test_cycle_onsets(self):
        resp, truth = ss.synth_respiration(50, 60, np.random.default_rng(1), rate_hz=0.2)
        c = detect_cycles(resp, 50)
        for o in c.onsets_s:
            assert np.min(np.abs(truth.values["inspiration_onsets_s"] - o)) < 0.4

    def test_too_short_withheld(self):
        resp, _ = ss.synth_respiration(50, 5, np.random.default_rng(1), rate_hz=0.2)
        assert respiration_features(resp, 50).value("resp_rate") is None

    def test_rsa_requires_quality(self):
        rng = np.random.default_rng(3)
        ecg, et = ss.synth_ecg(500, 120, rng, rsa_fraction=0.08, resp_rate_hz=0.25)
        resp, _ = ss.synth_respiration(50, 120, rng, rate_hz=0.25, rate_jitter=0.0)
        c = detect_cycles(resp, 50)
        ok = rsa_peak_to_trough(et.values["r_peak_times_s"], c, 0.95, 0.95)
        assert ok.valid and ok.value > 20
        assert not rsa_peak_to_trough(et.values["r_peak_times_s"], c, 0.3, 0.95).valid
