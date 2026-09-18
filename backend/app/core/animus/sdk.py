"""ANIMUS product SDK — a small typed facade over the loop.

Lets an application (or a future research decoder) drive the closed loop without touching controller
internals:

    session = animus.start(mode="amplifier")
    session.generate()
    session.feedback(channel="attribute_correction", direction="more_blue")
    session.complete()

A future validated neural decoder connects by supplying an ObservationProvider to a benchmark/synthetic
session — the same interface, no controller changes.
"""
from __future__ import annotations

from app.core.animus.service import MODE_AMPLIFIER, MODE_BENCHMARK, AnimusService, animus_service


class AnimusSessionHandle:
    def __init__(self, service: AnimusService, sid: str):
        self._svc = service
        self.session_id = sid

    def state(self) -> dict:
        return self._svc.state(self.session_id)

    def next_action(self) -> dict:
        return self._svc.next_action(self.session_id)

    def generate(self, n: int = 1, jitter: float = 0.0) -> dict:
        return self._svc.generate_candidate(self.session_id, n=n, jitter=jitter)

    def feedback(self, **raw) -> dict:
        return self._svc.apply_feedback(self.session_id, raw)

    def step(self) -> dict:
        return self._svc.step(self.session_id)

    def belief(self) -> dict:
        return self._svc.belief(self.session_id)

    def candidates(self) -> dict:
        return self._svc.candidates(self.session_id)

    def timeline(self) -> dict:
        return self._svc.timeline(self.session_id)

    def replay(self) -> dict:
        return self._svc.replay(self.session_id)

    def complete(self) -> dict:
        return self._svc.stop(self.session_id)

    def delete(self) -> dict:
        return self._svc.delete(self.session_id)


class Animus:
    """Top-level SDK entrypoint."""

    def __init__(self, service: AnimusService | None = None):
        self._svc = service or animus_service

    def start(self, mode: str = MODE_AMPLIFIER, controller: str = "ANIMUS_ACTIVE",
              seed: int = 20260909, max_iterations: int = 8,
              observation_mode: str | None = None, target_index: int | None = None) -> AnimusSessionHandle:
        st = self._svc.create_session(mode=mode, controller=controller, seed=seed,
                                      max_iterations=max_iterations, observation_mode=observation_mode,
                                      target_index=target_index)
        return AnimusSessionHandle(self._svc, st["session_id"])


# convenience
animus = Animus()
MODES = (MODE_AMPLIFIER, MODE_BENCHMARK)
