"""Deterministic intention -> scene composition.

This is not a language model. It is a small, inspectable grammar that turns a sentence into a scene the way
a storyboard assistant would: it recognises a bounded vocabulary, reports what it did not recognise, and
never invents a hidden target. Everything it cannot place is surfaced as a warning.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.animus.scene import library
from app.core.animus.scene.model import (
    PROVENANCE_USER_IMPLIED,
    AtmosphereSpec,
    AttributeValue,
    DynamicsSpec,
    LightingSpec,
    SceneEntity,
    SceneGraph,
    SceneRelation,
    new_scene,
    sanitize_text,
)

CLAIM_LEVEL = "L1_BEHAVIORAL_ASSISTED"
MAX_COMPOSED_ENTITIES = 12

STYLE_WORDS = {
    "cinematic": "cinematic", "minimal": "minimal", "minimalist": "minimal", "gothic": "gothic",
    "surreal": "surreal", "dreamlike": "surreal", "cyberpunk": "cyberpunk", "neon": "cyberpunk",
    "painterly": "painterly", "ancient": "ancient", "futuristic": "futuristic", "sci-fi": "futuristic",
}

MOOD_WORDS = {
    "calm": "calm", "peaceful": "peaceful", "serene": "peaceful", "ominous": "ominous",
    "gloomy": "dark", "hopeful": "hopeful", "melancholic": "melancholic",
    "sad": "melancholic", "epic": "epic", "grand": "epic", "mysterious": "mysterious",
    "joyful": "hopeful",
}

TIME_WORDS = {
    "dawn": "dawn", "sunrise": "dawn", "morning": "dawn", "day": "day", "daylight": "day",
    "noon": "day", "sunny": "day", "dusk": "dusk", "sunset": "dusk", "evening": "dusk",
    "twilight": "dusk", "night": "night", "midnight": "night", "starry": "night", "nocturnal": "night",
}

WEATHER_WORDS = {
    "rain": "rain", "rainy": "rain", "storm": "rain", "stormy": "rain", "snow": "snow",
    "snowy": "snow", "mist": "mist", "misty": "mist", "foggy": "mist",
}

NEGATIVE_RE = re.compile(r"\b(?:no|without|remove|delete|hide|not)\s+(?:the\s+|a\s+|an\s+)?", re.IGNORECASE)
COUNT_WORDS = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "several": 3, "many": 5, "a pair of": 2, "pair of": 2,
}
STOPWORDS = {
    "a", "an", "the", "and", "with", "of", "in", "on", "at", "to", "from", "over", "under", "above",
    "below", "very", "more", "less", "some", "that", "this", "it", "is", "are", "be", "should",
    "make", "set", "turn", "add", "put", "place", "create", "show", "keep", "preserve", "lock",
    "floating", "giant", "small", "large", "huge", "tiny", "old", "new", "white", "black",
    "camera", "view", "scene", "image", "picture", "style", "mood", "color", "colour", "light",
    "dark", "bright", "deep", "pale", "glowing", "golden", "majestic", "beautiful", "strange",
    "lonely", "vast", "tall", "broken", "ruined", "ancient", "modern", "soft", "sharp", "faint",
    "glittering", "shimmering", "misty", "foggy", "snowy", "rainy", "stormy", "warm", "cool",
}

_FILLER = set(library.COLOR_HEX) | set(library.COLOR_SYNONYMS) | set(STYLE_WORDS) | set(MOOD_WORDS) \
    | set(TIME_WORDS) | set(WEATHER_WORDS) | set(COUNT_WORDS) | STOPWORDS


@dataclass
class ComposeResult:
    scene: SceneGraph
    warnings: list[str] = field(default_factory=list)
    matched_terms: list[str] = field(default_factory=list)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    text = library.normalize_color(value).lstrip("#")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


def _rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, int(round(channel)))):02x}" for channel in rgb)


def shade(color: str, factor: float) -> str:
    return _rgb_to_hex(tuple(channel * factor for channel in _hex_to_rgb(color)))


def mix(first: str, second: str, t: float) -> str:
    a, b = _hex_to_rgb(first), _hex_to_rgb(second)
    return _rgb_to_hex(tuple(a[i] * (1 - t) + b[i] * t for i in range(3)))


def _first_word(text: str, mapping: dict[str, str]) -> str | None:
    for word in sorted(mapping, key=len, reverse=True):
        if re.search(rf"\b{re.escape(word)}\b", text):
            return mapping[word]
    return None


def _noun_matches(text: str) -> list[tuple[int, int, str, str]]:
    """Return ``(start, end, kind, surface)`` for known kinds, longest alias first, no overlaps."""
    aliases: list[tuple[str, str]] = [(kind, kind) for kind in library.OBJECT_KINDS]
    aliases += list(library.KIND_ALIASES.items())
    aliases.sort(key=lambda item: len(item[0]), reverse=True)
    taken: list[tuple[int, int]] = []
    matches: list[tuple[int, int, str, str]] = []
    for alias, kind in aliases:
        for found in re.finditer(rf"\b{re.escape(alias)}\b", text):
            span = (found.start(), found.end())
            if any(not (span[1] <= a or span[0] >= b) for a, b in taken):
                continue
            taken.append(span)
            matches.append((found.start(), found.end(), kind, found.group(0)))
    return sorted(matches)


def _negative_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in NEGATIVE_RE.finditer(text)]


def _in_negative(start: int, spans: list[tuple[int, int]]) -> bool:
    return any(start >= begin and start <= end + 24 for begin, end in spans)


def _count_for_noun(text: str, start: int) -> int:
    window = text[max(0, start - 18):start]
    for word in sorted(COUNT_WORDS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(word)}\s+$", window):
            return COUNT_WORDS[word]
    match = re.search(r"\b(\d{1,2})\s+$", window)
    if match:
        return max(1, min(12, int(match.group(1))))
    return 1


def _color_mentions(text: str) -> list[tuple[int, int, str]]:
    names = set(library.COLOR_HEX) | set(library.COLOR_SYNONYMS)
    out: list[tuple[int, int, str]] = []
    for name in sorted(names, key=len, reverse=True):
        for found in re.finditer(rf"\b{re.escape(name)}\b", text):
            try:
                out.append((found.start(), found.end(), library.normalize_color(name)))
            except Exception:  # noqa: BLE001 - unknown names are simply not colours
                continue
    return sorted(out)


def _nearest_color(mentions: list[tuple[int, int, str]], position: int) -> str | None:
    best: tuple[int, str] | None = None
    for start, end, color in mentions:
        if end <= position + 2:
            distance = position - end
            if distance <= 34 and (best is None or distance < best[0]):
                best = (distance, color)
    return best[1] if best else None


def _custom_nouns(text: str, known_spans: list[tuple[int, int]]) -> list[tuple[int, str]]:
    """Article-led words that are not in the library become honest abstract forms.

    Adjectives are skipped, so "a giant turtle" still resolves to the unknown noun "turtle".
    """
    out: list[tuple[int, str]] = []
    articles = r"\b(?:a|an|one|two|three|four|five|the)\b"
    for article in re.finditer(articles, text):
        tail_start = article.end()
        for word_match in re.finditer(r"[a-z][a-z\-]{2,24}", text[tail_start:tail_start + 44]):
            word = word_match.group(0)
            start = tail_start + word_match.start()
            if start - tail_start > 30:
                break
            if word in _FILLER:
                continue
            if library.normalize_kind(word) != "custom":
                break
            if any(start < end and start + len(word) > begin for begin, end in known_spans):
                break
            if word.endswith("ly"):
                break
            out.append((start, word))
            break
    return out


def _apply_time(scene: SceneGraph, time_of_day: str) -> None:
    preset = library.time_preset(time_of_day)
    scene.atmosphere = AtmosphereSpec(
        fog_color=preset["fog_color"], fog_density=scene.atmosphere.fog_density,
        sky_top=preset["sky_top"], sky_horizon=preset["sky_horizon"], sky_bottom=preset["sky_bottom"],
        stars=preset["stars"], aurora=scene.atmosphere.aurora,
        weather=scene.atmosphere.weather, time_of_day=time_of_day,
    )
    scene.lighting = LightingSpec(
        key_color=preset["key_color"], key_intensity=preset["key_intensity"],
        key_direction=scene.lighting.key_direction,
        ambient_color=preset["ambient_color"], ambient_intensity=scene.lighting.ambient_intensity,
        rim_color=scene.lighting.rim_color, rim_intensity=scene.lighting.rim_intensity,
    )


def _apply_style(scene: SceneGraph, style: str) -> None:
    preset = library.style_preset(style)
    scene.style = style
    lighting = preset.get("lighting", {})
    atmosphere = preset.get("atmosphere", {})
    camera = preset.get("camera", {})
    scene.lighting.key_intensity = float(lighting.get("key_intensity", scene.lighting.key_intensity))
    scene.lighting.ambient_intensity = float(lighting.get("ambient_intensity", scene.lighting.ambient_intensity))
    scene.lighting.rim_intensity = float(lighting.get("rim_intensity", scene.lighting.rim_intensity))
    scene.atmosphere.fog_density = float(atmosphere.get("fog_density", scene.atmosphere.fog_density))
    if "stars" in atmosphere:
        scene.atmosphere.stars = int(atmosphere["stars"])
    if "aurora" in atmosphere:
        scene.atmosphere.aurora = bool(atmosphere["aurora"])
    scene.camera.fov = float(camera.get("fov", scene.camera.fov))
    scene.camera.motion = str(camera.get("motion", scene.camera.motion))


def _apply_mood(scene: SceneGraph, mood: str) -> None:
    preset = library.mood_preset(mood)
    if not preset:
        return
    if "style" in preset:
        _apply_style(scene, preset["style"])
    if "key_intensity" in preset:
        scene.lighting.key_intensity = float(preset["key_intensity"])
    if "fog_density" in preset:
        scene.atmosphere.fog_density = float(preset["fog_density"])


def _apply_camera_hint(scene: SceneGraph, text: str) -> list[str]:
    warnings: list[str] = []
    if re.search(r"\b(aerial|from above|bird'?s[- ]eye|overhead)\b", text):
        scene.camera.position = [0.0, 9.0, 10.0]
        scene.camera.target = [0.0, 0.0, -1.0]
        scene.camera.fov = 56.0
        scene.camera.motion = "orbit"
    elif re.search(r"\b(close[- ]up|close|intimate)\b", text):
        scene.camera.position = [0.0, 1.6, 4.2]
        scene.camera.fov = 38.0
    elif re.search(r"\b(wide|panoramic|vast)\b", text):
        scene.camera.position = [0.0, 3.2, 15.0]
        scene.camera.fov = 60.0
    if re.search(r"\b(orbiting|orbit)\b", text):
        scene.camera.motion = "orbit"
    if re.search(r"\b(static|still camera|locked[- ]off)\b", text):
        scene.camera.motion = "static"
    return warnings


def _make_entity(kind: str, label: str, index: int, seed: int, color: str | None,
                 existing_ids: set[str], *, floating: bool = False) -> SceneEntity:
    from app.core.animus.scene.model import make_entity_id_unique

    entity_id = make_entity_id_unique(seed, kind, index, existing_ids)
    attributes: dict[str, AttributeValue] = {}
    defaults = dict(library.KIND_DEFAULT_ATTRIBUTES.get(kind, {}))
    if color:
        defaults["color"] = color
    for path, value in defaults.items():
        spec = library.attribute_spec(path)
        if spec is None:
            continue
        if spec["type"] == "color":
            value = library.normalize_color(str(value))
        elif spec["type"] == "number":
            value = float(max(spec["min"], min(spec["max"], float(value))))
        elif spec["type"] == "integer":
            value = int(max(spec["min"], min(spec["max"], float(value))))
        attributes[path] = AttributeValue(value=value, confidence=0.6,
                                          provenance=PROVENANCE_USER_IMPLIED)
    position = library.default_position(kind, index)
    if floating:
        position = [position[0], round(position[1] + 1.4, 3), position[2]]
    return SceneEntity(id=entity_id, kind=kind, label=label, role=library.default_role(kind),
                       position=position, attributes=attributes,
                       confidence=0.6, provenance=PROVENANCE_USER_IMPLIED)


def compose_from_intention(text: str, *, seed: int = 20260909, title: str | None = None) -> ComposeResult:
    raw = sanitize_text(text)
    if not raw:
        raise ValueError("intention must not be empty")
    lowered = raw.lower()
    warnings: list[str] = []
    matched: list[str] = []

    style = _first_word(lowered, STYLE_WORDS)
    mood = _first_word(lowered, MOOD_WORDS)
    time_of_day = _first_word(lowered, TIME_WORDS) or "night"
    weather = _first_word(lowered, WEATHER_WORDS) or "clear"

    scene_title = sanitize_text(title or raw, max_len=80)
    scene = new_scene(seed, scene_title)
    _apply_time(scene, time_of_day)
    if style:
        _apply_style(scene, style)
        matched.append(f"style:{style}")
    if mood:
        _apply_mood(scene, mood)
        matched.append(f"mood:{mood}")
    scene.atmosphere.weather = weather
    _apply_camera_hint(scene, lowered)

    negative_spans = _negative_spans(lowered)
    color_mentions = _color_mentions(lowered)
    global_color = color_mentions[0][2] if color_mentions else None

    # Explicit sky colour, e.g. "deep violet sky" or "sky the colour of embers".
    sky_color = None
    for start, end, color in color_mentions:
        around = lowered[max(0, start - 6):min(len(lowered), end + 20)]
        if "sky" in around or "horizon" in around:
            sky_color = color
            break
    if sky_color:
        scene.atmosphere.sky_top = shade(sky_color, 0.35)
        scene.atmosphere.sky_horizon = shade(sky_color, 0.9)
        scene.atmosphere.sky_bottom = shade(sky_color, 0.18)
        scene.atmosphere.fog_color = shade(sky_color, 0.22)
        scene.lighting.ambient_color = mix(scene.lighting.ambient_color, sky_color, 0.35)
        matched.append(f"sky:{sky_color}")

    matches = _noun_matches(lowered)
    custom_matches = _custom_nouns(lowered, [(start, end) for start, end, _, _ in matches])
    entity_specs: list[tuple[int, str, str]] = []
    for start, end, kind, surface in matches:
        if _in_negative(start, negative_spans):
            continue
        count = _count_for_noun(lowered, start)
        for _ in range(max(1, min(6, count))):
            entity_specs.append((start, kind, library.kind_label(kind)))
        matched.append(f"kind:{kind}")
    for start, word in custom_matches:
        if _in_negative(start, negative_spans):
            continue
        if any(start == m[0] for m in matches):
            continue
        entity_specs.append((start, "custom", word.title()))
        warnings.append(f"'{word}' has no detailed model yet; it is shown as an abstract form")
        matched.append(f"custom:{word}")
    # Preserve document order, then cap.
    entity_specs.sort(key=lambda item: item[0])
    seen_kind_counts: dict[str, int] = {}
    existing_ids: set[str] = set()
    floating = bool(re.search(r"\b(floating|hovering|levitating|in the sky|suspended)\b", lowered))
    if floating:
        warnings.append("'floating' is shown as an elevated static composition")
        scene.dynamics = DynamicsSpec(wind=scene.dynamics.wind, water=scene.dynamics.water,
                                      fire=scene.dynamics.fire, floating=0.7, pulse=scene.dynamics.pulse)

    for index, (start, kind, label) in enumerate(entity_specs[:MAX_COMPOSED_ENTITIES]):
        color = _nearest_color(color_mentions, start) or (global_color if kind not in ("water", "fog") else None)
        if kind == "water":
            color = color or "#1b4a78"
            if re.search(r"\bdark\b", lowered):
                color = shade(color, 0.55)
        if kind in ("moon", "sun", "star") and not color:
            color = library.KIND_DEFAULT_ATTRIBUTES[kind]["color"]
        same_index = seen_kind_counts.get(kind, 0)
        seen_kind_counts[kind] = same_index + 1
        entity = _make_entity(kind, label, same_index + index, seed, color, existing_ids,
                              floating=floating and kind not in ("water", "fog", "mountain", "star", "cloud"))
        existing_ids.add(entity.id)
        scene.entities.append(entity)

    if not scene.entities:
        fallback = _make_entity("custom", "Abstract form", 0, seed, global_color, existing_ids)
        scene.entities.append(fallback)
        warnings.append("No recognisable element was found; the scene is an abstract starting point")

    _apply_weather(scene, weather)
    _apply_negatives(scene, lowered, negative_spans)
    _apply_relations(scene, lowered, warnings)

    scene.atmosphere.weather = weather
    scene.metadata = {
        "claim_level": CLAIM_LEVEL,
        "generator": "compose.v1",
        "intention": raw,
        "warnings": warnings,
        "matched_terms": sorted(set(matched)),
        "floating": floating,
    }
    return ComposeResult(scene=scene, warnings=warnings, matched_terms=sorted(set(matched)))


def _apply_weather(scene: SceneGraph, weather: str) -> None:
    if weather == "rain":
        scene.atmosphere.stars = min(scene.atmosphere.stars, 120)
        scene.lighting.key_intensity *= 0.75
    elif weather == "snow":
        scene.atmosphere.stars = min(scene.atmosphere.stars, 200)
        scene.lighting.ambient_intensity = max(scene.lighting.ambient_intensity, 0.45)
    elif weather == "mist":
        scene.atmosphere.fog_density = min(0.2, scene.atmosphere.fog_density + 0.025)


def _apply_negatives(scene: SceneGraph, text: str, negative_spans: list[tuple[int, int]]) -> None:
    for begin, end in negative_spans:
        tail = text[end:end + 32]
        kind = library.normalize_kind(tail.split()[0]) if tail.split() else "custom"
        if kind != "custom":
            scene.entities = [e for e in scene.entities if e.kind != kind]
            scene.relations = [r for r in scene.relations
                               if r.subject_id in {e.id for e in scene.entities}
                               and r.object_id in {e.id for e in scene.entities}]
        if "stars" in tail:
            scene.atmosphere.stars = 0
        if "fog" in tail or "mist" in tail:
            scene.atmosphere.fog_density = 0.004
        if "light" in tail:
            scene.lighting.key_intensity = min(scene.lighting.key_intensity, 0.2)


def _apply_relations(scene: SceneGraph, text: str, warnings: list[str]) -> None:
    if len(scene.entities) < 2:
        return
    subject = next((e for e in scene.entities if e.role == "subject"), scene.entities[0])
    other = next((e for e in scene.entities if e.id != subject.id and e.role == "background"), None)
    if other is None:
        other = next((e for e in scene.entities if e.id != subject.id), None)
    if other is None:
        return
    for word in ("above", "below", "behind", "in_front_of", "next_to", "left_of", "right_of", "around"):
        if re.search(rf"\b{word.replace('_', ' ')}\b", text):
            try:
                scene.relations.append(SceneRelation(subject_id=subject.id, relation=word,
                                                     object_id=other.id, confidence=0.6,
                                                     provenance="USER_IMPLIED"))
            except Exception:  # noqa: BLE001 - relation validation is repeated by the scene
                warnings.append(f"Could not place the relation '{word}'")
            return


__all__ = ["ComposeResult", "compose_from_intention", "shade", "mix"]
