"""Structural scene diffs with human-readable explanations."""
from __future__ import annotations

from app.core.animus.scene import library
from app.core.animus.scene.model import SceneGraph

_SCENE_LABELS = {
    "style": "Style",
    "camera.position": "Camera position",
    "camera.target": "Camera target",
    "camera.fov": "Field of view",
    "camera.motion": "Camera motion",
    "camera.speed": "Camera speed",
    "lighting.key.color": "Key light color",
    "lighting.key.intensity": "Key light intensity",
    "lighting.ambient.color": "Ambient color",
    "lighting.ambient.intensity": "Ambient intensity",
    "lighting.rim.color": "Rim color",
    "lighting.rim.intensity": "Rim intensity",
    "atmosphere.fog.color": "Fog color",
    "atmosphere.fog.density": "Fog density",
    "atmosphere.sky.top": "Sky color",
    "atmosphere.sky.horizon": "Horizon color",
    "atmosphere.sky.bottom": "Sky floor color",
    "atmosphere.sky.stars": "Star count",
    "atmosphere.sky.aurora": "Aurora",
    "atmosphere.weather": "Weather",
    "atmosphere.time_of_day": "Time of day",
    "dynamics.wind": "Wind",
    "dynamics.water": "Water motion",
    "dynamics.fire": "Fire motion",
    "dynamics.floating": "Floating",
    "dynamics.pulse": "Pulse",
}


def _scene_values(scene: SceneGraph) -> dict:
    return {
        "style": scene.style,
        "camera.position": scene.camera.position,
        "camera.target": scene.camera.target,
        "camera.fov": scene.camera.fov,
        "camera.motion": scene.camera.motion,
        "camera.speed": scene.camera.speed,
        "lighting.key.color": scene.lighting.key_color,
        "lighting.key.intensity": scene.lighting.key_intensity,
        "lighting.ambient.color": scene.lighting.ambient_color,
        "lighting.ambient.intensity": scene.lighting.ambient_intensity,
        "lighting.rim.color": scene.lighting.rim_color,
        "lighting.rim.intensity": scene.lighting.rim_intensity,
        "atmosphere.fog.color": scene.atmosphere.fog_color,
        "atmosphere.fog.density": scene.atmosphere.fog_density,
        "atmosphere.sky.top": scene.atmosphere.sky_top,
        "atmosphere.sky.horizon": scene.atmosphere.sky_horizon,
        "atmosphere.sky.bottom": scene.atmosphere.sky_bottom,
        "atmosphere.sky.stars": scene.atmosphere.stars,
        "atmosphere.sky.aurora": scene.atmosphere.aurora,
        "atmosphere.weather": scene.atmosphere.weather,
        "atmosphere.time_of_day": scene.atmosphere.time_of_day,
        "dynamics.wind": scene.dynamics.wind,
        "dynamics.water": scene.dynamics.water,
        "dynamics.fire": scene.dynamics.fire,
        "dynamics.floating": scene.dynamics.floating,
        "dynamics.pulse": scene.dynamics.pulse,
    }


def _value_label(path: str, value) -> str:
    if path in ("atmosphere.fog.density", "dynamics.wind", "dynamics.water", "dynamics.fire",
                "dynamics.floating", "dynamics.pulse", "camera.speed", "lighting.key.intensity",
                "lighting.ambient.intensity", "lighting.rim.intensity"):
        return f"{float(value):.3f}"
    if path == "camera.fov":
        return f"{float(value):.0f} degrees"
    if isinstance(value, bool):
        return "on" if value else "off"
    if isinstance(value, list):
        return "[" + ", ".join(f"{float(v):.2f}" for v in value) + "]"
    return str(value)


