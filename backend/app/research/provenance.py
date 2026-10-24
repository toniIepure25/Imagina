from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone


def get_git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def build_provenance_record(
    study_id: str,
    participant_id: str,
    session_id: str,
    condition: str,
    trial_index: int,
    stimulus_id: str,
    signal_provider_id: str,
    protocol_version: str,
    software_version: str = "0.5.0.dev1",
) -> dict:
    return {
        "provenance_version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "software_version": software_version,
        "git_sha": get_git_sha(),
        "study_id": study_id,
        "participant_id": participant_id,
        "session_id": session_id,
        "condition": condition,
        "trial_index": trial_index,
        "stimulus_id": stimulus_id,
        "signal_provider_id": signal_provider_id,
        "protocol_version": protocol_version,
    }


def hash_trial_data(data: dict) -> str:
    import json
    content = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()[:32]
