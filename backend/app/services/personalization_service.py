import uuid

from app.core.time import utcnow
from app.schemas.profile import ImageryProfile, ProfileRecommendation, UserProfileCreate
from app.schemas.reports import SessionSummary
from app.storage import repository


async def create_local_profile(data: UserProfileCreate) -> ImageryProfile:
    now = utcnow()
    profile = ImageryProfile(
        user_id=str(uuid.uuid4()),
        display_name=data.display_name,
        created_at=now,
        updated_at=now,
        preferred_task_type=data.preferred_task_type,
        preferred_feedback_style=data.preferred_feedback_style,
    )
    await save_profile(profile)
    return profile


async def save_profile(profile: ImageryProfile) -> None:
    await repository.upsert_json(
        "user_profiles",
        "user_id",
        profile.user_id,
        profile.model_dump(mode="json"),
        {"created_at": profile.created_at.isoformat(), "updated_at": profile.updated_at.isoformat()},
    )


async def get_profile(user_id: str) -> ImageryProfile | None:
    payload = await repository.get_json("user_profiles", "user_id", user_id)
    return ImageryProfile(**payload) if payload else None


async def reset_progress(user_id: str) -> ImageryProfile | None:
    profile = await get_profile(user_id)
    if not profile:
        return None
    reset = ImageryProfile(
        user_id=profile.user_id,
        display_name=profile.display_name,
        created_at=profile.created_at,
        updated_at=utcnow(),
        preferred_task_type=profile.preferred_task_type,
        preferred_feedback_style=profile.preferred_feedback_style,
    )
    await save_profile(reset)
    return reset


async def update_profile_after_summary(user_id: str, summary: SessionSummary) -> ImageryProfile | None:
    profile = await get_profile(user_id)
    if not profile:
        return None
    if summary.session_id in profile.processed_session_ids:
        return profile
    n = profile.total_sessions
    total_sessions = n + 1
    avg_iqi = ((profile.average_iqi * n) + summary.average_iqi) / total_sessions
    avg_pid = ((profile.average_pid * n) + summary.average_pid) / total_sessions
    fatigue_sensitivity = min(1.0, max(0.0, (profile.fatigue_sensitivity * n + summary.fatigue_peak) / total_sessions))
    history = [
        *profile.progress_history_summary[-19:],
        {
            "session_id": summary.session_id,
            "average_iqi": summary.average_iqi,
            "average_pid": summary.average_pid,
            "max_level_reached": summary.max_level_reached,
            "fatigue_peak": summary.fatigue_peak,
            "generated_at": summary.generated_at.isoformat(),
        },
    ]
    profile.total_sessions = total_sessions
    profile.total_minutes = round(profile.total_minutes + summary.duration_seconds / 60, 2)
    profile.max_level_reached = max(profile.max_level_reached, summary.max_level_reached)
    profile.average_iqi = round(avg_iqi, 4)
    profile.best_iqi = max(profile.best_iqi, summary.best_iqi)
    profile.average_pid = round(avg_pid, 4)
    profile.best_pid = min(profile.best_pid, summary.best_pid)
    profile.fatigue_sensitivity = round(fatigue_sensitivity, 4)
    profile.optimal_difficulty_estimate = round(min(1.0, max(0.125, profile.max_level_reached / 8)), 4)
    profile.progress_history_summary = history
    profile.processed_session_ids = [*profile.processed_session_ids[-99:], summary.session_id]
    profile.updated_at = utcnow()
    await save_profile(profile)
    return profile


async def recommendation(user_id: str) -> ProfileRecommendation | None:
    profile = await get_profile(user_id)
    if not profile:
        return None
    duration = 8 if profile.fatigue_sensitivity > 0.7 else 12
    starting_level = max(1, min(8, profile.max_level_reached - (1 if profile.fatigue_sensitivity > 0.75 else 0)))
    task = "corridor_simple" if profile.average_iqi < 0.55 else profile.preferred_task_type
    rationale = (
        "Shorter, simpler session recommended due to fatigue sensitivity."
        if duration == 8
        else "Continue steady progression with current task preference."
    )
    return ProfileRecommendation(
        user_id=user_id,
        recommended_task=task,
        recommended_duration_minutes=duration,
        recommended_starting_level=starting_level,
        rationale=rationale,
    )


async def longitudinal_report(user_id: str) -> dict | None:
    profile = await get_profile(user_id)
    rec = await recommendation(user_id)
    if not profile or not rec:
        return None
    history = profile.progress_history_summary

    def slope(key: str) -> float:
        values = [row.get(key) for row in history if isinstance(row.get(key), (int, float))]
        if len(values) < 2:
            return 0.0
        return round((values[-1] - values[0]) / (len(values) - 1), 5)

    return {
        "disclaimer": (
            "Longitudinal progress summarizes experimental proxy metrics. "
            "It is not a clinical evaluation and does not decode mental content."
        ),
        "profile": profile.model_dump(mode="json"),
        "recommendation": rec.model_dump(mode="json"),
        "trends": {
            "iqi_slope": slope("average_iqi"),
            "pid_slope": slope("average_pid"),
            "fatigue_slope": slope("fatigue_peak"),
            "session_count": len(history),
        },
        "recent_sessions": history[-10:],
        "limitations": [
            "Local-only profile data depends on completed sessions in this browser/workspace.",
            "PID/IQI are experimental proxy metrics requiring validation.",
        ],
    }
