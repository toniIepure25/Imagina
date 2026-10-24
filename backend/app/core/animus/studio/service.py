"""ANIMUS Studio product service (local-first, async).

The central loop is: intention -> candidate -> correction -> version -> regenerate -> converge -> save.
Every mutation produces an immutable version, and every candidate is generated procedurally from the
symbolic scene. There is no hidden target, no image model, and no neural-content claim.
"""
from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import logging
import math
import secrets
import statistics
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
from app.core.animus.studio.adaptive import action_payload
from app.core.animus.studio.bus import AnimusEventBus, animus_bus
from app.core.animus.studio.contrast import (
    CONTRAST_PROTOCOL_VERSION,
    DEFAULT_MAX_TRIALS,
    MAX_MAX_TRIALS,
    MIN_MAX_TRIALS,
    next_trial as next_contrast_trial,
    score_trial as score_contrast_trial,
    summarize_contrast,
    validate_reflection,
)
from app.core.animus.studio.claims import (
    StudioClaimError,
    capability_envelope,
    claim_envelope,
    enforce_studio_text,
)
from app.core.animus.studio.epistemic import (
    DEFAULT_MAX_PROBES,
    ERI_PROTOCOL_VERSION,
    ERI_RESPONSE_KIND,
    ERI_SCORING_VERSION,
    ERI_TASK_FAMILY,
    EpistemicBelief,
    build_probe_pool,
    build_reconstruction,
    information_gain,
    init_belief,
    score_probe,
    select_probe,
    summarize_interview,
    update_belief,
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
from app.core.animus.studio.observatory import (
    build_evidence,
    build_observatory,
    build_reliability,
)
from app.core.animus.studio.profile import (
    PROFILE_ID,
    apply_observation,
    calibration_from_stats,
    error_signature_from_trials,
    estimate_from_stats,
    profile_payload,
)
from app.core.animus.studio.protocols import (
    BUILTIN_PROTOCOLS,
    PROTOCOL_VERSION,
    protocol_summary,
    validate_protocol,
)
from app.core.animus.studio.reconstruction import RECONSTRUCTION_TASK_TYPES, SCORING_VERSION
from app.core.animus.studio.repository import StudioRepository
from app.core.animus.studio.tasks import TASK_SPECS, TASK_TYPES, build_task, score_response
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
        self._profile_lock = asyncio.Lock()

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

    # --- behavioural profile / practice --------------------------------------
    async def _epistemic_summary(self) -> dict:
        interviews = await self.repository.list_completed_interviews(100)
        records: list[dict[str, Any]] = []
        for interview in interviews:
            probes = await self.repository.list_interview_probes(interview["interview_id"])
            records.extend(self._interview_records(probes))
        summary = summarize_interview(records)
        return {
            "n_interviews": len(interviews),
            "n_probes": summary["n_probes"],
            "mean_brier": summary["mean_brier"],
            "overconfidence": summary["overconfidence"],
            "abstention_rate": summary["abstention_rate"],
            "mean_information_gain": summary["mean_information_gain"],
            "last_interview_id": (interviews[-1]["interview_id"]
                                  if interviews and summary["n_probes"] else None),
        }

    async def _contrast_summary(self) -> dict:
        contrasts = await self.repository.list_all_contrasts(100)
        thresholds: list[float] = []
        dprimes: list[float] = []
        brier_values: list[float] = []
        calibration_n = 0
        n_trials = 0
        n_completed = 0
        for contrast in contrasts:
            trials = await self.repository.list_contrast_trials(contrast["contrast_id"])
            n_trials += len(trials)
            if contrast.get("status") != "completed":
                continue
            n_completed += 1
            result = summarize_contrast(contrast, trials, bootstrap=0)
            if result.get("dprime") is not None:
                dprimes.append(float(result["dprime"]))
            calibration = result.get("calibration") or {}
            if calibration.get("brier") is not None:
                brier_values.append(float(calibration["brier"]))
                calibration_n += int(calibration.get("n") or 0)
            for item in (result.get("thresholds") or {}).values():
                if item.get("threshold") is not None and not item.get("censored"):
                    thresholds.append(float(item["threshold"]))
        return {
            "n_sessions": len(contrasts),
            "n_completed": n_completed,
            "n_trials": n_trials,
            "median_threshold": round(statistics.median(thresholds), 6) if thresholds else None,
            "mean_dprime": round(sum(dprimes) / len(dprimes), 6) if dprimes else None,
            "mean_brier": round(sum(brier_values) / len(brier_values), 6) if brier_values else None,
            "calibration_n": calibration_n,
            "last_contrast_id": contrasts[-1]["contrast_id"] if contrasts else None,
        }

    @staticmethod
    def _interview_records(trials: list[dict]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for trial in trials:
            response = trial.get("response") or {}
            outcome = trial.get("outcome") or {}
            stimulus = trial.get("stimulus") or {}
            records.append({
                "probe_id": stimulus.get("probe_id"),
                "probe_type": trial.get("probe_type") or stimulus.get("probe_type"),
                "choice": response.get("choice"),
                "correct": outcome.get("correct"),
                "brier": outcome.get("brier"),
                "confidence": trial.get("confidence"),
                "abstained": bool(response.get("abstained")),
                "information_gain": trial.get("information_gain"),
                "created_at": trial.get("created_at"),
            })
        return records

    async def _profile_snapshot(self) -> tuple[dict, dict[str, dict]]:
        profile = await self.repository.ensure_profile(PROFILE_ID)
        rows = await self.repository.load_profile_estimates(PROFILE_ID)
        stats = {name: row.get("stats") or {} for name, row in rows.items()}
        count = await self.repository.profile_trial_count(PROFILE_ID)
        recent = await self.repository.list_recent_trials(PROFILE_ID, 500)
        return profile_payload(
            profile, stats, trial_count=count,
            error_signature=error_signature_from_trials(recent),
            epistemic=await self._epistemic_summary(),
            contrast=await self._contrast_summary(),
        ), stats

    @staticmethod
    def _estimate_row(dimension: str, stats: dict[str, Any]) -> dict[str, Any]:
        summary = (calibration_from_stats(stats) if dimension == "calibration"
                   else estimate_from_stats(stats))
        return {
            "profile_id": PROFILE_ID, "dimension": dimension,
            "estimate": summary["estimate"], "uncertainty": summary["uncertainty"],
            "n": summary["n"], "reliability": summary["reliability"],
            "stats": stats, "updated_at": _now(),
        }

    async def profile(self) -> dict:
        async with self._profile_lock:
            payload, _ = await self._profile_snapshot()
            return payload

    async def reset_profile(self) -> dict:
        async with self._profile_lock:
            await self.repository.ensure_profile(PROFILE_ID)
            await self.repository.reset_profile(PROFILE_ID)
            payload, _ = await self._profile_snapshot()
            return payload

    async def list_protocols(self) -> dict:
        for protocol in BUILTIN_PROTOCOLS:
            validate_protocol(protocol)
            await self.repository.upsert_protocol(protocol)
        protocols = await self.repository.list_protocols()
        return {"protocol_version": PROTOCOL_VERSION,
                "protocols": [protocol_summary(protocol) for protocol in protocols]}

    async def practice_start(self, session_id: str, *, task_type: str | None = None,
                             difficulty: float | None = None) -> dict:
        async with self._locks.hold(session_id):
            runtime = await self._load(session_id)
            self._assert_mutable(runtime)
            async with self._profile_lock:
                profile, stats = await self._profile_snapshot()
            trial_count = await self.repository.profile_trial_count(
                PROFILE_ID, exclude_family=ERI_TASK_FAMILY)
            recent = [trial for trial in await self.repository.list_recent_trials(PROFILE_ID, 30)
                      if trial.get("task_family") != ERI_TASK_FAMILY][:10]
            scores = [float((trial.get("outcome") or {}).get("score") or 0.0) for trial in recent]
            last_difficulty = float(recent[-1].get("difficulty") or 0.45) if recent else 0.45
            action = action_payload(
                stats, trial_index=trial_count,
                seed=int(runtime.session["seed"]) + trial_count,
                recent_scores=scores,
                current_difficulty=last_difficulty,
            )
            if task_type is not None:
                if task_type not in TASK_TYPES:
                    raise StudioValidationError("unknown practice task type")
                action["task_type"] = task_type
                action["dimension"] = TASK_SPECS[task_type]["dimension"]
                action["reason"] = "explicit_task"
            if difficulty is not None:
                action["difficulty"] = max(0.0, min(1.0, float(difficulty)))
            head = runtime.revisions.head(runtime.session["active_branch_id"])
            task_seed = int(runtime.session["seed"]) + (trial_count + 1) * 7919
            try:
                task = build_task(head.scene, action["task_type"], seed=task_seed,
                                  difficulty=float(action["difficulty"]))
            except Exception as exc:  # noqa: BLE001 - task input boundary
                raise StudioValidationError(str(exc)) from exc
            return {
                "session_id": session_id,
                "source_version_id": head.version_id,
                "task": task.public_payload(),
                "adaptive": action,
                "profile": profile,
                "claim_level": claims.L1_BEHAVIORAL_ASSISTED,
            }

    async def practice_submit(self, session_id: str, *, task_id: str, task_type: str,
                              task_seed: int, difficulty: float, response: dict, confidence: float,
                              latency_ms: int, client_trial_id: str,
                              expected_version_id: str | None = None) -> dict:
        async with self._locks.hold(session_id):
            runtime = await self._load(session_id)
            self._assert_mutable(runtime)
            if not isinstance(client_trial_id, str) or not 3 <= len(client_trial_id) <= 80:
                raise StudioValidationError("client_trial_id must contain 3 to 80 characters")
            existing = await self.repository.get_trial_by_client_id(session_id, client_trial_id)
            if existing is not None:
                async with self._profile_lock:
                    profile, _ = await self._profile_snapshot()
                return {
                    "session_id": session_id, "trial": self._trial_payload(existing),
                    "idempotent": True, "next_task": None, "profile": profile,
                    "last_event_seq": runtime.last_event_seq,
                }
            self._assert_expected(runtime, expected_version_id)
            if not isinstance(task_type, str) or task_type not in TASK_TYPES:
                raise StudioValidationError("unknown practice task type")
            if not isinstance(response, dict):
                raise StudioValidationError("response must be an object")
            try:
                confidence = float(confidence)
                latency_ms = int(latency_ms)
                task_seed = int(task_seed)
                difficulty = float(difficulty)
            except (TypeError, ValueError) as exc:
                raise StudioValidationError("confidence, latency and task fields must be numbers") from exc
            if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
                raise StudioValidationError("confidence must be between 0 and 1")
            if not math.isfinite(difficulty) or not 0.0 <= difficulty <= 1.0:
                raise StudioValidationError("difficulty must be between 0 and 1")
            if not 0 <= latency_ms <= 1_800_000:
                raise StudioValidationError("latency is out of range")

            head = runtime.revisions.head(runtime.session["active_branch_id"])
            recent = [trial for trial in await self.repository.list_recent_trials(PROFILE_ID, 20)
                      if trial.get("task_family") != ERI_TASK_FAMILY][:5]
            try:
                task = build_task(head.scene, task_type, seed=task_seed,
                                  difficulty=difficulty)
                if task.task_id != task_id:
                    raise StudioValidationError(
                        "task_id does not match this scene and task; restart the trial")
                outcome = score_response(task, response)
            except StudioValidationError:
                raise
            except Exception as exc:  # noqa: BLE001 - task input boundary
                raise StudioValidationError(str(exc)) from exc

            trial_id = "tr_" + _digest(session_id, client_trial_id, task_type, task_seed)[:16]
            trial = {
                "trial_id": trial_id, "session_id": session_id, "profile_id": PROFILE_ID,
                "client_trial_id": client_trial_id, "task_type": task.task_type,
                "dimension": task.dimension, "difficulty": task.difficulty,
                "stimulus": task.public_payload(), "response": dict(response),
                "outcome": outcome, "confidence": confidence, "latency_ms": latency_ms,
                "created_at": _now(),
                "task_family": ("reconstruction" if task.task_type in RECONSTRUCTION_TASK_TYPES
                                else "legacy"),
                "response_kind": task.response_kind,
                "scoring_version": (SCORING_VERSION if task.task_type in RECONSTRUCTION_TASK_TYPES
                                    else "v1"),
                "error_profile": outcome.get("error_profile") or {},
            }
            async with self._profile_lock:
                _, stats = await self._profile_snapshot()
                score = float(outcome["score"])
                target_stats = apply_observation(
                    stats.get(task.dimension), score=score, confidence=confidence)
                updates = {task.dimension: target_stats}
                if task.dimension != "calibration":
                    updates["calibration"] = apply_observation(
                        stats.get("calibration"), score=score, confidence=confidence)
                for dimension, updated in updates.items():
                    stats[dimension] = updated

                try:
                    event_seq = await self.repository.record_trial_bundle(
                        trial=trial,
                        estimates=[self._estimate_row(name, value) for name, value in updates.items()],
                        event_type="studio.trial.recorded",
                        event_payload={
                            "trial_id": trial_id, "client_trial_id": client_trial_id,
                            "task_type": task.task_type, "dimension": task.dimension,
                            "score": score, "confidence": confidence,
                        },
                    )
                except Exception as exc:  # noqa: BLE001 - product error boundary
                    logger.exception("studio.trial.persist_failed", extra={"session_id": session_id})
                    raise StudioPersistenceError("The practice trial could not be saved locally") from exc
                if event_seq is None:
                    existing = await self.repository.get_trial_by_client_id(session_id, client_trial_id)
                    profile, _ = await self._profile_snapshot()
                    return {
                        "session_id": session_id,
                        "trial": self._trial_payload(existing) if existing else None,
                        "idempotent": True, "next_task": None, "profile": profile,
                        "last_event_seq": runtime.last_event_seq,
                    }
                runtime.last_event_seq = event_seq
                updated_profile, updated_stats = await self._profile_snapshot()
            next_index = await self.repository.profile_trial_count(
                PROFILE_ID, exclude_family=ERI_TASK_FAMILY)
            next_action = action_payload(
                updated_stats, trial_index=next_index,
                seed=int(runtime.session["seed"]) + next_index,
                recent_scores=[score] + [float((item.get("outcome") or {}).get("score") or 0.0)
                                         for item in recent],
                current_difficulty=task.difficulty,
            )
            next_seed = int(runtime.session["seed"]) + (next_index + 1) * 7919
            try:
                next_task = build_task(head.scene, next_action["task_type"], seed=next_seed,
                                       difficulty=float(next_action["difficulty"]))
                next_task_payload = next_task.public_payload()
            except Exception:  # noqa: BLE001 - the saved trial must remain usable
                logger.exception("studio.trial.next_task_failed",
                                 extra={"session_id": session_id, "trial_id": trial_id})
                next_task_payload = None
            await self.bus.publish(session_id, {
                "type": "studio.trial.recorded", "session_id": session_id, "seq": event_seq,
                "trial": self._trial_payload(trial), "profile": updated_profile,
            })
            return {
                "session_id": session_id,
                "trial": self._trial_payload(trial),
                "idempotent": False,
                "feedback": self._trial_feedback(task, outcome),
                "next_task": next_task_payload,
                "adaptive": next_action,
                "profile": updated_profile,
                "last_event_seq": event_seq,
            }

    # --- epistemic reconstruction interview -----------------------------------
    async def interview_start(self, session_id: str, *, max_probes: int = DEFAULT_MAX_PROBES,
                              form_id: str = "A", difficulty: float = 0.45,
                              expected_version_id: str | None = None) -> dict:
        max_probes = int(max_probes)
        if not 6 <= max_probes <= 20:
            raise StudioValidationError("max_probes must be between 6 and 20")
        form_id = str(form_id or "A").upper()
        if form_id not in ("A", "B", "C"):
            raise StudioValidationError("form_id must be A, B, or C")
        difficulty = float(difficulty)
        if not 0.0 <= difficulty <= 1.0:
            raise StudioValidationError("difficulty must be between 0 and 1")
        async with self._locks.hold(session_id):
            runtime = await self._load(session_id)
            self._assert_mutable(runtime)
            self._assert_expected(runtime, expected_version_id)
            head = runtime.revisions.head(runtime.session["active_branch_id"])
            interview_id = "eri_" + uuid.uuid4().hex[:16]
            seed = int(runtime.session["seed"]) + int(_digest(interview_id)[:8], 16)
            try:
                pool = build_probe_pool(head.scene, seed=seed, form_id=form_id,
                                        difficulty=difficulty)
            except SceneValidationError as exc:
                raise StudioValidationError(str(exc)) from exc
            if not pool:
                raise StudioValidationError("This scene has no probeable objects")
            probe = select_probe(pool, init_belief(pool))
            if probe is None:
                raise StudioValidationError("This scene has no probeable objects")
            record = {
                "interview_id": interview_id,
                "session_id": session_id,
                "source_version_id": head.version_id,
                "scene_hash": head.scene.content_hash(),
                "protocol_version": ERI_PROTOCOL_VERSION,
                "form_id": form_id,
                "seed": seed,
                "difficulty": round(difficulty, 3),
                "max_probes": max_probes,
                "status": "active",
                "created_at": _now(),
                "completed_at": None,
            }
            async with self._profile_lock:
                profile, _ = await self._profile_snapshot()
            try:
                event_seq = await self.repository.create_interview_bundle(
                    record,
                    event_payload={
                        "interview_id": interview_id,
                        "source_version_id": head.version_id,
                        "form_id": form_id,
                        "max_probes": max_probes,
                        "protocol_version": ERI_PROTOCOL_VERSION,
                    },
                )
            except Exception as exc:  # noqa: BLE001 - product error boundary
                logger.exception("studio.interview.start_failed", extra={"session_id": session_id})
                raise StudioPersistenceError("The interview could not be saved locally") from exc
            runtime.last_event_seq = event_seq
            await self.bus.publish(session_id, {
                "type": "studio.interview.started", "session_id": session_id,
                "seq": event_seq, "interview_id": interview_id,
            })
            return {
                "session_id": session_id,
                "interview": self._interview_payload(record, probe_count=0),
                "probe": probe.public_payload(),
                "profile": profile,
                "claim_level": claims.L1_BEHAVIORAL_ASSISTED,
            }

    async def interview_submit(self, session_id: str, interview_id: str, *,
                               probe_id: str, task_id: str, choice: str, confidence: float,
                               abstained: bool, latency_ms: int, client_trial_id: str,
                               expected_version_id: str | None = None) -> dict:
        async with self._locks.hold(session_id):
            runtime = await self._load(session_id)
            self._assert_mutable(runtime)
            existing = await self.repository.get_trial_by_client_id(session_id, client_trial_id)
            if existing is not None:
                if existing.get("interview_id") != interview_id:
                    raise StudioValidationError(
                        "client_trial_id belongs to a different interview")
                interview = await self.repository.get_interview(interview_id)
                if interview is None:
                    raise StudioNotFound(f"unknown interview {interview_id!r}")
                return await self._interview_resume(
                    runtime, interview, existing, runtime.last_event_seq)
            interview = await self.repository.get_interview(interview_id)
            if interview is None or interview.get("session_id") != session_id:
                raise StudioNotFound(f"unknown interview {interview_id!r}")
            if interview.get("status") != "active":
                raise StudioConflict("This interview is already complete")
            self._assert_expected(runtime, expected_version_id)
            head = runtime.revisions.head(runtime.session["active_branch_id"])
            if (head.version_id != interview["source_version_id"]
                    or head.scene.content_hash() != interview["scene_hash"]):
                raise StudioConflict("The scene changed since this interview started")
            try:
                source = runtime.revisions.version(interview["source_version_id"]).scene
                pool = build_probe_pool(
                    source, seed=int(interview["seed"]), form_id=interview["form_id"],
                    difficulty=float(interview.get("difficulty") or 0.45),
                )
            except (SceneValidationError, KeyError) as exc:
                raise StudioConflict("The interview scene is no longer available") from exc
            by_id = {item.probe_id: item for item in pool}
            probe = by_id.get(probe_id)
            if probe is None or probe.task_id != task_id:
                raise StudioValidationError("The probe is not valid for this interview")
            if abstained:
                choice = ""
            elif choice not in {option["id"] for option in probe.options}:
                raise StudioValidationError("choice is not one of the probe options")
            confidence = float(confidence)
            if not 0.5 <= confidence <= 1.0:
                raise StudioValidationError("confidence must be between 0.5 and 1.0")
            latency_ms = max(0, min(int(latency_ms), 1_800_000))
            previous = await self.repository.list_interview_probes(interview_id)
            if len(previous) >= int(interview["max_probes"]):
                raise StudioConflict("This interview has already reached its probe limit")
            if any((trial.get("stimulus") or {}).get("probe_id") == probe.probe_id
                   for trial in previous):
                raise StudioValidationError("This probe has already been answered")
            try:
                belief = self._belief_from_trials(pool, previous)
            except (SceneValidationError, ValueError) as exc:
                raise StudioCorruptState("The interview belief history is unreadable") from exc
            before = belief.probability(probe.variable_id)
            try:
                outcome = score_probe(probe, choice=choice, confidence=confidence,
                                      abstained=abstained)
                updated_belief = update_belief(
                    belief, probe, choice=choice, confidence=confidence, abstained=abstained)
            except (SceneValidationError, ValueError) as exc:
                raise StudioValidationError(str(exc)) from exc
            after = updated_belief.probability(probe.variable_id)
            gain = information_gain(before, after)
            trial = {
                "trial_id": "trl_" + uuid.uuid4().hex[:16],
                "session_id": session_id,
                "profile_id": PROFILE_ID,
                "protocol_run_id": None,
                "client_trial_id": client_trial_id,
                "task_type": probe.task_type,
                "dimension": probe.dimension,
                "difficulty": probe.difficulty,
                "stimulus": probe.public_payload(),
                "response": {
                    "choice": choice,
                    "confidence": confidence,
                    "abstained": bool(abstained),
                },
                "outcome": {
                    **outcome,
                    "probe_type": probe.probe_type,
                    "information_gain": gain,
                },
                "error_profile": {
                    "epistemic_n": 1,
                    "brier": outcome.get("brier"),
                    "correct": outcome.get("correct"),
                    "abstained": bool(abstained),
                },
                "task_family": ERI_TASK_FAMILY,
                "response_kind": ERI_RESPONSE_KIND,
                "scoring_version": ERI_SCORING_VERSION,
                "interview_id": interview_id,
                "probe_index": len(previous),
                "probe_type": probe.probe_type,
                "belief": updated_belief.to_dict(),
                "information_gain": gain,
                "confidence": confidence,
                "latency_ms": latency_ms,
                "created_at": _now(),
            }
            remaining = int(interview["max_probes"]) - (len(previous) + 1)
            next_probe = (select_probe(pool, updated_belief)
                          if remaining > 0 else None)
            completed = next_probe is None
            try:
                event_seq = await self.repository.record_trial_bundle(
                    trial=trial,
                    estimates=[],
                    event_type="studio.interview.probe_recorded",
                    event_payload={
                        "interview_id": interview_id,
                        "probe_id": probe.probe_id,
                        "probe_index": len(previous),
                        "abstained": bool(abstained),
                        "information_gain": gain,
                    },
                    complete_interview_id=interview_id if completed else None,
                )
            except Exception as exc:  # noqa: BLE001 - product error boundary
                logger.exception("studio.interview.probe_failed", extra={"session_id": session_id})
                raise StudioPersistenceError("The interview probe could not be saved locally") from exc
            if event_seq is None:
                existing = await self.repository.get_trial_by_client_id(session_id, client_trial_id)
                if existing is None:
                    raise StudioPersistenceError(
                        "The probe was not persisted and no matching trial exists")
                return await self._interview_resume(
                    runtime, interview, existing, runtime.last_event_seq)
            runtime.last_event_seq = event_seq
            async with self._profile_lock:
                updated_profile, _ = await self._profile_snapshot()
            reconstruction = None
            if completed:
                reconstruction = build_reconstruction(
                    updated_belief, pool, self._interview_records(previous + [trial]))
            await self.bus.publish(session_id, {
                "type": "studio.interview.probe_recorded", "session_id": session_id,
                "seq": event_seq, "interview_id": interview_id,
                "trial": self._trial_payload(trial),
            })
            return {
                "session_id": session_id,
                "interview": self._interview_payload(
                    {**interview, "status": "completed" if completed else "active",
                     "completed_at": trial["created_at"] if completed else None},
                    probe_count=len(previous) + 1,
                ),
                "trial": self._trial_payload(trial),
                "idempotent": False,
                "feedback": self._epistemic_feedback(bool(abstained)),
                "next_probe": next_probe.public_payload() if next_probe else None,
                "reconstruction": reconstruction,
                "profile": updated_profile,
                "last_event_seq": event_seq,
            }

    async def interview_summary(self, interview_id: str) -> dict:
        interview = await self.repository.get_interview(interview_id)
        if interview is None:
            raise StudioNotFound(f"unknown interview {interview_id!r}")
        runtime = await self._load(interview["session_id"])
        try:
            source = runtime.revisions.version(interview["source_version_id"]).scene
            pool = build_probe_pool(
                source, seed=int(interview["seed"]), form_id=interview["form_id"],
                difficulty=float(interview.get("difficulty") or 0.45),
            )
            trials = await self.repository.list_interview_probes(interview_id)
            belief = self._belief_from_trials(pool, trials)
        except (SceneValidationError, KeyError, ValueError) as exc:
            raise StudioCorruptState("The interview history is unreadable") from exc
        reconstruction = build_reconstruction(
            belief, pool, self._interview_records(trials))
        async with self._profile_lock:
            profile, _ = await self._profile_snapshot()
        return {
            "session_id": interview["session_id"],
            "interview": self._interview_payload(interview, probe_count=len(trials)),
            "reconstruction": reconstruction,
            "profile": profile,
            "claim_level": claims.L1_BEHAVIORAL_ASSISTED,
        }

    async def list_interviews(self, session_id: str) -> dict:
        await self._load(session_id)
        interviews = await self.repository.list_interviews(session_id, 50)
        items = []
        for interview in interviews:
            count = await self.repository.interview_probe_count(interview["interview_id"])
            items.append(self._interview_payload(interview, probe_count=count))
        return {"session_id": session_id, "interviews": items}

    async def contrast_start(self, session_id: str, *, max_trials: int = DEFAULT_MAX_TRIALS,
                             form_id: str = "A", difficulty: float = 0.45,
                             occasion: str = "baseline", delay_hours: float | None = None,
                             source_version_id: str | None = None,
                             expected_version_id: str | None = None) -> dict:
        max_trials = int(max_trials)
        if not MIN_MAX_TRIALS <= max_trials <= MAX_MAX_TRIALS:
            raise StudioValidationError(
                f"max_trials must be between {MIN_MAX_TRIALS} and {MAX_MAX_TRIALS}")
        form_id = str(form_id or "A").upper()
        if form_id not in ("A", "B", "C"):
            raise StudioValidationError("form_id must be A, B, or C")
        occasion = str(occasion or "baseline")
        if occasion not in ("baseline", "follow_up"):
            raise StudioValidationError("occasion must be baseline or follow_up")
        difficulty = float(difficulty)
        if not math.isfinite(difficulty) or not 0.0 <= difficulty <= 1.0:
            raise StudioValidationError("difficulty must be between 0 and 1")
        if delay_hours is not None:
            delay_hours = float(delay_hours)
            if not math.isfinite(delay_hours) or not 0.0 <= delay_hours <= 720.0:
                raise StudioValidationError("delay_hours must be between 0 and 720")
        async with self._locks.hold(session_id):
            runtime = await self._load(session_id)
            self._assert_mutable(runtime)
            self._assert_expected(runtime, expected_version_id)
            if source_version_id:
                try:
                    source = runtime.revisions.version(source_version_id)
                except KeyError as exc:
                    raise StudioNotFound("The source version is not available") from exc
            else:
                source = runtime.revisions.head(runtime.session["active_branch_id"])
            scene = source.scene
            contrast_id = "ct_" + uuid.uuid4().hex[:16]
            seed = secrets.randbits(63)
            record = {
                "contrast_id": contrast_id,
                "session_id": session_id,
                "source_version_id": source.version_id,
                "scene_hash": scene.content_hash(),
                "protocol_version": CONTRAST_PROTOCOL_VERSION,
                "form_id": form_id,
                "seed": seed,
                "max_trials": max_trials,
                "difficulty": round(difficulty, 3),
                "occasion": occasion,
                "delay_hours": delay_hours,
                "reflection": {},
                "status": "active",
                "created_at": _now(),
                "completed_at": None,
            }
            try:
                pair = next_contrast_trial(scene, record, [])
            except SceneValidationError as exc:
                raise StudioValidationError(str(exc)) from exc
            if pair is None:
                raise StudioValidationError(
                    "This scene has no variation that can be used for a contrast trial")
            async with self._profile_lock:
                profile, _ = await self._profile_snapshot()
            try:
                event_seq = await self.repository.create_contrast_bundle(
                    record,
                    event_payload={
                        "contrast_id": contrast_id,
                        "source_version_id": source.version_id,
                        "form_id": form_id,
                        "max_trials": max_trials,
                        "occasion": occasion,
                        "protocol_version": CONTRAST_PROTOCOL_VERSION,
                    },
                )
            except Exception as exc:  # noqa: BLE001 - product error boundary
                logger.exception("studio.contrast.start_failed", extra={"session_id": session_id})
                raise StudioPersistenceError("The contrast session could not be saved locally") from exc
            runtime.last_event_seq = event_seq
            await self.bus.publish(session_id, {
                "type": "studio.contrast.started", "session_id": session_id,
                "seq": event_seq, "contrast_id": contrast_id,
            })
            return {
                "session_id": session_id,
                "contrast": self._contrast_payload(record, trial_count=0),
                "trial": pair.public_payload(),
                "profile": profile,
                "claim_level": claims.L1_BEHAVIORAL_ASSISTED,
            }

    async def contrast_submit(self, session_id: str, contrast_id: str, *,
                              trial_id: str, task_id: str, choice: str, confidence: float,
                              abstained: bool, latency_ms: int, client_trial_id: str,
                              expected_version_id: str | None = None) -> dict:
        async with self._locks.hold(session_id):
            runtime = await self._load(session_id)
            self._assert_mutable(runtime)
            existing = await self.repository.get_contrast_trial_by_client_id(
                contrast_id, client_trial_id)
            if existing is not None:
                if existing.get("task_id") != task_id:
                    raise StudioConflict("client_trial_id belongs to a different contrast trial")
                contrast = await self.repository.get_contrast(contrast_id)
                if contrast is None or contrast.get("session_id") != session_id:
                    raise StudioNotFound(f"unknown contrast session {contrast_id!r}")
                return await self._contrast_resume(runtime, contrast, existing,
                                                   runtime.last_event_seq)
            contrast = await self.repository.get_contrast(contrast_id)
            if contrast is None or contrast.get("session_id") != session_id:
                raise StudioNotFound(f"unknown contrast session {contrast_id!r}")
            if contrast.get("status") != "active":
                raise StudioConflict("This contrast session is already complete")
            if expected_version_id:
                head = runtime.revisions.head(runtime.session["active_branch_id"])
                if expected_version_id not in (contrast["source_version_id"], head.version_id):
                    raise StudioConflict(
                        "The scene changed since this view was loaded; refresh and try again")
            try:
                scene = runtime.revisions.version(contrast["source_version_id"]).scene
            except KeyError as exc:
                raise StudioConflict("The contrast scene is no longer available") from exc
            trials = await self.repository.list_contrast_trials(contrast_id)
            if len(trials) >= int(contrast["max_trials"]):
                raise StudioConflict("This contrast session has reached its trial limit")
            try:
                pair = next_contrast_trial(scene, contrast, trials)
            except SceneValidationError as exc:
                raise StudioCorruptState("The contrast history is unreadable") from exc
            if pair is None or pair.trial_id != trial_id or pair.task_id != task_id:
                raise StudioValidationError("The contrast trial is not valid for this session")
            if abstained:
                choice = ""
            elif choice not in ("a", "b"):
                raise StudioValidationError("choice must be 'a' or 'b'")
            confidence = float(confidence)
            if not math.isfinite(confidence) or not 0.5 <= confidence <= 1.0:
                raise StudioValidationError("confidence must be between 0.5 and 1.0")
            latency_ms = max(0, min(int(latency_ms), 1_800_000))
            try:
                outcome = score_contrast_trial(
                    pair, choice=choice, confidence=confidence, abstained=abstained)
            except (ValueError, SceneValidationError) as exc:
                raise StudioValidationError(str(exc)) from exc
            trial = self._contrast_trial_record(
                pair, contrast_id=contrast_id, client_trial_id=client_trial_id,
                choice=outcome["choice"], confidence=outcome["confidence"], abstained=abstained,
                latency_ms=latency_ms, created_at=_now(), outcome=outcome,
            )
            try:
                next_pair = next_contrast_trial(scene, contrast, trials + [trial])
            except SceneValidationError as exc:
                raise StudioCorruptState("The contrast history is unreadable") from exc
            completed = next_pair is None
            try:
                event_seq = await self.repository.record_contrast_trial_bundle(
                    contrast_id=contrast_id, trial=trial,
                    event_type="studio.contrast.trial_recorded",
                    event_payload={
                        "session_id": session_id,
                        "contrast_id": contrast_id,
                        "trial_index": trial["trial_index"],
                        "completed": completed,
                    },
                    complete=completed,
                )
            except Exception as exc:  # noqa: BLE001 - product error boundary
                logger.exception("studio.contrast.trial_failed", extra={"session_id": session_id})
                raise StudioPersistenceError("The contrast trial could not be saved locally") from exc
            if event_seq is None:
                existing = await self.repository.get_contrast_trial_by_client_id(
                    contrast_id, client_trial_id)
                if existing is None:
                    raise StudioPersistenceError(
                        "The contrast trial was not persisted and no matching trial exists")
                return await self._contrast_resume(runtime, contrast, existing,
                                                   runtime.last_event_seq)
            runtime.last_event_seq = event_seq
            async with self._profile_lock:
                profile, _ = await self._profile_snapshot()
            result = (summarize_contrast(contrast, trials + [trial], bootstrap=120)
                      if completed else None)
            updated = {
                **contrast,
                "status": "completed" if completed else "active",
                "completed_at": trial["created_at"] if completed else None,
            }
            await self.bus.publish(session_id, {
                "type": "studio.contrast.trial_recorded", "session_id": session_id,
                "seq": event_seq, "contrast_id": contrast_id,
                "trial_index": trial["trial_index"],
            })
            return {
                "session_id": session_id,
                "contrast": self._contrast_payload(updated, trial_count=len(trials) + 1),
                "trial": self._contrast_trial_payload(trial),
                "recorded": True,
                "next_trial": next_pair.public_payload() if next_pair else None,
                "result": result,
                "profile": profile,
                "last_event_seq": event_seq,
            }

    async def contrast_summary(self, contrast_id: str) -> dict:
        contrast = await self.repository.get_contrast(contrast_id)
        if contrast is None:
            raise StudioNotFound(f"unknown contrast session {contrast_id!r}")
        trials = await self.repository.list_contrast_trials(contrast_id)
        result = summarize_contrast(contrast, trials, bootstrap=120)
        async with self._profile_lock:
            profile, _ = await self._profile_snapshot()
        return {
            "session_id": contrast["session_id"],
            "contrast": self._contrast_payload(contrast, trial_count=len(trials)),
            "result": result,
            "profile": profile,
            "claim_level": claims.L1_BEHAVIORAL_ASSISTED,
        }

    async def list_contrasts(self, session_id: str) -> dict:
        await self._load(session_id)
        contrasts = await self.repository.list_contrasts(session_id, 50)
        items = []
        for contrast in contrasts:
            trials = await self.repository.list_contrast_trials(contrast["contrast_id"])
            items.append(self._contrast_payload(contrast, trial_count=len(trials)))
        return {"session_id": session_id, "contrasts": items}

    async def observatory(self, session_id: str) -> dict:
        runtime = await self._load(session_id)
        interviews = await self.repository.list_interviews(session_id, 50)
        completed_interviews = [item for item in interviews if item.get("status") == "completed"]
        contrasts = await self.repository.list_contrasts(session_id, 50)
        completed_session_contrasts = [
            item for item in contrasts if item.get("status") == "completed"]
        anchor = completed_session_contrasts[-1] if completed_session_contrasts else None
        if anchor is not None:
            source_version_id = anchor["source_version_id"]
            scene_hash = anchor["scene_hash"]
            try:
                scene = runtime.revisions.version(source_version_id).scene
            except KeyError as exc:
                raise StudioConflict("The contrast scene is no longer available") from exc
            interview = next(
                (item for item in reversed(completed_interviews)
                 if item.get("scene_hash") == scene_hash),
                None,
            )
        elif completed_interviews:
            interview = completed_interviews[-1]
            source_version_id = interview["source_version_id"]
            scene_hash = interview["scene_hash"]
            try:
                scene = runtime.revisions.version(source_version_id).scene
            except KeyError as exc:
                raise StudioConflict("The interview scene is no longer available") from exc
        else:
            interview = None
            head = runtime.revisions.head(runtime.session["active_branch_id"])
            source_version_id = head.version_id
            scene_hash = head.scene.content_hash()
            scene = head.scene
        if interview is not None:
            try:
                pool = build_probe_pool(
                    scene, seed=int(interview["seed"]), form_id=interview["form_id"],
                    difficulty=float(interview.get("difficulty") or 0.45),
                )
                trials = await self.repository.list_interview_probes(interview["interview_id"])
                belief = self._belief_from_trials(pool, trials)
                records = self._interview_records(trials)
                reconstruction = build_reconstruction(belief, pool, records)
                evidence = build_evidence(pool, belief, records)
            except (SceneValidationError, KeyError, ValueError) as exc:
                raise StudioCorruptState("The interview history is unreadable") from exc
        else:
            reconstruction = {
                "objects": [], "relations": [],
                "uncertainty": {"object_entropy": 0.0, "relation_entropy": 0.0},
                "scores": {}, "protocol_version": ERI_PROTOCOL_VERSION,
                "scoring_version": ERI_SCORING_VERSION,
            }
            evidence = []
        completed_contrasts = await self.repository.list_completed_contrasts_for_scene(
            scene_hash, 50)
        items: list[dict] = []
        for contrast in completed_contrasts:
            trials = await self.repository.list_contrast_trials(contrast["contrast_id"])
            items.append({
                **contrast,
                "result": summarize_contrast(contrast, trials, bootstrap=0),
            })
        own_items = [item for item in items if item.get("session_id") == session_id]
        discrimination = own_items[-1]["result"] if own_items else {
            "status": "unavailable",
            "reason": "no completed contrast session for this scene",
        }
        reliability = build_reliability(items)
        payload = build_observatory(
            session_id=session_id, source_version_id=source_version_id,
            scene_hash=scene_hash, reconstruction=reconstruction, evidence=evidence,
            discrimination=discrimination, reliability=reliability,
        )
        payload["claim_level"] = claims.L1_BEHAVIORAL_ASSISTED
        return payload

    async def contrast_reflection(self, contrast_id: str, *, strategies: list[str],
                                  notes: str = "") -> dict:
        contrast = await self.repository.get_contrast(contrast_id)
        if contrast is None:
            raise StudioNotFound(f"unknown contrast session {contrast_id!r}")
        if contrast.get("status") != "completed":
            raise StudioConflict("Reflection is available only after the contrast session")
        try:
            cleaned = validate_reflection(strategies)
        except ValueError as exc:
            raise StudioValidationError(str(exc)) from exc
        if not isinstance(notes, str) or len(notes) > 500:
            raise StudioValidationError("notes may contain at most 500 characters")
        reflection = {"strategies": cleaned, "notes": notes}
        await self.repository.set_contrast_reflection(contrast_id, reflection)
        return await self.contrast_summary(contrast_id)

    @staticmethod
    def _contrast_payload(contrast: dict, *, trial_count: int) -> dict:
        return {
            "contrast_id": contrast["contrast_id"],
            "session_id": contrast["session_id"],
            "source_version_id": contrast["source_version_id"],
            "protocol_version": contrast.get("protocol_version") or CONTRAST_PROTOCOL_VERSION,
            "form_id": contrast.get("form_id") or "A",
            "max_trials": int(contrast.get("max_trials") or DEFAULT_MAX_TRIALS),
            "difficulty": contrast.get("difficulty", 0.45),
            "occasion": contrast.get("occasion") or "baseline",
            "delay_hours": contrast.get("delay_hours"),
            "status": contrast.get("status") or "active",
            "trial_count": int(trial_count),
            "reflection": contrast.get("reflection") or {},
            "created_at": contrast.get("created_at"),
            "completed_at": contrast.get("completed_at"),
        }

    @staticmethod
    def _contrast_trial_record(pair, *, contrast_id: str, client_trial_id: str, choice: str,
                               confidence: float, abstained: bool, latency_ms: int,
                               created_at: str, outcome: dict | None = None) -> dict:
        return {
            "trial_id": pair.trial_id,
            "contrast_id": contrast_id,
            "trial_index": pair.trial_index,
            "task_id": pair.task_id,
            "feature_type": pair.feature_type,
            "feature_key": pair.feature_key,
            "delta": pair.delta,
            "staircase_level": pair.staircase_level,
            "target_side": pair.target_side,
            "chosen_option_id": choice if not abstained else None,
            "correct": (outcome or {}).get("correct"),
            "confidence": confidence,
            "abstained": bool(abstained),
            "latency_ms": latency_ms,
            "client_trial_id": client_trial_id,
            "created_at": created_at,
        }

    @staticmethod
    def _contrast_trial_payload(trial: dict) -> dict:
        return {
            "trial_id": trial.get("trial_id"),
            "task_id": trial.get("task_id"),
            "trial_index": trial.get("trial_index"),
            "recorded": True,
        }

    async def _contrast_resume(self, runtime, contrast: dict, existing: dict,
                               event_seq: int | None) -> dict:
        trials = await self.repository.list_contrast_trials(contrast["contrast_id"])
        result = (summarize_contrast(contrast, trials, bootstrap=120)
                  if contrast.get("status") == "completed" else None)
        next_pair = None
        if contrast.get("status") == "active":
            try:
                scene = runtime.revisions.version(contrast["source_version_id"]).scene
                next_pair = next_contrast_trial(scene, contrast, trials)
            except KeyError as exc:
                raise StudioConflict("The contrast scene is no longer available") from exc
            except SceneValidationError as exc:
                raise StudioCorruptState("The contrast history is unreadable") from exc
        async with self._profile_lock:
            profile, _ = await self._profile_snapshot()
        return {
            "session_id": contrast["session_id"],
            "contrast": self._contrast_payload(contrast, trial_count=len(trials)),
            "trial": self._contrast_trial_payload(existing),
            "recorded": True,
            "idempotent": True,
            "next_trial": next_pair.public_payload() if next_pair else None,
            "result": result,
            "profile": profile,
            "last_event_seq": event_seq if event_seq is not None else runtime.last_event_seq,
        }

    @staticmethod
    def _interview_payload(interview: dict, *, probe_count: int) -> dict:
        return {
            "interview_id": interview["interview_id"],
            "session_id": interview["session_id"],
            "source_version_id": interview["source_version_id"],
            "protocol_version": interview.get("protocol_version") or ERI_PROTOCOL_VERSION,
            "form_id": interview.get("form_id") or "A",
            "difficulty": interview.get("difficulty", 0.45),
            "status": interview.get("status") or "active",
            "probe_count": int(probe_count),
            "max_probes": int(interview.get("max_probes") or DEFAULT_MAX_PROBES),
            "created_at": interview.get("created_at"),
            "completed_at": interview.get("completed_at"),
        }

    @staticmethod
    def _belief_from_trials(pool, trials: list[dict]) -> EpistemicBelief:
        belief = init_belief(tuple(pool))
        by_id = {probe.probe_id: probe for probe in pool}
        for trial in trials:
            stimulus = trial.get("stimulus") or {}
            probe = by_id.get(stimulus.get("probe_id"))
            if probe is None:
                raise ValueError("stored probe is not in the interview pool")
            response = trial.get("response") or {}
            belief = update_belief(
                belief, probe,
                choice=str(response.get("choice") or ""),
                confidence=float(response.get("confidence") or 0.5),
                abstained=bool(response.get("abstained")),
            )
        return belief

    async def _interview_resume(self, runtime, interview: dict, existing: dict,
                                event_seq: int | None) -> dict:
        """Rebuild the deterministic interview state for an idempotent retry."""
        trials = await self.repository.list_interview_probes(interview["interview_id"])
        reconstruction = None
        next_probe = None
        try:
            source = runtime.revisions.version(interview["source_version_id"]).scene
            pool = build_probe_pool(
                source, seed=int(interview["seed"]), form_id=interview["form_id"],
                difficulty=float(interview.get("difficulty") or 0.45),
            )
            belief = self._belief_from_trials(pool, trials)
            if interview.get("status") == "completed":
                reconstruction = build_reconstruction(
                    belief, pool, self._interview_records(trials))
            else:
                selected = select_probe(pool, belief)
                next_probe = selected.public_payload() if selected else None
        except (SceneValidationError, KeyError, ValueError):
            logger.warning("studio.interview.resume_state_unavailable",
                           extra={"interview_id": interview["interview_id"]})
        async with self._profile_lock:
            profile, _ = await self._profile_snapshot()
        return {
            "session_id": interview["session_id"],
            "interview": self._interview_payload(interview, probe_count=len(trials)),
            "trial": self._trial_payload(existing),
            "idempotent": True,
            "feedback": self._epistemic_feedback(
                bool((existing.get("response") or {}).get("abstained")),
            ),
            "next_probe": next_probe,
            "reconstruction": reconstruction,
            "profile": profile,
            "last_event_seq": event_seq if event_seq is not None else runtime.last_event_seq,
        }

    @staticmethod
    def _epistemic_feedback(abstained: bool) -> dict:
        if abstained:
            message = "Recorded as uncertain. An abstention is data, not a failure."
        else:
            message = "Recorded. The next probe is selected from the updated belief."
        return {
            "correct": None,
            "correct_option_id": None,
            "correct_option_label": "",
            "error_profile": {},
            "message": message,
        }

    @staticmethod
    def _trial_payload(trial: dict) -> dict:
        return {
            "trial_id": trial.get("trial_id"),
            "session_id": trial.get("session_id"),
            "client_trial_id": trial.get("client_trial_id"),
            "task_type": trial.get("task_type"),
            "dimension": trial.get("dimension"),
            "difficulty": trial.get("difficulty"),
            "task_family": trial.get("task_family"),
            "response_kind": trial.get("response_kind"),
            "scoring_version": trial.get("scoring_version"),
            "stimulus": trial.get("stimulus") or {},
            "response": trial.get("response") or {},
            "outcome": ({} if trial.get("task_family") == ERI_TASK_FAMILY
                        else trial.get("outcome") or {}),
            "error_profile": ({} if trial.get("task_family") == ERI_TASK_FAMILY
                              else trial.get("error_profile") or {}),
            "interview_id": trial.get("interview_id"),
            "probe_index": trial.get("probe_index"),
            "probe_type": trial.get("probe_type"),
            "information_gain": trial.get("information_gain"),
            "confidence": trial.get("confidence"),
            "latency_ms": trial.get("latency_ms"),
            "created_at": trial.get("created_at"),
        }

    @staticmethod
    def _trial_feedback(task, outcome: dict) -> dict:
        error_profile = outcome.get("error_profile") or {}
        if task.response_kind != "option":
            score = float(outcome.get("score") or 0.0)
            if task.response_kind == "token_selection":
                message = (
                    f"Reconstruction score {round(score * 100)}%. "
                    f"Omissions: {int(error_profile.get('omissions') or 0)}; "
                    f"intrusions: {int(error_profile.get('intrusions') or 0)}. "
                    "An error is evidence, not a failure."
                )
            else:
                message = (
                    f"Layout score {round(score * 100)}%. "
                    f"Mean spatial error: {error_profile.get('mean_spatial_error')}. "
                    "An error is evidence, not a failure."
                )
            return {
                "correct": bool(outcome.get("correct")),
                "correct_option_id": None,
                "correct_option_label": "",
                "error_profile": error_profile,
                "message": message,
            }
        correct_label = next(
            (option.get("label") for option in task.options
             if option.get("id") == outcome.get("correct_option_id")), "")
        return {
            "correct": bool(outcome.get("correct")),
            "correct_option_id": outcome.get("correct_option_id"),
            "correct_option_label": correct_label,
            "error_profile": error_profile,
            "message": ("Correct. This trial adds evidence to your behavioural profile."
                        if outcome.get("correct") else
                        "Not quite. The correct option is shown above; an error is evidence, not a failure."),
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
