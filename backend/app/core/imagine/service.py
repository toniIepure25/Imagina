"""Imagine job orchestration with a fail-closed diffusion provider."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.imagine.providers import (
    DiffusionUnavailable,
    ProviderError,
    RemoteDiffusionProvider,
)
from app.core.imagine.store import ImagineStore, ImagineStoreError
from app.core.time import utcnow
from app.schemas.imagine import ImagineJobPublic, ImagineManifest


class JobNotFound(Exception):
    pass


class JobConflict(Exception):
    pass


class ArtifactNotFound(Exception):
    pass


class ImagineService:
    def __init__(self, store: ImagineStore, provider: RemoteDiffusionProvider) -> None:
        self.store = store
        self.provider = provider

    async def capabilities(self) -> dict[str, Any]:
        capability = await self.provider.capabilities()
        return {
            "local": {"status": "ready", "engine": "local-procedural", "first_person": True},
            "diffusion": {
                "status": capability.status,
                "provider": "remote-diffusion",
                "reason": capability.reason,
                "model_slot": capability.model_slot,
                "consent_required": True,
                "max_skybox": {"width": 4096, "height": 2048},
                "max_preview": {"width": 1280, "height": 720},
            },
            "claim_ceiling": "L1_BEHAVIORAL_ASSISTED",
        }

    async def create_job(self, request: dict[str, Any]) -> dict[str, Any]:
        capability = await self.provider.capabilities()
        if capability.status != "ready":
            raise DiffusionUnavailable(capability.reason or "No diffusion worker is attached.")
        inputs_hash = hashlib.sha256(
            json.dumps(request, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        existing = self.store.find_by_inputs(inputs_hash)
        if existing:
            return self.public(existing)
        submission = await self.provider.submit(request)
        timestamp = utcnow().isoformat()
        record = {
            "id": f"job-{uuid.uuid4().hex[:16]}",
            "state": submission.state if submission.state in {"queued", "running"} else "queued",
            "provider": "remote-diffusion",
            "model_slot": capability.model_slot,
            "created_at": timestamp,
            "updated_at": timestamp,
            "error_code": None,
            "error_message": None,
            "staged": submission.stage,
            "manifest": None,
            "remote_id": submission.remote_id,
            "inputs_hash": inputs_hash,
            "request": request,
            "poll_errors": 0,
        }
        self.store.create(record)
        return self.public(record)

    async def get_job(self, job_id: str) -> dict[str, Any]:
        record = self._record(job_id)
        if record["state"] in {"succeeded", "failed", "cancelled"}:
            return self.public(record)
        if not record.get("remote_id"):
            return self.public(record)
        try:
            status = await self.provider.status(str(record["remote_id"]))
        except ProviderError as exc:
            record["poll_errors"] = int(record.get("poll_errors", 0)) + 1
            record["staged"] = exc.code
            if record["poll_errors"] >= 3:
                record["state"] = "failed"
                record["error_code"] = exc.code
                record["error_message"] = exc.message
            record["updated_at"] = utcnow().isoformat()
            self.store.save(record)
            return self.public(record)
        record["poll_errors"] = 0
        record["staged"] = status.stage
        record["updated_at"] = utcnow().isoformat()
        if status.state in {"queued", "running", "cancelling", "cancelled", "failed", "succeeded"}:
            record["state"] = status.state
        if status.state == "failed":
            record["error_code"] = status.error_code or "worker_failed"
            record["error_message"] = status.error_message or "The diffusion worker failed."
        if status.state == "succeeded" and status.manifest:
            try:
                record["manifest"] = await self._ingest_manifest(record["id"], status.manifest)
                record["state"] = "succeeded"
            except (ProviderError, ValueError, ImagineStoreError) as exc:
                record["state"] = "failed"
                record["error_code"] = getattr(exc, "code", "artifact_invalid")
                record["error_message"] = str(exc)
        self.store.save(record)
        return self.public(record)

    async def cancel_job(self, job_id: str) -> dict[str, Any]:
        record = self._record(job_id)
        if record["state"] in {"succeeded", "failed", "cancelled"}:
            raise JobConflict("Job is already terminal.")
        record["state"] = "cancelling"
        record["updated_at"] = utcnow().isoformat()
        self.store.save(record)
        try:
            if record.get("remote_id"):
                await self.provider.cancel(str(record["remote_id"]))
            record["state"] = "cancelled"
        except ProviderError as exc:
            record["state"] = "failed"
            record["error_code"] = exc.code
            record["error_message"] = exc.message
        record["updated_at"] = utcnow().isoformat()
        self.store.save(record)
        return self.public(record)

    def list_jobs(self, limit: int = 10) -> list[dict[str, Any]]:
        return [self.public(record) for record in self.store.list(limit)]

    def delete_job(self, job_id: str) -> None:
        record = self._record(job_id)
        if record["state"] not in {"succeeded", "failed", "cancelled"}:
            raise JobConflict("Cancel the job before deleting it.")
        self.store.delete(job_id)

    def asset(self, asset_id: str) -> tuple[Any, str]:
        try:
            path = self.store.asset_file(asset_id)
            return path, self.store.media_type(asset_id)
        except ImagineStoreError as exc:
            raise ArtifactNotFound(str(exc)) from exc

    async def _ingest_manifest(self, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        manifest = ImagineManifest.model_validate(payload)
        try:
            expires = datetime.fromisoformat(manifest.expires_at.replace("Z", "+00:00"))
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise ProviderError("artifact_invalid", "Manifest expiry is invalid.", False) from exc
        if expires <= datetime.now(timezone.utc):
            raise ProviderError("artifact_expired", "Manifest has expired.", False)
        if manifest.skybox.width > 4096 or manifest.skybox.height > 2048:
            raise ProviderError("artifact_invalid", "Skybox dimensions exceed the declared maximum.", False)
        if manifest.preview.width > 1280 or manifest.preview.height > 720:
            raise ProviderError("artifact_invalid", "Preview dimensions exceed the declared maximum.", False)
        assets: dict[str, dict[str, Any]] = {}
        for name in ("skybox", "preview"):
            asset = getattr(manifest, name)
            data = await self.provider.download(asset.url)
            digest = hashlib.sha256(data).hexdigest()
            if digest.lower() != asset.sha256.lower():
                raise ProviderError("artifact_invalid", f"{name} checksum does not match the manifest.", False)
            asset_id = f"{job_id}-{name}"
            stored_digest = self.store.write_asset(asset_id, data)
            assets[name] = {
                "url": f"/animus/imagine/assets/{asset_id}",
                "width": asset.width,
                "height": asset.height,
                "sha256": stored_digest,
            }
        manifest = manifest.model_copy(
            update={
                "job_id": job_id,
                "skybox": manifest.skybox.model_copy(update=assets["skybox"]),
                "preview": manifest.preview.model_copy(update=assets["preview"]),
            }
        )
        return manifest.model_dump()

    def _record(self, job_id: str) -> dict[str, Any]:
        try:
            record = self.store.get(job_id)
        except ImagineStoreError as exc:
            raise JobNotFound(str(exc)) from exc
        if record is None:
            raise JobNotFound(f"Unknown job {job_id}.")
        return record

    @staticmethod
    def public(record: dict[str, Any]) -> dict[str, Any]:
        return ImagineJobPublic.model_validate(record).model_dump()
