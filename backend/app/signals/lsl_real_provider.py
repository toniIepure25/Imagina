import asyncio
import importlib.util
import time

from app.core.config import settings
from app.core.time import utcnow
from app.schemas.features import FeatureVector
from app.schemas.signals import EEGSampleWindow
from app.signals.base import ProviderType


class _SessionState:
    def __init__(self, inlet, info):
        self.inlet = inlet
        self.info = info


class RealLSLProvider:
    provider_id = "lsl.real"
    provider_type: ProviderType = "lsl"

    def __init__(self):
        self._sessions: dict[str, _SessionState] = {}
        self._has_pylsl = importlib.util.find_spec("pylsl") is not None
        self._last_streams: list[dict] = []

    async def start(self, session_id: str, **kwargs) -> None:
        if not self._has_pylsl:
            raise RuntimeError("pylsl is not installed. Cannot start LSL session.")
        streams = self.discover_streams()
        if not streams:
            raise RuntimeError("No LSL streams found. Cannot start session.")
        stream_name = kwargs.get("stream_name")
        selected = next((s for s in streams if s["name"] == stream_name), streams[0]) if stream_name else streams[0]
        import pylsl
        resolved = pylsl.resolve_streams(timeout=2.0)
        target = None
        for s in resolved:
            if s.name() == selected["name"] and s.type() == selected["type"]:
                target = s
                break
        if target is None:
            target = resolved[0] if resolved else None
        if target is None:
            raise RuntimeError("Could not resolve selected LSL stream.")
        inlet = pylsl.StreamInlet(target)
        self._sessions[session_id] = _SessionState(inlet=inlet, info=selected)

    async def stop(self, session_id: str) -> None:
        state = self._sessions.pop(session_id, None)
        if state is not None:
            try:
                state.inlet.close_stream()
            except Exception:
                pass

    async def next_window(
        self, session_id: str, window_index: int,
        self_report: dict | None = None, total_windows: int = 60,
    ) -> FeatureVector:
        state = self._sessions.get(session_id)
        if state is None:
            raise RuntimeError(
                "No LSL session active. Call start() before next_window()."
            )
        info = state.info
        sampling_rate = int(info.get("nominal_srate", 256))
        window_samples = sampling_rate * 2
        samples: list[list[float]] = []
        pull = state.inlet.pull_sample
        timeout = max(0.0, (window_samples / sampling_rate) * 3)

        deadline = time.monotonic() + timeout
        while len(samples) < window_samples and time.monotonic() < deadline:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: pull(timeout=0.0)
            )
            sample, timestamp = result if result else (None, None)
            if sample is None:
                break
            if isinstance(sample, (list, tuple)):
                samples.append(list(sample))
            else:
                samples.append([sample])

        if len(samples) < max(4, window_samples // 10):
            raise RuntimeError(
                f"Insufficient LSL samples collected ({len(samples)}/{window_samples}). "
                "Stream may be disconnected or too slow."
            )
        dropped = window_samples - len(samples) if len(samples) < window_samples else 0
        channel_count = info.get("channel_count", len(samples[0]) if samples else 0)
        channel_names = [f"ch{i}" for i in range(channel_count)]

        eeg = EEGSampleWindow(
            session_id=session_id,
            timestamp=utcnow(),
            window_index=window_index,
            sampling_rate_hz=sampling_rate,
            duration_seconds=2.0,
            channels=channel_names,
            samples=samples,
            simulated=False,
            generator_version="lsl_real_v3a",
            provider_id=self.provider_id,
            provider_type=self.provider_type,
            stream_name=info.get("name"),
            stream_type=info.get("type"),
            source_id=info.get("source_id"),
            nominal_sampling_rate_hz=sampling_rate,
            effective_sampling_rate_hz=sampling_rate,
            channel_names=channel_names,
            channel_count=channel_count,
            dropped_samples=dropped,
            raw_persisted=False,
            preprocessing_version="v3a",
        )

        from app.services.feature_engine import FeatureEngine
        engine = FeatureEngine()
        return engine.process_eeg_window(eeg, self_report)

    def health(self) -> dict:
        if not self._has_pylsl:
            return {
                "status": "unavailable",
                "available": False,
                "connected": False,
                "provider_id": self.provider_id,
                "provider_type": self.provider_type,
                "pylsl_installed": False,
                "stream_found": False,
                "window_collection_implemented": True,
                "session_start_allowed": False,
                "disabled_reason": "pylsl is not installed.",
            }
        streams = self.discover_streams()
        experimental_enabled = settings.enable_experimental_lsl
        if not streams:
            return {
                "status": "no_stream_found",
                "available": True,
                "connected": False,
                "provider_id": self.provider_id,
                "provider_type": self.provider_type,
                "pylsl_installed": True,
                "stream_found": False,
                "window_collection_implemented": True,
                "session_start_allowed": False,
                "disabled_reason": (
                    "No LSL streams found."
                    if experimental_enabled
                    else "Experimental LSL sessions are disabled by default. Set IMAGINA_ENABLE_EXPERIMENTAL_LSL=true."
                ),
                "stream_name": None,
                "stream_type": None,
                "sampling_rate_hz": None,
                "channel_count": None,
            }
        s = streams[0]
        return {
            "status": "stream_found",
            "available": True,
            "connected": False,
            "provider_id": self.provider_id,
            "provider_type": self.provider_type,
            "pylsl_installed": True,
            "stream_found": True,
            "stream_name": s["name"],
            "stream_type": s["type"],
            "sampling_rate_hz": s["nominal_srate"],
            "channel_count": s["channel_count"],
            "window_collection_implemented": True,
            "session_start_allowed": experimental_enabled,
            "disabled_reason": (
                None if experimental_enabled
                else "Experimental LSL sessions are disabled by default. Set IMAGINA_ENABLE_EXPERIMENTAL_LSL=true."
            ),
        }

    def metadata(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "provider_type": self.provider_type,
            "description": (
                "Experimental real LSL/EEG provider. Requires pylsl. "
                "Window collection supports mocked LSL streams."
            ),
            "real_signal_supported": True,
            "clinical_use": False,
            "raw_persistence_default": False,
            "requires_optional_dependency": "pylsl",
            "window_collection_implemented": True,
            "pylsl_installed": self._has_pylsl,
            "implementation_version": "v3a_mock_first",
        }

    def discover_streams(self) -> list[dict]:
        if not self._has_pylsl:
            return []
        try:
            import pylsl
            streams = pylsl.resolve_streams(timeout=1.0)
            self._last_streams = [
                {
                    "name": s.name(),
                    "type": s.type(),
                    "source_id": s.source_id(),
                    "channel_count": s.channel_count(),
                    "nominal_srate": s.nominal_srate(),
                }
                for s in streams
            ]
            return list(self._last_streams)
        except Exception:
            return []
