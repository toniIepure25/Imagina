"""HTTP contract for Scene Threshold contrast sessions and the observatory."""
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
    ContrastListResponseModel,
    ContrastStartResponseModel,
    ContrastSubmitResponseModel,
    ContrastSummaryResponseModel,
    ObservatoryModel,
)

pytestmark = pytest.mark.core


@pytest.fixture
def client(monkeypatch):
    directory = tempfile.mkdtemp(prefix="animus-contrast-api-")
    service = AnimusStudioService(repository=StudioRepository(str(Path(directory) / "studio.db")))
    monkeypatch.setattr(api_module, "studio_service", service)
    app = FastAPI()
    app.include_router(api_module.router)
    with TestClient(app) as test_client:
        yield test_client
    shutil.rmtree(directory, ignore_errors=True)


def _create(client: TestClient) -> dict:
    response = client.post("/animus/studio/sessions", json={
        "title": "Contrast scene",
        "intention": "a white castle above a dark ocean with a moon and three lanterns at dusk",
        "seed": 31,
    })
    assert response.status_code == 200, response.text
    return response.json()


def _start(client: TestClient, session_id: str, *, max_trials: int = 12) -> dict:
    response = client.post(
        f"/animus/studio/sessions/{session_id}/contrast/start",
        json={"max_trials": max_trials, "form_id": "A", "difficulty": 0.45},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _answer_body(trial: dict, client_trial_id: str, *,
                 expected_version_id: str | None = None) -> dict:
    return {
        "trial_id": trial["trial_id"],
        "task_id": trial["task_id"],
        "choice": trial["options"][0]["id"],
        "confidence": 0.8,
        "abstained": False,
        "latency_ms": 900,
        "client_trial_id": client_trial_id,
        **({"expected_version_id": expected_version_id} if expected_version_id else {}),
    }


def test_contrast_start_submit_summary_and_observatory_contract(client):
    created = _create(client)
    session_id = created["session_id"]
    started = _start(client, session_id)
    ContrastStartResponseModel.model_validate(started)
    assert started["contrast"]["trial_count"] == 0
    assert started["contrast"]["status"] == "active"
    assert "target_side" not in started["trial"]
    assert "feature_type" not in started["trial"]
    contrast_id = started["contrast"]["contrast_id"]

    trial_payload = started["trial"]
    body = started
    recorded = 0
    for index in range(12):
        response = client.post(
            f"/animus/studio/sessions/{session_id}/contrast/{contrast_id}/trials",
            json=_answer_body(trial_payload, f"cs-client-{index}"),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        ContrastSubmitResponseModel.model_validate(body)
        recorded += 1
        assert body["trial"]["trial_index"] == index
        if body["result"]:
            break
        assert body["next_trial"] is not None
        trial_payload = body["next_trial"]
    assert recorded == 12
    assert body["result"] is not None
    assert body["result"]["scoring_version"] == "sdt-v1"
    assert body["result"]["n_trials"] == 12
    assert body["contrast"]["status"] == "completed"

    summary = client.get(f"/animus/studio/contrast/{contrast_id}")
    assert summary.status_code == 200, summary.text
    ContrastSummaryResponseModel.model_validate(summary.json())
    assert summary.json()["result"]["n_trials"] == 12

    listed = client.get(f"/animus/studio/sessions/{session_id}/contrast")
    assert listed.status_code == 200, listed.text
    ContrastListResponseModel.model_validate(listed.json())
    assert any(item["contrast_id"] == contrast_id for item in listed.json()["contrasts"])

    observatory = client.get(f"/animus/studio/sessions/{session_id}/observatory")
    assert observatory.status_code == 200, observatory.text
    ObservatoryModel.model_validate(observatory.json())
    payload = observatory.json()
    assert payload["discrimination"]["scoring_version"] == "sdt-v1"
    assert payload["reliability"]["status"] in ("estimated", "insufficient")

    reflection = client.post(
        f"/animus/studio/contrast/{contrast_id}/reflection",
        json={"strategies": ["visual", "spatial"], "notes": "compared the lantern"},
    )
    assert reflection.status_code == 200, reflection.text
    assert reflection.json()["contrast"]["reflection"]["strategies"] == ["visual", "spatial"]
    assert client.get("/animus/studio/contrast/ct_unknown").status_code == 404


def test_contrast_submit_is_idempotent_and_rejects_stale_versions(client):
    created = _create(client)
    session_id = created["session_id"]
    started = _start(client, session_id)
    contrast_id = started["contrast"]["contrast_id"]
    trial = started["trial"]
    request = _answer_body(trial, "cs-idempotent-1")
    first = client.post(
        f"/animus/studio/sessions/{session_id}/contrast/{contrast_id}/trials", json=request)
    assert first.status_code == 200, first.text
    assert first.json().get("idempotent") is not True
    second = client.post(
        f"/animus/studio/sessions/{session_id}/contrast/{contrast_id}/trials", json=request)
    assert second.status_code == 200, second.text
    assert second.json()["idempotent"] is True
    assert second.json()["trial"]["trial_id"] == first.json()["trial"]["trial_id"]
    assert second.json()["contrast"]["trial_count"] == 1

    next_trial = first.json()["next_trial"]
    assert next_trial is not None
    stale = client.post(
        f"/animus/studio/sessions/{session_id}/contrast/{contrast_id}/trials",
        json=_answer_body(next_trial, "cs-stale-1", expected_version_id="ver_does_not_exist"),
    )
    assert stale.status_code == 409, stale.text
    assert stale.headers["X-Studio-Error-Code"] == "stale_version"


def test_contrast_rejects_invalid_choice_and_unknown_contrast(client):
    created = _create(client)
    session_id = created["session_id"]
    started = _start(client, session_id)
    contrast_id = started["contrast"]["contrast_id"]
    trial = started["trial"]
    invalid = _answer_body(trial, "cs-invalid-choice")
    invalid["choice"] = "c"
    response = client.post(
        f"/animus/studio/sessions/{session_id}/contrast/{contrast_id}/trials", json=invalid)
    assert response.status_code == 422

    unknown = client.post(
        f"/animus/studio/sessions/{session_id}/contrast/ct_unknown/trials",
        json=_answer_body(trial, "cs-unknown"),
    )
    assert unknown.status_code == 404
