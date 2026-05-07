import csv
import io
import json

from app.services import experiment_service
from app.services.report_service import generate_summary
from app.storage import event_store


async def events_jsonl(session_id: str) -> str:
    events = await event_store.list_events(session_id)
    return "\n".join(json.dumps(ev.model_dump(mode="json")) for ev in events) + ("\n" if events else "")


def _csv(rows: list[dict], headers: list[str]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


async def timeline_csv(session_id: str) -> str:
    events = await event_store.list_events(session_id)
    rows = []
    for ev in events:
        if ev.event_type in {"state_estimate", "pid_update", "iqi_update", "curriculum_update"}:
            rows.append(
                {
                    "timestamp": ev.timestamp.isoformat(),
                    "event_type": ev.event_type,
                    "window_index": ev.payload.get("window_index"),
                    "iqi": ev.payload.get("iqi"),
                    "pid": ev.payload.get("pid"),
                    "attention_stability": ev.payload.get("attention_stability"),
                    "fatigue": ev.payload.get("fatigue"),
                    "uncertainty": ev.payload.get("uncertainty"),
                    "current_level": ev.payload.get("current_level"),
                }
            )
    return _csv(
        rows,
        [
            "timestamp",
            "event_type",
            "window_index",
            "iqi",
            "pid",
            "attention_stability",
            "fatigue",
            "uncertainty",
            "current_level",
        ],
    )


async def self_reports_csv(session_id: str) -> str:
    events = await event_store.list_events(session_id, event_type="self_report")
    rows = [{"timestamp": ev.timestamp.isoformat(), **ev.payload} for ev in events]
    return _csv(
        rows,
        ["timestamp", "vividness", "stability", "focus", "relaxation", "effort", "fatigue", "distraction", "notes"],
    )


async def summary_csv(session_id: str) -> str:
    summary = await generate_summary(session_id)
    return _csv([summary.model_dump(mode="json")], list(summary.model_dump(mode="json").keys()))


async def experiment_summary_json(run_id: str) -> dict | None:
    return await experiment_service.run_summary(run_id)


def data_dictionary_markdown() -> str:
    return """# IMAGINA Data Dictionary

| Field | Type | Unit | Meaning | Source | Limitations |
|---|---|---|---|---|---|
| session_id | string | n/a | Local session identifier | real | Local only |
| event_type | string | n/a | Event envelope type | real | Depends on runtime flow |
| timestamp | ISO datetime | UTC | Event time | real | Host clock |
| iqi | float | 0-1 | Imagery Quality Index proxy | derived | Not validated ground truth |
| pid | float | 0-1 | Perception-Imagination Distance proxy | derived | Not decoded content |
| attention_stability | float | 0-1 | Attention stability proxy | derived | Simulated/self-report influenced |
| fatigue | float | 0-1 | Fatigue risk proxy | derived | Not clinical |
| uncertainty | float | 0-1 | Estimate uncertainty proxy | derived | Heuristic |
| signal_quality | float | 0-1 | Signal quality proxy | simulated/derived | V1/V2 simulated unless real provider added |
| current_level | integer | 1-8 | Curriculum level | derived | Rule-based |
| self_report.* | integer/string | 1-10/text | Subjective user report | real user input | Subjective |

IMAGINA exports experimental proxy metrics. They do not represent decoded mental content or clinical evaluation.
"""
