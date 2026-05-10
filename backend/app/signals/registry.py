from app.signals.base import SignalProvider
from app.signals.dataset_replay_provider import DatasetReplayProvider
from app.signals.lsl_provider_stub import LSLProviderStub
from app.signals.lsl_real_provider import RealLSLProvider
from app.signals.manual_provider import ManualSignalProvider
from app.signals.replay_provider import ReplaySignalProvider
from app.signals.simulated_provider import SimulatedSignalProvider

_PROVIDERS: dict[str, SignalProvider] = {
    "simulated.default": SimulatedSignalProvider(),
    "manual.self_report_only": ManualSignalProvider(),
    "replay.event_log": ReplaySignalProvider(),
    "lsl.stub": LSLProviderStub(),
    "lsl.real": RealLSLProvider(),
    "dataset.replay": DatasetReplayProvider(),
}


def list_providers() -> list[SignalProvider]:
    return list(_PROVIDERS.values())


def get_provider(provider_id: str) -> SignalProvider | None:
    return _PROVIDERS.get(provider_id)
