"""Renderable kind and attribute vocabulary for ANIMUS Studio.

This module is the backend half of the scene contract. The frontend has a matching renderer table; both
are versioned by ``SCENE_VERSION``. Unknown kinds and unknown attributes are allowed (as custom content)
but are marked non-renderable and surfaced as a warning instead of silently pretending to render them.
"""
from __future__ import annotations

import math
import re

from app.core.animus import vocab
from app.core.animus.scene.model import SceneValidationError

LIBRARY_VERSION = "ANIMUS-LIB-v1"

OBJECT_KINDS: tuple[str, ...] = tuple(vocab.OBJECT_VOCAB) + (
    "sun", "planet", "creature", "dragon", "door", "portal", "crystal", "rock", "grass", "island",
)

KIND_LABELS: dict[str, str] = {
    "castle": "Castle", "moon": "Moon", "fog": "Fog", "tree": "Tree", "mountain": "Mountain",
    "water": "Water", "person": "Person", "road": "Road", "star": "Star", "cloud": "Cloud",
    "fire": "Fire", "bird": "Bird", "building": "Building", "flower": "Flower", "boat": "Boat",
    "bridge": "Bridge", "sun": "Sun", "planet": "Planet", "creature": "Creature", "dragon": "Dragon",
    "door": "Door", "portal": "Portal", "crystal": "Crystal", "rock": "Rock", "grass": "Grass",
    "island": "Island", "custom": "Abstract form",
}

BACKGROUND_KINDS = {"water", "fog", "mountain", "forest", "cloud", "star", "grass", "island", "road", "bridge", "sky"}
SUBJECT_KINDS = {"castle", "dragon", "creature", "person", "boat", "building", "crystal", "portal", "door", "fire"}

COLOR_HEX: dict[str, str] = {
    "white": "#f4f6ff", "ivory": "#f1ead7", "black": "#080a12", "charcoal": "#1b1e2a",
    "gray": "#7b8496", "grey": "#7b8496", "silver": "#c9d3e3", "red": "#e14b4b",
    "crimson": "#b3123a", "scarlet": "#e2361f", "orange": "#f08a2c", "amber": "#f5b642",
    "gold": "#e8c35a", "yellow": "#f4e06a", "green": "#3fae6a", "emerald": "#1fae7a",
    "teal": "#1f9e9e", "cyan": "#57e0e6", "blue": "#4a7cf0", "azure": "#4fb7ff",
    "navy": "#24346e", "indigo": "#4b3a9e", "violet": "#8a5cf0", "purple": "#6c3bb5",
    "magenta": "#d23fa0", "pink": "#e98ab5", "rose": "#d76b83", "brown": "#7a5236",
    "copper": "#b26a3c", "sand": "#d8c08a", "bone": "#d9d2bd", "blood": "#8f1220",
    "midnight": "#0b1030", "moonlight": "#cfe0ff", "sunset": "#f08a5a", "warm": "#f2b06a",
    "cool": "#7fa8e8",
}

COLOR_SYNONYMS: dict[str, str] = {
    "deep violet": "violet", "dark violet": "violet", "violet": "violet", "purple": "purple",
    "deep blue": "navy", "dark blue": "navy", "midnight blue": "midnight", "sky blue": "azure",
    "blood red": "blood", "dark red": "crimson", "warm white": "ivory", "off white": "ivory",
    "emerald green": "emerald", "forest green": "green", "golden": "gold", "silver": "silver",
    "gray": "gray", "grey": "gray",
}

STYLE_PRESETS: dict[str, dict] = {
    "cinematic": {"lighting": {"key_intensity": 1.1, "ambient_intensity": 0.32, "rim_intensity": 0.7},
                  "atmosphere": {"fog_density": 0.03}, "camera": {"fov": 46, "motion": "orbit"}},
    "minimal": {"lighting": {"key_intensity": 0.9, "ambient_intensity": 0.45, "rim_intensity": 0.25},
                "atmosphere": {"fog_density": 0.012, "stars": 120}, "camera": {"fov": 42, "motion": "static"}},
    "gothic": {"lighting": {"key_intensity": 0.75, "ambient_intensity": 0.18, "rim_intensity": 0.45},
               "atmosphere": {"fog_density": 0.06, "stars": 220, "aurora": False}, "camera": {"fov": 50}},
    "surreal": {"lighting": {"key_intensity": 1.3, "ambient_intensity": 0.5, "rim_intensity": 0.9},
                "atmosphere": {"fog_density": 0.045, "stars": 900, "aurora": True}, "camera": {"fov": 58}},
    "cyberpunk": {"lighting": {"key_intensity": 1.4, "ambient_intensity": 0.4, "rim_intensity": 1.1},
                  "atmosphere": {"fog_density": 0.05, "stars": 80}, "camera": {"fov": 52}},
    "painterly": {"lighting": {"key_intensity": 1.0, "ambient_intensity": 0.4, "rim_intensity": 0.5},
                  "atmosphere": {"fog_density": 0.035, "stars": 300}, "camera": {"fov": 44}},
    "ancient": {"lighting": {"key_intensity": 0.85, "ambient_intensity": 0.28, "rim_intensity": 0.4},
                "atmosphere": {"fog_density": 0.05, "stars": 260}, "camera": {"fov": 48}},
    "futuristic": {"lighting": {"key_intensity": 1.2, "ambient_intensity": 0.42, "rim_intensity": 1.0},
                   "atmosphere": {"fog_density": 0.025, "stars": 500}, "camera": {"fov": 50}},
}

