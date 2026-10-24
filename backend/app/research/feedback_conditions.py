from __future__ import annotations

import uuid

from app.schemas.feedback import FeedbackAction
from app.schemas.research import FeedbackCondition


class FixedFeedbackPolicy:
    """Produces constant scene parameters regardless of state. Used as control condition."""

    def __init__(self, level: int = 3):
        self.level = level
        self._scene_params = self._make_fixed_params(level)

    @staticmethod
    def _make_fixed_params(level: int) -> dict[str, float]:
        t = min(level / 8.0, 1.0)
        return {
            "scene_clarity": round(0.4 + 0.2 * t, 4),
            "blur": round(0.35 - 0.1 * t, 4),
            "wall_distortion": round(0.25 - 0.05 * t, 4),
            "light_stability": round(0.55 + 0.1 * t, 4),
            "texture_detail": round(0.2 * t, 4),
            "particle_stability": round(0.6, 4),
            "door_complexity": 0.0,
            "fog_density": round(0.3, 4),
            "color_saturation": round(0.45 + 0.1 * t, 4),
            "breathing_cue_strength": round(0.2, 4),
        }

    def compute(
        self, session_id: str, window_index: int,
    ) -> FeedbackAction:
        from app.core.time import utcnow

        return FeedbackAction(
            session_id=session_id,
            timestamp=utcnow(),
            window_index=window_index,
            action_id=str(uuid.uuid4()),
            prompt_text="Continue imagining the corridor. Let it be whatever it is.",
            reason=f"fixed_feedback level={self.level}",
            **self._scene_params,
        )


class YokedFeedbackPolicy:
    """Replays scene parameters from a recorded adaptive session. Non-contingent control."""

    def __init__(self, replay_sequence: list[dict]):
        self._sequence = replay_sequence

    def compute(
        self, session_id: str, window_index: int,
    ) -> FeedbackAction:
        from app.core.time import utcnow

        idx = min(window_index, len(self._sequence) - 1) if self._sequence else 0
        params = self._sequence[idx] if self._sequence else {}

        return FeedbackAction(
            session_id=session_id,
            timestamp=utcnow(),
            window_index=window_index,
            action_id=str(uuid.uuid4()),
            scene_clarity=params.get("scene_clarity", 0.5),
            blur=params.get("blur", 0.3),
            wall_distortion=params.get("wall_distortion", 0.2),
            light_stability=params.get("light_stability", 0.6),
            texture_detail=params.get("texture_detail", 0.1),
            particle_stability=params.get("particle_stability", 0.6),
            door_complexity=params.get("door_complexity", 0.0),
            fog_density=params.get("fog_density", 0.3),
            color_saturation=params.get("color_saturation", 0.5),
            breathing_cue_strength=params.get("breathing_cue_strength", 0.2),
            prompt_text="Continue imagining the corridor. Let it be whatever it is.",
            reason="yoked_feedback",
        )


def get_feedback_policy(condition: FeedbackCondition, **kwargs):
    if condition == FeedbackCondition.ADAPTIVE:
        from app.services.feedback_policy_engine import FeedbackPolicyEngine
        return FeedbackPolicyEngine()
    elif condition == FeedbackCondition.FIXED:
        level = kwargs.get("level", 3)
        return FixedFeedbackPolicy(level=level)
    elif condition == FeedbackCondition.YOKED:
        replay_sequence = kwargs.get("replay_sequence", [])
        return YokedFeedbackPolicy(replay_sequence=replay_sequence)
    raise ValueError(f"Unknown feedback condition: {condition}")
