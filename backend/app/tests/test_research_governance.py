import pytest

from app.research.instrument_registry import get_instrument, list_instruments
from app.research.randomization import (
    generate_block_randomization,
    generate_condition_sequence,
    verify_counterbalance,
)
from app.schemas.research import (
    ConsentCreate,
    FeedbackCondition,
    ParticipantCreate,
    StudyCreate,
)
from app.storage.database import init_db


@pytest.fixture(autouse=True)
async def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_research.db")
    monkeypatch.setattr("app.storage.database.DB_PATH", db_path)
    _get_db = __import__("app.storage.database", fromlist=["get_db"]).get_db
    monkeypatch.setattr("app.research.study_manager.get_db", _get_db)
    monkeypatch.setattr("app.research.participant_registry.get_db", _get_db)
    monkeypatch.setattr("app.research.consent_gate.get_db", _get_db)
    await init_db()


class TestStudyMode:
    def test_require_demo_always_true(self):
        from app.research.study_manager import require_study_mode
        assert require_study_mode("demo", "demo") is True

    def test_require_pilot_blocks_demo(self):
        from app.research.study_manager import require_study_mode
        assert require_study_mode("demo", "pilot") is False

    def test_require_pilot_allows_pilot(self):
        from app.research.study_manager import require_study_mode
        assert require_study_mode("pilot", "pilot") is True

    def test_require_approved_allows_approved(self):
        from app.research.study_manager import require_study_mode
        assert require_study_mode("approved_study", "approved_study") is True

    def test_require_approved_blocks_pilot(self):
        from app.research.study_manager import require_study_mode
        assert require_study_mode("pilot", "approved_study") is False


class TestRandomization:
    def test_sequence_length_matches_conditions(self):
        conditions = [FeedbackCondition.ADAPTIVE, FeedbackCondition.FIXED, FeedbackCondition.YOKED]
        seq = generate_condition_sequence(conditions, seed=42)
        assert len(seq) == 3
        assert set(seq) == set(conditions)

    def test_sequence_deterministic(self):
        conditions = [FeedbackCondition.ADAPTIVE, FeedbackCondition.FIXED, FeedbackCondition.YOKED]
        seq1 = generate_condition_sequence(conditions, seed=123)
        seq2 = generate_condition_sequence(conditions, seed=123)
        assert seq1 == seq2

    def test_different_seeds_can_differ(self):
        conditions = [FeedbackCondition.ADAPTIVE, FeedbackCondition.FIXED, FeedbackCondition.YOKED]
        results = set()
        for seed in range(100):
            seq = generate_condition_sequence(conditions, seed=seed)
            results.add(tuple(seq))
        assert len(results) > 1

    def test_block_randomization_balanced(self):
        conditions = [FeedbackCondition.ADAPTIVE, FeedbackCondition.FIXED, FeedbackCondition.YOKED]
        assignments = generate_block_randomization(conditions, n_participants=12)
        assert len(assignments) == 12
        report = verify_counterbalance(assignments, conditions)
        assert report["balanced"] is True
        assert report["min_per_order"] == 2
        assert report["max_per_order"] == 2

    def test_block_randomization_uneven(self):
        conditions = [FeedbackCondition.ADAPTIVE, FeedbackCondition.FIXED, FeedbackCondition.YOKED]
        assignments = generate_block_randomization(conditions, n_participants=7)
        report = verify_counterbalance(assignments, conditions)
        assert report["max_per_order"] - report["min_per_order"] <= 1


class TestStudyManager:
    async def test_create_and_get_study(self):
        from app.research.study_manager import create_study, get_study

        data = StudyCreate(
            study_id="test-study-001",
            title="Test Study",
            protocol_version="1.0",
        )
        study = await create_study(data)
        assert study.study_id == "test-study-001"
        assert study.status == "created"
        assert len(study.conditions) == 3

        fetched = await get_study("test-study-001")
        assert fetched is not None
        assert fetched.title == "Test Study"

    async def test_duplicate_study_fails(self):
        from app.research.study_manager import create_study

        data = StudyCreate(study_id="dup-study", title="Dup", protocol_version="1.0")
        await create_study(data)
        with pytest.raises(Exception):
            await create_study(data)

    async def test_list_studies(self):
        from app.research.study_manager import create_study, list_studies

        await create_study(StudyCreate(study_id="s1", title="S1", protocol_version="1.0"))
        await create_study(StudyCreate(study_id="s2", title="S2", protocol_version="1.0"))
        studies = await list_studies()
        ids = {s.study_id for s in studies}
        assert "s1" in ids
        assert "s2" in ids