TIME_PRESETS: dict[str, dict] = {
    "dawn": {"sky_top": "#1a2340", "sky_horizon": "#f2a07a", "sky_bottom": "#2a1e3a",
             "key_color": "#ffd2b0", "ambient_color": "#7d7cff", "fog_color": "#2a2438",
             "stars": 80, "key_intensity": 0.9},
    "day": {"sky_top": "#3d7bd6", "sky_horizon": "#bfe0ff", "sky_bottom": "#6aa4e8",
            "key_color": "#fff6e6", "ambient_color": "#a9c8ff", "fog_color": "#9db6d8",
            "stars": 0, "key_intensity": 1.5},
    "dusk": {"sky_top": "#161a3c", "sky_horizon": "#f08a5a", "sky_bottom": "#1a1030",
             "key_color": "#ffb066", "ambient_color": "#6b6cf0", "fog_color": "#241a38",
             "stars": 260, "key_intensity": 1.0},
    "night": {"sky_top": "#050916", "sky_horizon": "#16224a", "sky_bottom": "#03040a",
              "key_color": "#cfe0ff", "ambient_color": "#4a5bd0", "fog_color": "#0b1024",
              "stars": 900, "key_intensity": 0.55},
}

MOOD_PRESETS: dict[str, dict] = {
    "calm": {"style": "minimal", "key_intensity": 0.7, "fog_density": 0.02},
    "ominous": {"style": "gothic", "key_intensity": 0.55, "fog_density": 0.075},
    "hopeful": {"style": "cinematic", "key_intensity": 1.25, "fog_density": 0.015},
    "melancholic": {"style": "painterly", "key_intensity": 0.65, "fog_density": 0.05},
    "epic": {"style": "cinematic", "key_intensity": 1.4, "fog_density": 0.03},
    "peaceful": {"style": "minimal", "key_intensity": 0.8, "fog_density": 0.018},
    "mysterious": {"style": "surreal", "key_intensity": 0.7, "fog_density": 0.055},
    "dark": {"style": "gothic", "key_intensity": 0.45, "fog_density": 0.07},
    "bright": {"style": "cinematic", "key_intensity": 1.5, "fog_density": 0.012},
}

ATTRIBUTE_SPECS: dict[str, dict] = {
    "color": {"type": "color", "label": "Color", "renderable": True},
    "secondary_color": {"type": "color", "label": "Secondary color", "renderable": True},
    "size": {"type": "number", "label": "Size", "min": 0.15, "max": 4.0, "renderable": True},
    "count": {"type": "integer", "label": "Count", "min": 1, "max": 40, "renderable": True},
    "material": {"type": "enum", "label": "Material", "options": ["stone", "wood", "metal", "glass",
                                                                  "water", "fabric", "energy", "foliage", "sand"],
                 "renderable": True},
    "roughness": {"type": "number", "label": "Roughness", "min": 0.0, "max": 1.0, "renderable": True},
    "metalness": {"type": "number", "label": "Metalness", "min": 0.0, "max": 1.0, "renderable": True},
    "emissive": {"type": "number", "label": "Glow", "min": 0.0, "max": 3.0, "renderable": True},
    "opacity": {"type": "number", "label": "Opacity", "min": 0.05, "max": 1.0, "renderable": True},
    "rotation_speed": {"type": "number", "label": "Rotation speed", "min": -3.0, "max": 3.0, "renderable": True},
    "wings": {"type": "integer", "label": "Wings", "min": 0, "max": 8, "renderable": True},
    "windows": {"type": "integer", "label": "Windows", "min": 0, "max": 60, "renderable": True},
    "animation": {"type": "enum", "label": "Animation",
                  "options": ["none", "float", "sway", "flicker", "flow", "pulse", "drift"], "renderable": True},
    "detail": {"type": "number", "label": "Detail", "min": 0.0, "max": 1.0, "renderable": True},
    "glow": {"type": "number", "label": "Aura", "min": 0.0, "max": 2.0, "renderable": True},
    "height": {"type": "number", "label": "Height", "min": 0.2, "max": 8.0, "renderable": True},
    "spread": {"type": "number", "label": "Spread", "min": 0.2, "max": 6.0, "renderable": True},
}

