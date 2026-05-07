from app.core.time import utcnow
from app.schemas.features import FeatureVector
from app.signals.base import ProviderType


class ManualSignalProvider:
    provider_id = "manual.self_report_only"
    provider_type: ProviderType = "manual"

    async def start(self, session_id: str) -> None:
        return None

    async def stop(self, session_id: str) -> None:
        return None

    async def next_window(self, session_id: str, window_index: int) -> FeatureVector:
        return FeatureVector(
            session_id=session_id,
            timestamp=utcnow(),
            window_index=window_index,
            theta_power=0.4,
            alpha_power=0.45,
            beta_power=0.32,
            theta_beta_ratio=1.25,
            alpha_stability=0.5,
            signal_quality=0.5,
            simulated_imagery_strength=0.5,
            behavioral_stability=0.5,
            reaction_time_ms=500,
        )

    def health(self) -> dict:
        return {"status": "ok", "available": True, "provider_id": self.provider_id}

    def metadata(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "provider_type": self.provider_type,
            "description": "Safe self-report-only fallback provider with neutral feature defaults.",
        }
