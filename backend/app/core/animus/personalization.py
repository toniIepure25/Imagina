"""ANIMUS local-first personalization.

``AnimusUserModel`` learns ONLY from prior interaction how to run the loop better for a given user: which
feedback channels are reliable, which attributes are hard, typical correction direction, response
reliability, fatigue pattern, preferred iteration length. It never infers clinical traits, personality, or
intelligence, and stores no neural identity fingerprint. State is a plain local dict (local-first); reset
and delete are first-class. Cold start returns defaults.
"""
from __future__ import annotations

from dataclasses import dataclass, field

USER_MODEL_VERSION = "animus-usermodel-v1"

# Explicitly forbidden inference targets (guarded by a test).
FORBIDDEN_INFERENCES = ("iq", "intelligence", "personality", "diagnosis", "clinical",
                        "disorder", "identity_fingerprint")


@dataclass
class AnimusUserModel:
    user_id: str
    channel_reliability: dict[str, float] = field(default_factory=dict)
    difficult_attributes: dict[str, float] = field(default_factory=dict)
    correction_direction: dict[str, int] = field(default_factory=dict)
    response_reliability: float = 0.5
    fatigue_onset_iteration: float = 6.0
    preferred_iteration_length: int = 6
    sessions_seen: int = 0
    version: str = USER_MODEL_VERSION

    # --- lifecycle -------------------------------------------------------------
    @classmethod
    def cold_start(cls, user_id: str) -> "AnimusUserModel":
        return cls(user_id=user_id)

    def reset(self) -> None:
        self.channel_reliability.clear()
        self.difficult_attributes.clear()
        self.correction_direction.clear()
        self.response_reliability = 0.5
        self.fatigue_onset_iteration = 6.0
        self.preferred_iteration_length = 6
        self.sessions_seen = 0

    # --- learning (EMA over sessions) -----------------------------------------
    def update_from_session(self, session_stats: dict) -> None:
        """session_stats: {channel_consistency:{ch:float}, attribute_iterations:{attr:int},
        completed_iterations:int, response_consistency:float, fatigue_onset:int}."""
        a = 0.3
        for ch, rel in session_stats.get("channel_consistency", {}).items():
            prev = self.channel_reliability.get(ch, 0.5)
            self.channel_reliability[ch] = (1 - a) * prev + a * float(rel)
        for attr, iters in session_stats.get("attribute_iterations", {}).items():
            prev = self.difficult_attributes.get(attr, float(iters))
            self.difficult_attributes[attr] = (1 - a) * prev + a * float(iters)
        if "response_consistency" in session_stats:
            self.response_reliability = (1 - a) * self.response_reliability + \
                a * float(session_stats["response_consistency"])
        if "completed_iterations" in session_stats:
            self.preferred_iteration_length = int(round(
                (1 - a) * self.preferred_iteration_length + a * int(session_stats["completed_iterations"])))
        if "fatigue_onset" in session_stats:
            self.fatigue_onset_iteration = (1 - a) * self.fatigue_onset_iteration + \
                a * float(session_stats["fatigue_onset"])
        self.sessions_seen += 1

    # --- recommendations (local, non-clinical) --------------------------------
    def recommend(self) -> dict:
        best_channel = max(self.channel_reliability.items(), key=lambda kv: kv[1])[0] \
            if self.channel_reliability else None
        hard = sorted(self.difficult_attributes.items(), key=lambda kv: -kv[1])[:2]
        return {
            "preferred_channel": best_channel,
            "prioritize_attributes": [a for a, _ in hard],
            "suggested_max_iterations": max(4, min(12, self.preferred_iteration_length)),
            "cooldown_before_iteration": int(round(self.fatigue_onset_iteration)),
        }

    def to_dict(self) -> dict:
        return {"user_id": self.user_id, "version": self.version, "sessions_seen": self.sessions_seen,
                "channel_reliability": {k: round(v, 4) for k, v in self.channel_reliability.items()},
                "difficult_attributes": {k: round(v, 4) for k, v in self.difficult_attributes.items()},
                "response_reliability": round(self.response_reliability, 4),
                "fatigue_onset_iteration": round(self.fatigue_onset_iteration, 4),
                "preferred_iteration_length": self.preferred_iteration_length}
