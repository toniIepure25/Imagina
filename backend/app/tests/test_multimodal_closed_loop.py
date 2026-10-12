import asyncio
import json

import numpy as np
import pytest

from app.multimodal.controller import (
    AuthorizationError,
    BoundedRulePolicy,
    ControllerConfig,
    ControllerState,
    FeedbackAuthorization,
    FeedbackController,
    GateInputs,
    PIDControllerPolicy,
    TransitionError,
    register_policy,
    verify_trace,
)
from app.multimodal.corridor import MAX_WALL_DISTORTION, VariationCache, corridor_action, validate_variation
from app.multimodal.estimator import (
    CalibrationProfile,
    DimensionEstimate,
    ImageryState,
    ImageryStateEstimator,
    SelfReport,
    perception_imagination_distance,
)
from app.multimodal.fusion import (
    FUSION_MODELS,
    IntermediateFusion,
    LateFusion,
    ModelRegistry,
    ablation,
    evaluate_fusion,
    measure_latency,
    synthetic_fusion_dataset,
)
from app.multimodal.processing.common import Feature, FeatureSet
from app.multimodal.runtime import ScriptedEvent, SessionConfig, replay_controller, run_session, session_digest
from app.multimodal.schemas import EvidenceClass, Modality, SourceKind
from app.multimodal.training import Curriculum, TrialOutcome, assign_arm, cue_cap_for_level

GOOD_GATES = GateInputs(usable_streams=3, mean_quality=0.9, max_alignment_uncertainty_s=0.001,
                        source_kinds=["SYNTHETIC"])


def _state(att=0.5, conf=0.8, fatigue=0.2, ro=0.95, iqi=0.5):
    dims = {
        "sustained_attention": DimensionEstimate(name="sustained_attention", value=att, confidence=conf,
                                                 evidence_class=EvidenceClass.EXPERIMENTAL_PROXY),
        "fatigue": DimensionEstimate(name="fatigue", value=fatigue, confidence=conf,
                                     evidence_class=EvidenceClass.EXPERIMENTAL_PROXY),
        "reality_orientation": DimensionEstimate(name="reality_orientation", value=ro, confidence=0.9,
                                                 evidence_class=EvidenceClass.SUBJECTIVE_REPORT),
        "mental_effort": DimensionEstimate(name="mental_effort", value=0.3, confidence=conf,
                                           evidence_class=EvidenceClass.EXPERIMENTAL_PROXY),
    }
    return ImageryState(t=0, dimensions=dims, iqi=iqi, overall_confidence=conf)


def _active(ctrl, state=ControllerState.ACTIVE_SHADOW, kinds=("SYNTHETIC",)):
    ctrl.transition(ControllerState.CALIBRATION, 0, "t", set(kinds))
    ctrl.transition(ControllerState.BASELINE, 1, "t", set(kinds))
    ctrl.transition(state, 2, "t", set(kinds))
    return ctrl


