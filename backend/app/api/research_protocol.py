from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.research import consent_gate, instrument_registry, participant_registry, study_manager
from app.research.governance import evaluate_collection_readiness, get_system_capabilities
from app.research.randomization import verify_counterbalance
from app.schemas.research import ConsentCreate, ParticipantCreate, StudyCreate

router = APIRouter(prefix="/api/research-protocol", tags=["research-protocol"])


def _check_study_mode(minimum: str = "pilot"):
    if not study_manager.require_study_mode(settings.study_mode, minimum):
        raise HTTPException(
            status_code=403,
            detail=f"Operation requires study_mode >= '{minimum}', current is '{settings.study_mode}'",
        )


@router.get("/mode")
async def get_study_mode():
    return {"study_mode": settings.study_mode}


@router.get("/capabilities")
async def get_capabilities():
    return await get_system_capabilities()


@router.get("/readiness/{study_id}/{participant_id}")
async def check_readiness(study_id: str, participant_id: str):
    result = await evaluate_collection_readiness(study_id, participant_id)
    return {"allowed": result.allowed, "checks": [vars(c) for c in result.checks]}


@router.get("/instruments")
async def list_instruments():
    return {"instruments": [i.model_dump() for i in instrument_registry.list_instruments()]}


@router.get("/instruments/{instrument_id}")
async def get_instrument(instrument_id: str):
    info = instrument_registry.get_instrument(instrument_id)
    if not info:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return info.model_dump()


@router.post("/studies")
async def create_study(data: StudyCreate):
    _check_study_mode("pilot")
    existing = await study_manager.get_study(data.study_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Study '{data.study_id}' already exists")
    study = await study_manager.create_study(data)
    return study.model_dump()


@router.get("/studies")
async def list_studies():
    _check_study_mode("pilot")
    studies = await study_manager.list_studies()
    return {"studies": [s.model_dump() for s in studies]}


@router.get("/studies/{study_id}")
async def get_study(study_id: str):
    _check_study_mode("pilot")
    study = await study_manager.get_study(study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    return study.model_dump()


@router.post("/studies/{study_id}/participants")
async def create_participant(study_id: str, data: ParticipantCreate):
    _check_study_mode("pilot")
    if data.study_id != study_id:
        raise HTTPException(status_code=400, detail="study_id mismatch")
    study = await study_manager.get_study(study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    participant = await participant_registry.create_participant(data, study.conditions)
    return participant.model_dump()


@router.get("/studies/{study_id}/participants")
async def list_participants(study_id: str):
    _check_study_mode("pilot")
    participants = await participant_registry.list_participants(study_id)
    return {"participants": [p.model_dump() for p in participants]}


@router.get("/participants/{participant_id}")
async def get_participant(participant_id: str):
    _check_study_mode("pilot")
    participant = await participant_registry.get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    return participant.model_dump()


@router.post("/consent")
async def record_consent(data: ConsentCreate):
    _check_study_mode("pilot")
    participant = await participant_registry.get_participant(data.participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    try:
        record = await consent_gate.record_consent(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return record.model_dump()


@router.get("/consent/{participant_id}/{study_id}")
async def check_consent(participant_id: str, study_id: str):
    has_consent = await consent_gate.has_valid_consent(participant_id, study_id)
    return {"has_valid_consent": has_consent}


@router.post("/consent/{participant_id}/{study_id}/withdraw")
async def withdraw_consent(participant_id: str, study_id: str):
    _check_study_mode("pilot")
    result = await consent_gate.withdraw_consent(participant_id, study_id)
    if not result:
        raise HTTPException(status_code=404, detail="No consent record found")
    return {"withdrawn": True}


@router.get("/studies/{study_id}/condition/{participant_id}/{session_index}")
async def get_condition_assignment(study_id: str, participant_id: str, session_index: int):
    _check_study_mode("pilot")
    assignment = await study_manager.get_condition_for_session(participant_id, study_id, session_index)
    if not assignment:
        participant = await participant_registry.get_participant(participant_id)
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
        if session_index >= len(participant.condition_sequence):
            raise HTTPException(status_code=400, detail="Session index out of range")
        condition = participant.condition_sequence[session_index]
        assignment = await study_manager.assign_condition(participant_id, study_id, session_index, condition)
    return assignment.model_dump()


@router.get("/studies/{study_id}/counterbalance")
async def check_counterbalance(study_id: str):
    _check_study_mode("pilot")
    study = await study_manager.get_study(study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    participants = await participant_registry.list_participants(study_id)
    sequences = [p.condition_sequence for p in participants]
    report = verify_counterbalance(sequences, study.conditions)
    return report
