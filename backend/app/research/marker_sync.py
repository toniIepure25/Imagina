from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class MarkerEvent:
    marker_type: str
    label: str
    timestamp_local: float
    timestamp_lsl: float = 0.0
    sample_index: int = -1
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "marker_type": self.marker_type,
            "label": self.label,
            "timestamp_local": self.timestamp_local,
            "timestamp_lsl": self.timestamp_lsl,
            "sample_index": self.sample_index,
            "metadata": self.metadata,
        }


class MarkerSynchronizer:
    """Synchronizes experiment events with EEG sample timing.

    Records markers (trial_start, trial_end, stimulus_onset, self_report, etc.)
    with both local and LSL timestamps for offline alignment.
    """

    def __init__(self, max_markers: int = 10000):
        self._markers: deque[MarkerEvent] = deque(maxlen=max_markers)
        self._clock_offset: float = 0.0
        self._session_start_local: float = 0.0
        self._session_start_lsl: float = 0.0

    def start_session(self, lsl_time: float = 0.0) -> None:
        self._session_start_local = time.monotonic()
        self._session_start_lsl = lsl_time
        if lsl_time > 0:
            self._clock_offset = lsl_time - self._session_start_local
        self.add_marker("session", "session_start")

    def add_marker(
        self,
        marker_type: str,
        label: str,
        lsl_time: float = 0.0,
        sample_index: int = -1,
        metadata: dict | None = None,
    ) -> MarkerEvent:
        now = time.monotonic()
        if lsl_time == 0.0 and self._clock_offset != 0.0:
            lsl_time = now + self._clock_offset

        event = MarkerEvent(
            marker_type=marker_type,
            label=label,
            timestamp_local=now,
            timestamp_lsl=lsl_time,
            sample_index=sample_index,
            metadata=metadata or {},
        )
        self._markers.append(event)
        return event

    def mark_trial_start(self, trial_index: int, stimulus_id: str = "") -> MarkerEvent:
        return self.add_marker(
            "trial", "trial_start",
            metadata={"trial_index": trial_index, "stimulus_id": stimulus_id},
        )

    def mark_trial_end(self, trial_index: int) -> MarkerEvent:
        return self.add_marker(
            "trial", "trial_end",
            metadata={"trial_index": trial_index},
        )

    def mark_stimulus_onset(self, stimulus_id: str, trial_index: int) -> MarkerEvent:
        return self.add_marker(
            "stimulus", "stimulus_onset",
            metadata={"stimulus_id": stimulus_id, "trial_index": trial_index},
        )

    def mark_self_report(self, trial_index: int, report_data: dict) -> MarkerEvent:
        return self.add_marker(
            "self_report", "self_report_submitted",
            metadata={"trial_index": trial_index, "report": report_data},
        )

    def get_markers(self, marker_type: str | None = None) -> list[dict]:
        if marker_type:
            return [m.to_dict() for m in self._markers if m.marker_type == marker_type]
        return [m.to_dict() for m in self._markers]

    def get_trial_markers(self, trial_index: int) -> list[dict]:
        return [
            m.to_dict() for m in self._markers
            if m.metadata.get("trial_index") == trial_index
        ]

    def export_markers(self) -> list[dict]:
        return [m.to_dict() for m in self._markers]

    @property
    def marker_count(self) -> int:
        return len(self._markers)

    def clear(self) -> None:
        self._markers.clear()
        self._clock_offset = 0.0
