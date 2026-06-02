"""IMAGINA V19 — Imagery Phenotype Builder + Gap Analyzer + Task-Based Planner."""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")
PHENOTYPE_DIR = os.path.join(BASE, "imagery_phenotypes")
PLANS_DIR = os.path.join(BASE, "task_based_plans")

SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, or validated BCI."),
}

ALL_DIMENSIONS = ["vividness", "stability", "color_control", "spatial_control",
                  "detail", "motion", "emotion", "multisensory", "meta_control"]

PHENOTYPE_LABELS = {
    "vividness": "vivid_visualizer",
    "spatial_control": "stable_constructor",
    "detail": "detail_builder",
    "motion": "motion_imager",
    "emotion": "emotional_scene_imager",
    "multisensory": "multisensory_imager",
}


def _load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def _save_json(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _get_sessions(user_id):
    from app.core.imagery.task_session_manager import list_imagery_task_sessions
    return [s for s in list_imagery_task_sessions(user_id) if s.get("status") == "completed"]


def build_imagery_phenotype(user_id="default") -> dict:
    sessions = _get_sessions(user_id)
    if not sessions:
        return {"user_id": user_id, "status": "no_data",
                "message": "Complete at least one imagery task session.", **SAFETY}

    dim_data = {d: {"scores": [], "confidence_sum": 0, "categories": set(), "fatigues": []}
                for d in ALL_DIMENSIONS}

    for s in sessions:
        scores = s.get("dimension_scores", {})
        ratings = s.get("rating_payload", {})
        cat = s.get("task_metadata", {}).get("category", "unknown")
        for d in ALL_DIMENSIONS:
            if d in scores:
                dim_data[d]["scores"].append(scores[d])
                dim_data[d]["confidence_sum"] += ratings.get("confidence", 5)
                dim_data[d]["categories"].add(cat)
                dim_data[d]["fatigues"].append(ratings.get("fatigue", 3))

    profile = {}
    for d in ALL_DIMENSIONS:
        data = dim_data[d]
        n = len(data["scores"])
        if n == 0:
            profile[d] = {"score": 0, "n_tasks": 0, "confidence": "none",
                          "interpretation": f"No data for {d} yet."}
            continue
        mean_score = round(sum(data["scores"]) / n, 3)
        mean_conf = data["confidence_sum"] / n
        conf = "high" if n >= 5 and mean_conf >= 7 else "medium" if n >= 3 else "low"
        profile[d] = {
            "score": mean_score,
            "n_tasks": n,
            "confidence": conf,
            "interpretation": _dim_interpretation(d, mean_score, conf, n),
        }

    sorted_dims = sorted(profile.items(), key=lambda x: x[1]["score"], reverse=True)
    strongest = [d for d, v in sorted_dims if v.get("score", 0) > 0.6 and v.get("n_tasks", 0) > 0]
    weakest = [d for d, v in sorted_dims if v.get("score", 0) < 0.4 and v.get("n_tasks", 0) > 0]
    if not weakest:
        weakest = [sorted_dims[-1][0]] if sorted_dims else []

    top_dim = strongest[0] if strongest else sorted_dims[0][0] if sorted_dims else ""
    phen_label = PHENOTYPE_LABELS.get(top_dim, "mixed_profile")
    if len(strongest) >= 3:
        phen_label = "mixed_profile"
    else:
        best_score = max(v["score"] for v in profile.values() if v["n_tasks"] > 0)
        worst_score = min(v["score"] for v in profile.values() if v["n_tasks"] > 0)
        if best_score < 0.45:
            phen_label = "emerging_imager"
        elif best_score - worst_score < 0.15:
            phen_label = "mixed_profile"

    fatigue_cats = {}
    for s in sessions:
        cat = s.get("task_metadata", {}).get("category", "unknown")
        f = s.get("rating_payload", {}).get("fatigue", 3)
        fatigue_cats.setdefault(cat, []).append(f)
    most_fatiguing = max(fatigue_cats.items(), key=lambda x: sum(x[1]) / max(len(x[1]), 1))[0] if fatigue_cats else ""

    phenotype = {
        "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_completed_sessions": len(sessions),
        "phenotype_label": phen_label,
        "phenotype_interpretation": _phenotype_text(phen_label),
        "profile": profile,
        "strongest_dimensions": strongest,
        "weakest_dimensions": weakest,
        "most_fatiguing_task_category": most_fatiguing,
        "recommended_next_dimension": weakest[0] if weakest else strongest[0] if strongest else "",
        **SAFETY,
    }

    _save_phenotype(user_id, phenotype)
    return phenotype


def _dim_interpretation(dim, score, conf, n):
    label = dim.replace("_", " ")
    if conf == "none":
        return f"No data yet for {label}."
    if score > 0.7:
        return f"Strong {label} — this appears to be a personal strength (n={n})."
    if score > 0.5:
        return f"Moderate {label} — functional and trainable (n={n})."
    if score > 0.3:
        return f"Developing {label} — room for growth with practice (n={n})."
    return f"Emerging {label} — this dimension may respond well to focused training (n={n})."


def _phenotype_text(label):
    return {
        "vivid_visualizer": "Your imagery tends to be vivid and clear. You may benefit from adding complexity and variety.",
        "stable_constructor": "You construct spatially stable scenes well. Adding motion and detail could expand your range.",
        "detail_builder": "You generate fine detail well. Balancing detail with overall scene coherence may help.",
        "motion_imager": "Motion imagery is a strength. Combining motion with spatial stability can deepen your practice.",
        "emotional_scene_imager": "Emotional tone in imagery comes naturally. Balancing emotion with structural control may help.",
        "multisensory_imager": "You integrate multiple senses well. Deepening each individual sensory channel could add richness.",
        "emerging_imager": "Your imagery skills are in early development. Regular practice across varied tasks will build breadth.",
        "mixed_profile": "Your imagery profile is balanced. Focused training on your weakest dimensions could add depth.",
        "effortful_imager": "Imagery requires significant effort. Easier tasks and shorter sessions may help build comfort.",
    }.get(label, "Continue varied practice to deepen and broaden your imagery skills.")


def _save_phenotype(user_id, phenotype):
    d = os.path.join(PHENOTYPE_DIR, user_id)
    os.makedirs(d, exist_ok=True)
    sn = os.path.join(d, "snapshots")
    os.makedirs(sn, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")[:19]
    _save_json(os.path.join(sn, f"{ts}.json"), phenotype)
    _save_json(os.path.join(d, "latest_phenotype.json"), phenotype)


def load_imagery_phenotype(user_id="default"):
    p = os.path.join(PHENOTYPE_DIR, user_id, "latest_phenotype.json")
    return _load_json(p)


def analyze_imagery_gaps(user_id="default") -> dict:
    phenotype = load_imagery_phenotype(user_id)
    if not phenotype or phenotype.get("status") == "no_data":
        return {"user_id": user_id, "status": "no_data",
                "message": "Build an imagery phenotype first.", **SAFETY}

    profile = phenotype.get("profile", {})
    gaps = []
    for dim in ALL_DIMENSIONS:
        d = profile.get(dim, {})
        score = d.get("score", 0)
        conf = d.get("confidence", "none")
        n = d.get("n_tasks", 0)
        if conf == "none" or (score > 0.7 and conf == "high"):
            continue

        severity = "high" if score < 0.30 else "medium" if score < 0.55 else "low"
        evidence = [f"Score: {score:.2f} (n={n}, conf={conf})"]

        priority = 0
        if severity == "high":
            priority += 4
        elif severity == "medium":
            priority += 2
        if conf == "low":
            priority += 1
        if dim in phenotype.get("weakest_dimensions", []):
            priority += 2
        priority = min(10, priority)

        rec_cats = {
            "vividness": ["basic_vividness", "color_control"],
            "stability": ["spatial_stability", "meta_control"],
            "color_control": ["color_control", "basic_vividness"],
            "spatial_control": ["spatial_stability", "perspective_control", "scene_construction"],
            "detail": ["detail_generation", "scene_construction"],
            "motion": ["motion_imagery", "spatial_stability"],
            "emotion": ["emotional_tone_imagery", "scene_construction"],
            "multisensory": ["multisensory_imagery", "scene_construction"],
            "meta_control": ["meta_control", "spatial_stability"],
        }

        rec_focus = {
            "vividness": "vividness_foundation",
            "stability": "spatial_stability_training",
            "color_control": "color_intensity_training",
            "spatial_control": "spatial_stability_training",
            "detail": "detail_generation",
            "motion": "spatial_stability_training",
            "emotion": "emotional_tone_control",
            "multisensory": "vividness_foundation",
            "meta_control": "confidence_stabilization",
        }

        gaps.append({
            "gap_id": f"{dim}_gap",
            "dimension": dim,
            "severity": severity,
            "evidence": evidence,
            "recommended_task_categories": rec_cats.get(dim, ["basic_vividness"]),
            "recommended_training_focus": rec_focus.get(dim, "baseline_rebuild"),
            "priority": priority,
        })

    gaps.sort(key=lambda x: x["priority"], reverse=True)
    return {
        "user_id": user_id,
        "phenotype_label": phenotype.get("phenotype_label", ""),
        "ranked_gaps": gaps,
        "primary_gap": gaps[0]["dimension"] if gaps else "",
        "secondary_gap": gaps[1]["dimension"] if len(gaps) > 1 else "",
        "recommended_training_focus": gaps[0]["recommended_training_focus"] if gaps else "",
        **SAFETY,
    }


def generate_task_based_imagery_plan(user_id="default", duration_days=7) -> dict:
    from app.core.imagery.task_battery import list_imagery_tasks
    phenotype = load_imagery_phenotype(user_id)

    gaps = analyze_imagery_gaps(user_id)
    primary_gap = gaps.get("primary_gap", "")
    target_dims = [primary_gap] if primary_gap else ["vividness"]

    fatigue_mult = 1.0
    try:
        from app.core.adaptive.fatigue_adherence_model import analyze_fatigue_adherence_patterns
        fa = analyze_fatigue_adherence_patterns(user_id)
        if fa.get("fatigue", {}).get("risk_level") == "high":
            fatigue_mult = 0.6
    except Exception:
        pass

    all_tasks = list_imagery_tasks()["tasks"]

    plan_days = []
    for day in range(1, duration_days + 1):
        target_dim = target_dims[(day - 1) % len(target_dims)]
        matching = [t for t in all_tasks if target_dim in t.get("target_dimensions", [])]
        if not matching:
            matching = all_tasks
        task = matching[day % len(matching)]
        diff = task.get("difficulty", 2)
        if fatigue_mult < 1.0:
            diff = max(1, diff - 1)
        plan_days.append({
            "day": day, "task_id": task["task_id"],
            "task_title": task["title"],
            "target_dimension": target_dim,
            "prompt": task.get("prompt", ""),
            "duration_seconds": int(task.get("duration_seconds", 60) * fatigue_mult),
            "difficulty": diff,
            "why_chosen": (f"Targets your {target_dim.replace('_', ' ')} gap — "
                           f"category: {task.get('category', '')}."),
            "expected_rating_dimensions": task.get("target_dimensions", []),
        })

    plan_id = str(uuid4())
    plan = {
        "plan_id": plan_id, "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "plan_type": "task_based_imagery_training",
        "primary_gap": primary_gap,
        "phenotype_label": phenotype.get("phenotype_label", "unknown") if phenotype else "unknown",
        "target_dimensions": target_dims,
        "daily_tasks": plan_days,
        "expected_outcome": ("Focused practice on your primary imagery gap should improve "
                             f"self-reported {primary_gap} scores over {duration_days} days."),
        "safety": {
            "max_session_minutes": 15,
            "pause_if_distressed": True,
            "no_clinical_claims": True,
            "personal_exploratory_only": True,
        },
        **SAFETY,
    }

    _save_task_plan(user_id, plan)
    return plan


def _save_task_plan(user_id, plan):
    d = os.path.join(PLANS_DIR, user_id)
    os.makedirs(d, exist_ok=True)
    sn = os.path.join(d, "snapshots")
    os.makedirs(sn, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")[:19]
    _save_json(os.path.join(sn, f"{ts}.json"), plan)
    _save_json(os.path.join(d, "latest_task_plan.json"), plan)


def load_task_based_plan(user_id="default"):
    p = os.path.join(PLANS_DIR, user_id, "latest_task_plan.json")
    return _load_json(p)
