"""Personalized imagery-training curriculum with cue fading, cue-free probe trials and control arms.

Difficulty level is a scheduling variable, not an ability score. Imagery ability is assessed separately on
cue-free probe trials and independent evaluation sessions without feedback, so improvements carried by the
presented visuals themselves are not mistaken for improved voluntary imagery.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np

EXERCISES = [
    {"id": "color_shape", "name": "Simple colour and shape", "sense": "visual", "base": 0},
    {"id": "object", "name": "Single object", "sense": "visual", "base": 1},
    {"id": "object_rotation", "name": "Object rotation", "sense": "visual", "base": 2, "objective_answer": True},
    {"id": "scene_construction", "name": "Spatial scene construction", "sense": "visual", "base": 3},
    {"id": "multi_object", "name": "Multi-object scene", "sense": "visual", "base": 4},
    {"id": "detail_maintenance", "name": "Visual detail maintenance", "sense": "visual", "base": 4},
    {"id": "navigation", "name": "Scene navigation", "sense": "visual", "base": 5},
    {"id": "auditory", "name": "Auditory imagery", "sense": "auditory", "base": 2},
    {"id": "multisensory", "name": "Multisensory imagery", "sense": "multisensory", "base": 5},
    {"id": "switching", "name": "Voluntary imagery switching", "sense": "visual", "base": 6},
    {"id": "distraction", "name": "Stability under distraction", "sense": "visual", "base": 7},
]
ARMS = ("adaptive_feedback", "sham_feedback", "no_feedback")
N_LEVELS = 8


def assign_arm(participant_pseudo_id: str, study_seed: str, arms: tuple[str, ...] = ARMS) -> dict:
    digest = hashlib.sha256(f"{study_seed}:{participant_pseudo_id}".encode()).hexdigest()
    return {"arm": arms[int(digest, 16) % len(arms)], "allocation_hash": digest[:16],
            "method": "sha256(study_seed:participant) mod n_arms"}


def cue_cap_for_level(level: int) -> float:
    return float(np.clip(1.0 - level / (N_LEVELS - 1), 0.0, 1.0))


@dataclass
class TrialOutcome:
    exercise_id: str
    level: int
    probe: bool
    vividness: float | None
    accuracy: float | None
    difficulty_rating: float | None
    fatigue: float | None


@dataclass
class Curriculum:
    participant_pseudo_id: str
    arm: str
    levels: dict[str, int] = field(default_factory=lambda: {e["id"]: 0 for e in EXERCISES})
    streak: dict[str, int] = field(default_factory=dict)
    trials_since_rest: int = 0
    probe_every: int = 5
    rest_every: int = 8
    history: list[TrialOutcome] = field(default_factory=list)
    trial_count: int = 0

    def next_trial(self, exercise_id: str) -> dict:
        self.trial_count += 1
        if self.trials_since_rest >= self.rest_every:
            self.trials_since_rest = 0
            return {"type": "rest", "duration_s": 60, "reason": "scheduled recovery period"}
        probe = self.trial_count % self.probe_every == 0
        lvl = self.levels[exercise_id]
        return {"type": "trial", "exercise_id": exercise_id, "difficulty_level": lvl, "probe": probe,
                "cue_cap": 0.0 if probe else cue_cap_for_level(lvl),
                "feedback": "none" if probe or self.arm == "no_feedback" else self.arm,
                "note": "difficulty_level is a schedule, not an ability measure"}

    def record(self, o: TrialOutcome) -> None:
        self.history.append(o)
        self.trials_since_rest += 1
        if o.probe:
            return
        if o.fatigue is not None and o.fatigue > 0.7:
            self.streak[o.exercise_id] = 0
            return
        score = o.accuracy if o.accuracy is not None else o.vividness
        if score is None:
            return
        too_hard = o.difficulty_rating is not None and o.difficulty_rating > 0.8
        if score >= 0.7 and not too_hard:
            self.streak[o.exercise_id] = self.streak.get(o.exercise_id, 0) + 1
            if self.streak[o.exercise_id] >= 2:
                self.levels[o.exercise_id] = min(self.levels[o.exercise_id] + 1, N_LEVELS - 1)
                self.streak[o.exercise_id] = 0
        elif score < 0.4 or too_hard:
            self.levels[o.exercise_id] = max(self.levels[o.exercise_id] - 1, 0)
            self.streak[o.exercise_id] = 0

    def report(self) -> dict:
        probes = [o for o in self.history if o.probe]
        trained = [o for o in self.history if not o.probe]

        def mean(xs, attr):
            v = [getattr(x, attr) for x in xs if getattr(x, attr) is not None]
            return float(np.mean(v)) if v else None

        return {
            "participant_pseudo_id": self.participant_pseudo_id, "arm": self.arm,
            "difficulty_levels": dict(self.levels),
            "cue_free_probe_vividness": mean(probes, "vividness"), "cue_free_probe_accuracy": mean(probes, "accuracy"),
            "cued_trial_vividness": mean(trained, "vividness"), "n_probes": len(probes), "n_trials": len(trained),
            "interpretation": ("Cue-free probe outcomes are the transfer measure. Cued-trial ratings may be "
                               "inflated by the presented visuals. Arm differences need the randomized protocol."),
        }
