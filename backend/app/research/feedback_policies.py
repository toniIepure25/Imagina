"""Unified feedback policy adapters for the research runtime.

All policies implement the same async compute() interface via FeedbackContext -> FeedbackDecision.
"""
from __future__ import annotations

import json
from typing import Any

from app.research.runtime import FeedbackContext, FeedbackDecision


class AdaptiveFeedbackPolicy:
    policy_id = "adaptive"
    policy_version = "1.0"

    def __init__(self) -> None:
        from app.services.feedback_policy_engine import FeedbackPolicyEngine
        self._engine = FeedbackPolicyEngine()

    async def compute(self, context: FeedbackContext) -> FeedbackDecision:
        from app.core.time import utcnow
        from app.schemas.pid_iqi import IQIResult, PIDResult
        from app.schemas.state import MentalState

        state = MentalState(
            session_id=context.session_id,
            timestamp=utcnow(),
            window_index=context.window_index,
            attention_stability=context.state_estimate.get("attention", 0.5),
            relaxation=context.state_estimate.get("relaxation", 0.5),
            imagery_engagement=context.state_estimate.get("engagement", 0.3),
            fatigue=context.state_estimate.get("fatigue", 0.2),
            confidence=0.7,
        )
        pid = PIDResult(
            session_id=context.session_id,
            timestamp=utcnow(),
            window_index=context.window_index,
            neural_proxy_distance=0.3,
            behavioral_distance=0.2,
            uncertainty=0.2,
            pid_score=context.pid or 0.3,
        )
        iqi = IQIResult(
            session_id=context.session_id,
            timestamp=utcnow(),
            window_index=context.window_index,
            attention_component=context.state_estimate.get("attention", 0.5),
            engagement_component=context.state_estimate.get("engagement", 0.3),
            behavioral_component=0.5,
            relaxation_component=context.state_estimate.get("relaxation", 0.5),
            confidence_weight=0.7,
            iqi_score=context.iqi or 0.5,
        )

        action = self._engine.compute_feedback(state, pid, iqi)
        scene_params = {
            "scene_clarity": action.scene_clarity,
            "blur": action.blur,
            "wall_distortion": action.wall_distortion,
            "light_stability": action.light_stability,
            "texture_detail": action.texture_detail,
            "particle_stability": action.particle_stability,
            "door_complexity": action.door_complexity,
            "fog_density": action.fog_density,
            "color_saturation": action.color_saturation,
            "breathing_cue_strength": action.breathing_cue_strength,
        }
        return FeedbackDecision(
            scene_params=scene_params,
            prompt_text=action.prompt_text,
            reason=action.reason,
            policy_id=self.policy_id,
            policy_version=self.policy_version,
        )


class FixedResearchFeedbackPolicy:
    policy_id = "fixed"
    policy_version = "1.0"

    def __init__(self, frozen_params: dict[str, float] | None = None):
        self._params = frozen_params or {
            "scene_clarity": 0.5,
            "blur": 0.3,
            "wall_distortion": 0.2,
            "light_stability": 0.6,
            "texture_detail": 0.1,
            "particle_stability": 0.6,
            "door_complexity": 0.0,
            "fog_density": 0.3,
            "color_saturation": 0.5,
            "breathing_cue_strength": 0.2,
        }

    async def compute(self, context: FeedbackContext) -> FeedbackDecision:
        return FeedbackDecision(
            scene_params=dict(self._params),
            prompt_text="Continue imagining the corridor. Let it be whatever it is.",
            reason="fixed_protocol",
            policy_id=self.policy_id,
            policy_version=self.policy_version,
        )


class FrozenYokedFeedbackPolicy:
    policy_id = "yoked"
    policy_version = "1.0"

    def __init__(self, trajectory_points: list[dict[str, Any]], trajectory_id: str = ""):
        self._points = trajectory_points
        self._trajectory_id = trajectory_id

    async def compute(self, context: FeedbackContext) -> FeedbackDecision:
        if not self._points:
            raise ValueError("Frozen yoked trajectory is empty — cannot compute feedback")

        idx = context.window_index
        if idx >= len(self._points):
            raise ValueError(
                f"Window index {idx} exceeds trajectory length {len(self._points)}. "
                "No fill-with-defaults allowed."
            )

        point = self._points[idx]
        scene_params = point.get("scene_params", point)
        if isinstance(scene_params, str):
            scene_params = json.loads(scene_params)

        return FeedbackDecision(
            scene_params=scene_params,
            prompt_text=point.get("prompt_text", "Continue imagining the corridor."),
            reason=f"yoked_replay_idx={idx}",
            policy_id=self.policy_id,
            policy_version=self.policy_version,
        )
