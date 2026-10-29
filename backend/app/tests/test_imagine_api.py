"""Imagine lab API: fail-closed default and mock diffusion state machine."""
from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.api import imagine as api_module
from app.core.imagine.providers import ProviderStatus, ProviderSubmission, RemoteDiffusionProvider
from app.core.imagine.service import ImagineService
from app.core.imagine.store import ImagineStore

pytestmark = pytest.mark.core

PNG = b"\x89PNG\r\n\x1a\n" + b"imagine-test-fixture"


def _payload() -> dict:
    vector = {
        "attention": 0.61,
        "arousal": 0.38,
        "valence": 0.64,
        "vividness": 0.57,
        "fatigue": 0.22,
        "confidence": 0.71,
        "theta": 0.31,
        "alpha": 0.55,
        "beta": 0.52,
        "gamma": 0.41,
        "hrv": 0.57,
        "eda": 0.33,
        "signal_quality": 0.86,
        "uncertainty": 0.28,
        "trend": 0.52,
        "stability": 0.66,
    }
    return {
        "schema": "IMAGINA-DIFFUSION-REQUEST-v2",
        "request_id": "req-12345678",
        "brief": {
            "prompt": "a quiet observatory above a dark ocean",
            "negative_prompt": "people, text",
            "style": "cinematic",
            "seed": "42",
        },
        "conditioning": {
            "schema": "IMAGINA-CONDITIONING-v1",
            "adapter": "conditioning-v0",
            "source": "demo",
            "vector": vector,
            "quality": 0.86,
            "uncertainty": 0.28,
            "trend": 0.52,
            "stability": 0.66,
            "vector_hash": "0123456789abcdef",
        },
        "controls": {
            "clarity": 0.6,
            "fog": 0.3,
            "motion": 0.4,
            "saturation": 0.6,
            "detail": 0.5,
            "glow": 0.4,
            "cameraPace": 0.5,
            "depthFalloff": 0.4,
        },
        "camera": {"mode": "first_person", "path": [], "start": [0, 1.68, 7.5], "fov": 70},
        "adaptive": {"target": "immersion", "hz": 0.2},
        "output": {"skybox": {"width": 4096, "height": 2048}, "preview": {"width": 1280, "height": 720}},
        "provenance": {"composer_version": "imagine-2.0", "policy_version": "adaptive-v0", "app_version": "2.0.0"},
        "boundary": "Generated environment texture, not a reconstruction.",
    }


def _manifest() -> dict:
    digest = hashlib.sha256(PNG).hexdigest()
    return {
        "schema": "IMAGINA-DIFFUSION-MANIFEST-v1",
        "job_id": "remote-job",
        "state": "succeeded",
        "model_slot": "scene-diffusion-v0",
        "model_hash": "model-sha",
        "seed": 42,
        "prompt_hash": "prompt-sha",
        "conditioning_hash": "conditioning-sha",
        "controls": {"clarity": 0.6},
        "skybox": {"url": "http://worker.local/v1/assets/skybox", "width": 4096, "height": 2048, "sha256": digest},
        "preview": {"url": "http://worker.local/v1/assets/preview", "width": 1280, "height": 720, "sha256": digest},
        "created_at": "2026-10-25T20:00:00+00:00",
        "expires_at": "2099-10-26T20:00:00+00:00",
        "provenance": {"worker": "mock"},
    }


class MockProvider:
    def __init__(self, state: str = "succeeded", manifest: dict | None = None, data: bytes = PNG) -> None:
        self.state = state
        self.cancelled = False
        self.downloads: list[str] = []
        self.manifest = manifest
        self.data = data

    async def capabilities(self):
        from app.core.imagine.providers import ProviderCapability

        return ProviderCapability(status="ready", reason=None)

    async def submit(self, request):
        return ProviderSubmission(remote_id="remote-job", state="queued", stage="queued")

    async def status(self, remote_id):
        manifest = self.manifest if self.manifest is not None else (_manifest() if self.state == "succeeded" else None)
        return ProviderStatus(state=self.state, stage=self.state, manifest=manifest)

    async def cancel(self, remote_id):
        self.cancelled = True

    async def download(self, url):
        self.downloads.append(url)
        return self.data


@pytest.fixture
def workspace(monkeypatch):
    directory = tempfile.mkdtemp(prefix="imagine-api-")
    store = ImagineStore(Path(directory) / "imagine")
    service = ImagineService(
        store,
        RemoteDiffusionProvider(base_url="", token="", enabled=False),
    )
    monkeypatch.setattr(api_module, "imagine_service", service)
    app = FastAPI()
    app.include_router(api_module.router)
    with TestClient(app) as client:
        yield client, store, service, directory
    shutil.rmtree(directory, ignore_errors=True)


def test_default_is_blocked_and_creates_no_job(workspace):
    client, store, _, _ = workspace
    capabilities = client.get("/animus/imagine/capabilities").json()
    assert capabilities["diffusion"]["status"] == "blocked"
    assert capabilities["diffusion"]["consent_required"] is True
    assert capabilities["claim_ceiling"] == "L1_BEHAVIORAL_ASSISTED"

    response = client.post("/animus/imagine/jobs", json=_payload())
    assert response.status_code == 503
    assert response.json()["code"] == "diffusion_unavailable"
    assert list(store.jobs.glob("*.json")) == []


