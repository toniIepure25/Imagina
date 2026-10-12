import numpy as np
import pytest

from app.multimodal.acquisition import fixtures
from app.multimodal.acquisition import synthetic_signals as ss
from app.multimodal.acquisition.synthetic import SyntheticEEG, SyntheticFNIRS
from app.multimodal.evaluation import (
    LeakageError,
    check_group_leakage,
    cross_validate,
    expected_calibration_error,
    hedges_g,
    holm,
)
from app.multimodal.processing import eeg, fmri, meg
from app.multimodal.processing.eeg_decoding import baseline_factories, make_fbcsp_lda, make_tangent_lr
from app.multimodal.processing.fnirs import FnirsMetadataError, glm, hrf_design, to_hemoglobin
from app.multimodal.schemas import ChannelSpec


class TestEEGPreprocessing:
    def _data(self, **kw):
        p = SyntheticEEG(n_channels=8, duration_s=20, seed=2, **kw)
        info = p.connect()
        return p._data, info.channel_names

    def test_notch_removes_line_noise(self):
        x, names = self._data()
        y, log = eeg.preprocess(x, 256, names)
        from scipy.signal import welch
        f, p_raw = welch(x[:, 0], 256, nperseg=512)
        _, p_clean = welch(y[:, 0], 256, nperseg=512)
        i50 = np.argmin(np.abs(f - 50))
        assert p_clean[i50] < 0.05 * p_raw[i50]
        assert log.steps[0] == "reference:average"

    def test_average_reference_zero_mean_across_channels(self):
        x, names = self._data()
        y, _ = eeg.preprocess(x, 256, names, eeg.PreprocessConfig(notch_hz=None, band_hz=None))
        assert np.allclose(y.mean(axis=1), 0)

    def test_blinks_flagged_and_epochs_rejected(self):
        x, names = self._data(blink_times_s=(5.0, 12.0))
        fs = eeg.eeg_features(x, 256, names)
        assert any(f.startswith("Fp1:") and "high_amplitude" in f for f in fs.flags)
        y, _ = eeg.preprocess(x, 256, names)
        times = np.arange(y.shape[0]) / 256
        ep, labels, rejected = eeg.epoch(y, times, [(5.0, "a"), (9.0, "b")], 256, -0.5, 1.0)
        assert rejected == [0] and labels == ["b"] and ep.shape == (1, 8, 384)
        assert fs.value("posterior_rel_alpha") is not None

    def test_posterior_alpha_feature_reflects_signal(self):
        x, names = self._data()
        f = eeg.eeg_features(x, 256, names)
        assert f.value("posterior_rel_alpha") > f.value("rel_alpha") * 0.9
        assert f.features["rel_alpha"].evidence_class.value == "DERIVED_METRIC"

    def test_time_frequency_shape(self):
        x, _ = self._data()
        tfr = eeg.time_frequency(x[:512, :2], 256, np.array([8.0, 10.0, 12.0]))
        assert tfr.shape == (2, 3, 512)
        assert tfr[:, 1].mean() > tfr[:, 0].mean() * 0.5

    def test_ica_reduces_blink(self):
        x, names = self._data(blink_times_s=(4.0, 8.0, 12.0, 16.0))
        clean, meta = eeg.ica_remove_ocular(x, 256, names, seed=0)
        i = int(8.0 * 256)
        assert meta["applied"] and meta["excluded_components"]
        assert np.abs(clean[i, 0]) < np.abs(x[i, 0]) * 0.2
        assert np.corrcoef(clean[:, names.index("O1")], x[:, names.index("O1")])[0, 1] > 0.99


