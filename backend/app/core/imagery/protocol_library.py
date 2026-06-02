"""IMAGINA V23 — Built-in Protocol Library.

8 standardized mental imagery training protocols.
"""

SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory adaptive mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, or validated BCI."),
    "visualization_boundary": ("Scene visualization is a symbolic training aid based on self-report proxies. "
                                "It is not a reconstruction of mental imagery, neural activity, dreams, or thoughts."),
}


def _make_blocks(task_ids):
    return [
        {
            "task_id": tid, "guided": True,
            "scene_template_id": "", "duration_seconds": 90,
            "target_dimension": "", "checkin_schedule": ["after_generation", "after_stabilization", "completion"],
            "success_criteria": {"min_iqi_proxy": 0.55, "max_pid_proxy": 0.50, "max_fatigue": 7},
        }
        for tid in task_ids
    ]


BUILTIN_PROTOCOLS = [
    {
        "template_id": "baseline_imagery_assessment_7d",
        "title": "Baseline Imagery Assessment (7-Day)",
        "description": "Balanced across vividness, stability, detail, color, motion, and multisensory dimensions to establish an initial phenotype baseline.",
        "protocol_type": "baseline_assessment",
        "target_dimensions": ["vividness", "stability", "color_control", "spatial_control", "detail", "motion", "multisensory"],
        "difficulty_range": [1, 2],
        "duration_days": 7,
        "task_sequence": [
            "red_circle_vividness", "blue_cube_vividness", "static_cube_stability",
            "color_shift_red_to_blue", "apple_detail_generation", "rotating_object",
            "visual_plus_sound_scene",
        ],
        "rationale": "Broad assessment across core imagery dimensions for initial phenotype calibration.",
        "expected_outcomes": "Baseline profile of imagery strengths and weaknesses.",
    },
    {
        "template_id": "vividness_foundation_7d",
        "title": "Vividness Foundation (7-Day)",
        "description": "Focus on basic vividness, color clarity, and brightness control with easy tasks.",
        "protocol_type": "training_block",
        "target_dimensions": ["vividness", "color_control"],
        "difficulty_range": [1, 2],
        "duration_days": 7,
        "task_sequence": [
            "red_circle_vividness", "candle_flame_vividness", "brightness_control",
            "blue_cube_vividness", "saturation_control", "red_circle_vividness",
            "candle_flame_vividness",
        ],
        "rationale": "Build foundational vividness and color control through repeated easy practice.",
        "expected_outcomes": "Improved vividness and color control self-report scores.",
    },
    {
        "template_id": "stability_under_load_7d",
        "title": "Stability Under Load (7-Day)",
        "description": "Hold images, rotating cube, scene stability. Medium difficulty.",
        "protocol_type": "training_block",
        "target_dimensions": ["spatial_control", "stability", "motion"],
        "difficulty_range": [2, 3],
        "duration_days": 7,
        "task_sequence": [
            "static_cube_stability", "rotating_cube_stability", "hold_image_30_seconds",
            "room_layout_stability", "rotating_object", "hold_image_30_seconds",
            "rotating_cube_stability",
        ],
        "rationale": "Develop stability under motion and spatial complexity.",
        "expected_outcomes": "Improved spatial stability and motion control.",
    },
    {
        "template_id": "detail_builder_7d",
        "title": "Detail Builder (7-Day)",
        "description": "Apple, face, forest, room — detail generation practice.",
        "protocol_type": "training_block",
        "target_dimensions": ["detail", "vividness"],
        "difficulty_range": [2, 4],
        "duration_days": 7,
        "task_sequence": [
            "apple_detail_generation", "apple_detail_generation", "forest_scene_detail",
            "face_detail_generation", "simple_room_construction", "apple_detail_generation",
            "forest_scene_detail",
        ],
        "rationale": "Progressive detail generation from objects to scenes.",
        "expected_outcomes": "Improved detail richness and texture perception.",
    },
    {
        "template_id": "multisensory_integration_7d",
        "title": "Multisensory Integration (7-Day)",
        "description": "Visual + sound/touch/smell integration tasks.",
        "protocol_type": "training_block",
        "target_dimensions": ["multisensory", "vividness"],
        "difficulty_range": [3, 4],
        "duration_days": 7,
        "task_sequence": [
            "visual_plus_sound_scene", "visual_plus_touch_object", "visual_plus_smell_food",
            "visual_plus_sound_scene", "visual_plus_touch_object", "visual_plus_smell_food",
            "visual_plus_touch_object",
        ],
        "rationale": "Strengthen multisensory integration for richer imagery.",
        "expected_outcomes": "Improved multisensory dimension scores.",
    },
    {
        "template_id": "meta_control_7d",
        "title": "Meta-Control Mastery (7-Day)",
        "description": "Blur/refocus, switch images, hold image — control tasks.",
        "protocol_type": "training_block",
        "target_dimensions": ["meta_control", "stability", "vividness"],
        "difficulty_range": [2, 4],
        "duration_days": 7,
        "task_sequence": [
            "hold_image_30_seconds", "intentionally_blur_then_refocus",
            "switch_between_two_images", "hold_image_30_seconds",
            "intentionally_blur_then_refocus", "switch_between_two_images",
            "intentionally_blur_then_refocus",
        ],
        "rationale": "Build intentional control over mental image manipulation.",
        "expected_outcomes": "Improved meta-control dimension scores.",
    },
    {
        "template_id": "recovery_low_fatigue_5d",
        "title": "Recovery — Low Fatigue (5-Day)",
        "description": "Low intensity calming scenes for fatigue recovery.",
        "protocol_type": "recovery_block",
        "target_dimensions": ["vividness", "emotion"],
        "difficulty_range": [1, 1],
        "duration_days": 5,
        "task_sequence": [
            "calm_scene_generation", "neutral_object_scene", "red_circle_vividness",
            "calm_scene_generation", "neutral_object_scene",
        ],
        "rationale": "Reduce fatigue with low-intensity, emotionally calm practice.",
        "expected_outcomes": "Reduced fatigue, maintained baseline imagery.",
    },
    {
        "template_id": "plateau_breaker_7d",
        "title": "Plateau Breaker (7-Day)",
        "description": "Switch task category and lower difficulty to break through plateaus.",
        "protocol_type": "recovery_block",
        "target_dimensions": ["vividness", "spatial_control", "detail"],
        "difficulty_range": [1, 2],
        "duration_days": 7,
        "task_sequence": [
            "red_circle_vividness", "hold_image_30_seconds", "calm_scene_generation",
            "brightness_control", "static_cube_stability", "apple_detail_generation",
            "red_circle_vividness",
        ],
        "rationale": "Vary task categories at low difficulty to break stagnation.",
        "expected_outcomes": "Reduced plateau indicators, renewed improvement trend.",
    },
]


