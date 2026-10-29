"""Provider boundary for the future A100 diffusion worker.

The default provider is disabled and performs no network request. Tests inject a mock provider.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024


class DiffusionUnavailable(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ProviderError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


@dataclass
class ProviderCapability:
    status: str
    reason: str | None
    model_slot: str = "scene-diffusion-v0"


@dataclass
class ProviderSubmission:
    remote_id: str
    state: str
    stage: str | None = None


@dataclass
class ProviderStatus:
    state: str
    stage: str | None
    manifest: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None


class RemoteDiffusionProvider:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        enabled: bool,
        timeout_seconds: float = 180,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def capabilities(self) -> ProviderCapability:
        if not self.enabled:
            return ProviderCapability(status="blocked", reason="Remote diffusion is disabled by local configuration.")
        if not self.base_url:
            return ProviderCapability(status="blocked", reason="No A100 worker URL is configured.")
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.base_url}/health", headers=self._headers())
            if response.status_code != 200:
                return ProviderCapability(status="blocked", reason=f"Worker health returned {response.status_code}.")
            payload = response.json()
            if payload.get("status") != "ok":
                return ProviderCapability(status="blocked", reason="Worker is not ready.")
            model_slot = str(payload.get("model_slot", "scene-diffusion-v0"))
            return ProviderCapability(status="ready", reason=None, model_slot=model_slot)
        except (httpx.HTTPError, ValueError):
            return ProviderCapability(status="blocked", reason="Worker is unreachable.")

    async def submit(self, request: dict[str, Any]) -> ProviderSubmission:
        if not self.enabled or not self.base_url:
            raise DiffusionUnavailable("Remote diffusion is not configured.")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.base_url}/v1/jobs", json=request, headers=self._headers())
        except httpx.HTTPError as exc:
            raise ProviderError("worker_timeout", "The diffusion worker did not accept the job.", True) from exc
        if response.status_code not in {200, 201, 202}:
            raise ProviderError("worker_rejected", f"Worker rejected the job ({response.status_code}).", False)
        try:
            payload = response.json()
            remote_id = str(payload["job_id"])
        except (ValueError, KeyError) as exc:
            raise ProviderError("worker_invalid_response", "Worker response has no job id.", False) from exc
        return ProviderSubmission(
            remote_id=remote_id,
            state=str(payload.get("state", "queued")),
            stage=payload.get("stage"),
        )

    async def status(self, remote_id: str) -> ProviderStatus:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/v1/jobs/{remote_id}",
                    headers=self._headers(),
                )
        except httpx.HTTPError as exc:
            raise ProviderError("worker_timeout", "The diffusion worker did not answer.", True) from exc
        if response.status_code == 404:
            raise ProviderError("worker_rejected", "The worker no longer knows this job.", False)
        if response.status_code != 200:
            raise ProviderError("worker_invalid_response", f"Worker status returned {response.status_code}.", True)
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("worker_invalid_response", "Worker status is not JSON.", False) from exc
        return ProviderStatus(
            state=str(payload.get("state", "running")),
            stage=payload.get("stage"),
            manifest=payload.get("manifest"),
            error_code=payload.get("error_code"),
            error_message=payload.get("error_message"),
        )

    async def cancel(self, remote_id: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/jobs/{remote_id}/cancel",
                    headers=self._headers(),
                )
        except httpx.HTTPError as exc:
            raise ProviderError("worker_timeout", "Cancellation did not reach the worker.", True) from exc
        if response.status_code not in {200, 202, 204, 404}:
            raise ProviderError("worker_invalid_response", "Worker did not confirm cancellation.", True)

    async def download(self, url: str) -> bytes:
        base = urlparse(self.base_url)
        target = urlparse(url)
        if target.scheme not in {"http", "https"} or target.netloc != base.netloc:
            raise ProviderError("artifact_invalid", "Worker returned a foreign artifact URL.", False)
        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=False) as client:
                async with client.stream("GET", url, headers=self._headers()) as response:
                    if response.status_code != 200:
                        raise ProviderError("artifact_invalid", "Artifact download failed.", True)
                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > MAX_DOWNLOAD_BYTES:
                            raise ProviderError("artifact_invalid", "Artifact exceeds the size limit.", False)
                        chunks.append(chunk)
                    return b"".join(chunks)
        except httpx.HTTPError as exc:
            raise ProviderError("worker_timeout", "Artifact download failed.", True) from exc
