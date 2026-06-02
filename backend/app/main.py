import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.calibration import router as calibration_router
from app.api.experiments import router as experiments_router
from app.api.exports import router as exports_router
from app.api.feedback import router as feedback_router
from app.api.health import router as health_router
from app.api.imagina.routes import router as imagina_router
from app.api.replay import router as replay_router
from app.api.reports import router as reports_router
from app.api.routes_datasets import router as datasets_router
from app.api.routes_research import router as research_router
from app.api.sessions import router as sessions_router
from app.api.signals import router as signals_router
from app.api.state import router as state_router
from app.api.tasks import router as tasks_router
from app.api.users import router as users_router
from app.core.config import settings
from app.services import replay_service, session_service
from app.storage.database import init_db
from app.websocket.manager import ws_manager
from app.websocket.session_stream import (
    is_session_loop_running,
    run_session_loop,
    set_self_report,
    stop_session_loop,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Dream Corridor Scene Stabilizer — closed-loop mental imagery training prototype",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(calibration_router)
app.include_router(datasets_router)
app.include_router(experiments_router)
app.include_router(exports_router)
app.include_router(health_router)
app.include_router(sessions_router)
app.include_router(signals_router)
app.include_router(tasks_router)
app.include_router(users_router)
app.include_router(imagina_router)
app.include_router(state_router)
app.include_router(feedback_router)
app.include_router(replay_router)
app.include_router(reports_router)
app.include_router(research_router)


@app.websocket("/ws/sessions/{session_id}")
async def websocket_session(ws: WebSocket, session_id: str):
    await ws_manager.connect(session_id, ws)
    loop_task: asyncio.Task | None = None
    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "start_session":
                if is_session_loop_running(session_id):
                    await ws_manager.send(
                        session_id,
                        "session_error",
                        {"message": "Session loop is already running"},
                    )
                    continue
                session = await session_service.get_session(session_id)
                scenario = data.get("scenario") or session.scenario or "improving_user"
                seed = data.get("seed", 42)
                baseline = data.get("baseline")
                loop_task = asyncio.create_task(
                    run_session_loop(session_id, scenario, seed, baseline)
                )

            elif msg_type == "self_report":
                set_self_report(session_id, data.get("payload", {}))

            elif msg_type == "stop_session":
                stop_session_loop(session_id)

            elif msg_type == "start_replay":
                speed = data.get("speed", 1.0)
                loop_task = asyncio.create_task(
                    replay_service.replay_to_websocket(session_id, speed)
                )

            elif msg_type == "pause_replay":
                replay_service.pause_replay(session_id)

            elif msg_type == "resume_replay":
                replay_service.resume_replay(session_id)

            elif msg_type == "stop_replay":
                replay_service.stop_replay(session_id)

            else:
                await ws_manager.send(
                    session_id,
                    "session_error",
                    {"message": f"Unknown WebSocket message type: {msg_type}"},
                )

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        stop_session_loop(session_id, reason="disconnect")
        replay_service.stop_replay(session_id)
        ws_manager.disconnect(session_id)
        if loop_task and not loop_task.done():
            loop_task.cancel()
