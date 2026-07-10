from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.schemas.research import FeedbackCondition


class TrialSpec:
    def __init__(
        self,
        trial_index: int,
        stimulus_id: str,
        target_duration_s: float = 120.0,
        inter_trial_interval_s: float = 30.0,
    ):
        self.trial_id = str(uuid.uuid4())
        self.trial_index = trial_index
        self.stimulus_id = stimulus_id
        self.target_duration_s = target_duration_s
        self.inter_trial_interval_s = inter_trial_interval_s
        self.started_at: str | None = None
        self.ended_at: str | None = None
        self.status: str = "pending"

    def start(self) -> None:
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.status = "running"

    def complete(self) -> None:
        self.ended_at = datetime.now(timezone.utc).isoformat()
        self.status = "completed"

    def to_dict(self) -> dict:
        return {
            "trial_id": self.trial_id,
            "trial_index": self.trial_index,
            "stimulus_id": self.stimulus_id,
            "target_duration_s": self.target_duration_s,
            "inter_trial_interval_s": self.inter_trial_interval_s,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "status": self.status,
        }


class TrialScheduler:
    """Generates a sequence of trials for a session within a given condition."""

    def __init__(
        self,
        condition: FeedbackCondition,
        stimulus_ids: list[str],
        trials_per_session: int = 5,
        trial_duration_s: float = 120.0,
        iti_s: float = 30.0,
    ):
        self.condition = condition
        self.stimulus_ids = stimulus_ids
        self.trials_per_session = trials_per_session
        self.trial_duration_s = trial_duration_s
        self.iti_s = iti_s
        self._trials: list[TrialSpec] = []
        self._current_index = 0
        self._generate_trials()

    def _generate_trials(self) -> None:
        n = len(self.stimulus_ids)
        for i in range(self.trials_per_session):
            stim_id = self.stimulus_ids[i % n] if n > 0 else "corridor_default"
            self._trials.append(TrialSpec(
                trial_index=i,
                stimulus_id=stim_id,
                target_duration_s=self.trial_duration_s,
                inter_trial_interval_s=self.iti_s,
            ))

    def has_next(self) -> bool:
        return self._current_index < len(self._trials)

    def current_trial(self) -> TrialSpec | None:
        if self._current_index < len(self._trials):
            return self._trials[self._current_index]
        return None

    def start_trial(self) -> TrialSpec | None:
        trial = self.current_trial()
        if trial:
            trial.start()
        return trial

    def complete_trial(self) -> TrialSpec | None:
        trial = self.current_trial()
        if trial:
            trial.complete()
            self._current_index += 1
        return trial

    def all_trials(self) -> list[dict]:
        return [t.to_dict() for t in self._trials]

    def completed_count(self) -> int:
        return sum(1 for t in self._trials if t.status == "completed")

    def total_estimated_duration_s(self) -> float:
        n = len(self._trials)
        return n * self.trial_duration_s + max(0, n - 1) * self.iti_s