class TestEEGDecoding:
    @pytest.fixture(scope="class")
    def data(self):
        return ss.synth_eeg_epochs(n_subjects=4, n_trials_per_class=25, effect=1.0, seed=1)

    @pytest.fixture(scope="class")
    def null_data(self):
        return ss.synth_eeg_epochs(n_subjects=4, n_trials_per_class=25, effect=0.0, seed=1)

    def test_fbcsp_detects_synthetic_effect_cross_subject(self, data):
        x, y, g = data
        r = cross_validate(lambda: make_fbcsp_lda(128), x, y, g, "loso", ["SYNTHETIC"], "fbcsp", n_permutations=9)
        assert r.mean > 0.8 and r.permutation_p <= 0.1
        assert "not a human neuroscience finding" in r.interpretation_scope

    def test_negative_control_at_chance(self, null_data):
        x, y, g = null_data
        for name in ("fbcsp_lda", "tangent_space_lr"):
            r = cross_validate(baseline_factories(128)[name], x, y, g, "loso", ["SYNTHETIC"], name)
            assert 0.35 < r.mean < 0.65, name

    def test_within_subject_scheme(self, data):
        x, y, g = data
        r = cross_validate(make_tangent_lr, x, y, g, "within_subject", ["SYNTHETIC"], "ts")
        assert r.mean > 0.7 and r.n_groups == 4

    def test_leakage_detection(self, data):
        x, y, g = data
        with pytest.raises(LeakageError):
            check_group_leakage(np.array([0, 1]), np.array([1, 2]))
        xd = np.concatenate([x, x[:5]])
        yd = np.concatenate([y, y[:5]])
        gd = np.concatenate([g, np.full(5, 3)])
        with pytest.raises(LeakageError):
            cross_validate(make_tangent_lr, xd, yd, gd, "loso", ["SYNTHETIC"])

    def test_shallow_net_runs(self, data):
        x, y, g = data
        m = baseline_factories(128)["shallow_net"]()
        m.fit(x[g != 0], y[g != 0])
        proba = m.predict_proba(x[g == 0])
        assert proba.shape == (50, 2) and np.allclose(proba.sum(axis=1), 1)

    def test_stats_helpers(self):
        rng = np.random.default_rng(0)
        assert hedges_g(rng.normal(1, 1, 50), rng.normal(0, 1, 50)) > 0.5
        res = holm({"a": 0.001, "b": 0.04, "c": 0.5})
        assert [r["significant"] for r in res] == [True, False, False]
        p = np.array([[0.9, 0.1], [0.2, 0.8]])
        assert expected_calibration_error(p, np.array([0, 1])) == pytest.approx(0.15)


class TestFNIRS:
    @pytest.fixture(scope="class")
    def stream(self):
        p = SyntheticFNIRS(duration_s=240, seed=0)
        return p, p.connect()

    def test_hemoglobin_recovers_task_response(self, stream):
        p, info = stream
        r = to_hemoglobin(info, p._data, ppf=6.0)
        assert r.short_channel_regressed and "motion:TDDR" in r.log
        ev = p.truth.values["evoked"]
        long_pairs = [k for k, n in enumerate(r.pair_names) if n not in r.short_pairs]
        for k in long_pairs:
            assert np.corrcoef(r.hbo[:, k], ev)[0, 1] > 0.9
            assert np.corrcoef(r.hbr[:, k], ev)[0, 1] < -0.5
        blocks = [b for b in p.blocks if b.label == "imagery"]
        reg = hrf_design([b.start_s for b in blocks], [b.duration_s for b in blocks], len(r.times), 10.0)
        _, t = glm(r.hbo, reg)
        assert all(t[k] > 5 for k in long_pairs)

    def test_without_short_channels_warns(self):
        p = SyntheticFNIRS(duration_s=60, include_short=False)
        r = to_hemoglobin(p.connect(), p._data, ppf=6.0)
        assert not r.short_channel_regressed
        assert any("superficial_physiology_not_removed" in s for s in r.log)

    def test_refuses_without_ppf(self, stream):
        p, info = stream
        with pytest.raises(FnirsMetadataError, match="pathlength"):
            to_hemoglobin(info, p._data, ppf=None)

    @pytest.mark.parametrize("mutation, match", [
        ({"wavelength_nm": None}, "wavelength"),
        ({"detector_position_m": None}, "geometry"),
        ({"detector_position_m": (0.5, 0.05, 0.08)}, "implausible"),
    ])
    def test_refuses_missing_metadata(self, stream, mutation, match):
        p, info = stream
        bad = info.model_copy(deep=True)
        bad.channels[0] = ChannelSpec(**{**bad.channels[0].model_dump(), **mutation})
        with pytest.raises(FnirsMetadataError, match=match):
            to_hemoglobin(bad, p._data, ppf=6.0)

    def test_refuses_single_wavelength(self, stream):
        p, info = stream
        bad = info.model_copy(deep=True)
        bad.channels[1] = ChannelSpec(**{**bad.channels[1].model_dump(), "wavelength_nm": 760.0, "name": "S1_D1 761"})
        with pytest.raises(FnirsMetadataError, match="wavelength"):
            to_hemoglobin(bad, p._data, ppf=6.0)

    def test_refuses_ppg(self, stream):
        p, info = stream
        bad = info.model_copy(deep=True)
        bad.channels[0] = ChannelSpec(**{**bad.channels[0].model_dump(), "kind": "ppg"})
        with pytest.raises(FnirsMetadataError, match="PPG"):
            to_hemoglobin(bad, p._data, ppf=6.0)


