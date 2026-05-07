import importlib.util

from app.signals.base import ProviderType
from app.signals.manual_provider import ManualSignalProvider


class LSLProviderStub(ManualSignalProvider):
    provider_id = "lsl.stub"
    provider_type: ProviderType = "lsl_stub"

    def health(self) -> dict:
        available = importlib.util.find_spec("pylsl") is not None
        return {
            "status": "available" if available else "not_available",
            "available": available,
            "provider_id": self.provider_id,
            "message": (
                "pylsl is installed"
                if available
                else "pylsl is not installed; LSL integration is a documented V2 extension point."
            ),
        }

    def metadata(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "provider_type": self.provider_type,
            "description": "Optional LSL EEG extension point. Does not require pylsl for V2 simulated operation.",
            "clinical_use": False,
        }
