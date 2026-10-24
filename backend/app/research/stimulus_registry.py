from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass
class StimulusEntry:
    stimulus_id: str
    name: str
    category: str
    description: str
    content_hash: str
    scene_params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "stimulus_id": self.stimulus_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "content_hash": self.content_hash,
            "scene_params": self.scene_params,
        }


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


_STIMULI: dict[str, StimulusEntry] = {
    "corridor_simple": StimulusEntry(
        stimulus_id="corridor_simple",
        name="Simple Corridor",
        category="corridor",
        description="A plain corridor with minimal detail. Focus on walls, floor, and a distant light.",
        content_hash=_hash_content("corridor_simple_v1"),
    ),
    "corridor_detailed": StimulusEntry(
        stimulus_id="corridor_detailed",
        name="Detailed Corridor",
        category="corridor",
        description="A corridor with textured walls, patterned floor, and multiple light sources.",
        content_hash=_hash_content("corridor_detailed_v1"),
    ),
    "corridor_doors": StimulusEntry(
        stimulus_id="corridor_doors",
        name="Corridor with Doors",
        category="corridor",
        description="A corridor with doors on both sides. Focus on making one door distinct.",
        content_hash=_hash_content("corridor_doors_v1"),
    ),
    "corridor_garden": StimulusEntry(
        stimulus_id="corridor_garden",
        name="Garden at End",
        category="corridor",
        description="A corridor opening into a garden. Transition from indoor to outdoor.",
        content_hash=_hash_content("corridor_garden_v1"),
    ),
    "corridor_memory": StimulusEntry(
        stimulus_id="corridor_memory",
        name="Memory Room",
        category="corridor",
        description="Step through a door into a familiar room from memory.",
        content_hash=_hash_content("corridor_memory_v1"),
    ),
}


def get_stimulus(stimulus_id: str) -> StimulusEntry | None:
    return _STIMULI.get(stimulus_id)


def list_stimuli() -> list[StimulusEntry]:
    return list(_STIMULI.values())


def list_stimulus_ids() -> list[str]:
    return list(_STIMULI.keys())


def register_stimulus(entry: StimulusEntry) -> None:
    _STIMULI[entry.stimulus_id] = entry