def get_builtin_protocol_library():
    return {"protocols": BUILTIN_PROTOCOLS, "n_protocols": len(BUILTIN_PROTOCOLS), **SAFETY}


def get_builtin_protocol(template_id):
    for p in BUILTIN_PROTOCOLS:
        if p["template_id"] == template_id:
            return {**p, **SAFETY}
    return {"error": "template_not_found", "template_id": template_id, **SAFETY}


def instantiate_builtin_protocol(user_id, template_id):
    from app.core.imagery.protocol_studio import create_imagery_protocol
    tpl = get_builtin_protocol(template_id)
    if tpl.get("error"):
        return tpl
    blocks = _make_blocks(tpl["task_sequence"])
    payload = {
        "title": tpl["title"], "description": tpl["description"],
        "protocol_type": tpl["protocol_type"],
        "target_dimensions": tpl["target_dimensions"],
        "difficulty_range": tpl["difficulty_range"],
        "duration_days": tpl["duration_days"],
        "daily_structure": [
            {"day": i + 1, "blocks": [blocks[i]]} for i in range(tpl["duration_days"])
        ],
        "measurement_plan": {
            "primary_metric": "iqi_proxy",
            "secondary_metrics": ["pid_proxy", "stability_proxy", "fatigue", "confidence"],
            "skill_dimensions": tpl["target_dimensions"],
            "scene_metrics": ["clarity_delta", "fog_delta", "stability_delta"],
        },
        "safety_policy": {"stop_if_discomfort_gte": 8, "pause_if_fatigue_gte": 8, "reduce_difficulty_if_effort_gte": 8},
    }
    return create_imagery_protocol(user_id, payload)
