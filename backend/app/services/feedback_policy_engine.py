"""
Maps StateEstimate + PID + IQI + CurriculumState -> FeedbackAction.

All scene parameters are 0-1 floats.  Prompt texts are deterministic templates.
"""

import uuid

from app.core.time import utcnow
from app.schemas.curriculum import CurriculumState
from app.schemas.feedback import FeedbackAction
from app.schemas.metrics import IQIEstimate, PIDEstimate, StateEstimate


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


PROMPTS = {
    "excellent":     "Good stability. Maintain the same corridor without adding new elements.",
    "good":          "Hold the shape of the walls. Let the light remain stable.",
    "building":      "Add one detail at a time: floor, door, light.",
    "low_attention": "Let the corridor become simple and steady. Do not force detail yet.",
    "fatigue":       "Your fatigue estimate is rising. Soften the image and return to breathing.",
    "unstable":      "Simplify the scene. Focus on the floor beneath you.",
    "breathing":     "Breathe slowly. Let the corridor fade to a simple outline.",
    "door_level":    "Notice the doors on the walls. Let one become clear.",
    "memory_room":   "Step through the door. Let a familiar room appear gently.",
    "default":       "Continue imagining the corridor. Let it be whatever it is.",
}


class FeedbackPolicyEngine:
    def compute(
        self,
        session_id: str,
        state: StateEstimate,
        pid: PIDEstimate,
        iqi: IQIEstimate,
        curriculum: CurriculumState,
        window_index: int,
    ) -> FeedbackAction:
        level = curriculum.current_level
        iqi_v = iqi.iqi
        pid_v = pid.pid

        scene_clarity = _clamp(iqi_v * 0.8 + (1 - pid_v) * 0.2)
        blur = _clamp(pid_v * 0.6 + (1 - state.attention_stability) * 0.4)
        wall_distortion = _clamp(
            (1 - state.imagery_engagement) * 0.5 + (1 - state.behavioral_consistency) * 0.3 + pid_v * 0.2
        )
        light_stability = _clamp(state.attention_stability * 0.5 + state.relaxation * 0.5)
        texture_detail = _clamp(iqi_v * 0.6 + (level / 8.0) * 0.4) if level >= 3 else 0.0
        particle_stability = _clamp(1.0 - state.uncertainty)
        door_complexity = _clamp((level - 5) / 3.0 * iqi_v) if level >= 6 else 0.0
        fog_density = _clamp(state.uncertainty * 0.5 + state.fatigue * 0.3 + pid_v * 0.2)
        color_saturation = _clamp(state.imagery_engagement * 0.7 + iqi_v * 0.3)
        breathing_cue = _clamp(
            (1 - state.attention_stability) * 0.4
            + state.fatigue * 0.4
            + (1 - state.relaxation) * 0.2
        )

        if state.fatigue > 0.65:
            fatigue_simplify = _clamp((state.fatigue - 0.65) / 0.35)
            texture_detail = _clamp(texture_detail * (1.0 - 0.75 * fatigue_simplify))
            wall_distortion = _clamp(wall_distortion * (1.0 - 0.55 * fatigue_simplify))
            particle_stability = _clamp(max(particle_stability, 0.65 + 0.25 * fatigue_simplify))
            color_saturation = _clamp(color_saturation * (1.0 - 0.45 * fatigue_simplify))
            breathing_cue = _clamp(max(breathing_cue, 0.65 + 0.25 * fatigue_simplify))

        prompt = self._select_prompt(state, pid, iqi, curriculum)
        reason = self._build_reason(state, pid, iqi, curriculum)

        return FeedbackAction(
            session_id=session_id,
            timestamp=utcnow(),
            window_index=window_index,
            action_id=str(uuid.uuid4()),
            scene_clarity=round(scene_clarity, 4),
            blur=round(blur, 4),
            wall_distortion=round(wall_distortion, 4),
            light_stability=round(light_stability, 4),
            texture_detail=round(texture_detail, 4),
            particle_stability=round(particle_stability, 4),
            door_complexity=round(door_complexity, 4),
            fog_density=round(fog_density, 4),
            color_saturation=round(color_saturation, 4),
            breathing_cue_strength=round(breathing_cue, 4),
            prompt_text=prompt,
            reason=reason,
        )

    @staticmethod
    def _select_prompt(
        state: StateEstimate,
        pid: PIDEstimate,
        iqi: IQIEstimate,
        curriculum: CurriculumState,
    ) -> str:
        if state.fatigue > 0.70:
            return PROMPTS["fatigue"]
        if state.attention_stability < 0.35:
            return PROMPTS["low_attention"]
        if pid.pid > 0.60:
            return PROMPTS["unstable"]
        if state.fatigue > 0.55:
            return PROMPTS["breathing"]
        if curriculum.current_level >= 7:
            return PROMPTS["memory_room"]
        if curriculum.current_level >= 6:
            return PROMPTS["door_level"]
        if pid.interpretation == "excellent":
            return PROMPTS["excellent"]
        if pid.interpretation == "good":
            return PROMPTS["good"]
        if iqi.iqi > 0.55:
            return PROMPTS["building"]
        return PROMPTS["default"]

    @staticmethod
    def _build_reason(
        state: StateEstimate,
        pid: PIDEstimate,
        iqi: IQIEstimate,
        curriculum: CurriculumState,
    ) -> str:
        parts = [
            f"L{curriculum.current_level}",
            f"IQI={iqi.iqi:.2f}",
            f"PID={pid.pid:.2f}",
            f"att={state.attention_stability:.2f}",
            f"fat={state.fatigue:.2f}",
        ]
        return " ".join(parts)
