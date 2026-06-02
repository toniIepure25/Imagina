"""Tests for IMAGINA Personalization Pipeline."""

import json
import os


class TestImaginaPersonalization:
    def test_default_profile_creation(self):
        from app.core.personalization.user_profile import reset_profile
        p = reset_profile("test_default")
        assert p["user_id"] == "test_default"
        assert p["session_count"] == 0
        assert p["total_steps"] == 0
        assert p["mean_iqi"] == 0.0
        assert p["recommendations"] == []

    def test_profile_persistence(self):
        from app.core.personalization.user_profile import load_profile, reset_profile, save_profile
        p = reset_profile("test_persist")
        p["session_count"] = 5
        save_profile(p)
        loaded = load_profile("test_persist")
        assert loaded["session_count"] == 5

    def test_analytics_on_empty_session(self):
        from app.core.analytics.session_analytics import analyze_session
        result = analyze_session("nonexistent_session")
        assert result["n_steps"] == 0
        assert "error" in result

    def test_full_pipeline(self):
        from app.core.analytics.session_analytics import analyze_session
        from app.core.personalization.adaptive_policy import personalization_confidence, recommend_next_task
        from app.core.personalization.recommender import generate_recommendations
        from app.core.personalization.user_profile import reset_profile, update_profile_from_session
        from app.core.sessions.session_manager import session_manager

        # Run session
        res = session_manager.start_session("pytest_user", {"demo_mode": True})
        sid = res["session_id"]
        session_manager.start_task(sid, "shape_stabilization")
        session_manager.submit_self_report(sid, 7, 6, 3)
        for _ in range(3):
            session_manager.run_step(sid)

        # Analytics
        a = analyze_session(sid)
        assert a["n_steps"] > 0
        assert a["mean_iqi"] > 0

        # Profile update
        p = update_profile_from_session("pytest_user", sid)
        assert p["session_count"] >= 1
        assert p["total_steps"] > 0
        assert len(p["recommendations"]) > 0

        # Recommendations
        recs = generate_recommendations(p)
        assert len(recs) > 0

        # Adaptive policy
        task_id = recommend_next_task(p, [{"id": "shape_stabilization"}, {"id": "color_stabilization"}])
        assert task_id is not None

        conf = personalization_confidence(p)
        assert conf in ("low", "medium", "high")

        # Cleanup
        reset_profile("pytest_user")

    def test_recommendations_generated(self):
        from app.core.personalization.recommender import generate_recommendations
        from app.core.personalization.user_profile import reset_profile, save_profile

        p = reset_profile("test_recs")
        p["session_count"] = 3
        p["iqi_trend_slope"] = 0.01
        p["fatigue_trend_slope"] = 0.02
        p["best_tasks"] = ["shape_stabilization", "motion"]
        p["optimal_session_length_steps"] = 12
        p["fatigue_threshold_estimate"] = 10
        save_profile(p)

        recs = generate_recommendations(p)
        assert len(recs) > 0

        reset_profile("test_recs")

    def test_adaptive_policy(self):
        from app.core.personalization.adaptive_policy import (
            get_disclaimer,
            recommend_session_length,
            tweak_feedback_params,
        )
        from app.core.personalization.user_profile import reset_profile, save_profile

        p = reset_profile("test_adapt")
        p["session_count"] = 3
        p["fatigue_trend_slope"] = 0.02
        p["attention_history"] = [0.3, 0.3, 0.32, 0.28]
        save_profile(p)

        base = {"clarity": 0.7, "scene_complexity": 0.6, "motion_speed": 0.4, "breathing_cue_intensity": 0.3}
        tweaked = tweak_feedback_params(p, base)
        assert tweaked["clarity"] < 0.7  # reduced due to fatigue
        assert tweaked["breathing_cue_intensity"] > 0.3  # increased for low attention

        assert recommend_session_length(p) > 0
        assert len(get_disclaimer()) > 50

        reset_profile("test_adapt")

    def test_api_endpoints(self):
        from app.api.imagina.routes import router
        assert router is not None

    def test_no_raw_imagery_stored(self):
        import glob
        profiles_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "..", "..", "..", "data", "imagina", "profiles")
        for f in glob.glob(os.path.join(profiles_path, "*.json")):
            with open(f) as fh:
                data = json.load(fh)
            text = json.dumps(data)
            assert "raw_eeg" not in text.lower()
            assert "raw_signal" not in text.lower()
            assert "image_content" not in text.lower()
