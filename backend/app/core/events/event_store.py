"""IMAGINA Event Store — JSONL persistence with deterministic replay."""

import json
import os
from datetime import datetime, timezone
from typing import Optional

SESSIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "..", "..", "data", "imagina", "sessions")


def _session_path(session_id: str) -> str:
    return os.path.join(SESSIONS_DIR, session_id)


def append_event(session_id: str, event: dict) -> str:
    """Append one event to the session JSONL file. Returns the event file path."""
    path = _session_path(session_id)
    os.makedirs(path, exist_ok=True)
    events_path = os.path.join(path, "events.jsonl")
    if "timestamp" not in event:
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(events_path, "a") as f:
        f.write(json.dumps(event, default=str) + "\n")
    return events_path


def load_events(session_id: str) -> list[dict]:
    """Load all events from a session JSONL file."""
    path = os.path.join(_session_path(session_id), "events.jsonl")
    if not os.path.exists(path):
        return []
    events = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events


def replay_events(session_id: str) -> list[dict]:
    """Load events in append order (deterministic replay)."""
    return load_events(session_id)


def write_session_manifest(session_id: str, config: dict):
    """Write session manifest with config metadata."""
    path = _session_path(session_id)
    os.makedirs(path, exist_ok=True)
    manifest = {
        "session_id": session_id,
        "config": config,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "event_count": len(load_events(session_id)),
    }
    with open(os.path.join(path, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2, default=str)


def list_sessions(user_id: Optional[str] = None) -> list[dict]:
    """List all session directories with their manifests."""
    if not os.path.isdir(SESSIONS_DIR):
        return []
    sessions = []
    for sid in sorted(os.listdir(SESSIONS_DIR)):
        mp = os.path.join(SESSIONS_DIR, sid, "manifest.json")
        if os.path.exists(mp):
            with open(mp) as f:
                m = json.load(f)
                if user_id is None or m.get("config", {}).get("user_id") == user_id:
                    sessions.append(m)
    return sessions

