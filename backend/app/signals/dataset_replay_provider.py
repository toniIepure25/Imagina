"""Signal provider that replays pre-loaded dataset windows (fixture or real EEG)."""

from app.datasets.loaders import load_windows
from app.schemas.features import FeatureVector
from app.signals.base import ProviderType


class DatasetReplayProvider:
    provider_id = "dataset.replay"
    provider_type: ProviderType = "dataset"

    def __init__(self):
        self._windows: list = []
        self._session_windows: dict[str, list] = {}
        self._session_index: dict[str, int] = {}
        self._loaded = False
        self._dataset_id = "fixture"
        self._is_fallback = True

    async def start(self, session_id: str, **kwargs) -> None:
        self._dataset_id = kwargs.get("dataset_id", "fixture")
        if not self._loaded:
            ds_id = kwargs.get("dataset_id", "fixture")
            max_w = kwargs.get("max_windows", 30)
            self._windows = load_windows(ds_id, max_windows=max_w)
            self._dataset_id = ds_id
            self._loaded = True
        self._session_windows[session_id] = list(self._windows)
        self._session_index[session_id] = 0

    async def stop(self, session_id: str) -> None:
        self._session_windows.pop(session_id, None)
        self._session_index.pop(session_id, None)

    async def next_window(
        self, session_id: str, window_index: int,
        self_report: dict | None = None, total_windows: int = 60,
    ) -> FeatureVector:
        windows = self._session_windows.get(session_id, [])
        idx = self._session_index.get(session_id, 0)
        if idx >= len(windows):
            raise RuntimeError(f"No more dataset windows available for session {session_id}")
        window = windows[idx]
        self._session_index[session_id] = idx + 1
        from app.services.feature_engine import FeatureEngine
        engine = FeatureEngine()
        return engine.process_eeg_window(window, self_report)

    def health(self) -> dict:
        return {
            "status": "dataset_ready" if self._loaded else "not_loaded",
            "available": self._loaded,
            "provider_id": self.provider_id,
            "provider_type": self.provider_type,
            "dataset_available": self._loaded,
            "dataset_name": self._dataset_id,
            "windows_available": len(self._windows),
            "real_signal": self._dataset_id != "fixture",
            "fallback_fixture": self._is_fallback,
            "session_start_allowed": self._loaded and len(self._windows) > 0,
        }

    def metadata(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "provider_type": self.provider_type,
            "description": "Replays pre-loaded dataset windows through the closed-loop pipeline.",
            "window_collection_implemented": True,
            "session_start_allowed": False,
            "clinical_use": False,
            "raw_persistence_default": False,
            "real_signal_supported": True,
            "dataset_id": self._dataset_id,
        }
