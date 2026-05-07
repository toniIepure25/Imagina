import uuid

from app.core.time import utcnow
from app.schemas.calibration import CalibrationCompleteInput, CalibrationProfile
from app.services import session_service
from app.services.signal_simulator import SignalSimulator
from app.storage import event_store, repository


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _round(v: float) -> float:
    return round(max(0.0, min(1.0, v)), 4)


async def start_calibration(session_id: str) -> dict:
    await session_service.get_session(session_id)
    await repository.update_session_status(session_id, "calibrating")
    await event_store.append_event(session_id, "calibration_started", {"started_at": utcnow().isoformat()})
    return {"status": "calibrating", "session_id": session_id}


async def complete_calibration(
    session_id: str,
    user_id: str | None,
    data: CalibrationCompleteInput,
) -> CalibrationProfile:
    session = await session_service.get_session(session_id)
    scenario = session.scenario or "improving_user"
    sim = SignalSimulator(seed=17, scenario=scenario)
    windows = max(3, min(12, data.duration_seconds // 5))
    fvs = [
        sim.generate_window(
            session_id,
            i,
            {
                "focus": data.focus,
                "relaxation": data.relaxation,
                "vividness": data.vividness,
                "fatigue": data.fatigue,
                "stability": 5,
                "distraction": 3,
            },
            windows,
        )[1]
        for i in range(windows)
    ]

    signal_quality = _avg([fv.signal_quality for fv in fvs])
    theta = _avg([fv.theta_power for fv in fvs])
    alpha = _avg([fv.alpha_power for fv in fvs])
    beta = _avg([fv.beta_power for fv in fvs])
    theta_beta = _avg([fv.theta_beta_ratio for fv in fvs])
    warnings: list[str] = []

    if data.duration_seconds < 20:
        warnings.append("baseline_too_short")
    if signal_quality < 0.45:
        warnings.append("low_signal_quality")
    if data.fatigue >= 7:
        warnings.append("high_baseline_fatigue")
    if abs(data.focus - data.relaxation) >= 6:
        warnings.append("inconsistent_self_report")

    quality = (
        0.35 * signal_quality
        + 0.25 * (1 - data.fatigue / 10)
        + 0.20 * (data.focus / 10)
        + 0.20 * (data.relaxation / 10)
    )
    quality -= min(0.35, 0.08 * len(warnings))

    profile = CalibrationProfile(
        calibration_id=str(uuid.uuid4()),
        session_id=session_id,
        user_id=user_id,
        created_at=utcnow(),
        duration_seconds=data.duration_seconds,
        mode=data.mode,
        baseline_focus=data.focus / 10,
        baseline_relaxation=data.relaxation / 10,
        baseline_vividness=data.vividness / 10,
        baseline_fatigue=data.fatigue / 10,
        baseline_theta_power=round(theta, 4),
        baseline_alpha_power=round(alpha, 4),
        baseline_beta_power=round(beta, 4),
        baseline_theta_beta_ratio=round(theta_beta, 4),
        baseline_signal_quality=round(signal_quality, 4),
        calibration_quality_score=_round(quality),
        warnings=warnings,
        normalization_params={
            "signal_provider_id": session.signal_provider_id,
            "scenario": scenario,
            "theta_mean": round(theta, 4),
            "alpha_mean": round(alpha, 4),
            "beta_mean": round(beta, 4),
            "theta_beta_ratio_mean": round(theta_beta, 4),
            "signal_quality_mean": round(signal_quality, 4),
        },
        notes=data.notes,
    )
    await repository.upsert_json(
        "calibrations",
        "calibration_id",
        profile.calibration_id,
        profile.model_dump(mode="json"),
        {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": profile.created_at.isoformat(),
        },
    )
    await repository.set_baseline(session_id, profile.model_dump(mode="json"))
    await event_store.append_event(session_id, "calibration_completed", profile.model_dump(mode="json"))
    return profile


async def get_calibration(session_id: str) -> CalibrationProfile | None:
    calibrations = await repository.list_json("calibrations", order_by="created_at")
    for payload in reversed(calibrations):
        if payload.get("session_id") == session_id:
            return CalibrationProfile(**payload)
    return None
