import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.storage.database import init_db


@pytest.fixture(autouse=True)
async def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("app.storage.database.DB_PATH", db_path)
    await init_db()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_health(client: AsyncClient):
    r = await client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


async def test_tasks(client: AsyncClient):
    r = await client.get("/api/tasks")
    assert r.status_code == 200
    tasks = r.json()
    assert len(tasks) >= 3


async def test_session_lifecycle(client: AsyncClient):
    r = await client.post(
        "/api/sessions",
        json={"display_name": "smoke", "task_id": "corridor_simple"},
    )
    assert r.status_code == 200
    sid = r.json()["session_id"]

    r = await client.post(
        f"/api/sessions/{sid}/baseline",
        json={"focus": 7, "relaxation": 5, "vividness": 6, "fatigue": 2},
    )
    assert r.status_code == 200

    r = await client.post(f"/api/sessions/{sid}/start")
    assert r.status_code == 200
    assert r.json()["status"] == "running"

    r = await client.post(
        f"/api/sessions/{sid}/self-report",
        json={
            "vividness": 7, "stability": 6, "focus": 7, "relaxation": 5,
            "effort": 5, "fatigue": 3, "distraction": 2,
        },
    )
    assert r.status_code == 200

    r = await client.post(f"/api/sessions/{sid}/stop")
    assert r.status_code == 200
    assert r.json()["status"] == "completed"

    r = await client.get(f"/api/sessions/{sid}/summary")
    assert r.status_code == 200
    assert r.json()["session_id"] == sid


async def test_start_without_baseline_returns_conflict(client: AsyncClient):
    r = await client.post(
        "/api/sessions",
        json={"display_name": "smoke", "task_id": "corridor_simple"},
    )
    assert r.status_code == 200
    sid = r.json()["session_id"]

    r = await client.post(f"/api/sessions/{sid}/start")
    assert r.status_code == 409
    assert "Baseline is required" in r.text
