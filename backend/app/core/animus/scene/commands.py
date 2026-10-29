"""Typed, validated scene commands.

Commands are the only way the product mutates a scene. They are intentionally narrow: every command has a
known target, every value is validated against the library, and locked content cannot be changed by any
command except an explicit unlock. This is what makes "preserve what is already right" enforceable rather
than a UI convention.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from app.core.animus.scene import library
from app.core.animus.scene.diff import diff_scenes
from app.core.animus.scene.model import (
    ALLOWED_MOTIONS,
    ALLOWED_RELATIONS,
    ALLOWED_STYLES,
    ALLOWED_TIMES,
    ALLOWED_WEATHER,
    MAX_ATTRIBUTE_TEXT,
    PROVENANCE_USER_EXPLICIT,
    PROVENANCE_USER_IMPLIED,
    USER_PROVENANCE,
    AttributeValue,
    SceneEntity,
    SceneGraph,
    SceneRelation,
    SceneValidationError,
    clamp,
    finite_number,
    make_entity_id_unique,
    sanitize_text,
)

SCENE_ATTRIBUTE_PATHS = {
    "style",
    "camera.position", "camera.target", "camera.fov", "camera.motion", "camera.speed",
    "lighting.key.color", "lighting.key.intensity", "lighting.key.direction",
    "lighting.ambient.color", "lighting.ambient.intensity",
    "lighting.rim.color", "lighting.rim.intensity",
    "atmosphere.fog.color", "atmosphere.fog.density",
    "atmosphere.sky.top", "atmosphere.sky.horizon", "atmosphere.sky.bottom",
    "atmosphere.sky.stars", "atmosphere.sky.aurora",
    "atmosphere.weather", "atmosphere.time_of_day",
    "dynamics.wind", "dynamics.water", "dynamics.fire", "dynamics.floating", "dynamics.pulse",
}


class LockedContentError(SceneValidationError):
    """Raised when a command tries to change locked content."""


class UnknownEntityError(SceneValidationError):
    """Raised when a command references an entity that does not exist."""


@dataclass
class AddEntityCommand:
    kind: str
    label: str | None = None
    position: list[float] | None = None
    role: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    op: str = "add_entity"


@dataclass
class RemoveEntityCommand:
    entity_id: str
    op: str = "remove_entity"


@dataclass
class SetEntityAttributeCommand:
    entity_id: str
    path: str
    value: Any
    lock: bool | None = None
    op: str = "set_entity_attribute"


@dataclass
class SetEntityTransformCommand:
    entity_id: str
    position: list[float] | None = None
    rotation: list[float] | None = None
    scale: list[float] | None = None
    op: str = "set_entity_transform"


@dataclass
class LockCommand:
    path: str = ""
    entity_id: str | None = None
    locked: bool = True
    op: str = "lock"


@dataclass
class SetSceneAttributeCommand:
    path: str
    value: Any
    op: str = "set_scene_attribute"


@dataclass
class SetRelationCommand:
    subject_id: str
    relation: str
    object_id: str
    op: str = "set_relation"


@dataclass
class RemoveRelationCommand:
    subject_id: str
    relation: str
    object_id: str
    op: str = "remove_relation"


SceneCommand = (
    AddEntityCommand | RemoveEntityCommand | SetEntityAttributeCommand | SetEntityTransformCommand
    | LockCommand | SetSceneAttributeCommand | SetRelationCommand | RemoveRelationCommand
)

_COMMAND_TYPES = {
    "add_entity": AddEntityCommand,
    "remove_entity": RemoveEntityCommand,
    "set_entity_attribute": SetEntityAttributeCommand,
    "set_entity_transform": SetEntityTransformCommand,
    "lock": LockCommand,
    "set_scene_attribute": SetSceneAttributeCommand,
    "set_relation": SetRelationCommand,
    "remove_relation": RemoveRelationCommand,
}


def parse_command(payload: dict) -> SceneCommand:
    if not isinstance(payload, dict):
        raise SceneValidationError("command must be an object")
    op = payload.get("op")
    cls = _COMMAND_TYPES.get(op)
    if cls is None:
        raise SceneValidationError(f"unknown command op {op!r}")
    allowed = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    extra = set(payload) - allowed
    if extra:
        raise SceneValidationError(f"unexpected fields for {op}: {sorted(extra)}")
    kwargs = {k: v for k, v in payload.items() if k != "op"}
    try:
        return cls(**kwargs)
    except TypeError as exc:
        raise SceneValidationError(f"invalid {op} command: {exc}") from exc


def _attribute(path: str, value: Any, provenance: str, *, locked: bool, source_text: str | None,
               warnings: list[str]) -> AttributeValue:
    if provenance not in USER_PROVENANCE:
        raise SceneValidationError("command attributes must carry explicit or implied user provenance")
    spec = library.attribute_spec(path)
    if spec is None:
        warnings.append(f"'{path}' is stored but not rendered yet")
        if isinstance(value, str):
            value = sanitize_text(value, max_len=MAX_ATTRIBUTE_TEXT)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            value = finite_number(value, field_name=path)
        elif isinstance(value, list):
            if len(value) > 16:
                raise SceneValidationError(f"{path} accepts at most 16 list items")
            cleaned: list[Any] = []
            for item in value:
                if isinstance(item, str):
                    cleaned.append(sanitize_text(item, max_len=MAX_ATTRIBUTE_TEXT))
                elif isinstance(item, (int, float)) and not isinstance(item, bool):
                    cleaned.append(finite_number(item, field_name=path))
                elif isinstance(item, bool):
                    cleaned.append(item)
                else:
                    raise SceneValidationError(f"unsupported list item for {path!r}")
            value = cleaned
        elif not isinstance(value, bool):
            raise SceneValidationError(f"unsupported custom attribute value for {path!r}")
        return AttributeValue(value=value, confidence=1.0 if provenance == PROVENANCE_USER_EXPLICIT else 0.6,
                              provenance=provenance, locked=locked, source_text=source_text,
                              renderable=False)

    kind = spec["type"]
    if kind == "color":
        value = library.normalize_color(str(value))
    elif kind == "number":
        value = clamp(finite_number(value, field_name=path), float(spec["min"]), float(spec["max"]))
        value = round(value, 6)
    elif kind == "integer":
        value = int(clamp(finite_number(value, field_name=path), float(spec["min"]), float(spec["max"])))
    elif kind == "enum":
        text = str(value).strip().lower()
        if text not in spec["options"]:
            raise SceneValidationError(f"{path} must be one of {spec['options']}")
        value = text
    else:
        raise SceneValidationError(f"unsupported attribute type {kind!r}")

    return AttributeValue(value=value, confidence=1.0 if provenance == PROVENANCE_USER_EXPLICIT else 0.6,
                          provenance=provenance, locked=locked, source_text=source_text,
                          renderable=bool(spec.get("renderable", True)))


def _parse_vec3(value: Any, name: str, *, minimum: float = -256.0,
                maximum: float = 256.0) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise SceneValidationError(f"{name} must be a 3-vector")
    out = [round(finite_number(v, field_name=name), 6) for v in value]
    if any(v < minimum or v > maximum for v in out):
        raise SceneValidationError(f"{name} must stay between {minimum:g} and {maximum:g}")
    return out


def _parse_rotation(value: Any, name: str) -> list[float]:
    out = _parse_vec3(value, name, minimum=-1000.0, maximum=1000.0)
    return out


def _parse_scale(value: Any) -> list[float]:
    out = _parse_vec3(value, "scale", minimum=0.01, maximum=64.0)
    return out


def _require_entity(scene: SceneGraph, entity_id: str) -> SceneEntity:
    try:
        return scene.find_entity(entity_id)
    except SceneValidationError as exc:
        raise UnknownEntityError(str(exc)) from exc


def _guard_unlocked(entity: SceneEntity, *, allow_label: bool = False) -> None:
    if entity.locked:
        raise LockedContentError(f"{entity.label} is locked; unlock it before changing it")


def _set_scene_value(scene: SceneGraph, path: str, value: Any) -> None:
    if path not in SCENE_ATTRIBUTE_PATHS:
        raise SceneValidationError(f"unknown scene attribute {path!r}")
    if path == "style":
        if value not in ALLOWED_STYLES:
            raise SceneValidationError(f"style must be one of {ALLOWED_STYLES}")
        scene.style = value
        return
    if path == "camera.position":
        scene.camera.position = _parse_vec3(value, path)
        return
    if path == "camera.target":
        scene.camera.target = _parse_vec3(value, path)
        return
    if path == "camera.fov":
        scene.camera.fov = float(clamp(finite_number(value, field_name=path), 20, 90))
        return
    if path == "camera.motion":
        if value not in ALLOWED_MOTIONS:
            raise SceneValidationError(f"camera.motion must be one of {ALLOWED_MOTIONS}")
        scene.camera.motion = value
        return
    if path == "camera.speed":
        scene.camera.speed = float(clamp(finite_number(value, field_name=path), 0, 2))
        return
    if path.startswith("lighting."):
        field_name = path.split(".", 1)[1]
        if field_name.endswith(".color") or field_name in ("key.color", "ambient.color", "rim.color"):
            color = library.normalize_color(str(value))
            if field_name == "key.color":
                scene.lighting.key_color = color
            elif field_name == "ambient.color":
                scene.lighting.ambient_color = color
            else:
                scene.lighting.rim_color = color
            return
        if field_name == "key.direction":
            scene.lighting.key_direction = _parse_vec3(value, path, minimum=-8.0, maximum=8.0)
            return
        if field_name == "key.intensity":
            scene.lighting.key_intensity = float(clamp(finite_number(value, field_name=path), 0, 8))
            return
        if field_name == "ambient.intensity":
            scene.lighting.ambient_intensity = float(clamp(finite_number(value, field_name=path), 0, 4))
            return
        if field_name == "rim.intensity":
            scene.lighting.rim_intensity = float(clamp(finite_number(value, field_name=path), 0, 4))
            return
        raise SceneValidationError(f"unknown lighting attribute {path!r}")
    if path.startswith("atmosphere."):
        field_name = path.split(".", 1)[1]
        if field_name in ("fog.color", "sky.top", "sky.horizon", "sky.bottom"):
            color = library.normalize_color(str(value))
            attr = {"fog.color": "fog_color", "sky.top": "sky_top", "sky.horizon": "sky_horizon",
                    "sky.bottom": "sky_bottom"}[field_name]
            setattr(scene.atmosphere, attr, color)
            return
        if field_name == "fog.density":
            scene.atmosphere.fog_density = float(clamp(finite_number(value, field_name=path), 0, 0.2))
            return
        if field_name == "sky.stars":
            scene.atmosphere.stars = int(clamp(finite_number(value, field_name=path), 0, 4000))
            return
        if field_name == "sky.aurora":
            scene.atmosphere.aurora = bool(value)
            return
        if field_name == "weather":
            if value not in ALLOWED_WEATHER:
                raise SceneValidationError(f"weather must be one of {ALLOWED_WEATHER}")
            scene.atmosphere.weather = value
            return
        if field_name == "time_of_day":
            if value not in ALLOWED_TIMES:
                raise SceneValidationError(f"time_of_day must be one of {ALLOWED_TIMES}")
            scene.atmosphere.time_of_day = value
            return
        raise SceneValidationError(f"unknown atmosphere attribute {path!r}")
    if path.startswith("dynamics."):
        field_name = path.split(".", 1)[1]
        if field_name not in ("wind", "water", "fire", "floating", "pulse"):
            raise SceneValidationError(f"unknown dynamics attribute {path!r}")
        setattr(scene.dynamics, field_name, float(clamp(finite_number(value, field_name=path), 0, 1)))
        return
    raise SceneValidationError(f"unknown scene attribute {path!r}")


def apply_commands(
        scene: SceneGraph,
        commands: list[SceneCommand],
        *,
        provenance: str = PROVENANCE_USER_EXPLICIT,
        source_text: str | None = None,
) -> tuple[SceneGraph, dict, list[str]]:
    """Apply commands to a copy of the scene and return ``(scene, diff, warnings)``.

    The version is not incremented here; versioning belongs to the session service so one command batch is
    exactly one immutable version.
    """
    if provenance not in USER_PROVENANCE:
        raise SceneValidationError("product commands must carry user provenance")
    if not commands:
        raise SceneValidationError("at least one command is required")
    if len(commands) > 24:
        raise SceneValidationError("at most 24 commands per batch")

    before = scene.copy()
    after = scene.copy()
    warnings: list[str] = []
    source = sanitize_text(source_text, max_len=MAX_ATTRIBUTE_TEXT) if source_text else None

    for command in commands:
        if isinstance(command, AddEntityCommand):
            if len(after.entities) >= 40:
                raise SceneValidationError("scene is full (40 elements)")
            kind = library.normalize_kind(command.kind)
            if kind == "custom":
                warnings.append(f"'{sanitize_text(command.kind, max_len=40)}' is shown as an abstract form")
            label = sanitize_text(command.label or library.kind_label(kind), max_len=80)
            entity_id = make_entity_id_unique(after.seed, kind, len(after.entities),
                                              {e.id for e in after.entities})
            position = _parse_vec3(command.position, "position") if command.position is not None else \
                library.default_position(kind, len(after.entities))
            attributes: dict[str, AttributeValue] = {}
            if command.attributes:
                for path, value in command.attributes.items():
                    attributes[path] = _attribute(path, value, provenance, locked=False,
                                                 source_text=source, warnings=warnings)
            else:
                for path, value in library.KIND_DEFAULT_ATTRIBUTES.get(kind, {}).items():
                    attributes[path] = _attribute(path, value, PROVENANCE_USER_IMPLIED, locked=False,
                                                 source_text=None, warnings=warnings)
            after.entities.append(SceneEntity(
                id=entity_id, kind=kind, label=label,
                role=command.role or library.default_role(kind),
                position=position, attributes=attributes,
                confidence=1.0 if provenance == PROVENANCE_USER_EXPLICIT else 0.6,
                provenance=provenance,
            ))
            continue

        if isinstance(command, RemoveEntityCommand):
            entity = _require_entity(after, command.entity_id)
            _guard_unlocked(entity)
            after.entities = [e for e in after.entities if e.id != entity.id]
            after.relations = [r for r in after.relations
                               if r.subject_id != entity.id and r.object_id != entity.id]
            warnings.append(f"Removed {entity.label}")
            continue

        if isinstance(command, SetEntityAttributeCommand):
            entity = _require_entity(after, command.entity_id)
            _guard_unlocked(entity)
            existing = entity.attributes.get(command.path)
            if existing is not None and existing.locked:
                raise LockedContentError(f"{entity.label} · {command.path} is locked")
            if not command.path or len(command.path) > 60:
                raise SceneValidationError("attribute path is invalid")
            lock = bool(command.lock) if command.lock is not None else bool(existing and existing.locked)
            attribute = _attribute(command.path, command.value, provenance, locked=lock,
                                   source_text=source, warnings=warnings)
            if existing is not None and existing.value == attribute.value and existing.locked == attribute.locked:
                warnings.append(f"No change for {entity.label} · {command.path}")
            entity.attributes[command.path] = attribute
            entity.confidence = min(1.0, max(entity.confidence, attribute.confidence))
            entity.provenance = provenance
            continue

        if isinstance(command, SetEntityTransformCommand):
            entity = _require_entity(after, command.entity_id)
            _guard_unlocked(entity)
            if command.position is not None:
                entity.position = _parse_vec3(command.position, "position")
            if command.rotation is not None:
                entity.rotation = _parse_rotation(command.rotation, "rotation")
            if command.scale is not None:
                entity.scale = _parse_scale(command.scale)
            entity.provenance = provenance
            continue

        if isinstance(command, LockCommand):
            if command.entity_id is None:
                raise SceneValidationError("lock requires an entity_id")
            entity = _require_entity(after, command.entity_id)
            if command.path:
                existing = entity.attributes.get(command.path)
                if existing is None:
                    raise SceneValidationError(f"{entity.label} has no attribute {command.path!r}")
                existing.locked = bool(command.locked)
            else:
                entity.locked = bool(command.locked)
            entity.provenance = provenance
            continue

        if isinstance(command, SetSceneAttributeCommand):
            _set_scene_value(after, command.path, command.value)
            edited = list(after.metadata.get("user_scene_paths") or [])
            if command.path not in edited:
                edited.append(command.path)
            after.metadata["user_scene_paths"] = edited
            continue

        if isinstance(command, SetRelationCommand):
            subject = _require_entity(after, command.subject_id)
            _require_entity(after, command.object_id)
            if command.relation not in ALLOWED_RELATIONS:
                raise SceneValidationError(f"relation must be one of {ALLOWED_RELATIONS}")
            if subject.id == command.object_id:
                raise SceneValidationError("a relation cannot reference the same entity twice")
            if not any(r.subject_id == command.subject_id and r.relation == command.relation
                       and r.object_id == command.object_id for r in after.relations):
                after.relations.append(SceneRelation(
                    subject_id=command.subject_id, relation=command.relation,
                    object_id=command.object_id, confidence=1.0 if provenance == PROVENANCE_USER_EXPLICIT else 0.6,
                    provenance=provenance))
            continue

        if isinstance(command, RemoveRelationCommand):
            before_count = len(after.relations)
            after.relations = [r for r in after.relations
                               if not (r.subject_id == command.subject_id and r.relation == command.relation
                                       and r.object_id == command.object_id)]
            if len(after.relations) == before_count:
                warnings.append("That relation was not present")
            continue

        raise SceneValidationError(f"unsupported command {type(command).__name__}")

    after.metadata = dict(after.metadata)
    after.metadata["last_provenance"] = provenance
    after.metadata["warnings"] = warnings
    after.metadata["source_text"] = source
    if not math.isfinite(after.camera.fov):
        raise SceneValidationError("camera fov is invalid")
    diff = diff_scenes(before, after)
    diff["warnings"] = sorted(set(warnings) | set(diff.get("warnings") or []))
    return after, diff, warnings


__all__ = [
    "SceneCommand", "AddEntityCommand", "RemoveEntityCommand", "SetEntityAttributeCommand",
    "SetEntityTransformCommand", "LockCommand", "SetSceneAttributeCommand", "SetRelationCommand",
    "RemoveRelationCommand", "LockedContentError", "UnknownEntityError", "parse_command",
    "apply_commands", "SCENE_ATTRIBUTE_PATHS",
]
