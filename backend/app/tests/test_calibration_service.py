import pytest

from app.schemas.calibration import CalibrationCompleteInput
from app.schemas.session import SessionCreate
from app.services import calibration_service, session_service
from app.storage.database import init_db


@pytest.fixture(autouse=True)
async def setup_db(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.database.DB_PATH", str(tmp_path / "test.db"))
    await init_db()


async def test_good_calibration_profile_quality_range():
    session = await session_service.create_session(SessionCreate())
    profile = await calibration_service.complete_calibration(
        session.session_id,
        session.user_id,
        CalibrationCompleteInput(focus=7, relaxation=7, vividness=6, fatigue=2, duration_seconds=30),
    )
    assert 0 <= profile.calibration_quality_score <= 1
    assert profile.normalization_params


async def test_low_quality_calibration_warns():
    session = await session_service.create_session(SessionCreate())
    profile = await calibration_service.complete_calibration(
        session.session_id,
        session.user_id,
        CalibrationCompleteInput(focus=1, relaxation=9, vividness=5, fatigue=9, duration_seconds=5),
    )
    assert "baseline_too_short" in profile.warnings
    assert "high_baseline_fatigue" in profile.warnings
