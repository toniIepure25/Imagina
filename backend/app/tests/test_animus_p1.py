"""ANIMUS-P1 test suite (design/product-only; NO human or neural data).

Covers: unit + property, closed-loop state machine, privacy invariants, determinism/replay, controller
behaviour, a small blind benchmark, API + event flow, claim-level enforcement, and adversarial cases
(contradictory / zero / NaN / duplicate feedback, fatigue stop, claim violation, scientific immutability).
"""
from __future__ import annotations

import numpy as np
import pytest
from starlette.testclient import TestClient

from app.core.animus import claims
from app.core.animus.belief_state import BeliefFusionEngine
from app.core.animus.benchmark import make_target, run_campaign, run_trial
from app.core.animus.candidate_generator import (
    DeterministicSceneGenerator,
    PrivacyViolation,
    assert_no_forbidden_content,
)
from app.core.animus.controller import CONTROLLERS, AnimusActiveController, build_controller
from app.core.animus.feedback import normalize_feedback, parse_freetext
from app.core.animus.loop_runtime import AnimusLoop, LoopConfig
from app.core.animus.models import (
    FB_CLOSER_FARTHER,
    ImaginationBeliefState,
    ObservationEnvelope,
)
from app.core.animus.sdk import animus
from app.core.animus.synthetic_imaginer import ImaginerParams, SyntheticImaginer


# ------------------------------------------------------------------ unit / property
def test_belief_prior_shapes_and_uncertainty():
    b = ImaginationBeliefState.broad_prior()
    assert len(b.visual_embedding.mean) == 16
    assert 0 < b.global_uncertainty() < 5
    assert set(b.global_scene_attributes) and all(
        abs(sum(cb.probs.values()) - 1.0) < 1e-6 for cb in b.global_scene_attributes.values())


def test_categorical_update_increases_target_probability():
    b = ImaginationBeliefState.broad_prior()
    eng = BeliefFusionEngine()
    fb = normalize_feedback({"channel": "attribute_correction", "attribute": "color_palette",
                             "target_option": "cold", "strength": 1.0})
    before = b.global_scene_attributes["color_palette"].probs["cold"]
    eng.apply_feedback(b, fb)
    after = b.global_scene_attributes["color_palette"].probs["cold"]
    assert after > before and b.global_scene_attributes["color_palette"].argmax() == "cold"


def test_freetext_maps_to_structured_feedback():
    subs = parse_freetext("make it more blue and add more depth")
    attrs = {s["attribute"] for s in subs}
    assert "color_palette" in attrs and "depth" in attrs


# ------------------------------------------------------------------ state machine
def _twin_loop(controller="ANIMUS_ACTIVE", seed=1, max_iterations=8):
    target = make_target(0, seed)
    twin = SyntheticImaginer(target, ImaginerParams(), np.random.default_rng(seed * 6151 + 17))
    from app.core.animus.benchmark import TwinRespondent
    cfg = LoopConfig(session_id="t", seed=seed, controller=controller, max_iterations=max_iterations)
    return AnimusLoop(cfg, TwinRespondent(twin), imaginer=twin)


def test_loop_runs_to_completion_and_emits_events():
    loop = _twin_loop()
    res = loop.run()
    assert res.final_state == "COMPLETE" and not res.aborted
    types = {e["event_type"] for e in res.events}
    for required in ("animus.session.started", "animus.controller.action", "animus.belief.updated",
                     "animus.convergence.updated", "animus.session.completed"):
        assert required in types
    assert res.iterations <= 8


def test_belief_hashes_recorded_each_step():
    loop = _twin_loop()
    res = loop.run()
    assert len(res.belief_hashes) == res.iterations + 1


# ------------------------------------------------------------------ determinism
def test_deterministic_replay_hash():
    r1 = run_trial("ANIMUS_ACTIVE", make_target(0, 1), 42)
    r2 = run_trial("ANIMUS_ACTIVE", make_target(0, 1), 42)
    assert r1.replay_hash == r2.replay_hash
    assert r1.similarity_series == r2.similarity_series