class TestFusion:
    @pytest.fixture(scope="class")
    def ds(self):
        return synthetic_fusion_dataset(n_subjects=6, n_trials=50, seed=0)

    def test_missing_modalities_handled(self, ds):
        m = LateFusion().fit(ds)
        sub = ds.subset(np.arange(20))
        for mod in sub.modalities[1:]:
            sub.features[mod][:] = np.nan
            sub.quality[mod][:] = 0
        p = m.predict_proba(sub)
        assert np.all(np.isfinite(p)) and np.allclose(p.sum(axis=1), 1)
        im = IntermediateFusion(epochs=10).fit(ds)
        assert np.all(np.isfinite(im.predict_proba(sub)))

    def test_all_fusion_baselines_above_chance_and_null_at_chance(self, ds):
        null = synthetic_fusion_dataset(n_subjects=6, n_trials=50, seed=0, effect=0.0)
        for name, cls in FUSION_MODELS.items():
            make = (lambda: IntermediateFusion(epochs=20)) if name == "intermediate" else cls
            assert evaluate_fusion(make, ds)["accuracy"] > 0.7, name
            assert 0.38 < evaluate_fusion(make, null)["accuracy"] < 0.62, name

    def test_ablation_reports_unimodal_and_leave_one_out(self, ds):
        res = ablation(ds, "late")
        assert "only_eeg" in res and "without_eeg" in res and "note" in res["_summary"]

    def test_uncertainty_and_latency(self, ds):
        im = IntermediateFusion(epochs=10).fit(ds)
        sd = im.mc_dropout_std(ds.subset(np.arange(10)))
        assert sd.shape == (10,) and np.all(sd >= 0)
        assert LateFusion().fit(ds).disagreement(ds.subset(np.arange(5))).shape == (5,)
        assert measure_latency(im, ds, 5)["p95_ms"] > 0

    def test_registry_provenance_and_tamper_detection(self, ds, tmp_path):
        reg = ModelRegistry(tmp_path)
        card = reg.save(LateFusion().fit(ds), "late", ds, {"accuracy": 0.8})
        assert card["validation_status"] == "UNVALIDATED" and card["source_kinds"] == ["SYNTHETIC"]
        assert len(card["training_data_sha256"]) == 64
        card_file = f"late-{card['checkpoint_sha256'][:12]}.json"
        model, _ = reg.load(card_file)
        assert hasattr(model, "models_")
        (tmp_path / card["checkpoint"]).write_bytes(b"tampered")
        with pytest.raises(ValueError):
            reg.load(card_file)


class TestEstimator:
    def _fs(self, m, **vals):
        f = FeatureSet(modality=m, stream_id=m.value, source_kind=SourceKind.SYNTHETIC, t_start=0, t_end=1,
                       quality=0.9)
        for k, v in vals.items():
            f.add(Feature(name=k, value=v, unit="x"))
        return f

    def test_vividness_never_inferred_without_validated_predictor(self):
        prof = CalibrationProfile("P", {"eeg.theta_beta_ratio": (2.0, 0.5), "ecg.heart_rate": (65, 5)})
        est = ImageryStateEstimator(prof)
        s = est.estimate(10, {Modality.EEG: self._fs(Modality.EEG, theta_beta_ratio=1.5),
                              Modality.ECG: self._fs(Modality.ECG, heart_rate=75)})
        assert s.value("vividness") is None
        assert "no validated physiological predictor" in s.dimensions["vividness"].reason
        assert s.dimensions["sustained_attention"].evidence_class == EvidenceClass.EXPERIMENTAL_PROXY
        assert s.dimensions["physiological_arousal"].evidence_class == EvidenceClass.DERIVED_METRIC
        assert s.value("sustained_attention") > 0.5 and s.value("physiological_arousal") > 0.5

    def test_self_report_is_subjective_and_expires(self):
        est = ImageryStateEstimator(stale_report_s=30)
        r = SelfReport(time=0, vividness=0.8, immersion=0.7)
        assert est.estimate(10, {}, r).dimensions["vividness"].evidence_class == EvidenceClass.SUBJECTIVE_REPORT
        assert est.estimate(10, {}, r).value("vividness") == 0.8
        assert est.estimate(100, {}, r).value("vividness") is None

    def test_uncalibrated_lowers_confidence(self):
        r = SelfReport(time=0, vividness=0.8, immersion=0.7)
        assert ImageryStateEstimator().estimate(1, {}, r).overall_confidence < 0.5

    def test_pid_metric_is_research_only(self):
        prof = CalibrationProfile("P", {"eeg.posterior_rel_alpha": (0.3, 0.05)},
                                  perception_centroid={"eeg.posterior_rel_alpha": 0.3})
        out = perception_imagination_distance({Modality.EEG: self._fs(Modality.EEG, posterior_rel_alpha=0.4)}, prof)
        assert out["value"] == pytest.approx(2.0) and out["objective_allowed"] is False


