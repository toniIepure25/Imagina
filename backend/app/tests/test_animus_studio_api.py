"""HTTP contract for the Studio product API (router-only app, temporary local DB)."""
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
    SessionListResponseModel,
    StudioCommandsResponseModel,
    StudioEventsResponseModel,
    StudioHealthResponseModel,
    StudioHistoryResponseModel,
    StudioIntentResponseModel,
    StudioRegenerateResponseModel,
    StudioSnapshotModel,
    VersionDetailModel,
    WorldListResponseModel,
    WorldModel,
)

pytestmark = pytest.mark.core


@pytest.fixture
def client(monkeypatch):
    directory = tempfile.mkdtemp(prefix="animus-studio-api-")
    service = AnimusStudioService(repository=StudioRepository(str(Path(directory) / "studio.db")))
    monkeypatch.setattr(api_module, "studio_service", service)
    app = FastAPI()
    app.include_router(api_module.router)
    with TestClient(app) as test_client:
        yield test_client
    shutil.rmtree(directory, ignore_errors=True)


def _create(client: TestClient) -> dict:
    response = client.post("/animus/studio/sessions", json={
        "title": "Castle", "intention": "a white castle above a dark ocean at dusk", "seed": 13})
    assert response.status_code == 200, response.text
    return response.json()


def test_health_and_capabilities(client):
    health = client.get("/animus/studio/health").json()
    assert health["status"] == "ok"
    assert health["claim_level"] == "L1_BEHAVIORAL_ASSISTED"
    assert health["capabilities"]["image_generation"] == "DISABLED"
    assert health["capabilities"]["neural_content"] == "UNAUTHORIZED"
    capabilities = client.get("/animus/studio/capabilities").json()
    assert capabilities["capabilities"]["privacy_scope"] == "local_only"


def test_session_crud_and_snapshot_shape(client):
    created = _create(client)
    session_id = created["session_id"]
    assert created["scene"]["entities"]
    assert created["active_branch_name"] == "Main"
    assert created["last_event_seq"] >= 1
    listed = client.get("/animus/studio/sessions").json()
    assert any(item["session_id"] == session_id for item in listed["sessions"])
    fetched = client.get(f"/animus/studio/sessions/{session_id}")
    assert fetched.status_code == 200
    assert fetched.json()["session_id"] == session_id
    deleted = client.delete(f"/animus/studio/sessions/{session_id}")
    assert deleted.status_code == 200
    assert client.get(f"/animus/studio/sessions/{session_id}").status_code == 404


def test_typed_response_contract_matches_published_payloads(client):
    created = _create(client)
    session_id = created["session_id"]
    StudioSnapshotModel.model_validate(created)
    SessionListResponseModel.model_validate(client.get("/animus/studio/sessions").json())
    StudioHealthResponseModel.model_validate(client.get("/animus/studio/health").json())

    intent = client.post(f"/animus/studio/sessions/{session_id}/intent",
                         json={"text": "make the sky deep violet"})
    assert intent.status_code == 200, intent.text
    StudioIntentResponseModel.model_validate(intent.json())

    castle = next(e for e in intent.json()["scene"]["entities"] if e["kind"] == "castle")
    commands = client.post(f"/animus/studio/sessions/{session_id}/commands", json={
        "commands": [{"op": "lock", "entity_id": castle["id"], "locked": True}],
        "source_text": "typed contract",
    })
    assert commands.status_code == 200, commands.text
    StudioCommandsResponseModel.model_validate(commands.json())

    generated = client.post(f"/animus/studio/sessions/{session_id}/regenerate",
                            json={"count": 2, "seed": 5})
    assert generated.status_code == 200, generated.text
    StudioRegenerateResponseModel.model_validate(generated.json())

    history = client.get(f"/animus/studio/sessions/{session_id}/history")
    assert history.status_code == 200
    StudioHistoryResponseModel.model_validate(history.json())

    version = client.get(
        f"/animus/studio/sessions/{session_id}/versions/{created['version']['version_id']}")
    assert version.status_code == 200, version.text
    VersionDetailModel.model_validate(version.json())

    saved = client.post(f"/animus/studio/sessions/{session_id}/worlds",
                        json={"name": "Contract world", "description": "typed response"})
    assert saved.status_code == 200, saved.text
    StudioSnapshotModel.model_validate(client.get(f"/animus/studio/sessions/{session_id}").json())
    WorldModel.model_validate(saved.json())
    WorldListResponseModel.model_validate(client.get("/animus/studio/worlds").json())


