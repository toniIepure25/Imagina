"""Deterministic seed derivation for scientific random streams.

Replaces Python built-in hash() (process-salted, nondeterministic) with
hashlib.sha256 for all scientific randomness. Provides named child streams
so that changing one stream does not alter unrelated streams.

Version: 1.0
"""
from __future__ import annotations

import hashlib
import struct

RNG_VERSION = "1.0"

STREAM_NAMES = frozenset({
    "population",
    "allocation",
    "stimulus",
    "latent_state",
    "motor_noise",
    "imagery_noise",
    "self_report",
    "dropout",
    "bootstrap",
    "randomization_test",
    "calibration",
    "oracle",
    "simulation",
    "schedule",
})


def derive_seed(
    root_seed: int,
    namespace: str,
    participant_id: str | None = None,
    session_index: int | None = None,
    trial_index: int | None = None,
    replicate_index: int | None = None,
) -> int:
    """Derive a deterministic seed from structured components.

    Uses SHA-256 of canonical serialization. Independent of PYTHONHASHSEED.
    Returns a non-negative 63-bit integer suitable for random.Random() or
    numpy SeedSequence.
    """
    parts = [str(root_seed), namespace]
    if participant_id is not None:
        parts.append(f"p={participant_id}")
    if session_index is not None:
        parts.append(f"s={session_index}")
    if trial_index is not None:
        parts.append(f"t={trial_index}")
    if replicate_index is not None:
        parts.append(f"r={replicate_index}")
    canonical = "|".join(parts).encode("utf-8")
    digest = hashlib.sha256(canonical).digest()
    return struct.unpack(">Q", digest[:8])[0] & 0x7FFFFFFFFFFFFFFF


def rng_version_hash() -> str:
    data = f"rng_registry|v={RNG_VERSION}|streams={'|'.join(sorted(STREAM_NAMES))}"
    return hashlib.sha256(data.encode()).hexdigest()
