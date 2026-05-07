import pytest

from app.reports.json_report import generate_json_report
from app.schemas.calibration import CalibrationCompleteInput
from app.schemas.experiments import ExperimentRunCreate
from app.schemas.profile import UserProfileCreate
from app.services import (
    calibration_service,
    experiment_service,
    export_service,
    personalization_service,
    report_service,
    session_service,
)
from app.storage.database import init_db


@pytest.fixture(autouse=True)
async def setup_db(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.database.DB_PATH", str(tmp_path / "test.db"))
    await init_db()


async def test_profile_create_and_recommendation():
    profile = await personalization_service.create_local_profile(UserProfileCreate(display_name="tester"))
    rec = await personalization_service.recommendation(profile.user_id)
    assert rec is not None
    assert rec.recommended_starting_level >= 1


async def test_experiment_run_creation_and_summary():
    run = await experiment_service.create_run(ExperimentRunCreate(protocol_id="catch_trial_validation_v1"))
    summary = await experiment_service.run_summary(run.run_id)
    assert summary is not None
    assert summary["catch_trial_count"] > 0


async def test_integrated_research_workflow_updates_profile_and_exports():
    profile = await personalization_service.create_local_profile(UserProfileCreate(display_name="researcher"))
    run = await experiment_service.create_run(
        ExperimentRunCreate(protocol_id="adaptive_guided_v1", participant_label="researcher")
    )

    session = await experiment_service.next_session(run.run_id, user_id=profile.user_id)
    assert session is not None
    assert session.experiment_run_id == run.run_id
    assert session.signal_provider_id == "simulated.default"

    calibration = await calibration_service.complete_calibration(
        session.session_id,
        session.user_id,
        CalibrationCompleteInput(
            duration_seconds=30,
            mode="simulated",
            focus=7,
            relaxation=6,
            vividness=6,
            fatigue=3,
        ),
    )
    assert 0 <= calibration.calibration_quality_score <= 1

    started = await session_service.start_session(session.session_id)
    assert started.status == "running"
    stopped = await session_service.stop_session(session.session_id)
    assert stopped.status == "completed"

    summary = await report_service.generate_summary(session.session_id)
    updated_profile = await personalization_service.get_profile(profile.user_id)
    assert updated_profile is not None
    assert updated_profile.total_sessions == 1
    await personalization_service.update_profile_after_summary(profile.user_id, summary)
    assert (await personalization_service.get_profile(profile.user_id)).total_sessions == 1

    progress = await experiment_service.run_progress(run.run_id)
    assert progress is not None
    assert progress["completed_count"] == 1

    report = await generate_json_report(session.session_id, summary)
    assert report["metadata"]["experiment_run_id"] == run.run_id
    assert report["calibration"]["calibration_id"] == calibration.calibration_id
    assert "events_jsonl" in report["exports"]

    timeline_csv = await export_service.timeline_csv(session.session_id)
    assert "timestamp,event_type,window_index" in timeline_csv
    events = await export_service.events_jsonl(session.session_id)
    assert "session_started" in events


async def test_export_data_dictionary_and_jsonl_shape():
    dictionary = export_service.data_dictionary_markdown()
    assert "IMAGINA Data Dictionary" in dictionary
    assert await export_service.events_jsonl("missing") == ""


def test_protocols_available():
    assert len(experiment_service.list_protocols()) >= 3
