from typing import Literal, Protocol

from app.schemas.features import FeatureVector

ProviderType = Literal["simulated", "replay", "manual", "lsl_stub"]


class SignalProvider(Protocol):
    provider_id: str
    provider_type: ProviderType

    async def start(self, session_id: str) -> None: ...

    async def stop(self, session_id: str) -> None: ...

    async def next_window(self, session_id: str, window_index: int) -> FeatureVector: ...

    def health(self) -> dict: ...

    def metadata(self) -> dict: ...
