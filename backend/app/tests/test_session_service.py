import pytest

from app.schemas.session import SessionCreate
from app.services import session_service
from app.storage.database import init_db


@pytest.fixture(autouse=True)
async def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("app.storage.database.DB_PATH", db_path)
    await init_db()


async def test_create_session():
    session = await session_service.create_session(
        SessionCreate(display_name="test_user")
    )
    assert session.session_id
    assert session.status == "created"
    assert session.display_name == "test_user"


async def test_start_stop_session():
    session = await session_service.create_session(SessionCreate())
    await session_service.store_baseline(
        session.session_id,
        {"focus": 6, "relaxation": 5, "vividness": 5, "fatigue": 3},
    )
    started = await session_service.start_session(session.session_id)
    assert started.status == "running"
    stopped = await session_service.stop_session(session.session_id)
    assert stopped.status == "completed"


async def test_start_requires_baseline():
    session = await session_service.create_session(SessionCreate())
    with pytest.raises(Exception, match="Baseline is required"):
        await session_service.start_session(session.session_id)


async def test_store_baseline():
    session = await session_service.create_session(SessionCreate())
    baseline = {
        "focus": 7, "relaxation": 6, "vividness": 5, "fatigue": 3,
    }
    await session_service.store_baseline(session.session_id, baseline)
    bl = await session_service.get_baseline(session.session_id)
    assert bl is not None
    assert bl["focus"] == 7