class TestController:
    def test_state_machine_rejects_invalid_transition(self):
        c = FeedbackController(BoundedRulePolicy())
        with pytest.raises(TransitionError):
            c.transition(ControllerState.FEEDBACK_RESEARCH, 0, "skip")

    def test_real_sensor_feedback_requires_authorization(self):
        c = FeedbackController(BoundedRulePolicy())
        with pytest.raises(AuthorizationError):
            _active(c, ControllerState.FEEDBACK_RESEARCH, kinds=("REAL_SENSOR",))
        auth = FeedbackAuthorization(protocol_id="P", ethics_approval_ref="E", supervisor_id="S",
                                     signal_validation_ref="V", safety_review_ref="R", allow_real_sensor=True)
        c2 = _active(FeedbackController(BoundedRulePolicy(), authorization=auth),
                     ControllerState.FEEDBACK_RESEARCH, kinds=("REAL_SENSOR",))
        assert c2.state == ControllerState.FEEDBACK_RESEARCH

    def test_shadow_never_delivers(self):
        c = _active(FeedbackController(BoundedRulePolicy()))
        ds = [c.tick(10 + 5 * i, _state(att=0.1 + 0.2 * i), GOOD_GATES) for i in range(4)]
        assert not any(d.delivered for d in ds) and any(d.proposed for d in ds)

    def test_feedback_research_delivers_in_simulation(self):
        c = _active(FeedbackController(BoundedRulePolicy()), ControllerState.FEEDBACK_RESEARCH)
        ds = [c.tick(10 + 5 * i, _state(att=0.9), GOOD_GATES) for i in range(3)]
        assert ds[0].delivered and verify_trace(c.trace)

    @pytest.mark.parametrize("gates, code", [
        (GateInputs(usable_streams=1, stale_streams=["eeg"], mean_quality=0.9, max_alignment_uncertainty_s=0.001),
         "stale_data"),
        (GateInputs(usable_streams=0, disconnected_streams=["ecg"], mean_quality=0.9,
                    max_alignment_uncertainty_s=0.001), "sensor_disconnected"),
        (GateInputs(usable_streams=2, mean_quality=0.1, max_alignment_uncertainty_s=0.001), "low_signal_quality"),
        (GateInputs(usable_streams=2, mean_quality=0.9, max_alignment_uncertainty_s=None), "alignment_unknown"),
        (GateInputs(usable_streams=2, mean_quality=0.9, max_alignment_uncertainty_s=0.2), "alignment_uncertain"),
    ])
    def test_bad_data_holds_then_falls_back(self, gates, code):
        c = _active(FeedbackController(BoundedRulePolicy()), ControllerState.FEEDBACK_RESEARCH)
        first = c.tick(10, _state(att=0.9), gates)
        assert code in first.hold_reason and first.proposed is None and not first.delivered
        for i in range(5):
            c.tick(12 + 2 * i, _state(att=0.9), gates)
        assert c.state == ControllerState.SAFE_FALLBACK

    def test_low_confidence_holds(self):
        c = _active(FeedbackController(BoundedRulePolicy()))
        assert "low_confidence" in c.tick(10, _state(conf=0.1), GOOD_GATES).hold_reason

    @pytest.mark.parametrize("kw, gate_kw, code", [
        ({"ro": 0.2}, {}, "reality_orientation_low"),
        ({}, {"self_report_text": "I feel dizzy and unreal"}, "dissociation_keyword"),
        ({}, {"discomfort": 0.9}, "discomfort_reported"),
    ])
    def test_adverse_reports_trigger_fallback(self, kw, gate_kw, code):
        c = _active(FeedbackController(BoundedRulePolicy()), ControllerState.FEEDBACK_RESEARCH)
        d = c.tick(10, _state(**kw), GOOD_GATES.model_copy(update=gate_kw))
        assert c.state == ControllerState.SAFE_FALLBACK and code in [f["code"] for f in d.safety_findings]
        assert d.applied["rest_cue"] == 1.0 and d.delivered

    def test_fatigue_requires_consecutive_ticks(self):
        c = _active(FeedbackController(BoundedRulePolicy()))
        c.tick(10, _state(fatigue=0.9), GOOD_GATES)
        assert c.state == ControllerState.ACTIVE_SHADOW
        c.tick(12, _state(fatigue=0.9), GOOD_GATES)
        assert c.state == ControllerState.SAFE_FALLBACK

    def test_session_time_limit_terminates(self):
        c = _active(FeedbackController(BoundedRulePolicy(), ControllerConfig(session_limit_s=60)))
        c.tick(61, _state(), GOOD_GATES)
        assert c.state == ControllerState.TERMINATED

    def test_emergency_stop_and_pause(self):
        c = _active(FeedbackController(BoundedRulePolicy()))
        c.pause(5)
        assert c.state == ControllerState.PAUSED
        assert c.tick(6, _state(), GOOD_GATES).proposed is None
        c.emergency_stop(7)
        assert c.state == ControllerState.TERMINATED and c.tick(8, _state(), GOOD_GATES).proposed is None

    def test_rate_limit_step_bound_and_hysteresis(self):
        cfg = ControllerConfig(ema_alpha=1.0, min_action_interval_s=4.0, max_step=0.1)
        c = _active(FeedbackController(BoundedRulePolicy(), cfg), ControllerState.FEEDBACK_RESEARCH)
        d1 = c.tick(10, _state(att=1.0), GOOD_GATES)
        d2 = c.tick(11, _state(att=0.0), GOOD_GATES)
        assert d2.adaptation_note == "rate_limited" and d2.applied == d1.applied
        assert abs(d1.applied["scene_complexity"] - 0.3) <= 0.1 + 1e-9
        d3 = c.tick(20, _state(att=1.0), GOOD_GATES)
        d4 = c.tick(30, _state(att=1.0), GOOD_GATES)
        assert d4.applied["scene_complexity"] <= 0.85
        assert d3.applied != d1.applied or d4.adaptation_note in {"", "within_hysteresis"}

    def test_pid_controller_policy_bounded(self):
        pol = PIDControllerPolicy()
        for iqi in (0.0, 1.0, 0.0, 1.0):
            p = pol.propose(_state(iqi=iqi), {})
            assert 0 <= p.scene_complexity <= 1 and 0 <= p.visual_cue_strength <= 1

    def test_forbidden_objectives_rejected(self):
        class Bad:
            name, version, objective = "bad", "1", "perception_imagination_distance"

        with pytest.raises(ValueError):
            register_policy("bad", Bad)
        with pytest.raises(ValueError):
            FeedbackController(Bad())

    def test_trace_tamper_detected(self):
        c = _active(FeedbackController(BoundedRulePolicy()), ControllerState.FEEDBACK_RESEARCH)
        for i in range(3):
            c.tick(10 + 5 * i, _state(att=0.3 * i), GOOD_GATES)
        assert verify_trace(c.trace)
        c.trace[1].applied["scene_complexity"] = 0.99
        assert not verify_trace(c.trace)


