"""Local-only JSON job store and validated image artifact store."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

JOB_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,80}$")
ASSET_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,100}$")
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024


class ImagineStoreError(Exception):
    pass


class ImagineStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.jobs = self.root / "jobs"
        self.artifacts = self.root / "artifacts"
        self.jobs.mkdir(parents=True, exist_ok=True)
        self.artifacts.mkdir(parents=True, exist_ok=True)

    def _job_path(self, job_id: str) -> Path:
        if not JOB_PATTERN.fullmatch(job_id):
            raise ImagineStoreError("invalid job id")
        return self.jobs / f"{job_id}.json"

    def create(self, record: dict[str, Any]) -> dict[str, Any]:
        path = self._job_path(str(record["id"]))
        if path.exists():
            raise ImagineStoreError("job already exists")
        self.save(record)
        return record

    def save(self, record: dict[str, Any]) -> None:
        path = self._job_path(str(record["id"]))
        temporary = path.with_suffix(".json.tmp")
        payload = json.dumps(record, indent=2, sort_keys=True).encode("utf-8")
        temporary.write_bytes(payload)
        os.replace(temporary, path)

    def get(self, job_id: str) -> dict[str, Any] | None:
        path = self._job_path(job_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ImagineStoreError("corrupt job record") from exc

    def list(self, limit: int = 10) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for path in sorted(self.jobs.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            if len(records) >= max(1, min(50, limit)):
                break
            try:
                records.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return records

    def delete(self, job_id: str) -> bool:
        path = self._job_path(job_id)
        if not path.exists():
            return False
        path.unlink()
        for asset in self.artifacts.glob(f"{job_id}-*"):
            asset.unlink(missing_ok=True)
        return True

    def find_by_inputs(self, inputs_hash: str) -> dict[str, Any] | None:
        for record in self.list(50):
            if record.get("inputs_hash") == inputs_hash and record.get("state") not in {"failed", "cancelled"}:
                return record
        return None

    def _asset_path(self, asset_id: str) -> Path:
        if not ASSET_PATTERN.fullmatch(asset_id):
            raise ImagineStoreError("invalid asset id")
        return self.artifacts / asset_id

    def asset_exists(self, asset_id: str) -> bool:
        return self._asset_path(asset_id).exists()

    def asset_file(self, asset_id: str) -> Path:
        path = self._asset_path(asset_id)
        if not path.exists():
            raise ImagineStoreError("asset not found")
        return path

    def write_asset(self, asset_id: str, data: bytes) -> str:
        if len(data) == 0 or len(data) > MAX_ARTIFACT_BYTES:
            raise ImagineStoreError("artifact size is invalid")
        if not self._valid_image(data):
            raise ImagineStoreError("artifact is not a supported image")
        path = self._asset_path(asset_id)
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(data)
        os.replace(temporary, path)
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _valid_image(data: bytes) -> bool:
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return True
        if data.startswith(b"\xff\xd8\xff"):
            return True
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"

    def media_type(self, asset_id: str) -> str:
        header = self.asset_file(asset_id).read_bytes()[:16]
        if header.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
            return "image/webp"
        return "image/png"