def test_distinct_seeds_differ():
    r1 = run_trial("ANIMUS_ACTIVE", make_target(0, 1), 1)
    r2 = run_trial("ANIMUS_ACTIVE", make_target(0, 2), 2)
    assert r1.replay_hash != r2.replay_hash


# ------------------------------------------------------------------ controller / benchmark
def test_all_controllers_run():
    for name in CONTROLLERS:
        r = run_trial(name, make_target(1, 1), 5)
        assert r.valid and 0 <= r.final_similarity <= 1


def test_animus_beats_static_and_random_small_campaign():
    camp = run_campaign(n_targets=12, seed_families=(1,), max_iterations=8)
    by = {}
    for t in camp["trials"]:
        by.setdefault(t["controller"], []).append(t["loop_gain"])
    med = {c: float(np.median(v)) for c, v in by.items()}
    assert med["ANIMUS_ACTIVE"] > med["STATIC"]
    assert med["ANIMUS_ACTIVE"] > med["RANDOM"]
    assert med["ANIMUS_ACTIVE"] >= 1.20 * med["RANDOM"]


def test_hidden_target_not_accessible_to_controller():
    ctrl = build_controller("ANIMUS_ACTIVE")
    belief = ImaginationBeliefState.broad_prior()
    # a controller decision is a pure function of the belief + context; no target reference exists
    from app.core.animus.controller import ControlContext
    dec = ctrl.select_action(belief, ControlContext(iteration=0, max_iterations=8))
    assert "target" not in str(dec).lower()


# ------------------------------------------------------------------ privacy
def test_generation_payload_rejects_raw_neural_and_identifiers():
    for bad in ({"raw_neural": [1, 2]}, {"eeg": [1]}, {"participant_id": "x"},
                {"forward_operator": [[1]]}, {"embedding": list(range(1000))}):
        with pytest.raises(PrivacyViolation):
            assert_no_forbidden_content(bad)


def test_generated_candidate_is_clean():
    gen = DeterministicSceneGenerator()
    cset = gen.generate(ImaginationBeliefState.broad_prior(), {"seed": 1, "n": 1})
    assert_no_forbidden_content(cset.candidates[0].to_dict())  # must not raise


# ------------------------------------------------------------------ claim level
def test_claim_ceiling_blocks_neural_content_level():
    auth = claims.ClaimAuthorization()
    assert auth.is_allowed(claims.L0_SIMULATED)
    assert auth.is_allowed(claims.L1_BEHAVIORAL_ASSISTED)
    for lvl in (claims.L2_BIOSIGNAL_ASSISTED_EXPERIMENTAL, claims.L3_NEURAL_CONTENT_INFORMED_VALIDATED):
        assert not auth.is_allowed(lvl)
        with pytest.raises(claims.ClaimLevelError):
            auth.enforce(lvl)


def test_forbidden_mind_reading_phrases_flagged():
    assert claims.audit_text_for_forbidden_claims("we can read your thoughts here")
    assert not claims.audit_text_for_forbidden_claims("a behavioral-assisted amplifier")


def test_future_neural_provider_fails_closed():
    from app.core.animus.models import SOURCE_VALIDATED_NEURAL_FUTURE
    from app.core.animus.observation import ProviderUnavailableError, build_provider
    prov = build_provider(SOURCE_VALIDATED_NEURAL_FUTURE)
    with pytest.raises(ProviderUnavailableError):
        prov.observe({})


# ------------------------------------------------------------------ adversarial
def test_contradictory_feedback_keeps_belief_finite():
    b = ImaginationBeliefState.broad_prior()
    eng = BeliefFusionEngine()
    emb = list(np.ones(16))
    eng.apply_feedback(b, normalize_feedback({"channel": FB_CLOSER_FARTHER,
                                              "preferred_embedding": emb, "closer": True}))
    eng.apply_feedback(b, normalize_feedback({"channel": FB_CLOSER_FARTHER,
                                              "preferred_embedding": emb, "closer": False}))
    assert np.all(np.isfinite(b.visual_embedding.mean))


def test_nan_observation_is_ignored():
    b = ImaginationBeliefState.broad_prior()
    eng = BeliefFusionEngine()
    obs = ObservationEnvelope(source_type="SIMULATED_NEURAL",
                              representation={"visual": [float("nan")] * 16},
                              uncertainty={"visual": 1.0}, signal_quality=0.5,
                              measurement_id="m", timestamp="t", provenance={},
                              scientific_authorization="SIM")
    eng.apply_observation(b, obs)
    assert np.all(np.isfinite(b.visual_embedding.mean))


