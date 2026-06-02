"""IMAGINA Safety Monitor — Fatigue, attention, session limits, well-being checks."""


def check_safety(
    fatigue: float = 0.2,
    attention_stability: float = 0.5,
    discomfort_report: float = 0.0,
    dissociation_warning: bool = False,
    session_duration_minutes: float = 5.0,
    max_duration_minutes: float = 20.0,
    failed_trials: int = 0,
    user_opted_out: bool = False,
) -> dict:
    """Evaluate safety conditions and return recommended action."""

    if user_opted_out:
        return {"action": "stop_session", "message": "User requested session end.",
                "safety_flags": ["user_opt_out"]}

    if fatigue > 0.85:
        return {"action": "stop_session",
                "message": "High fatigue detected. Please rest and return later. Overexertion does not improve imagery.",
                "safety_flags": ["critical_fatigue"]}

    if session_duration_minutes >= max_duration_minutes:
        return {"action": "stop_session",
                "message": "Maximum session duration reached. Regular breaks support effective practice.",
                "safety_flags": ["time_limit"]}

    if dissociation_warning:
        return {"action": "pause",
                "message": "Take a moment to ground yourself. Notice your physical surroundings before continuing.",
                "safety_flags": ["dissociation_warning"]}

    if fatigue > 0.60:
        return {"action": "simplify",
                "message": "Fatigue is elevated. Your scene will become simpler and calmer.",
                "safety_flags": ["elevated_fatigue"]}

    if attention_stability < 0.25:
        return {"action": "simplify",
                "message": "Attention seems diffuse. Let the imagery become softer and less demanding.",
                "safety_flags": ["low_attention"]}

    if discomfort_report > 7.0:
        return {"action": "simplify",
                "message": "Discomfort reported. Adjusting the experience to be gentler.",
                "safety_flags": ["discomfort"]}

    if failed_trials >= 4:
        return {"action": "simplify",
                "message": "Multiple attempts haven't produced stable imagery. Let's try something simpler.",
                "safety_flags": ["frustration_protection"]}

    return {"action": "continue", "message": "All safety checks passed.",
            "safety_flags": []}


def get_safety_disclaimers() -> list[str]:
    """Standard safety disclaimers for every session."""
    return [
        "IMAGINA is a research prototype, not therapy or clinical treatment.",
        "You can stop or pause the session at any time.",
        "If a scene becomes emotionally intense, stop and choose a neutral scene.",
        "No brain data is decoded or stored unless you explicitly enable an optional sensor.",
        "Your imagery sessions are stored only on your local device.",
        "No imagery content is reconstructed, extracted, or shared.",
        "Regular breaks support effective imagery practice.",
        "Imagery quality varies naturally — do not judge yourself against any standard.",
    ]
