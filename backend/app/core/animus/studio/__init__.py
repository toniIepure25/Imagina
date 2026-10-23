"""ANIMUS Studio product service."""
from app.core.animus.studio.bus import animus_bus
from app.core.animus.studio.repository import StudioRepository

__all__ = ["animus_bus", "StudioRepository"]
