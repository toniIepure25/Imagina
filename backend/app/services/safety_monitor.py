"""
Safety monitor — triggers warnings when proxy metrics indicate risk.

This is NOT medical advice.  Users should stop if they feel distress.
"""

import re

from app.core.time import utcnow
from app.schemas.metrics import StateEstimate
from app.schemas.safety import SafetyEvent

DISSOCIATION_KEYWORDS = re.compile(
    r"\b(dizzy|unreal|panic|detached|scared|dissociat|nausea|faint)\b",
    re.IGNORECASE,
)


class SafetyMonitor:
    def __init__(self, max_duration_s: int = 1200):
        self.max_duration_s = max_duration_s
        self.consecutive_high_fatigue = 0
        self.consecutive_low_quality = 0

    def check(
        self,
        session_id: str,
        state: StateEstimate,
        self_report: dict | None = None,
        session_elapsed_s: float = 0.0,
        signal_quality: float = 1.0,
    ) -> list[SafetyEvent]:
        events: list[SafetyEvent] = []
        sr = self_report or {}
        now = utcnow()

        # --- fatigue_high ---
        if state.fatigue > 0.80:
            self.consecutive_high_fatigue += 1
        else:
            self.consecutive_high_fatigue = 0

        if self.consecutive_high_fatigue >= 2:
            events.append(SafetyEvent(
                session_id=session_id,
                timestamp=now,
                severity="warning",
                event_type="fatigue_high",
                message="Fatigue estimate has been high for multiple windows. Consider taking a break.",
                recommended_action="pause_or_simplify",
            ))

        # --- overeffort ---
        if sr.get("effort", 5) > 8 and sr.get("fatigue", 3) > 6:
            events.append(SafetyEvent(
                session_id=session_id,
                timestamp=now,
                severity="warning",
                event_type="overeffort",
                message="High effort combined with rising fatigue. Reduce effort and breathe.",
                recommended_action="simplify_and_breathe",
            ))

        # --- session_too_long ---
        if session_elapsed_s > self.max_duration_s:
            events.append(SafetyEvent(
                session_id=session_id,
                timestamp=now,
                severity="stop",
                event_type="session_too_long",
                message=f"Session has exceeded {self.max_duration_s // 60} minutes. Ending session.",
                recommended_action="stop_session",
            ))

        # --- signal_unstable ---
        if signal_quality < 0.25:
            self.consecutive_low_quality += 1
        else:
            self.consecutive_low_quality = 0

        if self.consecutive_low_quality >= 3:
            events.append(SafetyEvent(
                session_id=session_id,
                timestamp=now,
                severity="info",
                event_type="signal_unstable",
                message="Simulated signal quality is persistently low. Metrics may be unreliable.",
                recommended_action="acknowledge",
            ))

        # --- dissociation_warning ---
        notes = sr.get("notes", "") or ""
        if notes and DISSOCIATION_KEYWORDS.search(notes):
            events.append(SafetyEvent(
                session_id=session_id,
                timestamp=now,
                severity="stop",
                event_type="dissociation_warning",
                message=(
                    "Your notes mention discomfort. Please stop the session if you feel "
                    "distress. This is not medical advice — seek professional help if needed."
                ),
                recommended_action="stop_session",
            ))

        return events
