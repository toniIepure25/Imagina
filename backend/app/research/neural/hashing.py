"""Content hashing helpers for neural dataset provenance."""
from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_SIZE = 1024 * 1024


def sha256_file(path: str | Path) -> str:
    """Compute the SHA-256 hex digest of a file's full contents.

    Streams in fixed-size chunks so multi-hundred-MB raw EEG files never
    need to be loaded fully into memory.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(_CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()
