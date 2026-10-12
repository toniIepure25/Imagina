"""Bridge from controller decisions to the existing Dream Corridor scene (``app.schemas.feedback.FeedbackAction``).

Design constraints: no strobing (light stability kept high), wall distortion kept low, prompts come from the
existing deterministic templates. Generative scene/guidance variations run asynchronously *outside* the control
loop, are validated against bounds and a text allow-list, and fall back to deterministic templates.
"""
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Protocol

from pydantic import BaseModel, Field

from app.multimodal.controller import Decision, FeedbackParams
from app.schemas.feedback import FeedbackAction
from app.services.feedback_policy_engine import PROMPTS

MAX_LIGHT_INSTABILITY = 0.2
MAX_WALL_DISTORTION = 0.2


class CorridorAction(BaseModel):
    action_id: str
    t: float
    controller_state: str
    policy: str
    policy_version: str
    triggering_estimate: dict
    confidence: float
    safety_decision: list[dict]
    delivered: bool
    probe_trial: bool = False
    cue_fade_level: float = Field(default=0.0, ge=0, le=1)
    audio: dict
    scene: FeedbackAction
    participant_rating: dict | None = None


def to_scene(session_id: str, window_index: int, p: FeedbackParams, cue_cap: float = 1.0,
             probe_trial: bool = False) -> FeedbackAction:
    cue = 0.0 if probe_trial else min(p.visual_cue_strength, cue_cap)
    c = p.scene_complexity
    clarity = 0.3 + 0.6 * cue
    return FeedbackAction(
        session_id=session_id, timestamp=datetime.now(timezone.utc), window_index=window_index,
        action_id=f"{session_id}:{window_index}",
        scene_clarity=clarity, blur=1.0 - clarity, wall_distortion=min(0.1 + 0.1 * c, MAX_WALL_DISTORTION),
        light_stability=1.0 - MAX_LIGHT_INSTABILITY * c * (1 - p.rest_cue), texture_detail=c * cue,
        particle_stability=0.8, door_complexity=max(0.0, c - 0.5) * 2 * cue,
        fog_density=min(1.0, 0.2 + 0.5 * p.rest_cue + 0.3 * (1 - cue)), color_saturation=0.3 + 0.5 * cue,
        breathing_cue_strength=max(p.rest_cue, 0.5 * p.audio_guidance),
        prompt_text=PROMPTS.get(p.prompt_key, PROMPTS["default"]),
        reason="probe_trial_cues_removed" if probe_trial else f"policy_prompt:{p.prompt_key}",
    )


def corridor_action(session_id: str, d: Decision, cue_cap: float = 1.0, probe_trial: bool = False) -> CorridorAction:
    p = FeedbackParams(**d.applied)
    shown = p if d.delivered else FeedbackParams()
    return CorridorAction(
        action_id=d.action_id, t=d.t, controller_state=d.controller_state.value, policy=d.policy,
        policy_version=d.policy_version, triggering_estimate=d.estimate_summary, confidence=d.confidence,
        safety_decision=d.safety_findings, delivered=d.delivered, probe_trial=probe_trial,
        cue_fade_level=1.0 - cue_cap,
        audio={"guidance_level": 0.0 if probe_trial else shown.audio_guidance, "ambient_level": shown.ambient_audio,
               "script_id": shown.prompt_key, "spatialized": True},
        scene=to_scene(session_id, d.tick, shown, cue_cap, probe_trial),
    )


class SceneVariation(BaseModel):
    variation_id: str
    palette: str
    ambient_sound: str
    guidance_text: str
    complexity_offset: float = Field(ge=-0.1, le=0.1)
    source: str


ALLOWED_PALETTES = ("dawn", "dusk", "stone", "forest", "sea")
ALLOWED_SOUNDS = ("rain", "wind", "distant_waves", "soft_hum", "silence")
BANNED_TEXT = re.compile(
    r"(you are (now )?(dreaming|asleep)|this is real|leave your body|cannot tell|lose yourself|cure|diagnos|"
    r"read (your|my) mind|decod)", re.IGNORECASE)
TEMPLATES = [
    "Notice the texture of the floor beneath you. Keep it simple.",
    "Let one wall become a little clearer, then rest.",
    "Hold a single object in the corridor and keep its colour steady.",
    "Listen to the ambient sound and let the corridor stay calm.",
    "Breathe out slowly. You can open your eyes at any time.",
]


class VariationProvider(Protocol):
    async def generate(self, seed: int) -> dict: ...


class DeterministicVariationProvider:
    async def generate(self, seed: int) -> dict:
        return {"variation_id": f"det-{seed}", "palette": ALLOWED_PALETTES[seed % len(ALLOWED_PALETTES)],
                "ambient_sound": ALLOWED_SOUNDS[seed % len(ALLOWED_SOUNDS)],
                "guidance_text": TEMPLATES[seed % len(TEMPLATES)], "complexity_offset": 0.0}


def validate_variation(raw: dict, source: str) -> SceneVariation:
    v = SceneVariation(**{**raw, "source": source})
    if v.palette not in ALLOWED_PALETTES or v.ambient_sound not in ALLOWED_SOUNDS:
        raise ValueError("variation outside allowed palette/sound set")
    if BANNED_TEXT.search(v.guidance_text) or len(v.guidance_text) > 200:
        raise ValueError("guidance text failed safety filter")
    return v


class VariationCache:
    """Pre-generates variations before/between trials. ``get`` never awaits and never blocks the control loop."""

    def __init__(self, provider: VariationProvider | None = None, timeout_s: float = 2.0) -> None:
        self.provider = provider
        self.timeout_s = timeout_s
        self.fallback = DeterministicVariationProvider()
        self._cache: dict[int, SceneVariation] = {}
        self.events: list[dict] = []

    async def prefetch(self, seeds: list[int]) -> None:
        for s in seeds:
            if self.provider is not None:
                try:
                    raw = await asyncio.wait_for(self.provider.generate(s), self.timeout_s)
                    self._cache[s] = validate_variation(raw, "generative")
                    continue
                except Exception as e:  # noqa: BLE001
                    self.events.append({"seed": s, "fallback_reason": type(e).__name__})
            self._cache[s] = validate_variation(await self.fallback.generate(s), "deterministic")

    def get(self, seed: int) -> SceneVariation:
        if seed in self._cache:
            return self._cache[seed]
        raw = {"variation_id": f"det-{seed}", "palette": ALLOWED_PALETTES[seed % 5],
               "ambient_sound": ALLOWED_SOUNDS[seed % 5], "guidance_text": TEMPLATES[seed % 5],
               "complexity_offset": 0.0}
        return validate_variation(raw, "deterministic")