def diff_scenes(before: SceneGraph, after: SceneGraph) -> dict:
    before_by_id = {e.id: e for e in before.entities}
    after_by_id = {e.id: e for e in after.entities}

    added = [{"entity_id": e.id, "label": e.label, "kind": e.kind}
             for e in after.entities if e.id not in before_by_id]
    removed = [{"entity_id": e.id, "label": e.label, "kind": e.kind}
               for e in before.entities if e.id not in after_by_id]

    changed: list[dict] = []
    locked_untouched: list[str] = []
    explanations: list[str] = []

    for entity in after.entities:
        old = before_by_id.get(entity.id)
        if old is None:
            continue
        for path in ("label", "visible", "locked", "role"):
            old_value, new_value = getattr(old, path), getattr(entity, path)
            if old_value != new_value:
                changed.append({"scope": "entity", "entity_id": entity.id, "label": entity.label,
                                "path": path, "before": old_value, "after": new_value,
                                "provenance": entity.provenance})
                explanations.append(f"{entity.label} · {path.replace('_', ' ').title()}: "
                                    f"{_value_label(path, old_value)} → {_value_label(path, new_value)}")

        for path in ("position", "rotation", "scale"):
            old_value, new_value = getattr(old, path), getattr(entity, path)
            if old_value != new_value:
                changed.append({"scope": "entity", "entity_id": entity.id, "label": entity.label,
                                "path": f"transform.{path}", "before": old_value, "after": new_value,
                                "provenance": entity.provenance})
                explanations.append(f"{entity.label} · {path.title()}: "
                                    f"{_value_label(path, old_value)} → {_value_label(path, new_value)}")

        for attr_path in sorted(set(old.attributes) | set(entity.attributes)):
            old_attr = old.attributes.get(attr_path)
            new_attr = entity.attributes.get(attr_path)
            if old_attr is not None and old_attr.locked and (
                    new_attr is None or new_attr.value != old_attr.value):
                # Commands enforce this; a diff still reports an impossible violation.
                changed.append({"scope": "entity", "entity_id": entity.id, "label": entity.label,
                                "path": f"attributes.{attr_path}", "before": old_attr.value,
                                "after": new_attr.value if new_attr else None,
                                "provenance": old_attr.provenance})
                continue
            if old_attr is None and new_attr is not None:
                changed.append({"scope": "entity", "entity_id": entity.id, "label": entity.label,
                                "path": f"attributes.{attr_path}", "before": None, "after": new_attr.value,
                                "provenance": new_attr.provenance})
                explanations.append(f"{entity.label} · {_attr_label(attr_path)} set to "
                                    f"{_value_label(attr_path, new_attr.value)}")
            elif old_attr is not None and new_attr is None:
                changed.append({"scope": "entity", "entity_id": entity.id, "label": entity.label,
                                "path": f"attributes.{attr_path}", "before": old_attr.value, "after": None,
                                "provenance": old_attr.provenance})
            elif old_attr is not None and new_attr is not None:
                if old_attr.value != new_attr.value:
                    changed.append({"scope": "entity", "entity_id": entity.id, "label": entity.label,
                                    "path": f"attributes.{attr_path}", "before": old_attr.value,
                                    "after": new_attr.value, "provenance": new_attr.provenance})
                    explanations.append(f"{entity.label} · {_attr_label(attr_path)}: "
                                        f"{_value_label(attr_path, old_attr.value)} → "
                                        f"{_value_label(attr_path, new_attr.value)}")
                elif old_attr.locked != new_attr.locked:
                    changed.append({"scope": "entity", "entity_id": entity.id, "label": entity.label,
                                    "path": f"attributes.{attr_path}.locked", "before": old_attr.locked,
                                    "after": new_attr.locked, "provenance": new_attr.provenance})
                    explanations.append(f"{entity.label} · {_attr_label(attr_path)} "
                                        f"{'locked' if new_attr.locked else 'unlocked'}")
                if old_attr.locked and old_attr.value == new_attr.value:
                    locked_untouched.append(f"{entity.id}.{attr_path}")

    before_scene, after_scene = _scene_values(before), _scene_values(after)
    for path, new_value in after_scene.items():
        old_value = before_scene[path]
        if old_value == new_value:
            continue
        changed.append({"scope": "scene", "entity_id": None, "label": _SCENE_LABELS.get(path, path),
                        "path": path, "before": old_value, "after": new_value,
                        "provenance": after.metadata.get("last_provenance", "SYSTEM_INFERRED")})
        explanations.append(f"{_SCENE_LABELS.get(path, path)}: "
                            f"{_value_label(path, old_value)} → {_value_label(path, new_value)}")

    constraints_before = {c.to_dict().__repr__() for c in before.constraints}
    constraints_after = {c.to_dict().__repr__() for c in after.constraints}
    if constraints_before != constraints_after:
        added_c = len(constraints_after - constraints_before)
        removed_c = len(constraints_before - constraints_after)
        explanations.append(f"Constraints: {added_c} added, {removed_c} removed")
        changed.append({"scope": "constraints", "entity_id": None, "label": "Constraints",
                        "path": "constraints", "before": len(before.constraints),
                        "after": len(after.constraints), "provenance": "USER_EXPLICIT"})

    if added:
        names = ", ".join(item["label"] for item in added)
        explanations.insert(0, f"Added {len(added)} element{'s' if len(added) != 1 else ''}: {names}")
    if removed:
        names = ", ".join(item["label"] for item in removed)
        explanations.insert(0, f"Removed {len(removed)} element{'s' if len(removed) != 1 else ''}: {names}")

    warnings = list(after.metadata.get("warnings") or [])
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "locked_untouched": sorted(set(locked_untouched)),
        "explanation": explanations,
        "warnings": warnings,
        "before_hash": before.content_hash(),
        "after_hash": after.content_hash(),
    }


def _attr_label(path: str) -> str:
    spec = library.attribute_spec(path)
    return spec["label"] if spec else path.replace("_", " ").title()


__all__ = ["diff_scenes"]
