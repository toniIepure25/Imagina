"""ANIMUS Studio product API (local-first, claim-safe).

All mutation endpoints return the same snapshot shape so the client can replace its state atomically.
Mutations are serialized per session in the service; an optional ``X-Expected-Version`` header gives
clients optimistic concurrency without changing the request bodies.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Path, Query

from app.core.animus.studio.claims import capability_envelope, claim_envelope
from app.core.animus.studio.errors import (
    StudioArchived,
    StudioConflict,
    StudioCorruptState,
    StudioError,
    StudioNotFound,
    StudioPersistenceError,
    StudioValidationError,
)
from app.core.animus.studio.service import studio_service
from app.schemas.animus_studio import (
    StudioBranchRequest,
    StudioCommandsRequest,
    StudioContrastReflectionRequest,
    StudioContrastStartRequest,
    StudioContrastSubmitRequest,
    StudioCreateRequest,
    StudioIntentRequest,
    StudioInterviewStartRequest,
    StudioInterviewSubmitRequest,
    StudioOpenWorldRequest,
    StudioPracticeStartRequest,
    StudioPracticeSubmitRequest,
    StudioRegenerateRequest,
    StudioWorldRequest,
)
from app.schemas.animus_studio_responses import (
    ContrastListResponseModel,
    ContrastStartResponseModel,
    ContrastSubmitResponseModel,
    ContrastSummaryResponseModel,
    DeleteResponseModel,
    InterviewListResponseModel,
    InterviewStartResponseModel,
    InterviewSubmitResponseModel,
    InterviewSummaryResponseModel,
    ObservatoryModel,
    PracticeStartResponseModel,
    PracticeSubmitResponseModel,
    ProfileModel,
    ProtocolListResponseModel,
    SessionListResponseModel,
    StudioCapabilitiesResponseModel,
    StudioCommandsResponseModel,
    StudioErrorResponseModel,
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

_ERROR_RESPONSES = {
    status: {
        "model": StudioErrorResponseModel,
        "description": description,
        "headers": {
            "X-Studio-Error-Code": {
                "description": "Stable machine-readable Studio error code.",
                "schema": {"type": "string"},
            }
        },
    }
    for status, description in {
        400: "The request is invalid for the current Studio state.",
        404: "The session, version, branch, candidate or world does not exist.",
        409: "The session is archived or the expected version is stale.",
        503: "The local Studio database is unavailable or corrupt.",
    }.items()
}

router = APIRouter(
    prefix="/animus/studio",
    tags=["animus-studio"],
    responses=_ERROR_RESPONSES,
)

SessionId = Annotated[str, Path(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")]
WorldId = Annotated[str, Path(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")]
CandidateId = Annotated[str, Path(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")]
VersionId = Annotated[str, Path(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")]
BranchId = Annotated[str, Path(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")]
InterviewId = Annotated[str, Path(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")]
ContrastId = Annotated[str, Path(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")]
ExpectedVersion = Annotated[str | None, Header(alias="X-Expected-Version", max_length=80)]


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail=message,
        headers={"X-Studio-Error-Code": code},
    )


async def _call(awaiter):
    try:
        return await awaiter
    except StudioArchived as exc:
        raise _error(409, "session_archived", str(exc)) from exc
    except StudioConflict as exc:
        raise _error(409, "stale_version", str(exc)) from exc
    except StudioNotFound as exc:
        raise _error(404, "not_found", str(exc)) from exc
    except StudioValidationError as exc:
        raise _error(400, "invalid_request", str(exc)) from exc
    except StudioPersistenceError as exc:
        raise _error(503, "persistence_failed", str(exc)) from exc
    except StudioCorruptState as exc:
        raise _error(503, "corrupt_local_state", str(exc)) from exc
    except StudioError as exc:
        raise _error(400, "studio_error", str(exc)) from exc


@router.get("/health", response_model=StudioHealthResponseModel)
async def health(deep: bool = Query(default=False)):
    try:
        diagnostics = await studio_service.repository.diagnostics(deep=deep)
    except Exception as exc:  # noqa: BLE001 - health must not leak internals
        raise _error(503, "database_unavailable", "The local Studio database is unavailable") from exc
    return {
        "status": "ok",
        "system": "ANIMUS Studio",
        "product": "closed-loop imagination amplifier",
        **diagnostics,
        **claim_envelope(),
        "capabilities": capability_envelope(),
    }


@router.get("/capabilities", response_model=StudioCapabilitiesResponseModel)
async def capabilities():
    return {**claim_envelope(), "capabilities": capability_envelope()}


@router.get("/profile", response_model=ProfileModel)
async def profile():
    return await _call(studio_service.profile())


@router.post("/profile/reset", response_model=ProfileModel)
async def reset_profile():
    return await _call(studio_service.reset_profile())


@router.get("/protocols", response_model=ProtocolListResponseModel)
async def protocols():
    return await _call(studio_service.list_protocols())


@router.post("/sessions/{session_id}/practice/start", response_model=PracticeStartResponseModel)
async def practice_start(
    session_id: SessionId,
    req: StudioPracticeStartRequest | None = None,
):
    return await _call(studio_service.practice_start(
        session_id,
        task_type=req.task_type if req else None,
        difficulty=req.difficulty if req else None,
    ))


@router.post("/sessions/{session_id}/practice/trials", response_model=PracticeSubmitResponseModel)
async def practice_submit(
    session_id: SessionId,
    req: StudioPracticeSubmitRequest,
    expected_version: ExpectedVersion = None,
):
    return await _call(studio_service.practice_submit(
        session_id,
        task_id=req.task_id,
        task_type=req.task_type,
        task_seed=req.task_seed,
        difficulty=req.difficulty,
        response=req.response,
        confidence=req.confidence,
        latency_ms=req.latency_ms,
        client_trial_id=req.client_trial_id,
        expected_version_id=req.expected_version_id or expected_version,
    ))


@router.post("/sessions/{session_id}/interviews/start",
             response_model=InterviewStartResponseModel)
async def interview_start(
    session_id: SessionId,
    req: StudioInterviewStartRequest | None = None,
):
    body = req or StudioInterviewStartRequest()
    return await _call(studio_service.interview_start(
        session_id,
        max_probes=body.max_probes,
        form_id=body.form_id,
        difficulty=body.difficulty,
        expected_version_id=body.expected_version_id,
    ))


@router.post("/sessions/{session_id}/interviews/{interview_id}/probes",
             response_model=InterviewSubmitResponseModel)
async def interview_submit(
    session_id: SessionId,
    interview_id: InterviewId,
    req: StudioInterviewSubmitRequest,
    expected_version: ExpectedVersion = None,
):
    return await _call(studio_service.interview_submit(
        session_id,
        interview_id,
        probe_id=req.probe_id,
        task_id=req.task_id,
        choice=req.choice,
        confidence=req.confidence,
        abstained=req.abstained,
        latency_ms=req.latency_ms,
        client_trial_id=req.client_trial_id,
        expected_version_id=req.expected_version_id or expected_version,
    ))


@router.get("/interviews/{interview_id}", response_model=InterviewSummaryResponseModel)
async def interview_summary(interview_id: InterviewId):
    return await _call(studio_service.interview_summary(interview_id))


@router.get("/sessions/{session_id}/interviews", response_model=InterviewListResponseModel)
async def list_interviews(session_id: SessionId):
    return await _call(studio_service.list_interviews(session_id))


@router.post("/sessions/{session_id}/contrast/start",
             response_model=ContrastStartResponseModel)
async def contrast_start(
    session_id: SessionId,
    req: StudioContrastStartRequest | None = None,
):
    body = req or StudioContrastStartRequest()
    return await _call(studio_service.contrast_start(
        session_id,
        max_trials=body.max_trials,
        form_id=body.form_id,
        difficulty=body.difficulty,
        occasion=body.occasion,
        delay_hours=body.delay_hours,
        source_version_id=body.source_version_id,
        expected_version_id=body.expected_version_id,
    ))


@router.post("/sessions/{session_id}/contrast/{contrast_id}/trials",
             response_model=ContrastSubmitResponseModel)
async def contrast_submit(
    session_id: SessionId,
    contrast_id: ContrastId,
    req: StudioContrastSubmitRequest,
    expected_version: ExpectedVersion = None,
):
    return await _call(studio_service.contrast_submit(
        session_id,
        contrast_id,
        trial_id=req.trial_id,
        task_id=req.task_id,
        choice=req.choice,
        confidence=req.confidence,
        abstained=req.abstained,
        latency_ms=req.latency_ms,
        client_trial_id=req.client_trial_id,
        expected_version_id=req.expected_version_id or expected_version,
    ))


@router.get("/contrast/{contrast_id}", response_model=ContrastSummaryResponseModel)
async def contrast_summary(contrast_id: ContrastId):
    return await _call(studio_service.contrast_summary(contrast_id))


@router.get("/sessions/{session_id}/contrast", response_model=ContrastListResponseModel)
async def list_contrasts(session_id: SessionId):
    return await _call(studio_service.list_contrasts(session_id))


@router.get("/sessions/{session_id}/observatory", response_model=ObservatoryModel)
async def observatory(session_id: SessionId):
    return await _call(studio_service.observatory(session_id))


@router.post("/contrast/{contrast_id}/reflection",
             response_model=ContrastSummaryResponseModel)
async def contrast_reflection(
    contrast_id: ContrastId,
    req: StudioContrastReflectionRequest,
):
    return await _call(studio_service.contrast_reflection(
        contrast_id, strategies=req.strategies, notes=req.notes))


@router.post("/sessions", response_model=StudioSnapshotModel)
async def create_session(req: StudioCreateRequest):
    return await _call(studio_service.create_session(
        title=req.title, intention=req.intention, seed=req.seed))


@router.get("/sessions", response_model=SessionListResponseModel)
async def list_sessions(limit: int = Query(default=50, ge=1, le=100)):
    return await _call(studio_service.list_sessions(limit=limit))


@router.get("/sessions/{session_id}", response_model=StudioSnapshotModel)
async def get_session(session_id: SessionId):
    return await _call(studio_service.get_session(session_id))


@router.delete("/sessions/{session_id}", response_model=DeleteResponseModel)
async def delete_session(session_id: SessionId):
    return await _call(studio_service.delete_session(session_id))


@router.post("/sessions/{session_id}/intent", response_model=StudioIntentResponseModel)
async def apply_intent(
    session_id: SessionId,
    req: StudioIntentRequest,
    expected_version: ExpectedVersion = None,
):
    return await _call(studio_service.apply_intent(
        session_id, req.text, expected_version_id=expected_version))


@router.post("/sessions/{session_id}/commands", response_model=StudioCommandsResponseModel)
async def apply_commands(
    session_id: SessionId,
    req: StudioCommandsRequest,
    expected_version: ExpectedVersion = None,
):
    return await _call(studio_service.apply_commands(
        session_id, req.commands, source_text=req.source_text,
        expected_version_id=expected_version))


@router.post("/sessions/{session_id}/regenerate", response_model=StudioRegenerateResponseModel)
async def regenerate(
    session_id: SessionId,
    req: StudioRegenerateRequest,
    expected_version: ExpectedVersion = None,
):
    return await _call(studio_service.regenerate(
        session_id, count=req.count, strength=req.strength, seed=req.seed, locks=req.locks,
        expected_version_id=expected_version,
        preserve_user_edits=req.preserve_user_edits, vary_camera=req.vary_camera))


@router.post("/sessions/{session_id}/candidates/{candidate_id}/select",
             response_model=StudioSnapshotModel)
async def select_candidate(
    session_id: SessionId,
    candidate_id: CandidateId,
    expected_version: ExpectedVersion = None,
):
    return await _call(studio_service.select_candidate(
        session_id, candidate_id, expected_version_id=expected_version))


@router.post("/sessions/{session_id}/undo", response_model=StudioSnapshotModel)
async def undo(session_id: SessionId, expected_version: ExpectedVersion = None):
    return await _call(studio_service.undo(session_id, expected_version_id=expected_version))


@router.post("/sessions/{session_id}/redo", response_model=StudioSnapshotModel)
async def redo(session_id: SessionId, expected_version: ExpectedVersion = None):
    return await _call(studio_service.redo(session_id, expected_version_id=expected_version))


@router.post("/sessions/{session_id}/branches", response_model=StudioSnapshotModel)
async def create_branch(
    session_id: SessionId,
    req: StudioBranchRequest,
    expected_version: ExpectedVersion = None,
):
    return await _call(studio_service.branch(
        session_id, name=req.name, from_version_id=req.from_version_id,
        expected_version_id=expected_version))


@router.post("/sessions/{session_id}/branches/{branch_id}/switch",
             response_model=StudioSnapshotModel)
async def switch_branch(
    session_id: SessionId,
    branch_id: BranchId,
    expected_version: ExpectedVersion = None,
):
    return await _call(studio_service.switch_branch(
        session_id, branch_id, expected_version_id=expected_version))


@router.get("/sessions/{session_id}/history", response_model=StudioHistoryResponseModel)
async def history(session_id: SessionId):
    return await _call(studio_service.history(session_id))


@router.get("/sessions/{session_id}/events", response_model=StudioEventsResponseModel)
async def events(
    session_id: SessionId,
    after_seq: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
):
    return await _call(studio_service.events(session_id, after_seq=after_seq, limit=limit))


@router.get("/sessions/{session_id}/versions/{version_id}", response_model=VersionDetailModel)
async def version(session_id: SessionId, version_id: VersionId):
    return await _call(studio_service.version(session_id, version_id))


@router.post("/sessions/{session_id}/worlds", response_model=WorldModel)
async def save_world(session_id: SessionId, req: StudioWorldRequest):
    return await _call(studio_service.save_world(
        session_id, name=req.name, description=req.description))


@router.get("/worlds", response_model=WorldListResponseModel)
async def list_worlds(limit: int = Query(default=50, ge=1, le=100)):
    return await _call(studio_service.list_worlds(limit=limit))


@router.get("/worlds/{world_id}", response_model=WorldModel)
async def get_world(world_id: WorldId):
    return await _call(studio_service.get_world(world_id))


@router.delete("/worlds/{world_id}", response_model=DeleteResponseModel)
async def delete_world(world_id: WorldId):
    return await _call(studio_service.delete_world(world_id))


@router.post("/worlds/{world_id}/open", response_model=StudioSnapshotModel)
async def open_world(world_id: WorldId, req: StudioOpenWorldRequest | None = None):
    return await _call(studio_service.open_world(
        world_id, title=req.title if req else None))