class TestCorridor:
    def test_action_bounds_and_shadow_shows_neutral(self):
        c = _active(FeedbackController(BoundedRulePolicy()))
        d = c.tick(10, _state(att=1.0), GOOD_GATES)
        a = corridor_action("s", d)
        assert not a.delivered and a.scene.prompt_text
        assert a.scene.wall_distortion <= MAX_WALL_DISTORTION and a.scene.light_stability >= 0.8
        assert a.policy_version and a.triggering_estimate and a.safety_decision == []

    def test_probe_trial_removes_cues(self):
        c = _active(FeedbackController(BoundedRulePolicy()), ControllerState.FEEDBACK_RESEARCH)
        a = corridor_action("s", c.tick(10, _state(att=1.0), GOOD_GATES), probe_trial=True)
        assert a.scene.texture_detail == 0 and a.audio["guidance_level"] == 0 and a.probe_trial

    def test_generative_variation_fallbacks(self):
        class Slow:
            async def generate(self, seed):
                await asyncio.sleep(1.0)
                return {}

        class Unsafe:
            async def generate(self, seed):
                return {"variation_id": "x", "palette": "dawn", "ambient_sound": "rain",
                        "guidance_text": "This is real, you cannot tell the difference.", "complexity_offset": 0}

        for prov in (Slow(), Unsafe()):
            cache = VariationCache(prov, timeout_s=0.05)
            asyncio.run(cache.prefetch([1, 2]))
            assert cache.get(1).source == "deterministic" and len(cache.events) == 2
        assert VariationCache().get(99).source == "deterministic"
        with pytest.raises(ValueError):
            validate_variation({"variation_id": "x", "palette": "neon_strobe", "ambient_sound": "rain",
                                "guidance_text": "ok", "complexity_offset": 0}, "generative")


