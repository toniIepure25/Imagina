"""Typed ANIMUS Studio product errors.

The API layer maps these to stable HTTP status codes. Keeping the classes in one place avoids the
service importing FastAPI and lets tests assert product semantics rather than transport details.
"""
from __future__ import annotations


class StudioError(RuntimeError):
    """Base class for product-service errors."""


class StudioNotFound(StudioError):
    """A session, world, candidate, version, or branch does not exist."""


class StudioValidationError(StudioError):
    """A request violates a domain invariant."""


class StudioConflict(StudioError):
    """The request is valid but no longer applies to the current session head."""


class StudioArchived(StudioConflict):
    """The session is archived and cannot be mutated."""


class StudioPersistenceError(StudioError):
    """The local durable write failed; the in-memory runtime was invalidated."""


class StudioCorruptState(StudioError):
    """Durable Studio records exist but cannot be decoded into a valid scene state."""


__all__ = [
    "StudioError",
    "StudioNotFound",
    "StudioValidationError",
    "StudioConflict",
    "StudioArchived",
    "StudioPersistenceError",
    "StudioCorruptState",
]
