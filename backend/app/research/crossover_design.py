"""Frozen versioned crossover design for scientific studies.

A single design object drives simulation, runtime, oracle, analysis, and replay.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from app.research.psychophysics.common import StimulusSpec
from app.research.rng_registry import derive_seed

DESIGN_VERSION = "1.0"

CONDITIONS = ["adaptive", "fixed", "yoked"]

WILLIAMS_SEQUENCES = [
    ["adaptive", "fixed", "yoked"],
    ["fixed", "yoked", "adaptive"],
    ["yoked", "adaptive", "fixed"],
    ["yoked", "fixed", "adaptive"],
    ["adaptive", "yoked", "fixed"],
    ["fixed", "adaptive", "yoked"],
]

TASK_FAMILIES = ["feature_reconstruction", "imagery_manipulation", "delayed_imagery", "perceptual_control"]

DEFAULT_DELAYS = {
    "feature_reconstruction": 0.0,
    "imagery_manipulation": 0.0,
    "delayed_imagery": 3.0,
    "perceptual_control": 0.0,
}


@dataclass
class TrialSlot:
    task_family: str
    trial_index: int
    target: StimulusSpec
    delay_s: float
    is_perceptual_control: bool
    difficulty: float = 1.0
    transformation_type: str = "none"
    transformation_magnitude: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_family": self.task_family,
            "trial_index": self.trial_index,
            "target": self.target.to_dict(),
            "delay_s": self.delay_s,
            "is_perceptual_control": self.is_perceptual_control,
            "difficulty": self.difficulty,
            "transformation_type": self.transformation_type,
            "transformation_magnitude": self.transformation_magnitude,
        }


@dataclass
class SessionBlock:
    participant_id: str
    period: int
    condition: str
    sequence_index: int
    prev_condition: str | None
    baseline_precision: float
    calibration_id: str
    washout_minutes: int
    trials: list[TrialSlot] = field(default_factory=list)
    negative_control_trials: list[TrialSlot] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "participant_id": self.participant_id,
            "period": self.period,
            "condition": self.condition,
            "sequence_index": self.sequence_index,
            "prev_condition": self.prev_condition,
            "baseline_precision": self.baseline_precision,
            "calibration_id": self.calibration_id,
            "washout_minutes": self.washout_minutes,
            "trials": [t.to_dict() for t in self.trials],
            "negative_control_trials": [t.to_dict() for t in self.negative_control_trials],
        }


@dataclass
class CrossoverDesign:
    design_id: str
    version: str = DESIGN_VERSION
    n_participants: int = 18
    n_sessions: int = 3
    trials_per_task: int = 5
    washout_minutes: int = 10
    conditions: list[str] = field(default_factory=lambda: list(CONDITIONS))
    task_families: list[str] = field(default_factory=lambda: list(TASK_FAMILIES))
    sessions: list[SessionBlock] = field(default_factory=list)
    seed: int = 42
    carryover_definition: str = "previous_condition"
    baseline_block_count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "design_id": self.design_id,
            "version": self.version,
            "n_participants": self.n_participants,
            "n_sessions": self.n_sessions,
            "trials_per_task": self.trials_per_task,
            "washout_minutes": self.washout_minutes,
            "conditions": self.conditions,
            "task_families": self.task_families,
            "seed": self.seed,
            "carryover_definition": self.carryover_definition,
            "baseline_block_count": self.baseline_block_count,
            "n_session_blocks": len(self.sessions),
        }


def _generate_targets(n: int, seed: int) -> list[StimulusSpec]:
    """Generate diverse stimuli for the battery."""
    import random
    rng = random.Random(derive_seed(seed, "stimulus"))
    orientations = [0, 20, 45, 70, 90, 110, 135, 160]
    hues = [0, 45, 90, 135, 180, 225, 270, 315]
    sfs = [1.0, 2.0, 3.0, 5.0, 8.0]
    sizes = [30, 40, 50, 60, 70]
    targets: list[StimulusSpec] = []
    for i in range(n):
        targets.append(StimulusSpec(
            orientation_deg=orientations[i % len(orientations)] + rng.gauss(0, 2),
            hue_deg=hues[i % len(hues)] + rng.gauss(0, 3),
            spatial_frequency_cpd=sfs[i % len(sfs)] * (1 + rng.gauss(0, 0.05)),
            position_x=300 + rng.randint(0, 400),
            position_y=200 + rng.randint(0, 400),
            size=sizes[i % len(sizes)],
        ))
    return targets


TRANSFORMATION_TYPES = ["rotation", "scaling", "translation", "hue_shift"]


def freeze_design(
    n_participants: int = 18,
    n_sessions: int = 3,
    trials_per_task: int = 5,
    seed: int = 42,
    washout_minutes: int = 10,
) -> CrossoverDesign:
    """Create and freeze a complete crossover design."""
    design = CrossoverDesign(
        design_id=f"design-{seed}",
        n_participants=n_participants,
        n_sessions=n_sessions,
        trials_per_task=trials_per_task,
        seed=seed,
        washout_minutes=washout_minutes,
    )

    targets = _generate_targets(trials_per_task * len(TASK_FAMILIES), seed)

    for pi in range(n_participants):
        seq = WILLIAMS_SEQUENCES[pi % len(WILLIAMS_SEQUENCES)]
        pid = f"agent-{seed}-{pi:04d}"
        calib_id = f"calib-{seed}-{pi:04d}"

        for si in range(min(n_sessions, len(seq))):
            cond = seq[si]
            prev = seq[si - 1] if si > 0 else None

            imagery_trials: list[TrialSlot] = []
            nc_trials: list[TrialSlot] = []

            for tf_idx, tf in enumerate(TASK_FAMILIES):
                is_pc = tf == "perceptual_control"
                delay = DEFAULT_DELAYS[tf]

                for ti in range(trials_per_task):
                    target = targets[(tf_idx * trials_per_task + ti) % len(targets)]
                    trans_type = "none"
                    trans_mag = 0.0
                    if tf == "imagery_manipulation":
                        trans_type = TRANSFORMATION_TYPES[ti % len(TRANSFORMATION_TYPES)]
                        trans_mag = 15.0 + ti * 5.0

                    slot = TrialSlot(
                        task_family=tf,
                        trial_index=ti,
                        target=target,
                        delay_s=delay,
                        is_perceptual_control=is_pc,
                        transformation_type=trans_type,
                        transformation_magnitude=trans_mag,
                    )
                    if is_pc:
                        nc_trials.append(slot)
                    else:
                        imagery_trials.append(slot)

            design.sessions.append(SessionBlock(
                participant_id=pid,
                period=si,
                condition=cond,
                sequence_index=pi % len(WILLIAMS_SEQUENCES),
                prev_condition=prev,
                baseline_precision=0.0,
                calibration_id=calib_id,
                washout_minutes=washout_minutes,
                trials=imagery_trials,
                negative_control_trials=nc_trials,
            ))

    return design


def design_hash(design: CrossoverDesign) -> str:
    data = json.dumps(design.to_dict(), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(data.encode()).hexdigest()


def validate_design_balance(design: CrossoverDesign) -> dict[str, Any]:
    """Check balance across condition, period, sequence, task family."""
    from collections import Counter
    cond_counts = Counter(s.condition for s in design.sessions)
    period_counts = Counter(s.period for s in design.sessions)
    seq_counts = Counter(s.sequence_index for s in design.sessions)
    tf_counts: Counter[str] = Counter()
    for s in design.sessions:
        for t in s.trials + s.negative_control_trials:
            tf_counts[t.task_family] += 1

    issues: list[str] = []
    cond_vals = list(cond_counts.values())
    if cond_vals and max(cond_vals) - min(cond_vals) > 2:
        issues.append(f"Condition imbalance: {dict(cond_counts)}")
    period_vals = list(period_counts.values())
    if period_vals and max(period_vals) - min(period_vals) > 2:
        issues.append(f"Period imbalance: {dict(period_counts)}")

    return {
        "condition_balance": dict(cond_counts),
        "period_balance": dict(period_counts),
        "sequence_balance": dict(seq_counts),
        "task_family_balance": dict(tf_counts),
        "issues": issues,
        "balanced": len(issues) == 0,
    }
