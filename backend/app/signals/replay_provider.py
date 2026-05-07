from datetime import datetime

from app.schemas.features import FeatureVector
from app.signals.base import ProviderType
from app.storage import event_store


class ReplaySignalProvider:
    provider_id = "replay.event_log"
    provider_type: ProviderType = "replay"

    async def start(self, session_id: str) -> None:
        return None

    async def stop(self, session_id: str) -> None:
        return None

    async def next_window(self, session_id: str, window_index: int) -> FeatureVector:
        events = await event_store.list_events(session_id, event_type="feature_vector")
        for event in events:
            if event.payload.get("window_index") == window_index:
                payload = dict(event.payload)
                if isinstance(payload.get("timestamp"), str):
                    payload["timestamp"] = datetime.fromisoformat(payload["timestamp"])
                return FeatureVector(**payload)
        raise ValueError(f"No replay feature_vector found for window {window_index}")

    def health(self) -> dict:
        return {"status": "ok", "available": True, "provider_id": self.provider_id}

    def metadata(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "provider_type": self.provider_type,
            "description": "Reads feature vectors from persisted event logs for deterministic replay validation.",
        }
