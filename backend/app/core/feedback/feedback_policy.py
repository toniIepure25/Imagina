"""IMAGINA Feedback Policy — Maps state estimates to procedural scene parameters."""


def compute_scene_params(
    iqi_score: float = 0.5,
    pid_score: float = 0.5,
    attention_stability: float = 0.5,
    relaxation: float = 0.5,
    fatigue: float = 0.2,
    uncertainty: float = 0.3,
    engagement: float = 0.5,
    task_level: int = 1,
) -> dict:
    """Map estimated cognitive state to scene feedback parameters."""

    # Clarity: driven by IQI and attention
    clarity = min(1.0, max(0.1, 0.3 + iqi_score * 0.6 + attention_stability * 0.3 - fatigue * 0.3))

    # Contrast: driven by engagement and IQI
    contrast = min(1.0, max(0.1, 0.2 + engagement * 0.5 + iqi_score * 0.3 - uncertainty * 0.2))

    # Saturation: driven by relaxation and IQI
    saturation = min(1.0, max(0.1, 0.3 + relaxation * 0.4 + iqi_score * 0.3 - fatigue * 0.3))

    # Motion speed: low when attention is low
    motion_speed = min(1.0, max(0.0, attention_stability * 0.7 - fatigue * 0.3 + relaxation * 0.3))

    # Visual noise: inverse of IQI
    visual_noise = min(1.0, max(0.0, 1.0 - iqi_score * 0.7 - relaxation * 0.3))

    # Scene complexity: driven by task level and fatigue
    scene_complexity = min(1.0, max(0.1, task_level / 8.0 - fatigue * 0.3 + engagement * 0.3))

    # Object detail: driven by IQI and task level
    object_detail = min(1.0, max(0.1, iqi_score * 0.6 + task_level / 10.0 - uncertainty * 0.2))

    # Symbol density: higher with engagement, lower with fatigue
    symbol_density = min(1.0, max(0.0, engagement * 0.5 - fatigue * 0.3 + relaxation * 0.2))

    # Breathing cue intensity: relaxation support
    breathing_cue = min(1.0, max(0.0, 1.0 - relaxation * 0.8))

    # Audio depth: engagement + relaxation
    audio_depth = min(1.0, max(0.0, relaxation * 0.5 + engagement * 0.3 - fatigue * 0.2))

    # Prompt specificity: driven by attention
    prompt_specificity = min(1.0, max(0.2, attention_stability * 0.8 + iqi_score * 0.2))

    # Transition speed: slow if uncertain or fatigued
    transition_speed = min(1.0, max(0.1, 1.0 - fatigue * 0.5 - uncertainty * 0.4))

    # Generate prompt text
    prompt = _generate_prompt(iqi_score, pid_score, attention_stability, fatigue, task_level)

    return {
        "clarity": round(clarity, 3),
        "contrast": round(contrast, 3),
        "saturation": round(saturation, 3),
        "motion_speed": round(motion_speed, 3),
        "visual_noise": round(visual_noise, 3),
        "scene_complexity": round(scene_complexity, 3),
        "object_detail": round(object_detail, 3),
        "symbol_density": round(symbol_density, 3),
        "breathing_cue_intensity": round(breathing_cue, 3),
        "audio_depth": round(audio_depth, 3),
        "prompt_specificity": round(prompt_specificity, 3),
        "transition_speed": round(transition_speed, 3),
        "prompt": prompt,
    }


def _generate_prompt(iqi, pid, attention, fatigue, level):
    if iqi >= 0.8:
        return "Your imagery is vivid and coherent. Feel free to explore details."
    if fatigue > 0.6:
        return "Take a gentle breath. Simplify the scene. Rest is part of the practice."
    if attention < 0.3:
        return "Let the scene come back softly. No need to force it."
    if pid > 0.6:
        return "Notice how the image feels — its color, texture, and presence."
    if iqi < 0.4:
        return "Try returning to a simple shape or color. Build up slowly."
    return "Stay with the image. Let it breathe naturally."
