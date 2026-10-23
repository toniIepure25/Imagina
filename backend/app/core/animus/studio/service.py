"""ANIMUS Studio product service (local-first, async).

The central loop is: intention -> candidate -> correction -> version -> regenerate -> converge -> save.
Every mutation produces an immutable version, and every candidate is generated procedurally from the
symbolic scene. There is no hidden target, no image model, and no neural-content claim.
"""
from __future__ import annotations

import dataclasses
import hashlib
import logging
import math
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.animus import claims
from app.core.animus.scene.commands import apply_commands, parse_command
from app.core.animus.scene.compose import compose_from_intention
from app.core.animus.scene.intent import parse_intent
from app.core.animus.scene.model import SceneGraph, SceneValidationError
from app.core.animus.scene.regenerate import RegenerationConfig, regenerate_variants, scene_lock_paths
from app.core.animus.scene.revisions import MAIN_BRANCH, RevisionStore
from app.core.animus.studio.bus import AnimusEventBus, animus_bus
from app.core.animus.studio.claims import (
    StudioClaimError,
    capability_envelope,
    claim_envelope,
    enforce_studio_text,
)
from app.core.animus.studio.errors import (
    StudioArchived,
    StudioConflict,
    StudioCorruptState,
    StudioError,
    StudioNotFound,
    StudioPersistenceError,
    StudioValidationError,
)
from app.core.animus.studio.locks import SessionLockRegistry
from app.core.animus.studio.repository import StudioRepository
from app.core.animus.studio.types import (
    StudioBranchSummaryRecord,
    StudioCandidateRecord,
    StudioSessionRecord,
    StudioVersionSummaryRecord,
    StudioWorldRecord,
)

