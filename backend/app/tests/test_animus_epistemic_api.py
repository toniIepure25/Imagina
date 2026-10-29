"""HTTP contract for the epistemic reconstruction interview."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.api import animus_studio as api_module
from app.core.animus.studio.repository import StudioRepository
from app.core.animus.studio.service import AnimusStudioService
from app.schemas.animus_studio_responses import (
    InterviewListResponseModel,
    InterviewStartResponseModel,
    InterviewSubmitResponseModel,
    InterviewSummaryResponseModel,
)

pytestmark = pytest.mark.core


@pytest.fixture
def client(monkeypatch):
    directory = tempfile.mkdtemp(prefix="animus-eri-api-")
    service = AnimusStudioService(repository=StudioRepository(str(Path(directory) / "studio.db")))
    monkeypatch.setattr(api_module, "studio_service", service)
    app = FastAPI()
    app.include_router(api_module.router)
    with TestClient(app) as test_client:
        yield test_client
    shutil.rmtree(directory, ignore_errors=True)


def _create(client: TestClient) -> dict:
    response = client.post("/animus/studio/sessions", json={
        "title": "Interview scene",
        "intention": "a white castle above a dark ocean with a moon and three lanterns at dusk",
        "seed": 31,
    })
    assert response.status_code == 200, response.text
    return response.json()


def _start(client: TestClient, session_id: str, max_probes: int = 6) -> dict:
    response = client.post(
        f"/animus/studio/sessions/{session_id}/interviews/start",
        json={"max_probes": max_probes, "form_id": "A", "difficulty": 0.45},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _probe_body(probe: dict, client_trial_id: str, *, expected_version_id: str | None = None) -> dict:
    return {
        "probe_id": probe["probe_id"],
        "task_id": probe["task_id"],
        "choice": probe["options"][0]["id"],
        "confidence": 0.8,
        "abstained": False,
        "latency_ms": 1200,
        "client_trial_id": client_trial_id,
        **({"expected_version_id": expected_version_id} if expected_version_id else {}),
    }


def test_interview_start_submit_and_summary_contract(client):
    created = _create(client)
    session_id = created["session_id"]
    started = _start(client, session_id)
    InterviewStartResponseModel.model_validate(started)
    assert started["interview"]["probe_count"] == 0
    assert started["interview"]["status"] == "active"
    assert "answer" not in started["probe"]
    assert started["probe"]["probe_type"] == "object_presence"
    interview_id = started["interview"]["interview_id"]

    body = started
    recorded = 0
    for index in range(6):
        probe = body.get("probe") or body.get("next_probe")
        assert probe is not None
        response = client.post(
            f"/animus/studio/sessions/{session_id}/interviews/{interview_id}/probes",
            json=_probe_body(probe, f"eri-client-{index}"),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        InterviewSubmitResponseModel.model_validate(body)
        recorded += 1
        if body["reconstruction"]:
            break
        assert body["next_probe"] is not None
    assert recorded >= 1
    assert body["reconstruction"] is not None
    assert body["reconstruction"]["scoring_version"] == "eri-v1"
    assert body["interview"]["status"] == "completed"

    summary = client.get(f"/animus/studio/interviews/{interview_id}")
    assert summary.status_code == 200, summary.text
    InterviewSummaryResponseModel.model_validate(summary.json())
    assert summary.json()["reconstruction"]["scores"]["n_probes"] == recorded

    listed = client.get(f"/animus/studio/sessions/{session_id}/interviews")
    assert listed.status_code == 200, listed.text
    InterviewListResponseModel.model_validate(listed.json())
    assert any(item["interview_id"] == interview_id for item in listed.json()["interviews"])
    assert client.get("/animus/studio/interviews/eri_unknown").status_code == 404


def test_interview_submit_is_idempotent_and_rejects_stale_versions(client):
    created = _create(client)
    session_id = created["session_id"]
    started = _start(client, session_id)
    interview_id = started["interview"]["interview_id"]
    probe = started["probe"]
    request = _probe_body(probe, "eri-idempotent-1")
    first = client.post(
        f"/animus/studio/sessions/{session_id}/interviews/{interview_id}/probes", json=request)
    assert first.status_code == 200, first.text
    assert first.json()["idempotent"] is False
    second = client.post(
        f"/animus/studio/sessions/{session_id}/interviews/{interview_id}/probes", json=request)
    assert second.status_code == 200, second.text
    assert second.json()["idempotent"] is True
    assert second.json()["trial"]["trial_id"] == first.json()["trial"]["trial_id"]

    next_probe = first.json()["next_probe"]
    assert next_probe is not None
    stale = client.post(
        f"/animus/studio/sessions/{session_id}/interviews/{interview_id}/probes",
        json=_probe_body(next_probe, "eri-stale-1", expected_version_id="ver_does_not_exist"),
    )
    assert stale.status_code == 409, stale.text
    assert stale.headers["X-Studio-Error-Code"] == "stale_version"


def test_interview_rejects_invalid_confidence_and_unknown_probe(client):
    created = _create(client)
    session_id = created["session_id"]
    started = _start(client, session_id)
    interview_id = started["interview"]["interview_id"]
    probe = started["probe"]
    bad_confidence = _probe_body(probe, "eri-bad-confidence")
    bad_confidence["confidence"] = 0.2
    response = client.post(
        f"/animus/studio/sessions/{session_id}/interviews/{interview_id}/probes",
        json=bad_confidence)
    assert response.status_code == 422

    unknown = _probe_body({**probe, "probe_id": "pr_00000000000000"}, "eri-unknown-probe")
    response = client.post(
        f"/animus/studio/sessions/{session_id}/interviews/{interview_id}/probes", json=unknown)
    assert response.status_code == 400, response.text
    assert response.headers["X-Studio-Error-Code"] == "invalid_request"
