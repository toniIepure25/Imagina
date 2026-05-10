from app.schemas.features import FeatureVector
from app.services.signal_simulator import SignalSimulator
from app.signals.base import ProviderType


class SimulatedSignalProvider:
    provider_id = "simulated.default"
    provider_type: ProviderType = "simulated"

    def __init__(self, scenario: str = "improving_user", seed: int = 42):
        self.scenario = scenario
        self.seed = seed
        self._sims: dict[str, SignalSimulator] = {}

    async def start(self, session_id: str, **kwargs) -> None:
        scenario = kwargs.get("scenario", self.scenario)
        seed = kwargs.get("seed", self.seed)
        self._sims[session_id] = SignalSimulator(seed=seed, scenario=scenario)

    async def stop(self, session_id: str) -> None:
        self._sims.pop(session_id, None)

    async def next_window(
        self, session_id: str, window_index: int,
        self_report: dict | None = None, total_windows: int = 60,
    ) -> FeatureVector:
        sim = self._sims.setdefault(
            session_id, SignalSimulator(seed=self.seed, scenario=self.scenario)
        )
        _, fv = sim.generate_window(session_id, window_index, self_report, total_windows)
        return fv

    def health(self) -> dict:
        return {
            "status": "ok", "available": True, "provider_id": self.provider_id,
            "session_start_allowed": True, "window_collection_implemented": True,
            "disabled_reason": None,
        }

    def metadata(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "provider_type": self.provider_type,
            "description": "Deterministic simulated EEG-like feature provider for V1/V2 demos.",
            "scenario": self.scenario,
            "seed": self.seed,
            "session_start_allowed": True,
            "window_collection_implemented": True,
            "disabled_reason": None,
        }
