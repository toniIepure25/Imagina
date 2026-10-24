"""ANIMUS replay — exact reconstruction of a session from its manifest.

An ``AnimusReplayManifest`` captures everything needed to reproduce a session bit-exactly: the loop config
(seed, controller, policy/fusion hashes), provider versions, and the target/params for a benchmark run.
Re-running under the manifest must yield identical belief hashes, actions, candidate IDs and metric series.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.animus.loop_runtime import LoopConfig
from app.core.animus.models import canonical_hash


@dataclass
class AnimusReplayManifest:
    session_id: str
    config: dict
    provider_versions: dict
    decoder_version: str
    target_ref: dict = field(default_factory=dict)   # benchmark-only (evaluator)
    manifest_version: str = "animus-replay-v1"

    def manifest_hash(self) -> str:
        return canonical_hash({"config": self.config, "provider_versions": self.provider_versions,
                               "decoder_version": self.decoder_version, "target_ref": self.target_ref})

    def to_dict(self) -> dict:
        d = {"session_id": self.session_id, "config": self.config,
             "provider_versions": self.provider_versions, "decoder_version": self.decoder_version,
             "target_ref": self.target_ref, "manifest_version": self.manifest_version}
        d["manifest_hash"] = self.manifest_hash()
        return d

    @classmethod
    def from_config(cls, config: LoopConfig, target_ref: dict | None = None) -> "AnimusReplayManifest":
        return cls(session_id=config.session_id, config=config.to_dict(),
                   provider_versions={"synthetic_neural": "synthetic-decoder-v1",
                                      "behavioral": "comparative-v1"},
                   decoder_version="synthetic-decoder-v1", target_ref=target_ref or {})


def verify_replay(run_fn, n: int = 2) -> dict:
    """Run ``run_fn`` (a 0-arg callable returning a LoopResult) n times; assert identical replay hashes."""
    hashes = [run_fn().replay_hash() for _ in range(n)]
    return {"deterministic": len(set(hashes)) == 1, "replay_hash": hashes[0], "n": n}
