from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.core.errors import SessionNotFoundError
from app.reports.html_report import generate_html_report
from app.reports.json_report import generate_json_report
from app.services import session_service
from app.services.report_service import generate_summary

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{session_id}")
async def get_json_report(session_id: str):
    try:
        await session_service.get_session(session_id)
        summary = await generate_summary(session_id)
    except SessionNotFoundError:
        raise HTTPException(404, "Session not found")
    except Exception:
        raise HTTPException(404, "Report not found or has no data")
    return await generate_json_report(session_id, summary)


@router.get("/{session_id}/html", response_class=HTMLResponse)
async def get_html_report(session_id: str):
    try:
        await session_service.get_session(session_id)
        summary = await generate_summary(session_id)
    except SessionNotFoundError:
        raise HTTPException(404, "Session not found")
    except Exception:
        raise HTTPException(404, "Report not found or has no data")
    return generate_html_report(summary)
