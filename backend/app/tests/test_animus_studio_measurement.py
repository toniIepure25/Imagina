"""Behavioural measurement, task determinism, and practice API contracts."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import aiosqlite
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.api import animus_studio as api_module
from app.core.animus.scene.compose import compose_from_intention
from app.core.animus.studio.adaptive import update_difficulty
from app.core.animus.studio.profile import (
    apply_observation,
    calibration_from_stats,
    error_signature_from_trials,
    estimate_from_stats,
    profile_payload,
)
from app.core.animus.studio.protocols import BUILTIN_PROTOCOLS, validate_protocol
from app.core.animus.studio.repository import StudioRepository
from app.core.animus.studio.service import AnimusStudioService
from app.core.animus.studio.tasks import build_task, score_response
from app.schemas.animus_studio_responses import (
    PracticeStartResponseModel,
    PracticeSubmitResponseModel,
    ProfileModel,
)
from app.storage.migrations import v018_animus_studio_measurement

pytestmark = pytest.mark.core


def _scene():
    return compose_from_intention("a white castle above a dark ocean at dusk", seed=17).scene


def test_profile_estimates_are_hidden_until_three_trials():
    stats = None
    for _ in range(2):
        stats = apply_observation(stats, score=1.0, confidence=0.8)
    early = estimate_from_stats(stats)
    assert early["estimate"] is None
    assert early["n"] == 2
    stats = apply_observation(stats, score=1.0, confidence=0.8)
    later = estimate_from_stats(stats)
    assert later["estimate"] == 0.8
    assert later["n"] == 3
    assert later["uncertainty"] > 0


def test_calibration_uses_brier_score_not_ability():
    stats = apply_observation(None, score=1.0, confidence=0.9)
    stats = apply_observation(stats, score=1.0, confidence=0.9)
    stats = apply_observation(stats, score=1.0, confidence=0.9)
    calibration = calibration_from_stats(stats)
    assert calibration["n"] == 3
    assert calibration["brier_score"] == pytest.approx(0.01)
    assert calibration["estimate"] is None


def test_brier_is_withheld_until_three_trials():
    stats = apply_observation(None, score=1.0, confidence=0.9)
    stats = apply_observation(stats, score=0.0, confidence=0.9)
    early = calibration_from_stats(stats)
    assert early["n"] == 2
    assert early["brier_score"] is None
    stats = apply_observation(stats, score=1.0, confidence=0.9)
    assert calibration_from_stats(stats)["brier_score"] is not None


def test_task_is_deterministic_and_does_not_publish_the_answer():
    scene = _scene()
    first = build_task(scene, "attribute_recall", seed=11, difficulty=0.4)
    second = build_task(scene, "attribute_recall", seed=11, difficulty=0.4)
    assert first.public_payload() == second.public_payload()
    assert "correct_option_id" not in first.public_payload()
    assert first.correct_option_id in {option["id"] for option in first.options}
    assert score_response(first, {"option_id": first.correct_option_id})["score"] == 1.0
    with pytest.raises(Exception):
        score_response(first, {"option_id": "not-an-option"})


def test_difficulty_controller_is_bounded():
    assert update_difficulty(0.5, [1, 1, 1]) > 0.5
    assert update_difficulty(0.5, [0, 0, 0]) < 0.5
    assert 0.1 <= update_difficulty(0.9, [1, 1, 1]) <= 0.9
    assert 0.1 <= update_difficulty(0.1, [0, 0, 0]) <= 0.9


def test_error_signature_ignores_legacy_option_trials_and_weights_spatial_error():
    trials = [
        {"outcome": {"response_kind": "option", "error_profile": {"omissions": 99, "intrusions": 99}}},
        {"outcome": {"response_kind": "token_selection",
                     "error_profile": {"omissions": 2, "intrusions": 1, "spatial_n": 0}}},
        {"outcome": {"response_kind": "spatial_placement",
                     "error_profile": {"omissions": 1, "intrusions": 0,
                                       "mean_spatial_error": 0.2, "spatial_n": 3}}},
    ]
    signature = error_signature_from_trials(trials)
    assert signature["n"] == 2
    assert signature["omissions"] == 3
    assert signature["intrusions"] == 1
    assert signature["spatial_n"] == 3
    assert signature["mean_spatial_error"] == 0.2


def test_profile_payload_has_uncertainty_and_no_composite():
    stats = apply_observation(None, score=1.0, confidence=0.7)
    payload = profile_payload(
        {"profile_id": "local_default", "profile_version": "ANIMUS-PROFILE-v1"},
        {"stability": stats}, trial_count=1,
    )
    assert payload["claim_level"] == "L1_BEHAVIORAL_ASSISTED"
    assert "composite" not in payload
    assert payload["error_signature"]["n"] == 0
    stability = next(item for item in payload["dimensions"] if item["id"] == "stability")
    assert stability["estimate"] is None
    assert stability["n"] == 1
    assert stability["uncertainty"] > 0
    assert any("not a diagnosis" in line for line in payload["limitations"])


def test_builtin_protocols_are_valid_and_unknown_dimensions_are_rejected():
    for protocol in BUILTIN_PROTOCOLS:
        validate_protocol(protocol)
    broken = {
        "protocol_id": "broken", "version": "ANIMUS-PROTOCOL-v1", "name": "Broken",
        "spec": {"total_trials": 8, "max_minutes": 8, "dimensions": ["imagery_strength"]},
    }
    with pytest.raises(ValueError, match="dimensions"):
        validate_protocol(broken)


@pytest.mark.asyncio
async def test_migration_v018_creates_measurement_tables():
    with tempfile.TemporaryDirectory() as directory:
        db = await aiosqlite.connect(Path(directory) / "measurement.db")
        try:
            await v018_animus_studio_measurement.upgrade(db)
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
            tables = {row[0] for row in await cursor.fetchall()}
            assert "animus_studio_profiles" in tables
            assert "animus_studio_profile_estimates" in tables
            assert "animus_studio_trials" in tables
            cursor = await db.execute(
                "SELECT profile_id, profile_version FROM animus_studio_profiles")
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "local_default"
            assert row[1] == "ANIMUS-PROFILE-v1"
        finally:
            await db.close()


@pytest.fixture
def client(monkeypatch):
    directory = tempfile.mkdtemp(prefix="animus-studio-measurement-")
    service = AnimusStudioService(repository=StudioRepository(str(Path(directory) / "studio.db")))
    monkeypatch.setattr(api_module, "studio_service", service)
    app = FastAPI()
    app.include_router(api_module.router)
    with TestClient(app) as test_client:
        yield test_client
    shutil.rmtree(directory, ignore_errors=True)


def _create(client: TestClient) -> dict:
    response = client.post("/animus/studio/sessions", json={
        "title": "Measurement", "intention": "a white castle above a dark ocean at dusk", "seed": 29})
    assert response.status_code == 200, response.text
    return response.json()


def _response_for_task(task: dict) -> dict:
    kind = task.get("response_kind", "option")
    if kind == "token_selection":
        return {"selected_token_ids": [task["tokens"][0]["token_id"]]}
    if kind == "spatial_placement":
        return {"placements": [{"token_id": token["token_id"], "x": 0.0, "z": 0.0}
                               for token in task["tokens"]]}
    return {"option_id": task["options"][0]["id"]}


def test_practice_api_records_a_trial_idempotently(client):
    created = _create(client)
    session_id = created["session_id"]
    started = client.post(f"/animus/studio/sessions/{session_id}/practice/start", json={})
    assert started.status_code == 200, started.text
    start_payload = started.json()
    PracticeStartResponseModel.model_validate(start_payload)
    task = start_payload["task"]
    assert "correct_option_id" not in task

    trial_request = {
        "task_id": task["task_id"],
        "task_type": task["task_type"],
        "task_seed": task["task_seed"],
        "difficulty": task["difficulty"],
        "response": _response_for_task(task),
        "confidence": 0.6,
        "latency_ms": 1200,
        "client_trial_id": "trial_001",
        "expected_version_id": start_payload["source_version_id"],
    }
    submitted = client.post(
        f"/animus/studio/sessions/{session_id}/practice/trials", json=trial_request)
    assert submitted.status_code == 200, submitted.text
    payload = submitted.json()
    PracticeSubmitResponseModel.model_validate(payload)
    assert 0.0 <= payload["trial"]["outcome"]["score"] <= 1.0
    assert payload["next_task"] is not None
    assert payload["profile"]["trial_count"] == 1

    repeated = client.post(
        f"/animus/studio/sessions/{session_id}/practice/trials", json=trial_request)
    assert repeated.status_code == 200, repeated.text
    repeated_payload = repeated.json()
    assert repeated_payload["idempotent"] is True
    assert repeated_payload["trial"]["trial_id"] == payload["trial"]["trial_id"]
    assert repeated_payload["profile"]["trial_count"] == 1

    profile = client.get("/animus/studio/profile")
    assert profile.status_code == 200
    ProfileModel.model_validate(profile.json())
    assert profile.json()["trial_count"] == 1


def test_reconstruction_practice_records_error_signature(client):
    created = _create(client)
    session_id = created["session_id"]
    added = client.post(
        f"/animus/studio/sessions/{session_id}/commands",
        json={"commands": [
            {"op": "add_entity", "kind": "tree", "label": "north tree", "position": [2.0, 0.0, -1.0]},
            {"op": "add_entity", "kind": "moon", "label": "second moon", "position": [-2.0, 3.0, 1.0]},
            {"op": "add_entity", "kind": "rock", "label": "shore rock", "position": [1.0, 0.0, 2.0]},
        ]},
    )
    assert added.status_code == 200, added.text
    started = client.post(f"/animus/studio/sessions/{session_id}/practice/start", json={})
    assert started.status_code == 200, started.text
    payload = started.json()
    task = payload["task"]
    assert task["response_kind"] == "token_selection"
    assert task["tokens"]
    assert all("is_target" not in token for token in task["tokens"])

    submitted = client.post(
        f"/animus/studio/sessions/{session_id}/practice/trials",
        json={
            "task_id": task["task_id"], "task_type": task["task_type"],
            "task_seed": task["task_seed"], "difficulty": task["difficulty"],
            "response": {"selected_token_ids": [token["token_id"] for token in task["tokens"]]},
            "confidence": 0.7, "latency_ms": 1200, "client_trial_id": "trial_reconstruction",
            "expected_version_id": payload["source_version_id"],
        },
    )
    assert submitted.status_code == 200, submitted.text
    result = submitted.json()
    assert result["trial"]["task_family"] == "reconstruction"
    assert result["trial"]["response_kind"] == "token_selection"
    assert result["trial"]["scoring_version"] == "recon-v1"
    assert result["trial"]["outcome"]["error_profile"]["intrusions"] >= 1
    assert result["profile"]["error_signature"]["n"] == 1


def test_practice_requires_version_consistency(client):
    created = _create(client)
    session_id = created["session_id"]
    started = client.post(f"/animus/studio/sessions/{session_id}/practice/start", json={}).json()
    task = started["task"]
    changed = client.post(
        f"/animus/studio/sessions/{session_id}/commands",
        json={"commands": [{"op": "set_scene_attribute", "path": "style", "value": "gothic"}],
              "source_text": "stale task check"},
    )
    assert changed.status_code == 200, changed.text
    response = client.post(
        f"/animus/studio/sessions/{session_id}/practice/trials",
        json={
            "task_id": task["task_id"],
            "task_type": task["task_type"], "task_seed": task["task_seed"],
            "difficulty": task["difficulty"],
            "response": _response_for_task(task),
            "confidence": 0.5, "latency_ms": 500, "client_trial_id": "trial_stale",
            "expected_version_id": started["source_version_id"],
        },
    )
    assert response.status_code == 409
    assert response.headers["X-Studio-Error-Code"] == "stale_version"


def test_practice_task_id_binds_the_task_to_the_scene(client):
    created = _create(client)
    session_id = created["session_id"]
    started = client.post(f"/animus/studio/sessions/{session_id}/practice/start", json={}).json()
    task = started["task"]
    changed = client.post(
        f"/animus/studio/sessions/{session_id}/commands",
        json={"commands": [{"op": "set_scene_attribute", "path": "atmosphere.weather",
                            "value": "rain"}]},
    )
    assert changed.status_code == 200, changed.text
    response = client.post(
        f"/animus/studio/sessions/{session_id}/practice/trials",
        json={
            "task_id": task["task_id"], "task_type": task["task_type"],
            "task_seed": task["task_seed"], "difficulty": task["difficulty"],
            "response": _response_for_task(task),
            "confidence": 0.5, "latency_ms": 500, "client_trial_id": "trial_binding",
        },
    )
    assert response.status_code == 400
    assert response.headers["X-Studio-Error-Code"] == "invalid_request"


def test_capabilities_publish_profile_boundary(client):
    capabilities = client.get("/animus/studio/capabilities").json()["capabilities"]
    assert capabilities["behavioral_profile"] == "EXPERIMENTAL"
    assert capabilities["behavioral_reconstruction"] == "EXPERIMENTAL"
    assert capabilities["adaptive_practice"] == "EXPERIMENTAL"
    assert capabilities["clinical_use"] == "DISABLED"
