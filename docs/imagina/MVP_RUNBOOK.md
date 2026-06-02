# IMAGINA MVP Runbook

## Quick Start

```bash
# 1. Start the backend
cd backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2. Demo session via curl
curl -s -X POST http://localhost:8000/api/imagina/session/start \
  -H 'Content-Type: application/json' \
  -d '{"demo_mode":true,"demo_profile":"stable_improving"}' | python3 -m json.tool

# 3. Start a task
SID="<session_id_from_step_2>"
curl -s -X POST "http://localhost:8000/api/imagina/session/$SID/task/start?task_id=shape_stabilization" | python3 -m json.tool

# 4. Submit self-report
curl -s -X POST "http://localhost:8000/api/imagina/session/$SID/self-report" \
  -H 'Content-Type: application/json' \
  -d '{"vividness":7,"stability":6,"effort":3,"fatigue":2,"comfort":8}' | python3 -m json.tool

# 5. Run a pipeline step
curl -s -X POST "http://localhost:8000/api/imagina/session/$SID/step" | python3 -m json.tool

# 6. Get summary
curl -s -X GET "http://localhost:8000/api/imagina/session/$SID/summary" | python3 -m json.tool

# 7. View events
curl -s -X GET "http://localhost:8000/api/imagina/session/$SID/events" | python3 -m json.tool
```

## Demo Profiles

| Profile | Behavior |
|---------|----------|
| stable_improving | Gradual improvement in attention and engagement |
| distracted | Declining attention, low engagement |
| fatigued | Rising fatigue, dropping attention |
| high_vividness | Strong start, high engagement |
| low_vividness | Weak start, slow improvement |
| noisy | Oscillating values |

## Session Data

All session events are persisted to:
```
data/imagina/sessions/{session_id}/events.jsonl
data/imagina/sessions/{session_id}/manifest.json
```

JSONL files are append-only — each line is one event.
Replay by reading lines in order.

## Python Demo

```python
from app.core.sessions.session_manager import session_manager
from app.core.events.event_store import load_events

res = session_manager.start_session('demo_user', {'demo_mode': True})
sid = res['session_id']
session_manager.start_task(sid, 'shape_stabilization')
session_manager.submit_self_report(sid, 7, 6, 3)

for i in range(5):
    step = session_manager.run_step(sid)
    print(f'Step {i+1}: IQI={step["iqi_score"]:.3f}')

print(session_manager.get_summary(sid))
print(f'Events: {len(load_events(sid))}')
```