KIND_DEFAULT_ATTRIBUTES: dict[str, dict] = {
    "castle": {"color": "#c9c4b4", "material": "stone", "size": 1.4, "windows": 12, "roughness": 0.8},
    "moon": {"color": "#dfe8ff", "emissive": 1.2, "size": 0.8, "roughness": 0.6, "animation": "float"},
    "sun": {"color": "#ffd27a", "emissive": 2.4, "size": 1.0, "glow": 1.4},
    "planet": {"color": "#b38bff", "emissive": 0.6, "size": 1.2, "roughness": 0.5},
    "tree": {"color": "#2f6b46", "secondary_color": "#6b4a2f", "material": "foliage", "size": 1.0, "animation": "sway"},
    "forest": {"color": "#1f4f35", "material": "foliage", "size": 1.2, "detail": 0.8},
    "mountain": {"color": "#39415c", "material": "stone", "size": 1.6, "roughness": 0.95},
    "water": {"color": "#1b4a78", "secondary_color": "#79e8ff", "material": "water", "roughness": 0.15,
              "metalness": 0.3, "animation": "flow"},
    "fog": {"color": "#8fa2c8", "opacity": 0.25, "size": 2.0, "animation": "drift"},
    "cloud": {"color": "#cfd8ea", "opacity": 0.85, "size": 1.3, "animation": "drift"},
    "star": {"color": "#ffffff", "emissive": 1.6, "size": 0.12, "count": 12},
    "fire": {"color": "#ff8a3c", "secondary_color": "#ffd36a", "emissive": 1.8, "size": 0.5, "animation": "flicker"},
    "person": {"color": "#d8b08c", "secondary_color": "#2a3550", "size": 0.9},
    "creature": {"color": "#7a6a9e", "secondary_color": "#2a2340", "size": 1.0, "wings": 0},
    "dragon": {"color": "#3f6b4f", "secondary_color": "#c9a24a", "size": 1.5, "wings": 2, "animation": "float"},
    "bird": {"color": "#1b1f2e", "size": 0.4, "count": 3, "animation": "float"},
    "boat": {"color": "#6b4a2f", "secondary_color": "#d8d2c0", "material": "wood", "size": 0.8},
    "bridge": {"color": "#6b6250", "material": "stone", "size": 1.2},
    "road": {"color": "#3a3a44", "material": "stone", "size": 1.2},
    "building": {"color": "#7d8699", "material": "stone", "windows": 18, "size": 1.3},
    "flower": {"color": "#e98ab5", "secondary_color": "#3fae6a", "size": 0.35},
    "door": {"color": "#8a5a3a", "material": "wood", "size": 1.0, "emissive": 0.2},
    "portal": {"color": "#57e0e6", "emissive": 1.8, "opacity": 0.7, "animation": "pulse", "size": 1.1},
    "crystal": {"color": "#8a5cf0", "emissive": 0.9, "material": "glass", "size": 0.8, "roughness": 0.1},
    "rock": {"color": "#4a4a55", "material": "stone", "size": 0.6, "roughness": 0.95},
    "grass": {"color": "#3f7a4a", "size": 0.8, "count": 18, "animation": "sway"},
    "island": {"color": "#5a6b4a", "secondary_color": "#d8c08a", "size": 1.5},
}

KIND_ALIASES: dict[str, str] = {
    "sea": "water", "ocean": "water", "lake": "water", "river": "water", "waves": "water",
    "woods": "forest", "trees": "tree", "wood": "forest", "hill": "mountain", "hills": "mountain",
    "peak": "mountain", "peaks": "mountain", "clouds": "cloud", "stars": "star", "flame": "fire",
    "flames": "fire", "campfire": "fire", "figure": "person", "man": "person", "woman": "person",
    "child": "person", "ship": "boat", "city": "building", "house": "building", "tower": "building",
    "flowers": "flower", "garden": "flower", "path": "road", "street": "road", "gate": "door",
    "beast": "creature", "wolf": "creature", "animal": "creature", "winged creature": "dragon",
    "moons": "moon", "planets": "planet", "sun": "sun", "crystal": "crystal", "crystals": "crystal",
    "stones": "rock", "rocks": "rock", "grass": "grass", "island": "island", "isle": "island",
}