class TestMEG:
    def test_epochs_and_time_resolved_decoding(self, tmp_path):
        path, meta = fixtures.write_meg_fif(tmp_path / "s_raw.fif", seed=1, n_trials_per_class=20)
        ep = meg.load_epochs(path, meta["event_id"])
        assert ep.data.shape[0] == 40 and set(ep.labels) == {"perception", "imagery"}
        auc = meg.time_resolved_decoding(ep.data, ep.labels)
        peak_t = ep.times[np.argmax(auc)]
        assert auc.max() > 0.9 and 0.2 < peak_t < 0.45
        assert np.mean(auc[ep.times < 0]) < 0.7
        feats = meg.sensor_features(ep, [(0.25, 0.35)])
        assert feats.shape == (40, len(ep.ch_names))

    def test_bad_channel_detection(self):
        rng = np.random.default_rng(0)
        d = rng.normal(0, 1e-13, (10, 1000))
        d[3] *= 100
        d[7] = 0
        assert meg.detect_bad_channels(d, [f"M{i}" for i in range(10)]) == ["M3", "M7"]

    def test_source_space_explicitly_unavailable(self):
        assert meg.SOURCE_SPACE_AVAILABLE is False and "MRI" in meg.SOURCE_SPACE_REASON


class TestFMRI:
    @pytest.fixture(scope="class")
    def bids(self, tmp_path_factory):
        root = tmp_path_factory.mktemp("bids")
        fixtures.write_bids_fmri(root, seed=0, n_subjects=3)
        return root

    def test_discovery_and_tr(self, bids):
        runs = fmri.discover_bids(bids)
        assert [r.subject for r in runs] == ["sub-01", "sub-02", "sub-03"]
        assert runs[0].tr == 2.0 and runs[0].tr_source == "sidecar"
        assert runs[0].confound_names == fmri.MOTION_COLUMNS

    def test_design_matrix_includes_nuisance(self, bids):
        run = fmri.discover_bids(bids)[0]
        x, names = fmri.design_matrix(run, 120, ["perception", "imagery"])
        assert names[:2] == ["perception", "imagery"] and "trans_x" in names and "intercept" in names
        assert any(n.startswith("drift") for n in names)
        assert np.linalg.matrix_rank(x) == x.shape[1]

    def test_glm_detects_roi_response(self, bids):
        run = fmri.discover_bids(bids)[0]
        y = fmri.roi_timeseries(run)
        x, names = fmri.design_matrix(run, y.shape[0], ["perception", "imagery"])
        _, t = fmri.fit_glm(y, x)
        assert np.median(np.abs(t[names.index("perception")])) > 2

    def test_cross_subject_trialwise_decoding(self, bids):
        from sklearn.linear_model import LogisticRegression
        xs, ys, gs = [], [], []
        for k, run in enumerate(fmri.discover_bids(bids)):
            b, labels = fmri.trial_betas(run, ["perception", "imagery"])
            xs.append((b - b.mean(axis=0)) / (b.std(axis=0) + 1e-9))
            ys += labels
            gs += [k] * len(labels)
        r = cross_validate(lambda: LogisticRegression(max_iter=1000), np.vstack(xs), np.array(ys), np.array(gs),
                           "loso", ["SYNTHETIC"], "fmri_lsa")
        assert r.mean > 0.7 and r.n_groups == 3

    def test_not_realtime(self):
        assert fmri.REALTIME_NEUROFEEDBACK_SUPPORTED is False