class TestParticipantRegistry:
    async def test_create_participant_with_sequence(self):
        from app.research.participant_registry import create_participant
        from app.research.study_manager import create_study

        await create_study(StudyCreate(study_id="ps1", title="PS1", protocol_version="1.0"))
        conditions = [FeedbackCondition.ADAPTIVE, FeedbackCondition.FIXED, FeedbackCondition.YOKED]
        participant = await create_participant(
            ParticipantCreate(pseudonym="P001", study_id="ps1"),
            conditions,
        )
        assert participant.pseudonym == "P001"
        assert len(participant.condition_sequence) == 3
        assert set(participant.condition_sequence) == set(conditions)

    async def test_list_participants_by_study(self):
        from app.research.participant_registry import create_participant, list_participants
        from app.research.study_manager import create_study

        await create_study(StudyCreate(study_id="ps2", title="PS2", protocol_version="1.0"))
        conditions = [FeedbackCondition.ADAPTIVE, FeedbackCondition.FIXED]
        await create_participant(ParticipantCreate(pseudonym="A", study_id="ps2"), conditions)
        await create_participant(ParticipantCreate(pseudonym="B", study_id="ps2"), conditions)
        participants = await list_participants("ps2")
        assert len(participants) == 2


class TestConsentGate:
    async def test_no_consent_by_default(self):
        from app.research.consent_gate import has_valid_consent
        assert await has_valid_consent("nonexistent", "nonexistent") is False

    async def test_record_and_check_consent(self):
        from app.research.consent_gate import has_valid_consent, record_consent
        from app.research.participant_registry import create_participant
        from app.research.study_manager import create_study

        await create_study(StudyCreate(study_id="cs1", title="CS1", protocol_version="1.0"))
        p = await create_participant(
            ParticipantCreate(pseudonym="C001", study_id="cs1"),
            [FeedbackCondition.ADAPTIVE],
        )
        await record_consent(ConsentCreate(
            participant_id=p.participant_id,
            study_id="cs1",
            consent_version="v1.0",
        ))
        assert await has_valid_consent(p.participant_id, "cs1") is True

    async def test_withdraw_consent(self):
        from app.research.consent_gate import has_valid_consent, record_consent, withdraw_consent
        from app.research.participant_registry import create_participant
        from app.research.study_manager import create_study

        await create_study(StudyCreate(study_id="cs2", title="CS2", protocol_version="1.0"))
        p = await create_participant(
            ParticipantCreate(pseudonym="C002", study_id="cs2"),
            [FeedbackCondition.ADAPTIVE],
        )
        await record_consent(ConsentCreate(
            participant_id=p.participant_id,
            study_id="cs2",
            consent_version="v1.0",
        ))
        assert await has_valid_consent(p.participant_id, "cs2") is True
        await withdraw_consent(p.participant_id, "cs2")
        assert await has_valid_consent(p.participant_id, "cs2") is False


class TestConditionAssignment:
    async def test_assign_and_retrieve(self):
        from app.research.participant_registry import create_participant
        from app.research.study_manager import assign_condition, create_study, get_condition_for_session

        await create_study(StudyCreate(study_id="ca1", title="CA1", protocol_version="1.0"))
        p = await create_participant(
            ParticipantCreate(pseudonym="D001", study_id="ca1"),
            [FeedbackCondition.ADAPTIVE, FeedbackCondition.FIXED, FeedbackCondition.YOKED],
        )
        assignment = await assign_condition(p.participant_id, "ca1", 0, FeedbackCondition.ADAPTIVE)
        assert assignment.condition == FeedbackCondition.ADAPTIVE
        assert assignment.session_index == 0

        fetched = await get_condition_for_session(p.participant_id, "ca1", 0)
        assert fetched is not None
        assert fetched.condition == FeedbackCondition.ADAPTIVE

    async def test_duplicate_assignment_fails(self):
        from app.research.participant_registry import create_participant
        from app.research.study_manager import assign_condition, create_study

        await create_study(StudyCreate(study_id="ca2", title="CA2", protocol_version="1.0"))
        p = await create_participant(
            ParticipantCreate(pseudonym="D002", study_id="ca2"),
            [FeedbackCondition.ADAPTIVE],
        )
        await assign_condition(p.participant_id, "ca2", 0, FeedbackCondition.ADAPTIVE)
        with pytest.raises(Exception):
            await assign_condition(p.participant_id, "ca2", 0, FeedbackCondition.FIXED)


class TestInstrumentRegistry:
    def test_list_instruments(self):
        instruments = list_instruments()
        assert len(instruments) >= 7
        ids = {i.instrument_id for i in instruments}
        assert "vviq2" in ids
        assert "perceived_contingency" in ids
        assert "vividness_trial" in ids

    def test_vviq2_no_items(self):
        info = get_instrument("vviq2")
        assert info is not None
        assert info.items_included is False

    def test_perceived_contingency_has_items(self):
        info = get_instrument("perceived_contingency")
        assert info is not None
        assert info.items_included is True

    def test_unknown_instrument(self):
        assert get_instrument("nonexistent") is None


class TestSchemaValidation:
    def test_study_create_requires_fields(self):
        with pytest.raises(Exception):
            StudyCreate(study_id="", title="T", protocol_version="1.0")  # type: ignore[arg-type]

    def test_condition_enum_values(self):
        assert FeedbackCondition.ADAPTIVE == "adaptive"
        assert FeedbackCondition.FIXED == "fixed"
        assert FeedbackCondition.YOKED == "yoked"

    def test_participant_create(self):
        p = ParticipantCreate(pseudonym="P001", study_id="s1")
        assert p.eligibility_confirmed is False
