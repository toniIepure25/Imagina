import pytest

from app.services.replay_service import create_demo_session
from app.services.report_service import generate_summary
from app.storage.database import init_db


@pytest.fixture(autouse=True)
async def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("app.storage.database.DB_PATH", db_path)
    await init_db()


async def test_report_has_required_fields():
    session = await create_demo_session(scenario="improving_user", seed=42, duration_windows=10)
    summary = await generate_summary(session.session_id)
    assert summary.session_id == session.session_id
    assert summary.duration_seconds >= 0
    assert 0 <= summary.average_iqi <= 1
    assert 0 <= summary.average_pid <= 1
    assert 0 <= summary.best_iqi <= 1
    assert summary.max_level_reached >= 1
    assert summary.recommendation
    assert summary.generated_at
