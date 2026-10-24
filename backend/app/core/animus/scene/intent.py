"""Deterministic refinement grammar: a sentence -> validated scene commands.

The parser is intentionally small and inspectable. It only acts on vocabulary it can resolve, and it returns
``needs_clarification`` instead of guessing when a sentence has no actionable target. Every resolution is
reported so the UI can show exactly what was understood before the candidate changes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.animus.scene import library
from app.core.animus.scene.commands import (
    AddEntityCommand,
    LockCommand,
    RemoveEntityCommand,
    SceneCommand,
    SetEntityAttributeCommand,
    SetEntityTransformCommand,
    SetSceneAttributeCommand,
)
from app.core.animus.scene.compose import MOOD_WORDS, STYLE_WORDS, TIME_WORDS, shade
from app.core.animus.scene.model import (
    SceneEntity,
    SceneGraph,
    clamp,
    sanitize_text,
)


@dataclass
class IntentParseResult:
    intent: str
    commands: list[SceneCommand] = field(default_factory=list)
    resolutions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    needs_clarification: bool = False
    clarification: str | None = None


_CLAUSE_SPLIT = re.compile(r"\s*(?:;|,|\band then\b|\bthen\b|\band\b)\s*", re.IGNORECASE)
_KEEP_RE = re.compile(r"\b(?:keep|preserve|lock|hold|don'?t change|do not change)\b", re.IGNORECASE)
_UNLOCK_RE = re.compile(r"\b(?:unlock|release|free)\b", re.IGNORECASE)
_ADD_RE = re.compile(r"\b(?:add|include|place|put|insert)\b", re.IGNORECASE)
_REMOVE_RE = re.compile(r"\b(?:remove|delete|drop|hide|erase|get rid of)\b", re.IGNORECASE)
_BRIGHTEN_RE = re.compile(r"\b(?:brighter|more light|more lit|lighten|illuminate)\b", re.IGNORECASE)
_DARKEN_RE = re.compile(r"\b(?:darker|less light|dim|darken)\b", re.IGNORECASE)
_BIGGER_RE = re.compile(r"\b(?:bigger|larger|grow|scale up)\b", re.IGNORECASE)
_SMALLER_RE = re.compile(r"\b(?:smaller|tinier|shrink|scale down)\b", re.IGNORECASE)
_MORE_RE = re.compile(r"\b(?:more|stronger|increase)\b", re.IGNORECASE)
_LESS_RE = re.compile(r"\b(?:less|weaker|reduce|lower)\b", re.IGNORECASE)
_COLOR_WORDS = sorted(set(library.COLOR_HEX) | set(library.COLOR_SYNONYMS), key=len, reverse=True)


def _find_color(text: str) -> tuple[str, str] | None:
    for name in _COLOR_WORDS:
        if re.search(rf"\b{re.escape(name)}\b", text):
            return name, library.normalize_color(name)
    return None


def _entity_matches(scene: SceneGraph, text: str) -> list[SceneEntity]:
    found: list[SceneEntity] = []
    for entity in scene.entities:
        names = {entity.kind, entity.label.lower()}
        names.update(alias for alias, kind in library.KIND_ALIASES.items() if kind == entity.kind)
        if any(re.search(rf"\b{re.escape(name)}\b", text) for name in names if name):
            found.append(entity)
    return found


def _subject(scene: SceneGraph) -> SceneEntity | None:
    if not scene.entities:
        return None
    return next((e for e in scene.entities if e.role == "subject"), scene.entities[0])


def _style_commands(style: str, scene: SceneGraph) -> list[SceneCommand]:
    preset = library.style_preset(style)
    commands: list[SceneCommand] = [SetSceneAttributeCommand(path="style", value=style)]
    lighting = preset.get("lighting", {})
    atmosphere = preset.get("atmosphere", {})
    camera = preset.get("camera", {})
    for path, value in (("lighting.key.intensity", lighting.get("key_intensity")),
                        ("lighting.ambient.intensity", lighting.get("ambient_intensity")),
                        ("lighting.rim.intensity", lighting.get("rim_intensity")),
                        ("atmosphere.fog.density", atmosphere.get("fog_density")),
                        ("atmosphere.sky.stars", atmosphere.get("stars")),
                        ("camera.fov", camera.get("fov")),
                        ("camera.motion", camera.get("motion"))):
        if value is not None:
            commands.append(SetSceneAttributeCommand(path=path, value=value))
    if style == "surreal":
        commands.append(SetSceneAttributeCommand(path="atmosphere.sky.aurora", value=True))
    return commands


def _time_commands(time_of_day: str) -> list[SceneCommand]:
    preset = library.time_preset(time_of_day)
    return [
        SetSceneAttributeCommand(path="atmosphere.time_of_day", value=time_of_day),
        SetSceneAttributeCommand(path="atmosphere.sky.top", value=preset["sky_top"]),
        SetSceneAttributeCommand(path="atmosphere.sky.horizon", value=preset["sky_horizon"]),
        SetSceneAttributeCommand(path="atmosphere.sky.bottom", value=preset["sky_bottom"]),
        SetSceneAttributeCommand(path="atmosphere.fog.color", value=preset["fog_color"]),
        SetSceneAttributeCommand(path="atmosphere.sky.stars", value=preset["stars"]),
        SetSceneAttributeCommand(path="lighting.key.color", value=preset["key_color"]),
        SetSceneAttributeCommand(path="lighting.key.intensity", value=preset["key_intensity"]),
        SetSceneAttributeCommand(path="lighting.ambient.color", value=preset["ambient_color"]),
    ]


def _clamp_int(value: float, low: int, high: int) -> int:
    return int(clamp(value, low, high))


def parse_intent(text: str, scene: SceneGraph) -> IntentParseResult:
    raw = sanitize_text(text, max_len=400)
    result = IntentParseResult(intent=raw)
    if not raw:
        result.needs_clarification = True
        result.clarification = "Describe one change you want to see."
        return result
    if scene.metadata.get("claim_level") == "L0_SIMULATED":
        result.warnings.append("This scene came from a simulated benchmark; corrections are user edits")

    for clause in [c.strip() for c in _CLAUSE_SPLIT.split(raw) if c.strip()]:
        lowered = clause.lower()
        before = len(result.commands)

        # Lock / unlock first so a clause like "keep the ocean" does not also become a style edit.
        if _KEEP_RE.search(lowered):
            matches = _entity_matches(scene, lowered)
            if matches:
                path = "color" if "color" in lowered or "colour" in lowered else ""
                for entity in matches[:1]:
                    result.commands.append(LockCommand(entity_id=entity.id, path=path, locked=True))
                    result.resolutions.append(
                        f"Lock {'color of ' if path else ''}{entity.label}")
                continue
            if "camera" in lowered:
                result.warnings.append("Camera locks are not available yet")
                continue
            result.warnings.append(f"Could not find what to keep in: '{clause}'")
            continue

        if _UNLOCK_RE.search(lowered):
            matches = _entity_matches(scene, lowered)
            if matches:
                path = "color" if "color" in lowered or "colour" in lowered else ""
                for entity in matches[:1]:
                    result.commands.append(LockCommand(entity_id=entity.id, path=path, locked=False))
                    result.resolutions.append(f"Unlock {entity.label}")
                continue

        # Add / remove entities.
        if _ADD_RE.search(lowered):
            kind = next((library.normalize_kind(word) for word in re.findall(r"[a-z\-]+", lowered)
                         if library.normalize_kind(word) != "custom"), None)
            if kind is None:
                unknown = next((word for word in re.findall(r"[a-z\-]{3,24}", lowered)
                                if library.normalize_kind(word) == "custom"
                                and word not in {"add", "include", "place", "put", "insert", "another",
                                                 "second", "more", "with", "and", "the"}), None)
                if unknown:
                    result.commands.append(AddEntityCommand(kind="custom", label=unknown.title()))
                    result.resolutions.append(f"Add abstract form '{unknown}'")
                    result.warnings.append(f"'{unknown}' has no detailed model; shown as an abstract form")
                    continue
            if kind:
                count = 1
                if re.search(r"\b(two|three|four|five|six)\b", lowered):
                    count = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6}[
                        re.search(r"\b(two|three|four|five|six)\b", lowered).group(1)]
                elif re.search(r"\b(second|another|one more)\b", lowered):
                    count = 1
                for offset in range(count):
                    result.commands.append(AddEntityCommand(kind=kind))
                result.resolutions.append(f"Add {count} × {library.kind_label(kind)}")
                continue

        if _REMOVE_RE.search(lowered):
            matches = _entity_matches(scene, lowered)
            if matches:
                for entity in matches:
                    if entity.locked:
                        result.warnings.append(f"{entity.label} is locked and was not removed")
                        continue
                    result.commands.append(RemoveEntityCommand(entity_id=entity.id))
                    result.resolutions.append(f"Remove {entity.label}")
                continue
            if "fog" in lowered:
                result.commands.append(SetSceneAttributeCommand(
                    path="atmosphere.fog.density", value=0.004))
                result.resolutions.append("Remove fog")
                continue

        # Style and time.
        style = next((STYLE_WORDS[w] for w in sorted(STYLE_WORDS, key=len, reverse=True)
                      if re.search(rf"\b{re.escape(w)}\b", lowered)), None)
        time_of_day = next((TIME_WORDS[w] for w in sorted(TIME_WORDS, key=len, reverse=True)
                            if re.search(rf"\b{re.escape(w)}\b", lowered)), None)
        if style:
            result.commands.extend(_style_commands(style, scene))
            result.resolutions.append(f"Style → {style}")
            # A clause may still carry an explicit target colour, e.g. "gothic with red windows".
            color = _find_color(lowered)
            matches = _entity_matches(scene, lowered)
            if color and matches:
                entity = matches[0]
                result.commands.append(SetEntityAttributeCommand(
                    entity_id=entity.id, path="color", value=color[1]))
                result.resolutions.append(f"{entity.label} color → {color[0]}")
            continue
        if time_of_day:
            result.commands.extend(_time_commands(time_of_day))
            result.resolutions.append(f"Time of day → {time_of_day}")
            continue

        # Scene-level brightness and fog.
        if _BRIGHTEN_RE.search(lowered):
            result.commands.extend([
                SetSceneAttributeCommand(path="lighting.key.intensity",
                                         value=clamp(scene.lighting.key_intensity * 1.35, 0, 8)),
                SetSceneAttributeCommand(path="lighting.ambient.intensity",
                                         value=clamp(scene.lighting.ambient_intensity * 1.3, 0, 4)),
            ])
            result.resolutions.append("Brighten the scene")
            continue
        if _DARKEN_RE.search(lowered):
            result.commands.extend([
                SetSceneAttributeCommand(path="lighting.key.intensity",
                                         value=clamp(scene.lighting.key_intensity * 0.7, 0, 8)),
                SetSceneAttributeCommand(path="lighting.ambient.intensity",
                                         value=clamp(scene.lighting.ambient_intensity * 0.75, 0, 4)),
            ])
            result.resolutions.append("Darken the scene")
            continue
        if "fog" in lowered and (_MORE_RE.search(lowered) or _LESS_RE.search(lowered)):
            delta = 0.015 if _MORE_RE.search(lowered) else -0.015
            result.commands.append(SetSceneAttributeCommand(
                path="atmosphere.fog.density",
                value=clamp(scene.atmosphere.fog_density + delta, 0, 0.2)))
            result.resolutions.append("More fog" if delta > 0 else "Less fog")
            continue

        color = _find_color(lowered)
        matches = _entity_matches(scene, lowered)

        # "make the sky deep violet" and close variants.
        if "sky" in lowered and color:
            result.commands.extend([
                SetSceneAttributeCommand(path="atmosphere.sky.top", value=shade(color[1], 0.35)),
                SetSceneAttributeCommand(path="atmosphere.sky.horizon", value=shade(color[1], 0.9)),
                SetSceneAttributeCommand(path="atmosphere.sky.bottom", value=shade(color[1], 0.18)),
                SetSceneAttributeCommand(path="atmosphere.fog.color", value=shade(color[1], 0.22)),
            ])
            result.resolutions.append(f"Sky → {color[0]}")
            continue

        if color and matches:
            entity = matches[0]
            if entity.locked:
                result.warnings.append(f"{entity.label} is locked; unlock it to change its color")
                continue
            result.commands.append(SetEntityAttributeCommand(
                entity_id=entity.id, path="color", value=color[1]))
            result.resolutions.append(f"{entity.label} color → {color[0]}")
            if len(matches) > 1:
                result.warnings.append(f"Matched {len(matches)} elements; changed {entity.label}")
            continue

        # Size and position edits.
        if matches and (_BIGGER_RE.search(lowered) or _SMALLER_RE.search(lowered)):
            entity = matches[0]
            current = entity.attributes.get("size")
            size = float(current.value) if current else 1.0
            factor = 1.25 if _BIGGER_RE.search(lowered) else 0.8
            result.commands.append(SetEntityAttributeCommand(
                entity_id=entity.id, path="size", value=clamp(size * factor, 0.15, 4.0)))
            result.resolutions.append(f"{entity.label} {'larger' if factor > 1 else 'smaller'}")
            continue

        if matches and re.search(r"\b(higher|lower|left|right|forward|back|up|down)\b", lowered):
            entity = matches[0]
            position = list(entity.position)
            if re.search(r"\bhigher\b|\bup\b", lowered):
                position[1] += 1.0
            if re.search(r"\blower\b|\bdown\b", lowered):
                position[1] -= 1.0
            if re.search(r"\bleft\b", lowered):
                position[0] -= 1.0
            if re.search(r"\bright\b", lowered):
                position[0] += 1.0
            if re.search(r"\bforward\b", lowered):
                position[2] += 1.0
            if re.search(r"\bback\b", lowered):
                position[2] -= 1.0
            result.commands.append(SetEntityTransformCommand(entity_id=entity.id, position=position))
            result.resolutions.append(f"Move {entity.label}")
            continue

        # Mood words as style edits.
        mood = next((MOOD_WORDS[w] for w in sorted(MOOD_WORDS, key=len, reverse=True)
                     if re.search(rf"\b{re.escape(w)}\b", lowered)), None)
        if mood:
            preset = library.mood_preset(mood)
            if preset.get("style"):
                result.commands.extend(_style_commands(preset["style"], scene))
            if "key_intensity" in preset:
                result.commands.append(SetSceneAttributeCommand(
                    path="lighting.key.intensity", value=preset["key_intensity"]))
            if "fog_density" in preset:
                result.commands.append(SetSceneAttributeCommand(
                    path="atmosphere.fog.density", value=preset["fog_density"]))
            result.resolutions.append(f"Mood → {mood}")
            continue

        if len(result.commands) == before:
            result.warnings.append(f"Did not understand: '{clause}'")

    if not result.commands:
        result.needs_clarification = True
        result.clarification = ("I can change the sky, lighting, style, time of day, an element's colour, "
                                "size or position, add or remove elements, or lock something.")
    if len(result.commands) > 24:
        result.commands = result.commands[:24]
        result.warnings.append("Only the first 24 changes were applied")
    return result


__all__ = ["IntentParseResult", "parse_intent"]
