"""ANIMUS Studio scene graph (ANIMUS-SG-v1).

The product layer edits a *symbolic* scene. It is deliberately separate from the research belief state
(IBS-v1): the belief state is an inference artifact, while the scene graph is the thing the user can see,
correct, lock, version and branch. Nothing here decodes neural content, and nothing here is a
reconstruction of imagery.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from typing import Any

SCENE_VERSION = "ANIMUS-SG-v1"
MAX_ENTITIES = 40
MAX_TEXT = 500
MAX_ATTRIBUTE_TEXT = 120

PROVENANCE_USER_EXPLICIT = "USER_EXPLICIT"
PROVENANCE_USER_IMPLIED = "USER_IMPLIED"
PROVENANCE_SYSTEM_DEFAULT = "SYSTEM_DEFAULT"
PROVENANCE_SYSTEM_INFERRED = "SYSTEM_INFERRED"
PROVENANCE_SIMULATED = "SIMULATED"
PROVENANCE_NEURAL_PERCEPTION = "NEURAL_PERCEPTION_VALIDATED"
PROVENANCE_NEURAL_IMAGERY_FORBIDDEN = "NEURAL_IMAGERY_UNAUTHORIZED"

ALL_PROVENANCE = (
    PROVENANCE_USER_EXPLICIT,
    PROVENANCE_USER_IMPLIED,
    PROVENANCE_SYSTEM_DEFAULT,
    PROVENANCE_SYSTEM_INFERRED,
    PROVENANCE_SIMULATED,
    PROVENANCE_NEURAL_PERCEPTION,
)

# Fail-closed: this provenance may never be written into a product scene.
FORBIDDEN_PROVENANCE = (PROVENANCE_NEURAL_IMAGERY_FORBIDDEN,)

PROVENANCE_CONFIDENCE = {
    PROVENANCE_USER_EXPLICIT: 1.0,
    PROVENANCE_USER_IMPLIED: 0.6,
    PROVENANCE_SYSTEM_DEFAULT: 0.2,
    PROVENANCE_SYSTEM_INFERRED: 0.4,
    PROVENANCE_SIMULATED: 0.5,
    PROVENANCE_NEURAL_PERCEPTION: 0.9,
}

USER_PROVENANCE = (PROVENANCE_USER_EXPLICIT, PROVENANCE_USER_IMPLIED)

ALLOWED_ROLES = ("subject", "background", "prop")
ALLOWED_STYLES = (
    "cinematic", "minimal", "gothic", "surreal", "cyberpunk", "painterly", "ancient", "futuristic",
)
ALLOWED_MOTIONS = ("static", "orbit", "dolly")
ALLOWED_WEATHER = ("clear", "rain", "snow", "mist")
ALLOWED_TIMES = ("dawn", "day", "dusk", "night")
ALLOWED_CONSTRAINT_KINDS = ("exclude", "require", "preserve")
ALLOWED_RELATIONS = ("above", "below", "left_of", "right_of", "behind", "in_front_of", "next_to", "around")


class SceneError(ValueError):
    """Base class for scene-domain errors."""


class SceneValidationError(SceneError):
    """Raised when a scene or command would violate a scene invariant."""


def sanitize_text(text: Any, *, max_len: int = MAX_TEXT) -> str:
    if text is None:
        return ""
    if not isinstance(text, str):
        raise SceneValidationError("text must be a string")
    cleaned = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    cleaned = re.sub(r"[ \t]+", " ", cleaned).strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip()
    return cleaned


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def finite_number(value: Any, *, field_name: str = "value") -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise SceneValidationError(f"{field_name} must be a number") from exc
    if not math.isfinite(number):
        raise SceneValidationError(f"{field_name} must be finite")
    return number


def _round(value: Any, digits: int = 6) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SceneValidationError("scene contains a non-finite number")
        return round(value, digits)
    if isinstance(value, list):
        return [_round(v, digits) for v in value]
    if isinstance(value, dict):
        return {str(k): _round(v, digits) for k, v in value.items()}
    return value


def canonical_json(payload: Any) -> str:
    return json.dumps(_round(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def make_scene_id(seed: int) -> str:
    return "scene_" + hashlib.sha256(f"{seed}:scene".encode("utf-8")).hexdigest()[:12]


def make_entity_id(seed: int, kind: str, index: int) -> str:
    digest = hashlib.sha256(f"{seed}:{kind}:{index}".encode("utf-8")).hexdigest()
    return "ent_" + digest[:8]


def make_entity_id_unique(seed: int, kind: str, index: int, existing: set[str]) -> str:
    candidate = make_entity_id(seed, kind, index)
    salt = 0
    while candidate in existing:
        salt += 1
        candidate = "ent_" + hashlib.sha256(f"{seed}:{kind}:{index}:{salt}".encode("utf-8")).hexdigest()[:8]
    return candidate


@dataclass
class AttributeValue:
    value: Any
    confidence: float = 0.2
    provenance: str = PROVENANCE_SYSTEM_DEFAULT
    locked: bool = False
    source_text: str | None = None
    renderable: bool = True

    def __post_init__(self) -> None:
        if self.provenance not in ALL_PROVENANCE:
            raise SceneValidationError(f"unknown provenance {self.provenance!r}")
        if self.provenance in FORBIDDEN_PROVENANCE:
            raise SceneValidationError("imagery-neural provenance is not authorized in a product scene")
        self.confidence = clamp(finite_number(self.confidence, field_name="confidence"), 0.0, 1.0)
        if self.source_text is not None:
            self.source_text = sanitize_text(self.source_text, max_len=MAX_ATTRIBUTE_TEXT)
        if isinstance(self.value, float):
            self.value = _round(self.value)
        if isinstance(self.value, str):
            self.value = sanitize_text(self.value, max_len=MAX_ATTRIBUTE_TEXT)
        if self.value is None:
            raise SceneValidationError("attribute value must not be None")

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "confidence": round(float(self.confidence), 6),
            "provenance": self.provenance,
            "locked": bool(self.locked),
            "source_text": self.source_text,
            "renderable": bool(self.renderable),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "AttributeValue":
        return cls(
            value=payload.get("value"),
            confidence=payload.get("confidence", 0.2),
            provenance=payload.get("provenance", PROVENANCE_SYSTEM_DEFAULT),
            locked=bool(payload.get("locked", False)),
            source_text=payload.get("source_text"),
            renderable=bool(payload.get("renderable", True)),
        )


@dataclass
class SceneEntity:
    id: str
    kind: str
    label: str
    role: str = "prop"
    position: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    attributes: dict[str, AttributeValue] = field(default_factory=dict)
    confidence: float = 0.5
    provenance: str = PROVENANCE_SYSTEM_DEFAULT
    locked: bool = False
    visible: bool = True
    parent_id: str | None = None

    def __post_init__(self) -> None:
        if not re.fullmatch(r"ent_[0-9a-f]{8}", str(self.id)):
            raise SceneValidationError(f"invalid entity id {self.id!r}")
        self.kind = sanitize_text(self.kind, max_len=40).lower() or "custom"
        self.label = sanitize_text(self.label, max_len=80) or self.kind
        if self.role not in ALLOWED_ROLES:
            raise SceneValidationError(f"invalid role {self.role!r}")
        self.position = self._vec3(self.position, "position")
        self.rotation = self._vec3(self.rotation, "rotation")
        self.scale = self._vec3(self.scale, "scale", positive=True)
        self.confidence = clamp(finite_number(self.confidence, field_name="confidence"), 0.0, 1.0)
        if self.provenance not in ALL_PROVENANCE:
            raise SceneValidationError(f"unknown provenance {self.provenance!r}")
        if not isinstance(self.attributes, dict):
            raise SceneValidationError("attributes must be a mapping")
        for path, attribute in self.attributes.items():
            if not isinstance(attribute, AttributeValue):
                raise SceneValidationError(f"attribute {path!r} is not an AttributeValue")

    @staticmethod
    def _vec3(value: Any, name: str, *, positive: bool = False) -> list[float]:
        if not isinstance(value, (list, tuple)) or len(value) != 3:
            raise SceneValidationError(f"{name} must be a 3-vector")
        out = [finite_number(v, field_name=name) for v in value]
        if positive and any(v <= 0 for v in out):
            raise SceneValidationError(f"{name} components must be positive")
        return [round(v, 6) for v in out]

    def attribute(self, path: str) -> AttributeValue | None:
        return self.attributes.get(path)

    def set_attribute(self, path: str, attribute: AttributeValue) -> None:
        self.attributes[path] = attribute

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "role": self.role,
            "transform": {
                "position": list(self.position),
                "rotation": list(self.rotation),
                "scale": list(self.scale),
            },
            "attributes": {k: v.to_dict() for k, v in sorted(self.attributes.items())},
            "confidence": round(float(self.confidence), 6),
            "provenance": self.provenance,
            "locked": bool(self.locked),
            "visible": bool(self.visible),
            "parent_id": self.parent_id,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "SceneEntity":
        transform = payload.get("transform") or {}
        return cls(
            id=payload.get("id", ""),
            kind=payload.get("kind", "custom"),
            label=payload.get("label", ""),
            role=payload.get("role", "prop"),
            position=transform.get("position", payload.get("position", [0, 0, 0])),
            rotation=transform.get("rotation", payload.get("rotation", [0, 0, 0])),
            scale=transform.get("scale", payload.get("scale", [1, 1, 1])),
            attributes={k: AttributeValue.from_dict(v) for k, v in (payload.get("attributes") or {}).items()},
            confidence=payload.get("confidence", 0.5),
            provenance=payload.get("provenance", PROVENANCE_SYSTEM_DEFAULT),
            locked=bool(payload.get("locked", False)),
            visible=bool(payload.get("visible", True)),
            parent_id=payload.get("parent_id"),
        )


@dataclass
class SceneRelation:
    subject_id: str
    relation: str
    object_id: str
    confidence: float = 0.5
    provenance: str = PROVENANCE_SYSTEM_DEFAULT

    def __post_init__(self) -> None:
        if self.relation not in ALLOWED_RELATIONS:
            raise SceneValidationError(f"invalid relation {self.relation!r}")
        if self.subject_id == self.object_id:
            raise SceneValidationError("a relation cannot reference the same entity twice")
        self.confidence = clamp(finite_number(self.confidence, field_name="confidence"), 0.0, 1.0)
        if self.provenance not in ALL_PROVENANCE:
            raise SceneValidationError(f"unknown provenance {self.provenance!r}")

    def to_dict(self) -> dict:
        return {
            "subject_id": self.subject_id,
            "relation": self.relation,
            "object_id": self.object_id,
            "confidence": round(float(self.confidence), 6),
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "SceneRelation":
        return cls(
            subject_id=payload.get("subject_id", ""),
            relation=payload.get("relation", "next_to"),
            object_id=payload.get("object_id", ""),
            confidence=payload.get("confidence", 0.5),
            provenance=payload.get("provenance", PROVENANCE_SYSTEM_DEFAULT),
        )


@dataclass
class SceneConstraint:
    kind: str
    target: str
    value: Any = None
    strength: float = 1.0
    provenance: str = PROVENANCE_USER_EXPLICIT

    def __post_init__(self) -> None:
        if self.kind not in ALLOWED_CONSTRAINT_KINDS:
            raise SceneValidationError(f"invalid constraint kind {self.kind!r}")
        self.target = sanitize_text(self.target, max_len=120)
        if not self.target:
            raise SceneValidationError("constraint target must not be empty")
        self.strength = clamp(finite_number(self.strength, field_name="strength"), 0.0, 1.0)
        if self.provenance not in ALL_PROVENANCE:
            raise SceneValidationError(f"unknown provenance {self.provenance!r}")

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "target": self.target,
            "value": self.value,
            "strength": round(float(self.strength), 6),
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "SceneConstraint":
        return cls(
            kind=payload.get("kind", "preserve"),
            target=payload.get("target", ""),
            value=payload.get("value"),
            strength=payload.get("strength", 1.0),
            provenance=payload.get("provenance", PROVENANCE_USER_EXPLICIT),
        )


@dataclass
class CameraSpec:
    position: list[float] = field(default_factory=lambda: [0.0, 2.4, 8.0])
    target: list[float] = field(default_factory=lambda: [0.0, 1.2, 0.0])
    fov: float = 48.0
    motion: str = "orbit"
    speed: float = 0.15

    def __post_init__(self) -> None:
        self.position = SceneEntity._vec3(self.position, "camera.position")
        self.target = SceneEntity._vec3(self.target, "camera.target")
        self.fov = clamp(finite_number(self.fov, field_name="camera.fov"), 20.0, 90.0)
        if self.motion not in ALLOWED_MOTIONS:
            raise SceneValidationError(f"invalid camera motion {self.motion!r}")
        self.speed = clamp(finite_number(self.speed, field_name="camera.speed"), 0.0, 2.0)

    def to_dict(self) -> dict:
        return {
            "position": list(self.position),
            "target": list(self.target),
            "fov": round(float(self.fov), 6),
            "motion": self.motion,
            "speed": round(float(self.speed), 6),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "CameraSpec":
        return cls(
            position=payload.get("position", [0, 2.4, 8]),
            target=payload.get("target", [0, 1.2, 0]),
            fov=payload.get("fov", 48),
            motion=payload.get("motion", "orbit"),
            speed=payload.get("speed", 0.15),
        )


@dataclass
class LightingSpec:
    key_color: str = "#ffffff"
    key_intensity: float = 1.0
    key_direction: list[float] = field(default_factory=lambda: [2.0, 4.0, 3.0])
    ambient_color: str = "#6f7cff"
    ambient_intensity: float = 0.35
    rim_color: str = "#79e8ff"
    rim_intensity: float = 0.5

    def __post_init__(self) -> None:
        for name in ("key_color", "ambient_color", "rim_color"):
            setattr(self, name, _normalize_hex(getattr(self, name)))
        self.key_intensity = clamp(finite_number(self.key_intensity, field_name="key_intensity"), 0.0, 8.0)
        self.ambient_intensity = clamp(finite_number(self.ambient_intensity, field_name="ambient_intensity"), 0.0, 4.0)
        self.rim_intensity = clamp(finite_number(self.rim_intensity, field_name="rim_intensity"), 0.0, 4.0)
        self.key_direction = SceneEntity._vec3(self.key_direction, "key_direction")

    def to_dict(self) -> dict:
        return {
            "key": {"color": self.key_color, "intensity": round(self.key_intensity, 6),
                    "direction": list(self.key_direction)},
            "ambient": {"color": self.ambient_color, "intensity": round(self.ambient_intensity, 6)},
            "rim": {"color": self.rim_color, "intensity": round(self.rim_intensity, 6)},
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "LightingSpec":
        key = payload.get("key") or {}
        ambient = payload.get("ambient") or {}
        rim = payload.get("rim") or {}
        return cls(
            key_color=key.get("color", "#ffffff"),
            key_intensity=key.get("intensity", 1.0),
            key_direction=key.get("direction", [2, 4, 3]),
            ambient_color=ambient.get("color", "#6f7cff"),
            ambient_intensity=ambient.get("intensity", 0.35),
            rim_color=rim.get("color", "#79e8ff"),
            rim_intensity=rim.get("intensity", 0.5),
        )


@dataclass
class AtmosphereSpec:
    fog_color: str = "#0b1024"
    fog_density: float = 0.025
    sky_top: str = "#070a18"
    sky_horizon: str = "#1b2a52"
    sky_bottom: str = "#05060d"
    stars: int = 400
    aurora: bool = False
    weather: str = "clear"
    time_of_day: str = "night"

    def __post_init__(self) -> None:
        for name in ("fog_color", "sky_top", "sky_horizon", "sky_bottom"):
            setattr(self, name, _normalize_hex(getattr(self, name)))
        self.fog_density = clamp(finite_number(self.fog_density, field_name="fog_density"), 0.0, 0.2)
        self.stars = int(clamp(finite_number(self.stars, field_name="stars"), 0, 4000))
        if self.weather not in ALLOWED_WEATHER:
            raise SceneValidationError(f"invalid weather {self.weather!r}")
        if self.time_of_day not in ALLOWED_TIMES:
            raise SceneValidationError(f"invalid time_of_day {self.time_of_day!r}")

    def to_dict(self) -> dict:
        return {
            "fog": {"color": self.fog_color, "density": round(self.fog_density, 6)},
            "sky": {"top": self.sky_top, "horizon": self.sky_horizon, "bottom": self.sky_bottom,
                    "stars": self.stars, "aurora": bool(self.aurora)},
            "weather": self.weather,
            "time_of_day": self.time_of_day,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "AtmosphereSpec":
        fog = payload.get("fog") or {}
        sky = payload.get("sky") or {}
        return cls(
            fog_color=fog.get("color", "#0b1024"),
            fog_density=fog.get("density", 0.025),
            sky_top=sky.get("top", "#070a18"),
            sky_horizon=sky.get("horizon", "#1b2a52"),
            sky_bottom=sky.get("bottom", "#05060d"),
            stars=sky.get("stars", 400),
            aurora=bool(sky.get("aurora", False)),
            weather=payload.get("weather", "clear"),
            time_of_day=payload.get("time_of_day", "night"),
        )


@dataclass
class DynamicsSpec:
    wind: float = 0.2
    water: float = 0.3
    fire: float = 0.0
    floating: float = 0.0
    pulse: float = 0.0

    def __post_init__(self) -> None:
        for name in ("wind", "water", "fire", "floating", "pulse"):
            setattr(self, name, clamp(finite_number(getattr(self, name), field_name=name), 0.0, 1.0))

    def to_dict(self) -> dict:
        return {name: round(float(getattr(self, name)), 6)
                for name in ("wind", "water", "fire", "floating", "pulse")}

    @classmethod
    def from_dict(cls, payload: dict) -> "DynamicsSpec":
        return cls(**{name: payload.get(name, default) for name, default in
                      (("wind", 0.2), ("water", 0.3), ("fire", 0.0), ("floating", 0.0), ("pulse", 0.0))})


def _normalize_hex(value: Any) -> str:
    if not isinstance(value, str):
        raise SceneValidationError("color must be a hex string")
    text = value.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3}", text):
        return "#" + "".join(ch * 2 for ch in text[1:])
    if re.fullmatch(r"#[0-9a-f]{6}", text):
        return text
    raise SceneValidationError(f"invalid hex color {value!r}")


@dataclass
class SceneGraph:
    scene_id: str
    version: int = 1
    seed: int = 0
    title: str = "Untitled scene"
    entities: list[SceneEntity] = field(default_factory=list)
    relations: list[SceneRelation] = field(default_factory=list)
    style: str = "cinematic"
    camera: CameraSpec = field(default_factory=CameraSpec)
    lighting: LightingSpec = field(default_factory=LightingSpec)
    atmosphere: AtmosphereSpec = field(default_factory=AtmosphereSpec)
    dynamics: DynamicsSpec = field(default_factory=DynamicsSpec)
    constraints: list[SceneConstraint] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    version_tag: str = SCENE_VERSION

    def __post_init__(self) -> None:
        if not re.fullmatch(r"scene_[0-9a-f]{8,16}", str(self.scene_id)):
            raise SceneValidationError(f"invalid scene id {self.scene_id!r}")
        self.version = int(clamp(finite_number(self.version, field_name="version"), 1, 1_000_000))
        self.seed = int(finite_number(self.seed, field_name="seed"))
        self.title = sanitize_text(self.title, max_len=120) or "Untitled scene"
        if self.style not in ALLOWED_STYLES:
            raise SceneValidationError(f"invalid style {self.style!r}")
        if not isinstance(self.entities, list) or not all(isinstance(e, SceneEntity) for e in self.entities):
            raise SceneValidationError("entities must be a list of SceneEntity")
        if len(self.entities) > MAX_ENTITIES:
            raise SceneValidationError(f"scene exceeds the {MAX_ENTITIES}-entity limit")
        ids = [e.id for e in self.entities]
        if len(ids) != len(set(ids)):
            raise SceneValidationError("duplicate entity id")
        entity_ids = set(ids)
        for relation in self.relations:
            if not isinstance(relation, SceneRelation):
                raise SceneValidationError("relations must be a list of SceneRelation")
            if relation.subject_id not in entity_ids or relation.object_id not in entity_ids:
                raise SceneValidationError("relation references an unknown entity")
        if not isinstance(self.constraints, list) or not all(isinstance(c, SceneConstraint) for c in self.constraints):
            raise SceneValidationError("constraints must be a list of SceneConstraint")
        if self.metadata is None:
            self.metadata = {}
        if not isinstance(self.metadata, dict):
            raise SceneValidationError("metadata must be a mapping")

    def find_entity(self, entity_id: str) -> SceneEntity:
        for entity in self.entities:
            if entity.id == entity_id:
                return entity
        raise SceneValidationError(f"unknown entity {entity_id!r}")

    def has_entity(self, entity_id: str) -> bool:
        return any(e.id == entity_id for e in self.entities)

    def attribute_confidence(self) -> float:
        values: list[float] = []
        for entity in self.entities:
            if entity.attributes:
                values.extend(a.confidence for a in entity.attributes.values())
            else:
                values.append(entity.confidence)
        if not values:
            return 0.0
        return float(sum(values) / len(values))

    def to_dict(self) -> dict:
        payload = {
            "scene_id": self.scene_id,
            "version": self.version,
            "seed": self.seed,
            "title": self.title,
            "version_tag": self.version_tag,
            "entities": [e.to_dict() for e in self.entities],
            "relations": [r.to_dict() for r in self.relations],
            "style": self.style,
            "camera": self.camera.to_dict(),
            "lighting": self.lighting.to_dict(),
            "atmosphere": self.atmosphere.to_dict(),
            "dynamics": self.dynamics.to_dict(),
            "constraints": [c.to_dict() for c in self.constraints],
            "metadata": dict(self.metadata),
        }
        payload["metadata"]["content_hash"] = self.content_hash()
        return payload

    def content_hash(self) -> str:
        payload = {
            "scene_id": self.scene_id,
            "version": self.version,
            "seed": self.seed,
            "title": self.title,
            "entities": [e.to_dict() for e in self.entities],
            "relations": [r.to_dict() for r in self.relations],
            "style": self.style,
            "camera": self.camera.to_dict(),
            "lighting": self.lighting.to_dict(),
            "atmosphere": self.atmosphere.to_dict(),
            "dynamics": self.dynamics.to_dict(),
            "constraints": [c.to_dict() for c in self.constraints],
            "metadata": {k: v for k, v in self.metadata.items()
                         if k not in ("content_hash", "created_at", "updated_at")},
        }
        return canonical_hash(payload)

    @classmethod
    def from_dict(cls, payload: dict) -> "SceneGraph":
        if not isinstance(payload, dict):
            raise SceneValidationError("scene payload must be a mapping")
        metadata = dict(payload.get("metadata") or {})
        metadata.pop("content_hash", None)
        return cls(
            scene_id=payload.get("scene_id", ""),
            version=payload.get("version", 1),
            seed=payload.get("seed", 0),
            title=payload.get("title", "Untitled scene"),
            entities=[SceneEntity.from_dict(e) for e in (payload.get("entities") or [])],
            relations=[SceneRelation.from_dict(r) for r in (payload.get("relations") or [])],
            style=payload.get("style", "cinematic"),
            camera=CameraSpec.from_dict(payload.get("camera") or {}),
            lighting=LightingSpec.from_dict(payload.get("lighting") or {}),
            atmosphere=AtmosphereSpec.from_dict(payload.get("atmosphere") or {}),
            dynamics=DynamicsSpec.from_dict(payload.get("dynamics") or {}),
            constraints=[SceneConstraint.from_dict(c) for c in (payload.get("constraints") or [])],
            metadata=metadata,
            version_tag=payload.get("version_tag", SCENE_VERSION),
        )

    def copy(self) -> "SceneGraph":
        return SceneGraph.from_dict(self.to_dict())


def validate_scene(scene: SceneGraph) -> SceneGraph:
    """Re-validate a scene that may have been assembled incrementally.

    Locked attributes are allowed to be changed only by explicit commands; this function only checks
    structural invariants, never business policy.
    """
    return SceneGraph.from_dict(scene.to_dict())


def new_scene(seed: int, title: str = "Untitled scene") -> SceneGraph:
    return SceneGraph(scene_id=make_scene_id(seed), seed=int(seed), title=title)


def entity_for_new_scene(seed: int, kind: str, index: int, existing: set[str] | None = None) -> str:
    current = existing or set()
    return make_entity_id_unique(seed, kind, index, current)


__all__ = [
    "SCENE_VERSION",
    "MAX_ENTITIES",
    "ALLOWED_STYLES",
    "ALLOWED_MOTIONS",
    "ALLOWED_WEATHER",
    "ALLOWED_TIMES",
    "ALLOWED_RELATIONS",
    "PROVENANCE_USER_EXPLICIT",
    "PROVENANCE_USER_IMPLIED",
    "PROVENANCE_SYSTEM_DEFAULT",
    "PROVENANCE_SYSTEM_INFERRED",
    "PROVENANCE_SIMULATED",
    "PROVENANCE_NEURAL_PERCEPTION",
    "PROVENANCE_NEURAL_IMAGERY_FORBIDDEN",
    "PROVENANCE_CONFIDENCE",
    "USER_PROVENANCE",
    "SceneError",
    "SceneValidationError",
    "AttributeValue",
    "SceneEntity",
    "SceneRelation",
    "SceneConstraint",
    "CameraSpec",
    "LightingSpec",
    "AtmosphereSpec",
    "DynamicsSpec",
    "SceneGraph",
    "canonical_hash",
    "canonical_json",
    "sanitize_text",
    "validate_scene",
    "new_scene",
    "entity_for_new_scene",
    "make_entity_id",
    "make_scene_id",
]
