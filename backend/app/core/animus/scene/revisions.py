"""Immutable scene versions, branches, undo, and version trees.

A version is a frozen snapshot plus the command batch that produced it. Undo moves a branch head to the
parent; it never deletes history. Branching forks from an existing version so users can explore a
correction without losing the line they were on.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.animus.scene.model import SceneGraph, SceneValidationError

MAIN_BRANCH = "main"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(*parts: Any) -> str:
    payload = "|".join(str(p) for p in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SceneVersion:
    version_id: str
    number: int
    branch_id: str
    parent_version_id: str | None
    _scene: SceneGraph
    commands: tuple[dict, ...] = ()
    diff: dict = field(default_factory=dict)
    source: str = "compose"
    label: str = "Initial scene"
    intention: str | None = None
    claim_level: str = "L1_BEHAVIORAL_ASSISTED"
    generator: str = "compose.v1"
    created_at: str = field(default_factory=_now)

    @property
    def scene(self) -> SceneGraph:
        return self._scene.copy()

    @property
    def content_hash(self) -> str:
        return self._scene.content_hash()

    def to_dict(self) -> dict:
        return {
            "version_id": self.version_id,
            "number": self.number,
            "branch_id": self.branch_id,
            "parent_version_id": self.parent_version_id,
            "scene": self._scene.to_dict(),
            "commands": list(self.commands),
            "diff": self.diff,
            "source": self.source,
            "label": self.label,
            "intention": self.intention,
            "claim_level": self.claim_level,
            "generator": self.generator,
            "created_at": self.created_at,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "SceneVersion":
        return cls(
            version_id=payload["version_id"],
            number=int(payload["number"]),
            branch_id=payload.get("branch_id", MAIN_BRANCH),
            parent_version_id=payload.get("parent_version_id"),
            _scene=SceneGraph.from_dict(payload["scene"]),
            commands=tuple(payload.get("commands") or ()),
            diff=dict(payload.get("diff") or {}),
            source=payload.get("source", "compose"),
            label=payload.get("label", ""),
            intention=payload.get("intention"),
            claim_level=payload.get("claim_level", "L1_BEHAVIORAL_ASSISTED"),
            generator=payload.get("generator", "compose.v1"),
            created_at=payload.get("created_at", _now()),
        )


@dataclass(frozen=True)
class BranchInfo:
    branch_id: str
    name: str
    head_version_id: str
    created_at: str = field(default_factory=_now)
    parent_branch_id: str | None = None
    fork_version_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "branch_id": self.branch_id,
            "name": self.name,
            "head_version_id": self.head_version_id,
            "created_at": self.created_at,
            "parent_branch_id": self.parent_branch_id,
            "fork_version_id": self.fork_version_id,
        }


class RevisionError(SceneValidationError):
    """Raised for invalid revision operations."""


class RevisionStore:
    def __init__(self) -> None:
        self._versions: dict[str, SceneVersion] = {}
        self._branches: dict[str, BranchInfo] = {}
        self._redo: dict[str, list[str]] = {}
        self._next_number = 1
        self._scope = ""

    @property
    def scope(self) -> str:
        return self._scope

    @scope.setter
    def scope(self, value: str) -> None:
        self._scope = value or ""

    @classmethod
    def with_root(cls, scene: SceneGraph, *, intention: str | None = None,
                  claim_level: str = "L1_BEHAVIORAL_ASSISTED",
                  generator: str = "compose.v1", scope: str = "") -> "RevisionStore":
        store = cls()
        store.scope = scope
        root = store._make_version(
            scene=scene, branch_id=MAIN_BRANCH, parent_version_id=None,
            commands=(), diff={}, source="compose", label="Initial scene",
            intention=intention, claim_level=claim_level, generator=generator,
        )
        store._versions[root.version_id] = root
        store._branches[MAIN_BRANCH] = BranchInfo(
            branch_id=MAIN_BRANCH, name="Main", head_version_id=root.version_id)
        store._next_number = 2
        return store

    @property
    def branches(self) -> list[BranchInfo]:
        return sorted(self._branches.values(), key=lambda b: (b.created_at, b.branch_id))

    def branch(self, branch_id: str) -> BranchInfo:
        if branch_id not in self._branches:
            raise RevisionError(f"unknown branch {branch_id!r}")
        return self._branches[branch_id]

    def version(self, version_id: str) -> SceneVersion:
        if version_id not in self._versions:
            raise RevisionError(f"unknown version {version_id!r}")
        return self._versions[version_id]

    def head(self, branch_id: str = MAIN_BRANCH) -> SceneVersion:
        return self.version(self.branch(branch_id).head_version_id)

    def _make_version(self, *, scene: SceneGraph, branch_id: str, parent_version_id: str | None,
                      commands: list[dict] | tuple[dict, ...], diff: dict, source: str, label: str,
                      intention: str | None, claim_level: str, generator: str) -> SceneVersion:
        number = self._next_number
        version_id = "ver_" + _digest(self._scope, branch_id, parent_version_id, scene.content_hash(), number)[:12]
        return SceneVersion(
            version_id=version_id, number=number, branch_id=branch_id,
            parent_version_id=parent_version_id, _scene=scene.copy(), commands=tuple(commands),
            diff=dict(diff), source=source, label=label, intention=intention,
            claim_level=claim_level, generator=generator,
        )

    def commit(self, branch_id: str, scene: SceneGraph, *, commands: list[dict] | tuple[dict, ...] = (),
               diff: dict | None = None, source: str = "refine", label: str = "",
               intention: str | None = None, claim_level: str = "L1_BEHAVIORAL_ASSISTED",
               generator: str = "compose.v1") -> SceneVersion:
        current = self.branch(branch_id)
        version = self._make_version(
            scene=scene, branch_id=branch_id, parent_version_id=current.head_version_id,
            commands=commands, diff=diff or {}, source=source, label=label,
            intention=intention, claim_level=claim_level, generator=generator,
        )
        self._versions[version.version_id] = version
        self._next_number += 1
        self._branches[branch_id] = BranchInfo(
            branch_id=current.branch_id, name=current.name, head_version_id=version.version_id,
            created_at=current.created_at, parent_branch_id=current.parent_branch_id,
            fork_version_id=current.fork_version_id)
        self._redo[branch_id] = []
        return version

    def can_undo(self, branch_id: str = MAIN_BRANCH) -> bool:
        return self.head(branch_id).parent_version_id is not None

    def undo(self, branch_id: str = MAIN_BRANCH) -> SceneVersion:
        current = self.branch(branch_id)
        head = self.version(current.head_version_id)
        if head.parent_version_id is None:
            raise RevisionError("already at the first version")
        parent = self.version(head.parent_version_id)
        self._redo.setdefault(branch_id, []).append(head.version_id)
        self._branches[branch_id] = BranchInfo(
            branch_id=current.branch_id, name=current.name, head_version_id=parent.version_id,
            created_at=current.created_at, parent_branch_id=current.parent_branch_id,
            fork_version_id=current.fork_version_id)
        return parent

    def can_redo(self, branch_id: str = MAIN_BRANCH) -> bool:
        return bool(self._redo.get(branch_id))

    def redo_ids(self, branch_id: str = MAIN_BRANCH) -> list[str]:
        """Return a copy of the persisted redo stack for a branch."""
        return list(self._redo.get(branch_id) or [])

    def redo(self, branch_id: str = MAIN_BRANCH) -> SceneVersion:
        stack = self._redo.get(branch_id) or []
        if not stack:
            raise RevisionError("nothing to redo")
        version = self.version(stack.pop())
        current = self.branch(branch_id)
        self._branches[branch_id] = BranchInfo(
            branch_id=current.branch_id, name=current.name, head_version_id=version.version_id,
            created_at=current.created_at, parent_branch_id=current.parent_branch_id,
            fork_version_id=current.fork_version_id)
        return version

    def branch_from(self, version_id: str, name: str | None = None) -> BranchInfo:
        version = self.version(version_id)
        branch_id = "br_" + _digest(version_id, name or "", len(self._branches))[:10]
        info = BranchInfo(
            branch_id=branch_id, name=name or f"Branch {len(self._branches)}",
            head_version_id=version_id, parent_branch_id=version.branch_id,
            fork_version_id=version_id,
        )
        self._branches[branch_id] = info
        self._redo[branch_id] = []
        return info

    def history(self, branch_id: str = MAIN_BRANCH) -> list[SceneVersion]:
        head = self.branch(branch_id).head_version_id
        chain: list[SceneVersion] = []
        seen: set[str] = set()
        current: str | None = head
        while current is not None and current not in seen:
            seen.add(current)
            version = self.version(current)
            chain.append(version)
            current = version.parent_version_id
        chain.reverse()
        return chain

    def versions(self) -> list[SceneVersion]:
        return sorted(self._versions.values(), key=lambda v: v.number)

    def snapshot(self) -> dict:
        return {
            "versions": [v.to_dict() for v in self.versions()],
            "branches": [b.to_dict() for b in self.branches],
            "redo": {branch: list(items) for branch, items in self._redo.items()},
            "next_number": self._next_number,
        }

    @classmethod
    def from_snapshot(cls, payload: dict) -> "RevisionStore":
        store = cls()
        for item in payload.get("versions", []):
            version = SceneVersion.from_dict(item)
            store._versions[version.version_id] = version
        for item in payload.get("branches", []):
            info = BranchInfo(
                branch_id=item["branch_id"], name=item.get("name", ""),
                head_version_id=item["head_version_id"], created_at=item.get("created_at", _now()),
                parent_branch_id=item.get("parent_branch_id"), fork_version_id=item.get("fork_version_id"))
            store._branches[info.branch_id] = info
        store._redo = {k: list(v) for k, v in (payload.get("redo") or {}).items()}
        store._next_number = int(payload.get("next_number", len(store._versions) + 1))
        if MAIN_BRANCH not in store._branches and store._versions:
            first = min(store._versions.values(), key=lambda v: v.number)
            store._branches[MAIN_BRANCH] = BranchInfo(
                branch_id=MAIN_BRANCH, name="Main", head_version_id=first.version_id)
        return store


__all__ = ["MAIN_BRANCH", "SceneVersion", "BranchInfo", "RevisionStore", "RevisionError"]
