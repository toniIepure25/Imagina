from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, Response

from app.services import export_service

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.get("/session/{session_id}/events.jsonl", response_class=PlainTextResponse)
async def events_jsonl(session_id: str):
    return Response(await export_service.events_jsonl(session_id), media_type="application/x-ndjson")


@router.get("/session/{session_id}/timeline.csv", response_class=PlainTextResponse)
async def timeline_csv(session_id: str):
    return Response(await export_service.timeline_csv(session_id), media_type="text/csv")


@router.get("/session/{session_id}/self_reports.csv", response_class=PlainTextResponse)
async def self_reports_csv(session_id: str):
    return Response(await export_service.self_reports_csv(session_id), media_type="text/csv")


@router.get("/session/{session_id}/summary.csv", response_class=PlainTextResponse)
async def summary_csv(session_id: str):
    return Response(await export_service.summary_csv(session_id), media_type="text/csv")


@router.get("/experiment/{run_id}/summary.json")
async def experiment_summary(run_id: str):
    result = await export_service.experiment_summary_json(run_id)
    if not result:
        raise HTTPException(404, "Experiment run not found")
    return result


@router.get("/data_dictionary.md", response_class=PlainTextResponse)
async def data_dictionary():
    return export_service.data_dictionary_markdown()
