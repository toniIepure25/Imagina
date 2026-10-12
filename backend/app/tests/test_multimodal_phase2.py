import numpy as np
import pytest

from app.multimodal.acquisition import synthetic_signals as ss
from app.multimodal.acquisition.devices import BrainFlowProvider, LSLInletProvider
from app.multimodal.persistence import MultimodalSessionRepository, recover_session
from app.multimodal.processing.eda import decompose, detect_scrs
from app.multimodal.processing.meg import detect_bad_channels
from app.multimodal.runtime import ClosedLoopSession, SessionConfig, session_digest
from app.multimodal.schemas import ChannelSpec, Modality, Provenance, SourceKind, StreamInfo
from app.multimodal.validation.gates import Criterion, GateResult, blocked


class TestGates:
    def test_criterion_bands(self):
        c = Criterion("x", ">=", 0.9, 0.8, "r")
        assert [c.judge(v) for v in (0.95, 0.85, 0.5, None)] == ["PASS", "INCONCLUSIVE", "FAIL", "INCONCLUSIVE"]
        d = Criterion("e", "<=", 0.1, 0.3, "r")
        assert [d.judge(v) for v in (0.05, 0.2, 0.4)] == ["PASS", "INCONCLUSIVE", "FAIL"]

    def test_overall_verdict_and_blocked(self, tmp_path):
        g = GateResult("exp", {}, {}, "", "", {}, [Criterion("a", ">=", 1, 0, ""), Criterion("b", ">=", 1, 0, "")])
        assert g.decide({"a": 2, "b": -1}) == "FAIL"
        assert g.decide({"a": 2, "b": 0.5}) == "INCONCLUSIVE"
        assert g.decide({"a": 2, "b": 2}) == "PASS"
        assert blocked("x", "no data").verdict == "BLOCKED"
        assert (g.write(tmp_path / "g.json")).exists()


class TestEDAFix:
    def test_tangent_method_reduces_bias_and_handles_drift(self):
        onsets, amps = (10.0, 40.0, 70.0, 100.0), (0.3, 0.1, 0.5, 0.05)
        res = {}
        for method in ("threshold", "tangent"):
            bias, missed, spurious = [], 0, 0
            for seed in range(4):
                x, truth = ss.synth_eda(32, 120, np.random.default_rng(seed), onsets, amps, drift_us_per_min=1.2)
                dec = decompose(x, 32)
                scrs = detect_scrs(dec.cleaned, 32, dec.artifact_mask, method=method)
                used = set()
                for t_on, t_pk in zip(truth.values["scr_response_onsets_s"], truth.values["scr_peak_times_s"]):
                    c = [i for i, s in enumerate(scrs) if abs(s.peak_s - t_pk) < 0.75 and i not in used]
                    if not c:
                        missed += 1
                        continue
                    used.add(c[0])
                    bias.append(scrs[c[0]].onset_s - t_on)
                spurious += len(scrs) - len(used)
            res[method] = (float(np.median(bias)) if bias else None, missed, spurious)
        assert res["tangent"][1] == 0 and res["threshold"][1] > 0
        assert abs(res["tangent"][0]) < 0.2


class TestMEGBadChannels:
    def test_per_type_scoring_does_not_flag_scale_difference(self):
        rng = np.random.default_rng(0)
        mags = rng.normal(0, 1e-13, (10, 2000))
        grads = rng.normal(0, 1e-11, (20, 2000))
        grads[4] *= 50
        names = [f"M{i}" for i in range(10)] + [f"G{i}" for i in range(20)]
        types = ["mag"] * 10 + ["grad"] * 20
        assert detect_bad_channels(np.vstack([mags, grads]), names, ch_types=types) == ["G4"]


class _FakeInlet:
    def __init__(self, batches):
        self.batches = list(batches)

    def pull_chunk(self, timeout=0.0):
        return self.batches.pop(0) if self.batches else ([], [])

    def time_correction(self):
        return 0.001


class TestDeviceGapInference:
    def test_lsl_gap_from_timestamps(self):
        p = LSLInletProvider(Modality.ECG, "ECG", "mV")
        p._info = StreamInfo(stream_id="lsl:x", modality=Modality.ECG, nominal_rate_hz=100.0,
                             channels=[ChannelSpec(name="c", unit="mV")],
                             provenance=Provenance(source_kind=SourceKind.REAL_SENSOR, provider_id="lsl.ecg",
                                                   provider_version="t"))
        t = np.arange(0, 1.0, 0.01)
        t2 = np.arange(1.5, 2.0, 0.01)
        p._inlet = _FakeInlet([([[0.0]] * len(t), t.tolist()), ([[0.0]] * len(t2), t2.tolist())])
        a, b = p.read(0), p.read(0)
        assert a.sample_indices[0] == 0 and a.sample_indices[-1] == 99
        assert b.sample_indices[0] == 150 and b.dropped_before == 50 and p.stats.samples_dropped == 50

    def test_brainflow_counter_wraparound_and_gap(self):
        bf = BrainFlowProvider(-1, clock=lambda: 100.0)
        bf._info = StreamInfo(stream_id="bf", modality=Modality.EEG, nominal_rate_hz=250.0,
                              channels=[ChannelSpec(name="c1", unit="uV")],
                              provenance=Provenance(source_kind=SourceKind.REAL_SENSOR, provider_id="bf",
                                                    provider_version="t"))
        bf._rows, bf._ts_row, bf._pkg_row = [1], 2, 0
        pkg = np.array([253, 254, 255, 0, 1, 3, 4])
        buf = np.vstack([pkg, np.zeros(7), 1.7e9 + np.arange(7) / 250])

        class B:
            def get_board_data(self):
                return buf

        bf._board = B()
        c = bf.read(0)
        assert np.diff(c.sample_indices).tolist() == [1, 1, 1, 1, 2, 1]
        assert bf.stats.samples_dropped == 1
        assert c.local_timestamps[-1] == pytest.approx(100.0)


class TestPersistence:
    def test_record_interrupt_recover_paused(self, tmp_path):
        repo = MultimodalSessionRepository(tmp_path / "mm.db")
        cfg = SessionConfig(session_id="p1", duration_s=120, mode="feedback_research", seed=4)
        s = ClosedLoopSession(cfg, repo=repo)
        s.start()
        for _ in range(35):
            s.step()
        row = repo.session("p1")
        assert row["status"] == "RUNNING" and row["last_tick"] == 35 and row["calibration_version"] == 1
        assert len(repo.decisions("p1")) == 35 and repo.safety_events("p1")
        assert repo.mark_interrupted() == ["p1"]
        rec, report = recover_session(repo, "p1")
        assert report["hash_chain_verified"] and report["controller_state"] == "PAUSED"
        assert rec.cfg.mode == "shadow" and repo.session("p1")["status"] == "RECOVERED_PAUSED"
        e = rec.step()
        assert e["decision"]["controller_state"] == "PAUSED" and not e["decision"]["delivered"]

    def test_stage_timing_does_not_change_decisions(self):
        a = ClosedLoopSession(SessionConfig(duration_s=70, seed=2))
        a.run()
        b = ClosedLoopSession(SessionConfig(duration_s=70, seed=2))
        b.run()
        assert session_digest(a.log) == session_digest(b.log)
        assert {"safety_ms", "estimation_ms", "tick_total_ms"} <= set(a.stage_ms[-1])