KIND_POSITIONS: dict[str, list[float]] = {
    "water": [0.0, -0.05, -2.0],
    "fog": [0.0, 1.2, -6.0],
    "mountain": [0.0, 0.8, -14.0],
    "forest": [-6.0, 0.0, -9.0],
    "cloud": [0.0, 4.5, -10.0],
    "star": [0.0, 6.0, -12.0],
    "moon": [4.0, 5.0, -12.0],
    "sun": [5.0, 4.0, -16.0],
    "planet": [-5.0, 5.5, -15.0],
    "castle": [0.0, 0.0, 0.0],
    "dragon": [0.0, 3.0, -2.0],
    "creature": [0.0, 0.0, 0.0],
    "bird": [0.0, 4.0, -6.0],
    "tree": [2.5, 0.0, -1.0],
    "building": [-3.0, 0.0, -3.0],
    "person": [0.0, 0.0, 2.0],
    "boat": [1.5, 0.1, 1.5],
    "bridge": [0.0, 0.4, 1.0],
    "road": [0.0, 0.0, 2.0],
    "fire": [1.8, 0.0, 1.8],
    "flower": [1.0, 0.0, 2.2],
    "door": [0.0, 1.0, -1.5],
    "portal": [0.0, 1.4, -2.0],
    "crystal": [-1.5, 0.4, 1.0],
    "rock": [2.0, 0.2, 0.5],
    "grass": [0.0, 0.0, 2.0],
    "island": [0.0, -0.2, -6.0],
}

KIND_ROLES: dict[str, str] = {
    "water": "background", "fog": "background", "mountain": "background", "forest": "background",
    "cloud": "background", "star": "background", "sky": "background", "grass": "background",
    "island": "background", "road": "background", "bridge": "background",
}


def normalize_kind(raw: str) -> str:
    text = (raw or "").strip().lower()
    if text in OBJECT_KINDS or text == "custom":
        return text
    return KIND_ALIASES.get(text, "custom")


def is_renderable_kind(kind: str) -> bool:
    return kind in OBJECT_KINDS


def kind_label(kind: str) -> str:
    return KIND_LABELS.get(kind, kind.replace("_", " ").title())


def attribute_spec(path: str) -> dict | None:
    return ATTRIBUTE_SPECS.get(path)


def normalize_color(value: str) -> str:
    text = (value or "").strip().lower()
    if text.startswith("#"):
        if re.fullmatch(r"#[0-9a-f]{3}", text):
            return "#" + "".join(ch * 2 for ch in text[1:])
        if re.fullmatch(r"#[0-9a-f]{6}", text):
            return text
        raise SceneValidationError(f"invalid hex color {value!r}")
    if text in COLOR_HEX:
        return COLOR_HEX[text]
    if text in COLOR_SYNONYMS:
        return COLOR_HEX[COLOR_SYNONYMS[text]]
    raise SceneValidationError(f"unknown color name {value!r}")


def default_position(kind: str, index: int) -> list[float]:
    base = KIND_POSITIONS.get(kind)
    if base is None:
        angle = (index * 1.7) % 6.283
        return [round(2.4 * (1 + index // 6) * math.cos(angle), 3), 0.0,
                round(2.4 * (1 + index // 6) * math.sin(angle), 3)]
    # Spread repeated background/prop kinds so two moons do not overlap exactly.
    offset = 0.0 if index == 0 else (index + 1) * 1.6 * (1 if index % 2 else -1)
    return [round(base[0] + offset, 3), base[1], base[2]]


def default_role(kind: str) -> str:
    return KIND_ROLES.get(kind, "subject" if kind in SUBJECT_KINDS else "prop")


def style_preset(style: str) -> dict:
    return STYLE_PRESETS.get(style, STYLE_PRESETS["cinematic"])


def time_preset(time_of_day: str) -> dict:
    return TIME_PRESETS.get(time_of_day, TIME_PRESETS["night"])


def mood_preset(mood: str) -> dict:
    return MOOD_PRESETS.get(mood, {})


__all__ = [
    "LIBRARY_VERSION", "OBJECT_KINDS", "KIND_LABELS", "COLOR_HEX", "COLOR_SYNONYMS",
    "STYLE_PRESETS", "TIME_PRESETS", "MOOD_PRESETS", "ATTRIBUTE_SPECS", "KIND_DEFAULT_ATTRIBUTES",
    "KIND_ALIASES", "KIND_POSITIONS", "KIND_ROLES", "normalize_kind", "is_renderable_kind",
    "kind_label", "attribute_spec", "normalize_color", "default_position", "default_role",
    "style_preset", "time_preset", "mood_preset",
]
