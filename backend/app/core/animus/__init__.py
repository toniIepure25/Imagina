"""ANIMUS — closed-loop imagination inference / amplification engine (product layer of IMAGINA).

ANIMUS-P1 vertical slice: observation -> belief -> generation -> feedback -> belief update -> controller ->
next candidate, with simulated/behavioral evidence only (claim levels L0/L1). A future validated neural
decoder plugs in as an interchangeable observation source without redesigning the loop. Nothing here
executes or reinterprets any frozen C3XAT/C3XRP/C3XRA scientific result.
"""
from app.core.animus.claims import (
    MAX_AUTHORIZED_LEVEL,
    ClaimAuthorization,
    ClaimLevelError,
)
from app.core.animus.models import ImaginationBeliefState

__all__ = [
    "ImaginationBeliefState",
    "ClaimAuthorization",
    "ClaimLevelError",
    "MAX_AUTHORIZED_LEVEL",
]