def test_intent_and_commands(client):
    created = _create(client)
    session_id = created["session_id"]
    intent = client.post(f"/animus/studio/sessions/{session_id}/intent",
                         json={"text": "make the sky deep violet"})
    assert intent.status_code == 200, intent.text
    body = intent.json()
    assert body["version"]["number"] == 2
    assert body["resolutions"]

    castle = next(e for e in body["scene"]["entities"] if e["kind"] == "castle")
    commands = client.post(f"/animus/studio/sessions/{session_id}/commands", json={
        "commands": [{"op": "set_entity_attribute", "entity_id": castle["id"],
                      "path": "color", "value": "red", "lock": True}],
        "source_text": "manual edit",
    })
    assert commands.status_code == 200, commands.text
    updated = commands.json()
    assert next(e for e in updated["scene"]["entities"] if e["kind"] == "castle")[
        "attributes"]["color"]["value"] == "#e14b4b"


def test_element_lock_command_and_regeneration_preserve_it(client):
    created = _create(client)
    session_id = created["session_id"]
    castle = next(e for e in created["scene"]["entities"] if e["kind"] == "castle")
    locked = client.post(f"/animus/studio/sessions/{session_id}/commands", json={
        "commands": [{"op": "lock", "entity_id": castle["id"], "locked": True}],
        "source_text": "lock castle",
    })
    assert locked.status_code == 200, locked.text
    body = locked.json()
    assert body["version"]["number"] == 2
    assert next(e for e in body["scene"]["entities"] if e["id"] == castle["id"])["locked"] is True

    candidates = client.post(f"/animus/studio/sessions/{session_id}/regenerate", json={
        "count": 2, "strength": 0.5, "seed": 21, "preserve_user_edits": True})
    assert candidates.status_code == 200, candidates.text
    generated = candidates.json()
    assert len(generated["candidates"]) == 2
    for candidate in generated["candidates"]:
        assert castle["id"] in candidate["diff"]["locked_untouched"]
        assert candidate["diff"]["after_hash"] != body["version"]["content_hash"]


def test_clarification_returns_200_without_new_version(client):
    created = _create(client)
    session_id = created["session_id"]
    response = client.post(f"/animus/studio/sessions/{session_id}/intent",
                           json={"text": "make it better somehow"})
    assert response.status_code == 200
    body = response.json()
    assert body["needs_clarification"] is True
    assert body["version"]["number"] == 1
    assert body["clarification"]


def test_regenerate_and_select(client):
    created = _create(client)
    session_id = created["session_id"]
    response = client.post(f"/animus/studio/sessions/{session_id}/regenerate",
                           json={"count": 2, "seed": 4})
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["generated"]) == 2
    candidate_id = body["generated"][0]["candidate_id"]
    selected = client.post(
        f"/animus/studio/sessions/{session_id}/candidates/{candidate_id}/select")
    assert selected.status_code == 200, selected.text
    assert selected.json()["version"]["source"] == "candidate"


def test_undo_redo_and_history(client):
    created = _create(client)
    session_id = created["session_id"]
    root_hash = created["scene"]["metadata"]["content_hash"]
    client.post(f"/animus/studio/sessions/{session_id}/intent", json={"text": "make the sky deep violet"})
    undone = client.post(f"/animus/studio/sessions/{session_id}/undo").json()
    assert undone["scene"]["metadata"]["content_hash"] == root_hash
    redone = client.post(f"/animus/studio/sessions/{session_id}/redo").json()
    assert redone["version"]["number"] == 2
    history = client.get(f"/animus/studio/sessions/{session_id}/history").json()
    assert len(history["versions"]) == 2
    assert history["branches"][0]["is_active"] is True


def test_branch_and_switch(client):
    created = _create(client)
    session_id = created["session_id"]
    main_hash = created["scene"]["metadata"]["content_hash"]
    branched = client.post(f"/animus/studio/sessions/{session_id}/branches",
                           json={"name": "violet"}).json()
    branch_id = branched["active_branch_id"]
    assert branched["active_branch_name"] == "violet"
    client.post(f"/animus/studio/sessions/{session_id}/intent", json={"text": "make the sky deep violet"})
    switched = client.post(f"/animus/studio/sessions/{session_id}/branches/main/switch").json()
    assert switched["scene"]["metadata"]["content_hash"] == main_hash
    back = client.post(f"/animus/studio/sessions/{session_id}/branches/{branch_id}/switch").json()
    assert back["active_branch_id"] == branch_id


