"""WebSocket contract for the live ANIMUS Studio channel."""
from __future__ import annotations

import asyncio
import pathlib
import shutil
import tempfile

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api import animus_studio_ws as ws_module
from app.core.animus.studio.bus import AnimusEventBus
from app.core.animus.studio.errors import StudioPersistenceError
from app.core.animus.studio.repository import StudioRepository
from app.core.animus.studio.service import AnimusStudioService

pytestmark = pytest.mark.core


@pytest.fixture
def service():
    directory = tempfile.mkdtemp(prefix="animus-studio-ws-")
    svc = AnimusStudioService(repository=StudioRepository(str(pathlib.Path(directory) / "studio.db")))
    yield svc
    shutil.rmtree(directory, ignore_errors=True)


@pytest.fixture
def client(service, monkeypatch):
    monkeypatch.setattr(ws_module, "studio_service", service)
    app = FastAPI()
    app.include_router(ws_module.router)
    with TestClient(app) as test_client:
        yield test_client


def _create(service: AnimusStudioService) -> dict:
    created = asyncio.run(service.create_session(
        title="Live", intention="a white castle above a dark ocean at dusk", seed=31))
    return created


def _url(session_id: str) -> str:
    return f"/ws/animus/{session_id}"


def test_snapshot_on_connect(client, service):
    created = _create(service)
    with client.websocket_connect(_url(created["session_id"])) as ws:
        message = ws.receive_json()
        assert message["type"] == "snapshot"
        assert message["session"]["session_id"] == created["session_id"]
        assert message["session"]["last_event_seq"] == created["last_event_seq"]
        assert message["session"]["scene"]["entities"]


def test_event_is_not_lost_between_snapshot_and_subscribe(client, service, monkeypatch):
    created = _create(service)
    session_id = created["session_id"]
    original = service.get_session

    async def delayed_snapshot(target: str) -> dict:
        await service.bus.publish(target, {"type": "gap_probe", "session_id": target})
        return await original(target)

    monkeypatch.setattr(service, "get_session", delayed_snapshot)
    with client.websocket_connect(_url(session_id)) as ws:
        assert ws.receive_json()["type"] == "snapshot"
        event = ws.receive_json()
        assert event["type"] == "event"
        assert event["event_type"] == "gap_probe"


def test_ws_intent_streams_event_and_snapshot(client, service):
    created = _create(service)
    session_id = created["session_id"]
    with client.websocket_connect(_url(session_id)) as ws:
        assert ws.receive_json()["type"] == "snapshot"
        ws.send_json({"type": "intent", "text": "make the sky deep violet"})
        received = [ws.receive_json(), ws.receive_json()]
        assert {message["type"] for message in received} == {"event", "snapshot"}
        event = next(message for message in received if message["type"] == "event")
        assert event["seq"] == created["last_event_seq"] + 1
        snapshot = next(message["session"] for message in received if message["type"] == "snapshot")
        assert snapshot["version"]["number"] == 2
        assert snapshot["last_event_seq"] == event["seq"]


def test_ws_stale_version_is_typed(client, service):
    created = _create(service)
    session_id = created["session_id"]
    old_head = created["active_version_id"]
    with client.websocket_connect(_url(session_id)) as ws:
        assert ws.receive_json()["type"] == "snapshot"
        ws.send_json({"type": "intent", "text": "make the sky deep violet", "expected_version_id": old_head})
        first = [ws.receive_json(), ws.receive_json()]
        assert {message["type"] for message in first} == {"event", "snapshot"}
        ws.send_json({"type": "intent", "text": "make it darker", "expected_version_id": old_head})
        error = ws.receive_json()
        assert error["type"] == "error"
        assert error["code"] == "stale_version"


def test_ws_persistence_error_is_not_reported_as_invalid_request(client, service, monkeypatch):
    created = _create(service)
    session_id = created["session_id"]

    async def fail(*args, **kwargs):
        raise StudioPersistenceError("disk unavailable")

    monkeypatch.setattr(service, "apply_intent", fail)
    with client.websocket_connect(_url(session_id)) as ws:
        assert ws.receive_json()["type"] == "snapshot"
        ws.send_json({"type": "intent", "text": "make the sky deep violet"})
        error = ws.receive_json()
        assert error["code"] == "persistence_failed"


def test_ws_rejects_bad_origin(client, service):
    created = _create(service)
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(_url(created["session_id"]), headers={"origin": "http://evil.test"}):
            pass
    assert exc.value.code == 1008


def test_ws_rejects_oversized_message(client, service):
    created = _create(service)
    with client.websocket_connect(_url(created["session_id"])) as ws:
        assert ws.receive_json()["type"] == "snapshot"
        ws.send_text("x" * (64 * 1024 + 1))
        with pytest.raises(WebSocketDisconnect) as exc:
            while True:
                ws.receive_json()
        assert exc.value.code == 1009


def test_ws_malformed_and_unknown_messages(client, service):
    created = _create(service)
    with client.websocket_connect(_url(created["session_id"])) as ws:
        assert ws.receive_json()["type"] == "snapshot"
        ws.send_text("{")
        assert ws.receive_json()["code"] == "invalid_json"
        ws.send_json(["not", "an", "object"])
        assert ws.receive_json()["code"] == "invalid_message"
        ws.send_json({"type": "nope"})
        assert ws.receive_json()["code"] == "unsupported_message"
        ws.send_json({"type": "ping"})
        assert ws.receive_json()["type"] == "pong"


def test_ws_unknown_session_returns_typed_error(client):
    with client.websocket_connect(_url("ast_missing")) as ws:
        error = ws.receive_json()
        assert error["type"] == "error"
        assert error["code"] == "not_found"


def test_bus_overflow_emits_resync_marker():
    async def scenario():
        bus = AnimusEventBus()
        queue = await bus.subscribe("ast_test")
        for index in range(70):
            await bus.publish("ast_test", {"type": "tick", "index": index})
        drained = []
        while not queue.empty():
            drained.append(queue.get_nowait())
        await bus.unsubscribe("ast_test", queue)
        return drained

    events = asyncio.run(scenario())
    assert events[0]["type"] == "resync_required"
    assert events[-1]["type"] == "tick"
    assert len(events) == 7