class TestTraining:
    def test_arm_assignment_deterministic_and_balanced(self):
        arms = [assign_arm(f"P{i}", "study-1")["arm"] for i in range(300)]
        assert assign_arm("P1", "study-1") == assign_arm("P1", "study-1")
        counts = {a: arms.count(a) for a in set(arms)}
        assert len(counts) == 3 and min(counts.values()) > 70

    def test_cue_fading_probes_rest_and_progression(self):
        cur = Curriculum("P", "adaptive_feedback", probe_every=3, rest_every=100)
        trials = [cur.next_trial("object") for _ in range(6)]
        assert [t["probe"] for t in trials] == [False, False, True, False, False, True]
        assert all(t["cue_cap"] == 0.0 and t["feedback"] == "none" for t in trials if t["probe"])
        assert cue_cap_for_level(0) == 1.0 and cue_cap_for_level(7) == 0.0
        for _ in range(2):
            cur.record(TrialOutcome("object", 0, False, 0.9, None, 0.3, 0.2))
        assert cur.levels["object"] == 1
        cur.record(TrialOutcome("object", 1, False, 0.9, None, 0.3, 0.9))
        assert cur.levels["object"] == 1
        cur.record(TrialOutcome("object", 1, True, 0.4, None, None, 0.2))
        rep = cur.report()
        assert rep["cue_free_probe_vividness"] == 0.4 and "transfer measure" in rep["interpretation"]

    def test_rest_periods_scheduled(self):
        cur = Curriculum("P", "no_feedback", rest_every=2)
        for _ in range(2):
            cur.next_trial("object")
            cur.record(TrialOutcome("object", 0, False, 0.5, None, None, 0.1))
        assert cur.next_trial("object")["type"] == "rest"


