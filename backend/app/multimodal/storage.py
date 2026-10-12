"""Local-first session storage: one chunked HDF5 file per stream plus a JSON manifest.

Nothing here transmits data. Public review bundles exclude raw biosignal arrays unless explicitly requested.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel, Field

from app.multimodal import SCHEMA_VERSION
from app.multimodal.schemas import ChannelSpec, Modality, SampleChunk, StreamInfo


class ConsentRecord(BaseModel):
    protocol_id: str
    consent_version: str
    data_uses: list[str] = Field(default_factory=lambda: ["local_research"])
    allow_raw_export: bool = False
    recorded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RetentionPolicy(BaseModel):
    retain_days: int = Field(default=365, ge=1)
    delete_raw_after_days: int | None = None


def pseudonymize(identifier: str, salt: bytes) -> str:
    if len(salt) < 16:
        raise ValueError("salt must be at least 16 bytes")
    return "P-" + hmac.new(salt, identifier.encode(), hashlib.sha256).hexdigest()[:16]


class StreamRecorder:
    def __init__(self, path: Path, info: StreamInfo, chunk_rows: int = 4096) -> None:
        import h5py

        self.path = path
        self.info = info
        self._h = h5py.File(path, "w")
        n_ch = len(info.channels)
        kw = {"chunks": True, "compression": "gzip", "compression_opts": 4}
        self._data = self._h.create_dataset("data", (0, n_ch), maxshape=(None, n_ch), dtype="f8", **kw)
        self._dev = self._h.create_dataset("device_timestamps", (0,), maxshape=(None,), dtype="f8", **kw)
        self._loc = self._h.create_dataset("local_timestamps", (0,), maxshape=(None,), dtype="f8", **kw)
        self._idx = self._h.create_dataset("sample_indices", (0,), maxshape=(None,), dtype="i8", **kw)
        self._h.attrs["stream_info"] = info.model_dump_json()
        self._h.attrs["schema_version"] = SCHEMA_VERSION
        self.n = 0

    def append(self, chunk: SampleChunk) -> None:
        k = chunk.n_samples
        for ds, arr in ((self._data, chunk.data), (self._dev, chunk.device_timestamps),
                        (self._loc, chunk.local_timestamps), (self._idx, chunk.sample_indices)):
            ds.resize(self.n + k, axis=0)
            ds[self.n:self.n + k] = arr
        self.n += k

    def close(self) -> None:
        if self._h.id.valid:
            self._h.close()


def read_stream_recording(path: Path):
    import h5py

    from app.multimodal.acquisition.replay import LoadedRecording

    with h5py.File(path, "r") as h:
        info = StreamInfo.model_validate_json(h.attrs["stream_info"])
        data = h["data"][:]
        meta = {"format": "IMAGINA-HDF5", "original_source_kind": info.source_kind.value,
                "original_provider": info.provenance.provider_id,
                "device_timestamps": h["device_timestamps"][:], "local_timestamps": h["local_timestamps"][:],
                "sample_indices": h["sample_indices"][:]}
    channels = [ChannelSpec(**c.model_dump()) for c in info.channels]
    return LoadedRecording(Modality(info.modality), info.nominal_rate_hz, channels, data, Path(path), metadata=meta)


class SessionStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def session_dir(self, session_id: str) -> Path:
        if not session_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError("invalid session id")
        return self.root / session_id

    def create_session(self, session_id: str, participant_pseudo_id: str, consent: ConsentRecord | None,
                       retention: RetentionPolicy | None = None, extra: dict[str, Any] | None = None) -> Path:
        d = self.session_dir(session_id)
        (d / "streams").mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema_version": SCHEMA_VERSION, "session_id": session_id,
            "participant_pseudo_id": participant_pseudo_id,
            "consent": consent.model_dump() if consent else None,
            "retention": (retention or RetentionPolicy()).model_dump(),
            "created_at": datetime.now(timezone.utc).isoformat(), "streams": {}, **(extra or {}),
        }
        self._write_manifest(session_id, manifest)
        return d

    def recorder(self, session_id: str, info: StreamInfo) -> StreamRecorder:
        safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in info.stream_id)
        path = self.session_dir(session_id) / "streams" / f"{safe}.h5"
        m = self.manifest(session_id)
        m["streams"][info.stream_id] = {"file": path.name, "modality": info.modality.value,
                                        "source_kind": info.source_kind.value}
        self._write_manifest(session_id, m)
        return StreamRecorder(path, info)

    def write_json(self, session_id: str, name: str, obj: Any) -> Path:
        p = self.session_dir(session_id) / name
        p.write_text(json.dumps(obj, indent=2, default=_default))
        return p

    def write_jsonl(self, session_id: str, name: str, rows: list[dict]) -> Path:
        p = self.session_dir(session_id) / name
        with open(p, "w") as fh:
            for r in rows:
                fh.write(json.dumps(r, default=_default) + "\n")
        return p

    def manifest(self, session_id: str) -> dict:
        return json.loads((self.session_dir(session_id) / "manifest.json").read_text())

    def _write_manifest(self, session_id: str, m: dict) -> None:
        (self.session_dir(session_id) / "manifest.json").write_text(json.dumps(m, indent=2))

    def delete_session(self, session_id: str) -> bool:
        d = self.session_dir(session_id)
        if d.exists():
            shutil.rmtree(d)
            return True
        return False

    def apply_retention(self, now: datetime | None = None) -> dict[str, list[str]]:
        now = now or datetime.now(timezone.utc)
        result: dict[str, list[str]] = {"deleted_sessions": [], "raw_purged": []}
        for d in sorted(p for p in self.root.iterdir() if (p / "manifest.json").exists()):
            m = json.loads((d / "manifest.json").read_text())
            created = datetime.fromisoformat(m["created_at"])
            ret = RetentionPolicy(**m["retention"])
            if now - created > timedelta(days=ret.retain_days):
                shutil.rmtree(d)
                result["deleted_sessions"].append(d.name)
                continue
            if ret.delete_raw_after_days is not None and now - created > timedelta(days=ret.delete_raw_after_days):
                streams = d / "streams"
                if streams.exists() and any(streams.iterdir()):
                    shutil.rmtree(streams)
                    streams.mkdir()
                    m["raw_purged_at"] = now.isoformat()
                    (d / "manifest.json").write_text(json.dumps(m, indent=2))
                    result["raw_purged"].append(d.name)
        return result

    def export_review_bundle(self, session_id: str, out_dir: Path, include_raw: bool = False) -> dict:
        m = self.manifest(session_id)
        if include_raw and not (m.get("consent") or {}).get("allow_raw_export"):
            raise PermissionError("raw biosignal export not permitted by consent record")
        src = self.session_dir(session_id)
        out = Path(out_dir) / session_id
        out.mkdir(parents=True, exist_ok=True)
        copied = []
        for p in src.iterdir():
            if p.is_file():
                shutil.copy2(p, out / p.name)
                copied.append(p.name)
        if include_raw and (src / "streams").exists():
            shutil.copytree(src / "streams", out / "streams", dirs_exist_ok=True)
            copied.append("streams/")
        return {"session_id": session_id, "files": sorted(copied), "raw_included": include_raw}


def _default(o: Any) -> Any:
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    if isinstance(o, BaseModel):
        return o.model_dump(mode="json")
    if hasattr(o, "value"):
        return o.value
    raise TypeError(type(o))
