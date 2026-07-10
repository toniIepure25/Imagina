"""Tests for unified feedback policy contracts."""
import pytest

from app.research.feedback_policies import (
    FixedResearchFeedbackPolicy,
    FrozenYokedFeedbackPolicy,
)
from app.research.runtime import FeedbackContext


def _make_context(window_index=0, attention=0.5, engagement=0.3, fatigue=0.2, pid=0.3, iqi=0.5):
    return FeedbackContext(
        session_id="rs1",
        trial_id="t1",
        window_index=window_index,
        state_estimate={"attention": attention, "engagement": engagement, "fatigue": fatigue, "relaxation": 0.5},
        feature_vector={"alpha": 0.5, "beta": 0.4, "theta": 0.3, "gamma": 0.2},
        pid=pid,
        iqi=iqi,
        curriculum_level=1,
        safety_context={},
        seed=42,
    )


class TestFixedPolicy:
    async def test_constant_output(self):
        policy = FixedResearchFeedbackPolicy()
        d1 = await policy.compute(_make_context(attention=0.1, iqi=0.2))
        d2 = await policy.compute(_make_context(attention=0.9, iqi=0.9))
        assert d1.scene_params == d2.scene_params

    async def test_ignores_state(self):
        policy = FixedResearchFeedbackPolicy(frozen_params={"scene_clarity": 0.7})
        d = await policy.compute(_make_context(attention=0.0, engagement=0.0))
        assert d.scene_params["scene_clarity"] == 0.7

    async def test_policy_metadata(self):
        policy = FixedResearchFeedbackPolicy()
        d = await policy.compute(_make_context())
        assert d.policy_id == "fixed"
        assert d.policy_version == "1.0"
        assert d.reason == "fixed_protocol"


class TestYokedPolicy:
    async def test_replays_trajectory(self):
        points = [
            {"scene_params": {"scene_clarity": 0.3}, "prompt_text": "Step 0"},
            {"scene_params": {"scene_clarity": 0.6}, "prompt_text": "Step 1"},
            {"scene_params": {"scene_clarity": 0.9}, "prompt_text": "Step 2"},
        ]
        policy = FrozenYokedFeedbackPolicy(points)
        d0 = await policy.compute(_make_context(window_index=0))
        d1 = await policy.compute(_make_context(window_index=1))
        d2 = await policy.compute(_make_context(window_index=2))
        assert d0.scene_params["scene_clarity"] == 0.3
        assert d1.scene_params["scene_clarity"] == 0.6
        assert d2.scene_params["scene_clarity"] == 0.9

    async def test_ignores_current_state(self):
        points = [{"scene_params": {"scene_clarity": 0.5}}]
        policy = FrozenYokedFeedbackPolicy(points)
        d1 = await policy.compute(_make_context(window_index=0, attention=0.0, iqi=0.0))
        d2 = await policy.compute(_make_context(window_index=0, attention=1.0, iqi=1.0))
        assert d1.scene_params == d2.scene_params

    async def test_exceeds_trajectory_raises(self):
        points = [{"scene_params": {"scene_clarity": 0.5}}]
        policy = FrozenYokedFeedbackPolicy(points)
        with pytest.raises(ValueError, match="exceeds trajectory length"):
            await policy.compute(_make_context(window_index=1))

    async def test_empty_trajectory_raises(self):
        policy = FrozenYokedFeedbackPolicy([])
        with pytest.raises(ValueError, match="empty"):
            await policy.compute(_make_context(window_index=0))