class TestClosedLoopRuntime:
    @pytest.fixture(scope="class")
    def shadow(self):
        return run_session(SessionConfig(duration_s=100, seed=3))

    def test_default_shadow_mode_never_delivers(self, shadow):
        s, summ = shadow
        assert summ["mode"] == "shadow" and summ["n_delivered"] == 0
        assert summ["final_state"] == "ACTIVE_SHADOW" and summ["trace_valid"]
        assert summ["source_kinds"] == ["SYNTHETIC"] and "not participant outcomes" in summ["disclaimer"]
        assert any(e["decision"]["proposed"] for e in s.log)

    def test_estimates_expose_provenance(self, shadow):
        s, _ = shadow
        st = s.log[-1]["state"]
        assert st["source_kinds"] == ["SYNTHETIC"] and "eeg" in st["modalities_used"]
        for d in st["dimensions"].values():
            assert d["evidence_class"] in {e.value for e in EvidenceClass}
            assert d["value"] is None or d["inputs"]

    def test_controller_replay_reproduces_decisions(self, shadow):
        s, summ = shadow
        r = replay_controller(json.loads(json.dumps(s.log)), s.cfg)
        assert r["reproduced"] and r["final_hash"] == summ["decision_hash"]

    def test_full_rerun_is_deterministic(self, shadow):
        s, _ = shadow
        s2, _ = run_session(SessionConfig(duration_s=100, seed=3))
        assert session_digest(s.log) == session_digest(s2.log)

    def test_simulated_feedback_research_end_to_end(self):
        s, summ = run_session(SessionConfig(duration_s=100, seed=3, mode="feedback_research"))
        assert summ["n_delivered"] > 0
        delivered = [e for e in s.log if e["corridor"]["delivered"]]
        assert delivered and all(e["corridor"]["scene"]["prompt_text"] for e in delivered)

    def test_real_sensor_feedback_blocked_without_authorization(self, monkeypatch):
        from app.multimodal.acquisition import synthetic
        monkeypatch.setattr(synthetic.SyntheticECG, "source_kind", SourceKind.REAL_SENSOR)
        with pytest.raises(AuthorizationError):
            run_session(SessionConfig(duration_s=60, mode="feedback_research"))
        _, summ = run_session(SessionConfig(duration_s=60, mode="shadow"))
        assert "REAL_SENSOR" in summ["source_kinds"] and summ["n_delivered"] == 0

    def test_sensor_disconnect_prevents_adaptation(self):
        from app.multimodal.acquisition.base import FaultPlan
        cfg = SessionConfig(duration_s=100, seed=3, mode="feedback_research",
                            faults={Modality.EEG: FaultPlan(disconnect_at_s=60.0, reconnect_after_s=100.0)})
        s, summ = run_session(cfg)
        after = [e for e in s.log if e["t"] > 61]
        assert all(not e["decision"]["delivered"] or e["decision"]["controller_state"] == "SAFE_FALLBACK"
                   for e in after)
        assert "sensor_disconnected" in summ["safety_codes"] and summ["final_state"] == "SAFE_FALLBACK"

    def test_replay_reproduces_feedback_session_with_fallback(self):
        s, summ = run_session(SessionConfig(duration_s=100, seed=5, mode="feedback_research",
                                            events=[ScriptedEvent(t=80, kind="discomfort", value=0.9)]))
        assert summ["final_state"] == "SAFE_FALLBACK" and summ["n_delivered"] > 0
        r = replay_controller(json.loads(json.dumps(s.log)), s.cfg)
        assert r["reproduced"] and r["final_hash"] == summ["decision_hash"]

    def test_scripted_distress_and_emergency_stop(self):
        _, summ = run_session(SessionConfig(duration_s=100, seed=3, mode="feedback_research",
                                            events=[ScriptedEvent(t=70, kind="report_text", value="I feel dizzy")]))
        assert summ["final_state"] == "SAFE_FALLBACK" and "dissociation_keyword" in summ["safety_codes"]
        _, summ = run_session(SessionConfig(duration_s=100, events=[ScriptedEvent(t=60, kind="emergency_stop")]))
        assert summ["final_state"] == "TERMINATED" and summ["n_ticks"] < 31

    def test_record_then_replay_from_files(self, tmp_path):
        s, _ = run_session(SessionConfig(duration_s=70, seed=4, store_root=str(tmp_path),
                                         modalities=[Modality.EEG, Modality.ECG]))
        files = {p.stem.split(".")[1].split("_")[0]: p for p in (tmp_path / "mm-sim" / "streams").iterdir()}
        cfg = SessionConfig(duration_s=60, source="replay", modalities=[Modality.EEG, Modality.ECG],
                            replay_paths={Modality.EEG: str(files["eeg"]), Modality.ECG: str(files["ecg"])})
        r1, summ = run_session(cfg)
        r2, _ = run_session(cfg)
        assert summ["source_kinds"] == ["REPLAY"] and summ["trace_valid"]
        assert session_digest(r1.log) == session_digest(r2.log)
        assert (tmp_path / "mm-sim" / "decisions.jsonl").exists()