def test_event_history_is_ordered_and_cursorable(client):
    created = _create(client)
    session_id = created["session_id"]
    client.post(f"/animus/studio/sessions/{session_id}/intent", json={"text": "make the sky deep violet"})
    client.post(f"/animus/studio/sessions/{session_id}/intent", json={"text": "add a second moon"})

    response = client.get(f"/animus/studio/sessions/{session_id}/events")
    assert response.status_code == 200, response.text
    body = response.json()
    StudioEventsResponseModel.model_validate(body)
    events = body["events"]
    assert len(events) >= 2
    assert [event["seq"] for event in events] == sorted(event["seq"] for event in events)
    assert all(event["session_id"] == session_id for event in events)
    assert body["has_more"] is False

    cursor = client.get(
        f"/animus/studio/sessions/{session_id}/events?after_seq={events[0]['seq']}&limit=1")
    assert cursor.status_code == 200
    page = cursor.json()
    assert len(page["events"]) == 1
    assert page["events"][0]["seq"] > events[0]["seq"]
    assert page["has_more"] is True
    assert client.get("/animus/studio/sessions/ast_missing/events").status_code == 404


def test_health_deep_reports_sqlite_diagnostics(client):
    body = client.get("/animus/studio/health?deep=true").json()
    StudioHealthResponseModel.model_validate(body)
    assert body["journal_mode"] == "wal"
    assert body["synchronous"] == 2
    assert body["integrity"] == "ok"
    assert body["foreign_key_violations"] == 0


def test_openapi_publishes_success_and_error_contracts(client):
    paths = client.app.openapi()["paths"]
    studio_paths = {
        path: operations for path, operations in paths.items()
        if path.startswith("/animus/studio/")
    }
    assert studio_paths
    for path, operations in studio_paths.items():
        for method, operation in operations.items():
            if method not in {"get", "post", "delete", "put", "patch"}:
                continue
            assert "200" in operation["responses"], f"{method.upper()} {path}"
            for status in ("400", "404", "409", "503"):
                assert status in operation["responses"], f"{method.upper()} {path} missing {status}"
                headers = operation["responses"][status].get("headers", {})
                assert "X-Studio-Error-Code" in headers


def test_worlds(client):
    created = _create(client)
    session_id = created["session_id"]
    saved = client.post(f"/animus/studio/sessions/{session_id}/worlds",
                        json={"name": "Castle world", "description": "keep this"}).json()
    assert saved["items"]
    listed = client.get("/animus/studio/worlds").json()
    assert any(world["world_id"] == saved["world_id"] for world in listed["worlds"])
    opened = client.post(f"/animus/studio/worlds/{saved['world_id']}/open", json={}).json()
    assert opened["session_id"] != session_id
    fetched = client.get(f"/animus/studio/worlds/{saved['world_id']}").json()
    assert len(fetched["items"]) == len(saved["items"])
    assert client.delete(f"/animus/studio/worlds/{saved['world_id']}").status_code == 200


def test_errors_are_typed(client):
    assert client.get("/animus/studio/sessions/ast_missing").status_code == 404
    created = _create(client)
    session_id = created["session_id"]
    bad = client.post(f"/animus/studio/sessions/{session_id}/commands", json={
        "commands": [{"op": "explode"}]})
    assert bad.status_code == 400
    claim = client.post("/animus/studio/sessions", json={
        "title": "Mind reading", "intention": "a castle", "seed": 1})
    assert claim.status_code == 400
    assert "mind-reading" in claim.json()["detail"] or "mind-reading" in claim.text.lower()


def test_version_endpoint_returns_immutable_scene(client):
    created = _create(client)
    version_id = created["active_version_id"]
    version = client.get(f"/animus/studio/sessions/{created['session_id']}/versions/{version_id}").json()
    assert version["version_id"] == version_id
    assert version["content_hash"] == created["scene"]["metadata"]["content_hash"]


def test_expected_version_header_returns_typed_conflict(client):
    created = _create(client)
    session_id = created["session_id"]
    head = created["active_version_id"]

    accepted = client.post(
        f"/animus/studio/sessions/{session_id}/intent",
        json={"text": "make the sky deep violet"},
        headers={"X-Expected-Version": head},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["version"]["number"] == 2

    stale = client.post(
        f"/animus/studio/sessions/{session_id}/intent",
        json={"text": "make the sky deep violet"},
        headers={"X-Expected-Version": head},
    )
    assert stale.status_code == 409
    assert stale.headers["X-Studio-Error-Code"] == "stale_version"
    assert "changed" in stale.json()["detail"]


def test_request_models_reject_unknown_fields_and_oversized_values(client):
    created = _create(client)
    session_id = created["session_id"]
    unknown = client.post(
        f"/animus/studio/sessions/{session_id}/intent",
        json={"text": "make the sky deep violet", "unexpected": True},
    )
    assert unknown.status_code == 422

    too_many = client.post(
        f"/animus/studio/sessions/{session_id}/regenerate",
        json={"count": 99},
    )
    assert too_many.status_code == 422

    bad_path = client.get("/animus/studio/sessions/not valid!")
    assert bad_path.status_code == 422
