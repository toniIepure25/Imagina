from typing import Any, Literal, Protocol

from app.schemas.features import FeatureVector

ProviderType = Literal["simulated", "replay", "manual", "lsl_stub", "lsl", "dataset"]


class SignalProvider(Protocol):
    provider_id: str
    provider_type: ProviderType

    async def start(self, session_id: str, **kwargs: Any) -> None: ...

    async def stop(self, session_id: str) -> None: ...

    async def next_window(
        self, session_id: str, window_index: int,
        self_report: dict | None = None, total_windows: int = 60,
    ) -> FeatureVector: ...

    def health(self) -> dict: ...

    def metadata(self) -> dict: ...
