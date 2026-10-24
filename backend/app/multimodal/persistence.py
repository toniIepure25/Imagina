"""Synchronous SQLite repository for multimodal sessions (same database file as the app; schema from migration v013).

Recovery policy: a session found RUNNING after a restart is marked INTERRUPTED. ``recover_session`` deterministically
re-executes it up to the last persisted tick, verifies every decision hash against the database, and leaves the
controller PAUSED. Participant-facing feedback is never resumed automatically.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.storage.migrations.v013_multimodal_sessions import STATEMENTS

TERMINAL = {"COMPLETED", "TERMINATED"}


class MultimodalSessionRepository:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=None)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA busy_timeout = 5000")
        for stmt in STATEMENTS:
            self._conn.execute(stmt)

    def close(self) -> None:
        self._conn.close()

    def create_session(self, cfg, source_kinds: list[str]) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO mm_sessions (session_id, participant_pseudo_id, status, mode, policy, source_kinds,"
            " modality_config, experiment_params) VALUES (?,?,?,?,?,?,?,?)",
            (cfg.session_id, cfg.participant_pseudo_id, "RUNNING", cfg.mode, cfg.policy, json.dumps(source_kinds),
             json.dumps([m.value for m in cfg.modalities]), cfg.model_dump_json()))

    def record_tick(self, session_id: str, entry: dict, recovery_state: dict) -> None:
        d = entry["decision"]
        with self._conn:
            self._conn.execute("BEGIN")
            self._conn.execute(
                "INSERT OR REPLACE INTO mm_decisions VALUES (?,?,?,?,?,?,?,?)",
                (session_id, entry["tick"], entry["t"], d["controller_state"], int(d["delivered"]), d["hash"],
                 d["prev_hash"], json.dumps(d)))
            for f in d["safety_findings"]:
                self._conn.execute(
                    "INSERT INTO mm_safety_events (session_id, tick, t, code, severity, detail) VALUES (?,?,?,?,?,?)",
                    (session_id, entry["tick"], entry["t"], f["code"], f["severity"], f["detail"]))
            self._conn.execute(
                "INSERT OR REPLACE INTO mm_feedback_actions VALUES (?,?,?,?,?)",
                (session_id, entry["tick"], d["action_id"], int(entry["corridor"]["delivered"]),
                 json.dumps(entry["corridor"])))
            self._conn.execute(
                "UPDATE mm_sessions SET last_tick=?, last_t=?, recovery_state=?, updated_at=datetime('now') "
                "WHERE session_id=?", (entry["tick"], entry["t"], json.dumps(recovery_state), session_id))

    def record_calibration(self, session_id: str, profile: dict) -> int:
        row = self._conn.execute("SELECT COALESCE(MAX(version), 0) FROM mm_calibrations WHERE session_id=?",
                                 (session_id,)).fetchone()
        version = int(row[0]) + 1
        self._conn.execute("INSERT INTO mm_calibrations (session_id, version, profile) VALUES (?,?,?)",
                           (session_id, version, json.dumps(profile)))
        self._conn.execute("UPDATE mm_sessions SET calibration_version=? WHERE session_id=?", (version, session_id))
        return version

    def set_model_versions(self, session_id: str, versions: dict) -> None:
        self._conn.execute("UPDATE mm_sessions SET model_versions=? WHERE session_id=?",
                           (json.dumps(versions), session_id))

    def set_status(self, session_id: str, status: str) -> None:
        self._conn.execute("UPDATE mm_sessions SET status=?, updated_at=datetime('now') WHERE session_id=?",
                           (status, session_id))

    def session(self, session_id: str) -> dict | None:
        cur = self._conn.execute("SELECT * FROM mm_sessions WHERE session_id=?", (session_id,))
        row = cur.fetchone()
        if row is None:
            return None
        out = dict(zip([c[0] for c in cur.description], row))
        for k in ("source_kinds", "modality_config", "experiment_params", "model_versions", "recovery_state"):
            out[k] = json.loads(out[k])
        return out

    def list_sessions(self) -> list[dict]:
        cur = self._conn.execute("SELECT session_id, status, mode, policy, last_tick, last_t, updated_at "
                                 "FROM mm_sessions ORDER BY updated_at DESC")
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def decisions(self, session_id: str) -> list[dict]:
        rows = self._conn.execute("SELECT decision FROM mm_decisions WHERE session_id=? ORDER BY tick",
                                  (session_id,)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def safety_events(self, session_id: str) -> list[dict]:
        cur = self._conn.execute("SELECT tick, t, code, severity, detail FROM mm_safety_events WHERE session_id=? "
                                 "ORDER BY id", (session_id,))
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def mark_interrupted(self) -> list[str]:
        ids = [r[0] for r in self._conn.execute("SELECT session_id FROM mm_sessions WHERE status='RUNNING'")]
        for i in ids:
            self.set_status(i, "INTERRUPTED")
        return ids


def recover_session(repo: MultimodalSessionRepository, session_id: str):
    """Rebuild an interrupted session up to its last persisted tick (deterministic sources only), verify the
    decision hash chain against the database, then leave the controller PAUSED in shadow mode."""
    from app.multimodal.controller import ControllerState
    from app.multimodal.runtime import ClosedLoopSession, SessionConfig

    row = repo.session(session_id)
    if row is None:
        raise KeyError(session_id)
    if row["status"] in TERMINAL:
        raise ValueError(f"session {session_id} is {row['status']}; nothing to recover")
    if "REAL_SENSOR" in row["source_kinds"]:
        repo.set_status(session_id, "RECOVERED_PAUSED_NO_REPLAY")
        return None, {"session_id": session_id, "hash_chain_verified": None, "controller_state": "PAUSED",
                      "note": "real-sensor sessions cannot be re-executed; persisted decisions kept, operator must "
                              "start a new session"}
    cfg = SessionConfig.model_validate(row["experiment_params"])
    persisted = repo.decisions(session_id)
    original_mode = cfg.mode
    s = ClosedLoopSession(cfg, repo=None)
    s.start()
    mismatches = []
    for d in persisted:
        e = s.step()
        if e is None or e["decision"]["hash"] != d["hash"]:
            mismatches.append(d["tick"])
            break
    verified = not mismatches and len(s.log) == len(persisted)
    if s.controller.state not in (ControllerState.TERMINATED, ControllerState.PAUSED):
        s.controller.restore_state(ControllerState.PAUSED)
        s.controller.transitions.append({"t": s.t, "from": "RECOVERY", "to": "PAUSED",
                                         "reason": "recovered after restart; feedback not resumed"})
    s.cfg = cfg.model_copy(update={"mode": "shadow"})
    s.repo = repo
    repo.set_status(session_id, "RECOVERED_PAUSED" if verified else "RECOVERY_FAILED")
    return s, {"session_id": session_id, "replayed_ticks": len(s.log), "persisted_ticks": len(persisted),
               "hash_chain_verified": verified, "mismatch_ticks": mismatches, "original_mode": original_mode,
               "resumed_mode": "shadow", "controller_state": s.controller.state.value}
