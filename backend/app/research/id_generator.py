"""Deterministic ID generation for synthetic entities.

For synthetic records, UUIDs are derived deterministically from a namespace
composed of study + protocol_hash + runtime_seed + entity_type + parent + ordinal.
This enables deterministic replay validation.
"""
from __future__ import annotations

import uuid
from typing import Protocol

IMAGINA_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


class IdGenerator(Protocol):
    def generate(self, entity_type: str, parent_id: str, ordinal: int) -> str: ...


class RandomIdGenerator:
    def generate(self, entity_type: str, parent_id: str, ordinal: int) -> str:
        return str(uuid.uuid4())


class DeterministicIdGenerator:
    def __init__(self, study_id: str, protocol_hash: str, runtime_seed: int):
        self._prefix = f"{study_id}:{protocol_hash}:{runtime_seed}"

    def generate(self, entity_type: str, parent_id: str, ordinal: int) -> str:
        name = f"{self._prefix}:{entity_type}:{parent_id}:{ordinal}"
        return str(uuid.uuid5(IMAGINA_NAMESPACE, name))