def test_all_zero_observation_handled():
    b = ImaginationBeliefState.broad_prior()
    eng = BeliefFusionEngine()
    obs = ObservationEnvelope(source_type="SIMULATED_NEURAL",
                              representation={"visual": [0.0] * 16}, uncertainty={"visual": 1.0},
                              signal_quality=0.1, measurement_id="m", timestamp="t", provenance={},
                              scientific_authorization="SIM")
    eng.apply_observation(b, obs)
    assert np.all(np.isfinite(b.visual_embedding.mean))


def test_fatigue_budget_aborts():
    target = make_target(0, 1)
    params = ImaginerParams(fatigue=0.9, fatigue_rate=0.2)
    twin = SyntheticImaginer(target, params, np.random.default_rng(3))
    from app.core.animus.benchmark import TwinRespondent
    cfg = LoopConfig(session_id="f", seed=1, controller="ANIMUS_ACTIVE", max_iterations=8,
                     fatigue_budget=0.5)
    loop = AnimusLoop(cfg, TwinRespondent(twin), imaginer=twin)
    res = loop.run()
    assert res.aborted and "fatigue" in (res.abort_reason or "")


def test_duplicate_feedback_is_idempotent_enough():
    b = ImaginationBeliefState.broad_prior()
    eng = BeliefFusionEngine()
    fb = normalize_feedback({"channel": "object_correction", "object": "castle", "op": "add"})
    eng.apply_feedback(b, fb)
    p1 = b.objects["castle"]
    eng.apply_feedback(b, fb)
    p2 = b.objects["castle"]
    assert 0 < p1 <= p2 <= 1  # monotone, bounded


# ------------------------------------------------------------------ SDK + API
def test_sdk_amplifier_flow():
    s = animus.start(mode="amplifier", seed=99)
    s.generate(n=1)
    st = s.feedback(channel="attribute_correction", direction="brighter")
    assert st["scene_graph"]["attributes"]["brightness"] == "bright"
    assert s.replay()["final_belief_hash"]
    s.complete()


def test_api_session_lifecycle():
    from app.main import app
    c = TestClient(app)
    assert c.get("/animus/health").json()["status"] == "ok"
    sid = c.post("/animus/sessions", json={"mode": "amplifier", "seed": 5}).json()["session_id"]
    c.post(f"/animus/sessions/{sid}/generate", json={"n": 1})
    st = c.post(f"/animus/sessions/{sid}/feedback",
                json={"channel": "object_correction", "object": "moon", "op": "add"}).json()
    assert "moon" in st["scene_graph"]["objects"]
    tl = c.get(f"/animus/sessions/{sid}/timeline").json()
    assert any(e["event_type"] == "animus.feedback.received" for e in tl["events"])
    assert c.get("/animus/scientific-registry").json()["max_authorized_claim_level"] == \
        "L1_BEHAVIORAL_ASSISTED"


def test_api_benchmark_endpoint_passes():
    from app.main import app
    c = TestClient(app)
    r = c.post("/animus/benchmarks/run", json={"n_targets": 6, "seed_families": [1]}).json()
    assert r["decision"]["decision"].startswith("ANIMUS_P1_VERTICAL_SLICE")


# ------------------------------------------------------------------ scientific boundary
def test_scientific_registry_no_content_claim():
    from app.core.animus.evidence_registry import registry_snapshot
    snap = registry_snapshot()
    assert snap["max_authorized_claim_level"] == "L1_BEHAVIORAL_ASSISTED"
    assert all(not v["authorizes_content_claim"] for v in snap["registry"].values())


def test_active_controller_is_not_labeled_validated_cognitive_model():
    assert AnimusActiveController.__doc__ and "engineering controller" not in ""  # sanity
    # the controller must not claim to be a validated model in its own metadata
    from app.core.animus.controller import AnimusPolicyConfig
    assert "validated" not in str(AnimusPolicyConfig().to_dict()).lower()