def test_mock_job_succeeds_and_serves_only_local_assets(workspace, monkeypatch):
    client, store, service, _ = workspace
    provider = MockProvider()
    monkeypatch.setattr(service, "provider", provider)

    created = client.post("/animus/imagine/jobs", json=_payload())
    assert created.status_code == 202, created.text
    job = created.json()
    assert job["state"] == "queued"
    assert "remote_id" not in job

    fetched = client.get(f"/animus/imagine/jobs/{job['id']}")
    assert fetched.status_code == 200, fetched.text
    completed = fetched.json()
    assert completed["state"] == "succeeded"
    assert completed["manifest"]["skybox"]["url"].startswith("/animus/imagine/assets/")
    assert completed["manifest"]["skybox"]["sha256"] == hashlib.sha256(PNG).hexdigest()
    assert provider.downloads

    asset = client.get(completed["manifest"]["preview"]["url"])
    assert asset.status_code == 200
    assert asset.headers["content-type"] == "image/png"
    assert asset.headers["x-content-type-options"] == "nosniff"
    assert asset.content == PNG


def test_expired_manifest_fails_closed_without_assets(workspace, monkeypatch):
    client, store, service, _ = workspace
    manifest = _manifest()
    manifest["expires_at"] = "2020-01-01T00:00:00+00:00"
    provider = MockProvider(manifest=manifest)
    monkeypatch.setattr(service, "provider", provider)
    job = client.post("/animus/imagine/jobs", json=_payload()).json()
    fetched = client.get(f"/animus/imagine/jobs/{job['id']}").json()
    assert fetched["state"] == "failed"
    assert fetched["error_code"] == "artifact_expired"
    assert list(store.artifacts.glob("*")) == []
    assert provider.downloads == []


def test_checksum_mismatch_fails_closed(workspace, monkeypatch):
    client, store, service, _ = workspace
    provider = MockProvider(data=PNG + b"tampered")
    monkeypatch.setattr(service, "provider", provider)
    job = client.post("/animus/imagine/jobs", json=_payload()).json()
    fetched = client.get(f"/animus/imagine/jobs/{job['id']}").json()
    assert fetched["state"] == "failed"
    assert fetched["error_code"] == "artifact_invalid"
    assert list(store.artifacts.glob("*")) == []


def test_oversized_preview_is_rejected(workspace, monkeypatch):
    client, store, service, _ = workspace
    manifest = _manifest()
    manifest["preview"]["width"] = 1920
    provider = MockProvider(manifest=manifest)
    monkeypatch.setattr(service, "provider", provider)
    job = client.post("/animus/imagine/jobs", json=_payload()).json()
    fetched = client.get(f"/animus/imagine/jobs/{job['id']}").json()
    assert fetched["state"] == "failed"
    assert fetched["error_code"] == "artifact_invalid"
    assert list(store.artifacts.glob("*")) == []


def test_idempotent_post_and_list(workspace, monkeypatch):
    client, _, service, _ = workspace
    monkeypatch.setattr(service, "provider", MockProvider())
    first = client.post("/animus/imagine/jobs", json=_payload()).json()
    second = client.post("/animus/imagine/jobs", json=_payload()).json()
    assert first["id"] == second["id"]
    listed = client.get("/animus/imagine/jobs").json()
    assert len(listed["jobs"]) == 1


def test_cancel_and_terminal_conflict(workspace, monkeypatch):
    client, _, service, _ = workspace
    provider = MockProvider(state="running")
    monkeypatch.setattr(service, "provider", provider)
    job = client.post("/animus/imagine/jobs", json=_payload()).json()
    cancelled = client.post(f"/animus/imagine/jobs/{job['id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["state"] == "cancelled"
    assert provider.cancelled is True
    conflict = client.post(f"/animus/imagine/jobs/{job['id']}/cancel")
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "job_not_cancellable"


def test_failed_worker_and_invalid_payload(workspace, monkeypatch):
    client, _, service, _ = workspace
    monkeypatch.setattr(service, "provider", MockProvider(state="failed"))
    job = client.post("/animus/imagine/jobs", json=_payload()).json()
    fetched = client.get(f"/animus/imagine/jobs/{job['id']}").json()
    assert fetched["state"] == "failed"
    assert fetched["error_code"] == "worker_failed"

    payload = _payload()
    payload["session_id"] = "must-not-be-forwarded"
    assert client.post("/animus/imagine/jobs", json=payload).status_code == 422
    assert client.get("/animus/imagine/jobs/../../etc/passwd").status_code == 404


def test_artifact_path_traversal_is_rejected(workspace):
    client, _, _, _ = workspace
    assert client.get("/animus/imagine/assets/..%2F..%2Fetc%2Fpasswd").status_code == 404
    assert client.get("/animus/imagine/assets/not-an-asset").status_code == 404
