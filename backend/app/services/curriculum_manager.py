"""
Adaptive curriculum with 8 levels for the Dream Corridor task.

Staircase rules:
  - Advance after 3 consecutive successful windows
  - Regress after 1 major failure window
  - Fatigue cooldown overrides normal regression
"""

from app.core.time import utcnow
from app.schemas.curriculum import CurriculumState
from app.schemas.metrics import IQIEstimate, PIDEstimate, StateEstimate

LEVELS = [
    {
        "level": 1, "name": "Breath + Fixation",
        "iqi": None, "pid": None, "attention": 0.55, "max_fatigue": 0.50,
    },
    {
        "level": 2, "name": "Simple Corridor Shape",
        "iqi": 0.55, "pid": 0.55, "attention": None, "max_fatigue": None,
    },
    {
        "level": 3, "name": "Stable Walls",
        "iqi": 0.60, "pid": 0.50, "attention": None, "max_fatigue": None,
    },
    {
        "level": 4, "name": "Lighting Stability",
        "iqi": 0.65, "pid": 0.45, "attention": None, "max_fatigue": None,
    },
    {
        "level": 5, "name": "Texture Detail",
        "iqi": 0.70, "pid": 0.40, "attention": None, "max_fatigue": None,
    },
    {
        "level": 6, "name": "Door Formation",
        "iqi": 0.72, "pid": 0.38, "attention": None, "max_fatigue": None,
    },
    {
        "level": 7, "name": "Memory Room Entry",
        "iqi": 0.75, "pid": 0.35, "attention": None, "max_fatigue": None,
    },
    {
        "level": 8, "name": "Return-to-Scene",
        "iqi": 0.78, "pid": 0.32, "attention": None, "max_fatigue": None,
    },
]

ADVANCE_THRESHOLD = 3
FATIGUE_COOLDOWN = 0.80
MAJOR_FAIL_PID = 0.70
MAJOR_FAIL_IQI = 0.35
MAJOR_FAIL_FATIGUE = 0.75
MAJOR_FAIL_UNCERTAINTY = 0.80


class CurriculumManager:
    def __init__(self, starting_level: int = 1):
        self.current_level = max(1, min(starting_level, 8))
        self.consecutive_successes = 0
        self.consecutive_failures = 0

    def _level_def(self) -> dict:
        return LEVELS[self.current_level - 1]

    def _is_success(
        self, state: StateEstimate, pid: PIDEstimate, iqi: IQIEstimate
    ) -> bool:
        ldef = self._level_def()
        if ldef["attention"] is not None and state.attention_stability < ldef["attention"]:
            return False
        if ldef["max_fatigue"] is not None and state.fatigue > ldef["max_fatigue"]:
            return False
        if ldef["iqi"] is not None and iqi.iqi < ldef["iqi"]:
            return False
        if ldef["pid"] is not None and pid.pid > ldef["pid"]:
            return False
        return True

    def _is_major_failure(
        self, state: StateEstimate, pid: PIDEstimate, iqi: IQIEstimate
    ) -> bool:
        return (
            pid.pid > MAJOR_FAIL_PID
            or iqi.iqi < MAJOR_FAIL_IQI
            or state.fatigue > MAJOR_FAIL_FATIGUE
            or state.uncertainty > MAJOR_FAIL_UNCERTAINTY
        )

    def update(
        self,
        session_id: str,
        state: StateEstimate,
        pid: PIDEstimate,
        iqi: IQIEstimate,
    ) -> CurriculumState:
        reason = ""

        if state.fatigue > FATIGUE_COOLDOWN:
            if self.current_level > 1:
                self.current_level -= 1
            self.consecutive_successes = 0
            self.consecutive_failures = 0
            reason = "fatigue_cooldown"
        elif self._is_major_failure(state, pid, iqi):
            self.consecutive_failures += 1
            self.consecutive_successes = 0
            if self.current_level > 1:
                self.current_level -= 1
            reason = "major_failure_regress"
        elif self._is_success(state, pid, iqi):
            self.consecutive_successes += 1
            self.consecutive_failures = 0
            if self.consecutive_successes >= ADVANCE_THRESHOLD and self.current_level < 8:
                self.current_level += 1
                self.consecutive_successes = 0
                reason = "advance"
            else:
                reason = f"success_{self.consecutive_successes}/{ADVANCE_THRESHOLD}"
        else:
            self.consecutive_successes = 0
            reason = "below_threshold"

        return CurriculumState(
            session_id=session_id,
            timestamp=utcnow(),
            current_level=self.current_level,
            level_name=self._level_def()["name"],
            consecutive_successes=self.consecutive_successes,
            consecutive_failures=self.consecutive_failures,
            difficulty=round(self.current_level / 8.0, 3),
            reason=reason,
        )