MODE_AMPLIFIER = "amplifier"
MAX_TITLE = 120
MAX_INTENTION = 500
RUNTIME_CACHE_LIMIT = 32

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(*parts: Any) -> str:
    payload = "|".join(str(p) for p in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class StudioRuntime:
    session: StudioSessionRecord
    revisions: RevisionStore
    candidates: list[StudioCandidateRecord] = field(default_factory=list)
    last_event_seq: int = 0


class AnimusStudioService:
    def __init__(self, repository: StudioRepository | None = None, bus: AnimusEventBus | None = None) -> None:
        self.repository = repository or StudioRepository()
        self.bus = bus or animus_bus
        self._runtimes: dict[str, StudioRuntime] = {}
        self._locks = SessionLockRegistry()

    # --- cache / locking ------------------------------------------------------
    def _cache_runtime(self, runtime: StudioRuntime) -> StudioRuntime:
        session_id = runtime.session["session_id"]
        self._runtimes.pop(session_id, None)
        self._runtimes[session_id] = runtime
        while len(self._runtimes) > RUNTIME_CACHE_LIMIT:
            oldest = next(iter(self._runtimes))
            self._runtimes.pop(oldest, None)
        return runtime

    def _invalidate(self, session_id: str) -> None:
        self._runtimes.pop(session_id, None)

    @staticmethod
    def _assert_mutable(runtime: StudioRuntime) -> None:
        if runtime.session.get("status") != "active":
            raise StudioArchived("This session is archived and cannot be changed")

    @staticmethod
    def _assert_expected(runtime: StudioRuntime, expected_version_id: str | None) -> None:
        if not expected_version_id:
            return
        head = runtime.revisions.head(runtime.session["active_branch_id"])
        if head.version_id != expected_version_id:
            raise StudioConflict("The scene changed since this view was loaded; refresh and try again")

    # --- creation / loading ---------------------------------------------------
    async def create_session(self, *, title: str, intention: str, seed: int = 20260909) -> dict:
        title = (title or "").strip()[:MAX_TITLE]
        intention = (intention or "").strip()[:MAX_INTENTION]
        if len(intention) < 3:
            raise StudioValidationError("Describe what you want to imagine (at least 3 characters)")
        try:
            enforce_studio_text(title, field="title")
            enforce_studio_text(intention, field="intention")
        except StudioClaimError as exc:
            raise StudioValidationError(str(exc)) from exc
        seed = int(seed)
        if not -(2**31) <= seed <= 2**31 - 1:
            raise StudioValidationError("seed is out of range")
        composed = compose_from_intention(intention, seed=seed, title=title or "Untitled scene")
        runtime = await self._create_runtime(
            scene=composed.scene, title=title or "Untitled scene", intention=intention, seed=seed)
        return self._snapshot(runtime)

    async def _create_runtime(self, *, scene: SceneGraph, title: str, intention: str, seed: int) -> StudioRuntime:
        session_id = "ast_" + uuid.uuid4().hex[:12]
        store = RevisionStore.with_root(scene, intention=intention)
        root = store.head()
        now = _now()
        session = {
            "session_id": session_id, "title": title, "intention": intention,
            "mode": MODE_AMPLIFIER, "status": "active", "seed": seed,
            "claim_level": claims.L1_BEHAVIORAL_ASSISTED,
            "active_branch_id": MAIN_BRANCH, "active_version_id": root.version_id,
            "privacy_scope": "local_only", "warnings": list(scene.metadata.get("warnings") or []),
            "metadata": {"generator": "compose.v1", "scene_version": scene.version_tag},
            "created_at": now, "updated_at": now,
        }
        branch = {
            "branch_id": MAIN_BRANCH, "session_id": session_id, "name": "Main",
            "head_version_id": root.version_id, "parent_branch_id": None,
            "fork_version_id": None, "created_at": now,
        }
        try:
            event_seq = await self.repository.create_session_bundle(
                session=session, version={**root.to_dict(), "session_id": session_id}, branch=branch,
                event_type="studio.session.created",
                event_payload={
                    "title": title, "intention": intention, "version_id": root.version_id,
                    "claim_level": claims.L1_BEHAVIORAL_ASSISTED,
                },
            )
        except Exception as exc:  # noqa: BLE001 - product error boundary
            logger.exception("studio.session.create_failed", extra={"session_id": session_id})
            raise StudioPersistenceError("The session could not be saved locally") from exc
        runtime = StudioRuntime(session=session, revisions=store, last_event_seq=event_seq)
        self._cache_runtime(runtime)
        await self.bus.publish(session_id, {
            "type": "session_created", "session_id": session_id,
            "seq": event_seq, "version": self._version_summary(root),
        })
        return runtime

    async def _load(self, session_id: str) -> StudioRuntime:
        cached = self._runtimes.get(session_id)
        if cached is not None:
            return self._cache_runtime(cached)
        session = await self.repository.get_session(session_id)
        if session is None:
            raise StudioNotFound(f"unknown studio session {session_id!r}")
        try:
            versions = await self.repository.load_versions(session_id)
            branches = await self.repository.load_branches(session_id)
            if not versions or not branches:
                raise StudioNotFound(f"studio session {session_id!r} has no scene history")
            active_branch_id = session["active_branch_id"]
            active_version_id = session.get("active_version_id")
            if active_version_id and any(
                version["version_id"] == active_version_id and version["branch_id"] == active_branch_id
                for version in versions
            ):
                for branch in branches:
                    if (branch["branch_id"] == active_branch_id
                            and branch["head_version_id"] != active_version_id):
                        branch["head_version_id"] = active_version_id
                        await self.repository.save_branch(branch)
            redo = {
                branch["branch_id"]: list(branch.get("redo") or [])
                for branch in branches
            }
            store = RevisionStore.from_snapshot({
                "versions": versions, "branches": branches, "redo": redo,
                "next_number": max(int(v["number"]) for v in versions) + 1,
            })
            if active_branch_id not in {branch["branch_id"] for branch in branches}:
                raise StudioNotFound(f"unknown studio branch {active_branch_id!r}")
            head = store.head(active_branch_id)
            candidates = await self.repository.load_candidates(
                session_id, source_version_id=head.version_id, include_selected=False)
            last_event_seq = await self.repository.latest_event_seq(session_id)
        except (StudioNotFound, StudioCorruptState):
            raise
        except (KeyError, TypeError, ValueError, AttributeError, IndexError,
                SceneValidationError) as exc:
            logger.exception("studio.load.corrupt_state", extra={"session_id": session_id})
            raise StudioCorruptState(
                "The local Studio record for this session is unreadable. Back up the database and "
                "inspect the session before continuing."
            ) from exc
        runtime = StudioRuntime(
            session=session, revisions=store, candidates=candidates,
            last_event_seq=last_event_seq,
        )
        return self._cache_runtime(runtime)

    # --- reads ----------------------------------------------------------------
    async def get_session(self, session_id: str) -> dict:
        async with self._locks.hold(session_id):
            return self._snapshot(await self._load(session_id))

    async def list_sessions(self, limit: int = 50) -> dict:
        rows = await self.repository.list_sessions(limit=min(max(limit, 1), 100))
        return {"sessions": [{
            "session_id": row["session_id"], "title": row["title"], "intention": row["intention"],
            "status": row["status"], "seed": row["seed"], "claim_level": row["claim_level"],
            "created_at": row["created_at"], "updated_at": row["updated_at"],
        } for row in rows]}

    async def history(self, session_id: str) -> dict:
        async with self._locks.hold(session_id):
            runtime = await self._load(session_id)
            branch_id = runtime.session["active_branch_id"]
            return {
                "session_id": session_id,
                "active_branch_id": branch_id,
                "branches": self._branches(runtime),
                "versions": [self._version_summary(v) for v in runtime.revisions.history(branch_id)],
                "has_undo": runtime.revisions.can_undo(branch_id),
                "has_redo": runtime.revisions.can_redo(branch_id),
            }

    async def version(self, session_id: str, version_id: str) -> dict:
        async with self._locks.hold(session_id):
            runtime = await self._load(session_id)
            try:
                version = runtime.revisions.version(version_id)
            except SceneValidationError as exc:
                raise StudioNotFound(f"unknown version {version_id}") from exc
            payload = version.to_dict()
            payload["entity_count"] = len(version.scene.entities)
            return payload

    async def events(self, session_id: str, *, after_seq: int = 0, limit: int = 100) -> dict:
        async with self._locks.hold(session_id):
            if await self.repository.get_session(session_id) is None:
                raise StudioNotFound(f"unknown studio session {session_id!r}")
            try:
                events = await self.repository.load_events_after(session_id, after_seq, limit + 1)
            except ValueError as exc:
                logger.exception("studio.events.corrupt_state", extra={"session_id": session_id})
                raise StudioCorruptState(
                    "The local event history for this session is unreadable."
                ) from exc
            has_more = len(events) > limit
            return {
                "session_id": session_id,
                "events": events[:limit],
                "has_more": has_more,
            }

    # --- intent / commands ----------------------------------------------------
    async def apply_intent(self, session_id: str, text: str, *,
                           expected_version_id: str | None = None) -> dict:
        async with self._locks.hold(session_id):
            runtime = await self._load(session_id)
            self._assert_mutable(runtime)
            self._assert_expected(runtime, expected_version_id)
            if not isinstance(text, str) or not text.strip():
                raise StudioValidationError("Describe a change first")
            if len(text) > 400:
                raise StudioValidationError("A correction may contain at most 400 characters")
            try:
                enforce_studio_text(text, field="correction")
            except StudioClaimError as exc:
                raise StudioValidationError(str(exc)) from exc
            head = runtime.revisions.head(runtime.session["active_branch_id"])
            parsed = parse_intent(text, head.scene)
            if not parsed.commands:
                return {
                    **self._snapshot(runtime),
                    "needs_clarification": True,
                    "clarification": parsed.clarification,
                    "resolutions": parsed.resolutions,
                    "parse_warnings": parsed.warnings,
                    "applied": 0,
                }
            try:
                scene, diff, warnings = apply_commands(head.scene, parsed.commands, source_text=text)
            except SceneValidationError as exc:
                raise StudioValidationError(str(exc)) from exc
            version = runtime.revisions.commit(
                runtime.session["active_branch_id"], scene,
                commands=[dataclasses.asdict(command) for command in parsed.commands],
                diff=diff, source="refine", label=text[:MAX_TITLE],
                intention=text[:MAX_INTENTION],
            )
            await self._persist_commit(runtime, version, "studio.intent.applied", {
                "text": text, "resolutions": parsed.resolutions, "warnings": warnings,
            })
            return {
                **self._snapshot(runtime),
                "needs_clarification": False,
                "clarification": None,
                "resolutions": parsed.resolutions,
                "parse_warnings": parsed.warnings + warnings,
                "applied": len(parsed.commands),
            }

    async def apply_commands(self, session_id: str, raw_commands: list[dict], *, source_text: str = "",
                             expected_version_id: str | None = None) -> dict:
        async with self._locks.hold(session_id):
            runtime = await self._load(session_id)
            self._assert_mutable(runtime)
            self._assert_expected(runtime, expected_version_id)
            if not raw_commands:
                raise StudioValidationError("At least one command is required")
            if not isinstance(raw_commands, list) or len(raw_commands) > 24:
                raise StudioValidationError("A batch may contain at most 24 commands")
            if not isinstance(source_text, str) or len(source_text) > 500:
                raise StudioValidationError("The edit note may contain at most 500 characters")
            try:
                enforce_studio_text(source_text, field="edit note")
            except StudioClaimError as exc:
                raise StudioValidationError(str(exc)) from exc
            try:
                parsed = [parse_command(item) for item in raw_commands]
                head = runtime.revisions.head(runtime.session["active_branch_id"])
                scene, diff, warnings = apply_commands(head.scene, parsed, source_text=source_text)
            except SceneValidationError as exc:
                raise StudioValidationError(str(exc)) from exc
            version = runtime.revisions.commit(
                runtime.session["active_branch_id"], scene,
                commands=[dataclasses.asdict(command) for command in parsed],
                diff=diff, source="direct-edit", label=f"{len(parsed)} manual edit"
                f"{'s' if len(parsed) != 1 else ''}", intention=source_text[:MAX_INTENTION] or None,
            )
            await self._persist_commit(runtime, version, "studio.commands.applied", {
                "commands": [dataclasses.asdict(command) for command in parsed], "warnings": warnings,
            })
            return {**self._snapshot(runtime), "applied": len(parsed), "warnings": warnings}

    # --- candidates -----------------------------------------------------------
    async def regenerate(self, session_id: str, *, count: int = 3, strength: float = 0.22,
                         seed: int | None = None, locks: list[str] | None = None,
                         expected_version_id: str | None = None,
                         preserve_user_edits: bool = True, vary_camera: bool = True) -> dict:
        async with self._locks.hold(session_id):
            runtime = await self._load(session_id)
            self._assert_mutable(runtime)
            self._assert_expected(runtime, expected_version_id)
            head = runtime.revisions.head(runtime.session["active_branch_id"])
            valid_locks = scene_lock_paths(head.scene)
            extra_locks = set(locks or ())
            if len(extra_locks) > 80 or any(not isinstance(path, str) or len(path) > 80 for path in extra_locks):
                raise StudioValidationError("A lock set may contain at most 80 short paths")
            unknown = sorted(extra_locks - valid_locks - {"camera"})
            if unknown:
                raise StudioValidationError(f"unknown lock path(s): {', '.join(unknown[:3])}")
            try:
                count = int(count)
                strength = float(strength)
            except (TypeError, ValueError) as exc:
                raise StudioValidationError("count and strength must be numbers") from exc
            if not 1 <= count <= 6:
                raise StudioValidationError("count must be between 1 and 6")
            if not math.isfinite(strength) or not 0.0 <= strength <= 1.0:
                raise StudioValidationError("strength must be between 0 and 1")
            use_seed = int(seed) if seed is not None else int(runtime.session["seed"]) + head.number * 7919
            if not -(2**31) <= use_seed <= 2**31 - 1:
                raise StudioValidationError("seed is out of range")
            config = RegenerationConfig(
                count=count, strength=strength, seed=use_seed,
                preserve_user_edits=preserve_user_edits, vary_camera=vary_camera,
            )
            variants = regenerate_variants(head.scene, config, locks=extra_locks)
            created_at = _now()
            generated: list[dict] = []
            for variant in variants:
                candidate_id = "cand_" + _digest(session_id, head.version_id, variant.index,
                                                 variant.scene.content_hash())[:12]
                generated.append({
                    "candidate_id": candidate_id, "session_id": session_id,
                    "source_version_id": head.version_id, "variant_index": variant.index,
                    "scene": variant.scene.to_dict(), "diff": variant.diff, "notes": variant.notes,
                    "selected": False, "created_at": created_at,
                })
            try:
                event_seq = await self.repository.save_candidates_bundle(
                    generated, event_type="studio.candidates.generated",
                    event_payload={
                        "count": len(generated), "source_version_id": head.version_id,
                        "candidate_ids": [c["candidate_id"] for c in generated],
                    },
                )
            except Exception as exc:  # noqa: BLE001 - product error boundary
                logger.exception("studio.candidates.persist_failed", extra={"session_id": session_id})
                raise StudioPersistenceError("The candidates could not be saved locally") from exc
            runtime.last_event_seq = event_seq
            runtime.candidates = await self.repository.load_candidates(
                session_id, source_version_id=head.version_id, include_selected=False)
            visible_ids = {candidate["candidate_id"] for candidate in runtime.candidates}
            await self.bus.publish(session_id, {
                "type": "candidates_generated", "session_id": session_id, "seq": event_seq,
                "source_version_id": head.version_id, "candidates": [
                    {"candidate_id": c["candidate_id"], "variant_index": c["variant_index"],
                     "notes": c["notes"]} for c in generated if c["candidate_id"] in visible_ids],
            })
            return {
                **self._snapshot(runtime),
                "generated": [self._candidate_payload(c) for c in generated
                              if c["candidate_id"] in visible_ids],
                "source_version_id": head.version_id,
                "active_locks": sorted(scene_lock_paths(head.scene) | extra_locks),
            }

    async def select_candidate(self, session_id: str, candidate_id: str, *,
                               expected_version_id: str | None = None) -> dict:
        async with self._locks.hold(session_id):
            runtime = await self._load(session_id)
            self._assert_mutable(runtime)
            self._assert_expected(runtime, expected_version_id)
            head = runtime.revisions.head(runtime.session["active_branch_id"])
            candidate = next((c for c in runtime.candidates if c["candidate_id"] == candidate_id), None)
            if candidate is None:
                try:
                    candidate = await self.repository.get_candidate(session_id, candidate_id)
                except ValueError as exc:
                    logger.exception("studio.candidate.corrupt_state",
                                     extra={"session_id": session_id, "candidate_id": candidate_id})
                    raise StudioCorruptState(
                        f"The stored candidate {candidate_id!r} is unreadable."
                    ) from exc
            if candidate is None:
                raise StudioNotFound(f"unknown candidate {candidate_id!r}")
            if candidate.get("source_version_id") != head.version_id or candidate.get("selected"):
                raise StudioConflict("This candidate belongs to an older scene; generate a fresh set")
            try:
                scene = SceneGraph.from_dict(candidate["scene"])
            except (SceneValidationError, KeyError, TypeError, ValueError,
                    AttributeError, IndexError) as exc:
                logger.exception("studio.candidate.scene_corrupt",
                                 extra={"session_id": session_id, "candidate_id": candidate_id})
                raise StudioCorruptState(
                    f"The stored candidate {candidate_id!r} is unreadable."
                ) from exc
            version = runtime.revisions.commit(
                runtime.session["active_branch_id"], scene,
                commands=[], diff=candidate.get("diff") or {}, source="candidate",
                label=f"Candidate {int(candidate.get('variant_index', 0)) + 1}",
                intention=runtime.session["intention"],
            )
            await self._persist_commit(runtime, version, "studio.candidate.selected", {
                "candidate_id": candidate_id, "variant_index": candidate.get("variant_index"),
            }, candidate_id=candidate_id)
            runtime.candidates = [c for c in runtime.candidates if c["candidate_id"] != candidate_id]
            return self._snapshot(runtime)

    # --- history operations ---------------------------------------------------
    async def undo(self, session_id: str, *, expected_version_id: str | None = None) -> dict:
        async with self._locks.hold(session_id):
            runtime = await self._load(session_id)
            self._assert_mutable(runtime)
            self._assert_expected(runtime, expected_version_id)
            branch_id = runtime.session["active_branch_id"]
            try:
                runtime.revisions.undo(branch_id)
            except Exception as exc:  # noqa: BLE001 - converted to a product error
                raise StudioValidationError(str(exc)) from exc
            await self._persist_head(runtime, "studio.undo")
            return self._snapshot(runtime)

    async def redo(self, session_id: str, *, expected_version_id: str | None = None) -> dict:
        async with self._locks.hold(session_id):
            runtime = await self._load(session_id)
            self._assert_mutable(runtime)
            self._assert_expected(runtime, expected_version_id)
            branch_id = runtime.session["active_branch_id"]
            try:
                runtime.revisions.redo(branch_id)
            except Exception as exc:  # noqa: BLE001
                raise StudioValidationError(str(exc)) from exc
            await self._persist_head(runtime, "studio.redo")
            return self._snapshot(runtime)

    async def branch(self, session_id: str, *, name: str | None = None,
                     from_version_id: str | None = None,
                     expected_version_id: str | None = None) -> dict:
        async with self._locks.hold(session_id):
            runtime = await self._load(session_id)
            self._assert_mutable(runtime)
            self._assert_expected(runtime, expected_version_id)
            branch_id = runtime.session["active_branch_id"]
            version_id = from_version_id or runtime.revisions.head(branch_id).version_id
            if name:
                if len(name.strip()) > 40:
                    raise StudioValidationError("A branch name may contain at most 40 characters")
                try:
                    enforce_studio_text(name, field="branch name")
                except StudioClaimError as exc:
                    raise StudioValidationError(str(exc)) from exc
                normalized = name.strip().casefold()
                if any(info.name.strip().casefold() == normalized for info in runtime.revisions.branches):
                    raise StudioValidationError("A branch with that name already exists")
            try:
                info = runtime.revisions.branch_from(version_id, name=name)
            except Exception as exc:  # noqa: BLE001
                raise StudioValidationError(str(exc)) from exc
            runtime.session["active_branch_id"] = info.branch_id
            runtime.session["active_version_id"] = info.head_version_id
            runtime.session["updated_at"] = _now()
            branch_record = self._branch_record(runtime, info.branch_id)
            try:
                event_seq = await self.repository.update_head_bundle(
                    session=runtime.session, branch=branch_record,
                    event_type="studio.branch.created",
                    event_payload={"branch_id": info.branch_id, "name": info.name,
                                   "from_version_id": version_id},
                )
            except Exception as exc:  # noqa: BLE001 - product error boundary
                self._invalidate(session_id)
                logger.exception("studio.branch.persist_failed", extra={"session_id": session_id})
                raise StudioPersistenceError("The branch could not be saved locally") from exc
            runtime.last_event_seq = event_seq
            await self._refresh_candidates(runtime)
            await self.bus.publish(session_id, {
                "type": "branch_created", "session_id": session_id, "seq": event_seq,
                "branch_id": info.branch_id, "name": info.name,
            })
            return self._snapshot(runtime)

    async def switch_branch(self, session_id: str, branch_id: str, *,
                            expected_version_id: str | None = None) -> dict:
        async with self._locks.hold(session_id):
            runtime = await self._load(session_id)
            self._assert_mutable(runtime)
            self._assert_expected(runtime, expected_version_id)
            try:
                info = runtime.revisions.branch(branch_id)
            except SceneValidationError as exc:
                raise StudioNotFound(f"unknown branch {branch_id}") from exc
            except Exception as exc:  # noqa: BLE001
                raise StudioValidationError(str(exc)) from exc
            runtime.session["active_branch_id"] = branch_id
            runtime.session["active_version_id"] = info.head_version_id
            runtime.session["updated_at"] = _now()
            branch_record = self._branch_record(runtime, branch_id)
            try:
                event_seq = await self.repository.update_head_bundle(
                    session=runtime.session, branch=branch_record,
                    event_type="studio.branch.switched", event_payload={"branch_id": branch_id},
                )
            except Exception as exc:  # noqa: BLE001
                self._invalidate(session_id)
                logger.exception("studio.branch.switch_failed", extra={"session_id": session_id})
                raise StudioPersistenceError("The branch switch could not be saved locally") from exc
            runtime.last_event_seq = event_seq
            # Candidate sets are scoped to the head of the branch now in front.
            await self._refresh_candidates(runtime)
            await self.bus.publish(session_id, {
                "type": "branch_switched", "session_id": session_id, "seq": event_seq,
                "branch_id": branch_id,
            })
            return self._snapshot(runtime)

    async def delete_session(self, session_id: str) -> dict:
        async with self._locks.hold(session_id):
            try:
                deleted = await self.repository.delete_session(session_id)
            except Exception as exc:  # noqa: BLE001 - product error boundary
                logger.exception("studio.session.delete_failed", extra={"session_id": session_id})
                raise StudioPersistenceError("The session could not be deleted locally") from exc
            self._invalidate(session_id)
            if not deleted:
                raise StudioNotFound(f"unknown studio session {session_id!r}")
        self._locks.forget(session_id)
        return {"deleted": session_id}

    # --- worlds ---------------------------------------------------------------
    async def save_world(self, session_id: str, *, name: str, description: str = "") -> StudioWorldRecord:
        started = time.perf_counter()
        async with self._locks.hold(session_id):
            runtime = await self._load(session_id)
            self._assert_mutable(runtime)
            try:
                enforce_studio_text(name, field="world name")
                enforce_studio_text(description, field="world description")
            except StudioClaimError as exc:
                raise StudioValidationError(str(exc)) from exc
            if not name.strip():
                raise StudioValidationError("A world needs a name")
            head = runtime.revisions.head(runtime.session["active_branch_id"])
            world_id = "world_" + uuid.uuid4().hex[:12]
            now = _now()
            world = {
                "world_id": world_id, "name": name.strip()[:MAX_TITLE],
                "description": description.strip()[:MAX_INTENTION], "scene": head.scene.to_dict(),
                "created_at": now,
            }
            items = [{
                "item_id": "wi_" + _digest(world_id, entity.id)[:12], "world_id": world_id,
                "label": entity.label, "kind": entity.kind, "scene": entity.to_dict(),
                "created_at": now,
            } for entity in head.scene.entities]
            try:
                event_seq = await self.repository.save_world_bundle(
                    session_id=session_id, world=world, items=items,
                    event_type="studio.world.saved",
                    event_payload={"world_id": world_id, "name": world["name"], "items": len(items)},
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("studio.world.persist_failed", extra={"session_id": session_id})
                raise StudioPersistenceError("The world could not be saved locally") from exc
            runtime.last_event_seq = event_seq
            logger.info(
                "studio.mutation.committed",
                extra={
                    "session_id": session_id, "event_type": "studio.world.saved",
                    "world_id": world_id, "event_seq": event_seq,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            return {**world, "items": items, "source_session_id": session_id}

    async def list_worlds(self, limit: int = 50) -> dict:
        try:
            worlds = await self.repository.list_worlds(limit=min(max(limit, 1), 100))
        except ValueError as exc:
            logger.exception("studio.worlds.corrupt_state")
            raise StudioCorruptState("A saved world record is unreadable.") from exc
        return {"worlds": worlds}

    async def get_world(self, world_id: str) -> dict:
        try:
            world = await self.repository.get_world(world_id)
        except ValueError as exc:
            logger.exception("studio.world.corrupt_state", extra={"world_id": world_id})
            raise StudioCorruptState(f"The saved world {world_id!r} is unreadable.") from exc
        if world is None:
            raise StudioNotFound(f"unknown world {world_id!r}")
        return world

    async def delete_world(self, world_id: str) -> dict:
        if not await self.repository.delete_world(world_id):
            raise StudioNotFound(f"unknown world {world_id!r}")
        return {"deleted": world_id}

    async def open_world(self, world_id: str, *, title: str | None = None) -> dict:
        world = await self.get_world(world_id)
        selected_title = (title or world["name"]).strip()[:MAX_TITLE]
        try:
            enforce_studio_text(selected_title, field="title")
        except StudioClaimError as exc:
            raise StudioValidationError(str(exc)) from exc
        try:
            scene = SceneGraph.from_dict(world["scene"])
        except (SceneValidationError, KeyError, TypeError, ValueError,
                AttributeError, IndexError) as exc:
            logger.exception("studio.world.scene_corrupt", extra={"world_id": world_id})
            raise StudioCorruptState(f"The saved world {world_id!r} is unreadable.") from exc
        intention = world.get("description") or world["name"]
        runtime = await self._create_runtime(
            scene=scene, title=selected_title, intention=intention[:MAX_INTENTION],
            seed=int(scene.seed))
        runtime.session["metadata"] = {
            **(runtime.session.get("metadata") or {}),
            "world_id": world_id, "world_name": world["name"],
        }
        try:
            await self._update_session_row(runtime)
        except Exception as exc:  # noqa: BLE001 - product error boundary
            self._invalidate(runtime.session["session_id"])
            logger.exception("studio.world.open_failed", extra={"world_id": world_id})
            raise StudioPersistenceError("The reopened session could not be saved locally") from exc
        return self._snapshot(runtime)

    # --- persistence helpers --------------------------------------------------
    def _branch_record(self, runtime: StudioRuntime, branch_id: str) -> dict:
        info = runtime.revisions.branch(branch_id)
        return {
            "branch_id": branch_id, "session_id": runtime.session["session_id"], "name": info.name,
            "head_version_id": info.head_version_id,
            "parent_branch_id": info.parent_branch_id,
            "fork_version_id": info.fork_version_id, "created_at": info.created_at,
            "redo": runtime.revisions.redo_ids(branch_id),
        }

    async def _persist_commit(self, runtime: StudioRuntime, version, event_type: str, payload: dict,
                              *, candidate_id: str | None = None) -> None:
        started = time.perf_counter()
        session_id = runtime.session["session_id"]
        branch_id = runtime.session["active_branch_id"]
        runtime.session["active_version_id"] = version.version_id
        runtime.session["updated_at"] = _now()
        branch_record = self._branch_record(runtime, branch_id)
        event_payload = {
            **payload, "version_id": version.version_id, "content_hash": version.content_hash,
        }
        try:
            if candidate_id is None:
                event_seq = await self.repository.commit_version_bundle(
                    session=runtime.session, version={**version.to_dict(), "session_id": session_id},
                    branch=branch_record, event_type=event_type, event_payload=event_payload,
                )
            else:
                event_seq = await self.repository.select_candidate_bundle(
                    session=runtime.session, version={**version.to_dict(), "session_id": session_id},
                    branch=branch_record, candidate_id=candidate_id,
                    event_type=event_type, event_payload=event_payload,
                )
        except Exception as exc:  # noqa: BLE001 - product error boundary
            self._invalidate(session_id)
            logger.exception("studio.commit.persist_failed",
                             extra={"session_id": session_id, "version_id": version.version_id})
            raise StudioPersistenceError("The scene could not be saved locally") from exc
        runtime.last_event_seq = event_seq
        logger.info(
            "studio.mutation.committed",
            extra={
                "session_id": session_id, "branch_id": branch_id, "version_id": version.version_id,
                "event_type": event_type, "event_seq": event_seq,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        await self._refresh_candidates(runtime)
        await self.bus.publish(session_id, {
            "type": event_type, "session_id": session_id, "seq": event_seq,
            "version": self._version_summary(version), "diff": version.diff,
        })

    async def _persist_head(self, runtime: StudioRuntime, event_type: str) -> int:
        started = time.perf_counter()
        session_id = runtime.session["session_id"]
        branch_id = runtime.session["active_branch_id"]
        info = runtime.revisions.branch(branch_id)
        runtime.session["active_version_id"] = info.head_version_id
        runtime.session["updated_at"] = _now()
        branch_record = self._branch_record(runtime, branch_id)
        try:
            event_seq = await self.repository.update_head_bundle(
                session=runtime.session, branch=branch_record, event_type=event_type,
                event_payload={"branch_id": branch_id, "head_version_id": info.head_version_id},
                version_id=info.head_version_id,
            )
        except Exception as exc:  # noqa: BLE001 - product error boundary
            self._invalidate(session_id)
            logger.exception("studio.head.persist_failed", extra={"session_id": session_id})
            raise StudioPersistenceError("The history position could not be saved locally") from exc
        runtime.last_event_seq = event_seq
        logger.info(
            "studio.mutation.committed",
            extra={
                "session_id": session_id, "branch_id": branch_id,
                "version_id": info.head_version_id, "event_type": event_type, "event_seq": event_seq,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        head = runtime.revisions.head(branch_id)
        runtime.candidates = await self.repository.load_candidates(
            session_id, source_version_id=head.version_id, include_selected=False)
        await self.bus.publish(session_id, {
            "type": event_type, "session_id": session_id, "seq": event_seq,
            "branch_id": branch_id, "head_version_id": info.head_version_id,
        })
        return event_seq

    async def _refresh_candidates(self, runtime: StudioRuntime) -> None:
        head = runtime.revisions.head(runtime.session["active_branch_id"])
        runtime.candidates = await self.repository.load_candidates(
            runtime.session["session_id"], source_version_id=head.version_id, include_selected=False)

    async def _update_session_row(self, runtime: StudioRuntime) -> None:
        await self.repository.update_session(
            runtime.session["session_id"], updated_at=runtime.session.get("updated_at", _now()),
            title=runtime.session["title"], status=runtime.session["status"],
            active_branch_id=runtime.session["active_branch_id"],
            active_version_id=runtime.session["active_version_id"],
            claim_level=runtime.session["claim_level"],
            warnings=runtime.session.get("warnings") or [],
            metadata=runtime.session.get("metadata") or {},
        )

    # --- serialization --------------------------------------------------------
    def _snapshot(self, runtime: StudioRuntime) -> dict:
        branch_id = runtime.session["active_branch_id"]
        head = runtime.revisions.head(branch_id)
        claimed = claim_envelope(runtime.session["claim_level"])
        return {
            "session_id": runtime.session["session_id"],
            "title": runtime.session["title"],
            "intention": runtime.session["intention"],
            "mode": runtime.session["mode"],
            "status": runtime.session["status"],
            "seed": runtime.session["seed"],
            "privacy_scope": runtime.session["privacy_scope"],
            **claimed,
            "capabilities": capability_envelope(),
            "active_branch_id": branch_id,
            "active_branch_name": runtime.revisions.branch(branch_id).name,
            "active_version_id": head.version_id,
            "scene": head.scene.to_dict(),
            "version": self._version_summary(head),
            "diff": head.diff,
            "branches": self._branches(runtime),
            "history": [self._version_summary(v) for v in runtime.revisions.history(branch_id)],
            "candidates": [self._candidate_payload(c) for c in runtime.candidates[:6]],
            "warnings": list(head.scene.metadata.get("warnings") or []),
            "has_undo": runtime.revisions.can_undo(branch_id),
            "has_redo": runtime.revisions.can_redo(branch_id),
            "last_event_seq": runtime.last_event_seq,
            "created_at": runtime.session["created_at"],
            "updated_at": runtime.session["updated_at"],
        }

    def _branches(self, runtime: StudioRuntime) -> list[StudioBranchSummaryRecord]:
        active = runtime.session["active_branch_id"]
        return [{**info.to_dict(), "is_active": info.branch_id == active}
                for info in runtime.revisions.branches]

    @staticmethod
    def _version_summary(version) -> StudioVersionSummaryRecord:
        return {
            "version_id": version.version_id,
            "number": version.number,
            "branch_id": version.branch_id,
            "parent_version_id": version.parent_version_id,
            "source": version.source,
            "label": version.label,
            "intention": version.intention,
            "claim_level": version.claim_level,
            "created_at": version.created_at,
            "content_hash": version.content_hash,
            "entity_count": len(version.scene.entities),
        }

    @staticmethod
    def _candidate_payload(candidate: StudioCandidateRecord) -> StudioCandidateRecord:
        return {
            "candidate_id": candidate["candidate_id"],
            "session_id": candidate.get("session_id"),
            "source_version_id": candidate.get("source_version_id"),
            "variant_index": candidate.get("variant_index", 0),
            "scene": candidate.get("scene"),
            "diff": candidate.get("diff") or {},
            "notes": candidate.get("notes") or [],
            "selected": bool(candidate.get("selected")),
            "created_at": candidate.get("created_at"),
        }

    @staticmethod
    def capabilities() -> dict:
        return {**capability_envelope(), **claim_envelope()}


studio_service = AnimusStudioService()

__all__ = [
    "AnimusStudioService", "StudioRuntime", "StudioError", "StudioNotFound",
    "StudioValidationError", "StudioConflict", "StudioArchived", "StudioPersistenceError",
    "studio_service",
]
