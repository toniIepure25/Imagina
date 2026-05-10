# Demo Script (3-5 minutes)

## Setup

1. Start the backend: `cd backend && uvicorn app.main:app --reload --port 8000`
2. Start the frontend: `cd frontend && npm run dev`
3. Open http://localhost:3000

## 3-Minute Script

### Opening (20s)

> "This is IMAGINA V2 — a research prototype for closed-loop mental imagery training. It does NOT read minds or decode dreams. V2 uses simulated EEG-like signals plus self-report and behavioral proxies, then adapts a procedural 3D corridor scene in real time."

Point to the landing page disclaimers and the system loop.

### Demo Replay (2 min)

1. Click **Watch Replay**.
2. Click **Start Demo**.
3. Narrate as the corridor evolves:
   > "The system is replaying a pre-generated improving-user scenario. Watch how the corridor starts blurry and distorted..."
4. Point out metrics updating in real time:
   > "IQI is rising as the simulated user's proxy stability improves. IQI is higher-is-better. PID is dropping; PID is lower-is-better. Neither metric is ground truth."
5. Point to the curriculum timeline:
   > "The system just advanced from Level 1 to Level 2 after three successful windows."
6. Show the visual mapping:
   > "Clarity follows IQI proxy. Fog follows uncertainty and fatigue. Wall distortion follows instability. Doors follow curriculum progression. The breathing pulse is a reset cue."
7. If doors appear:
   > "At Level 6, doors appear in the corridor — the task is getting more complex."

### Report (40s)

1. Open a session report.
2. Show average IQI, best IQI, average PID, best PID, max level, fatigue peak, and recommendation.
3. Say:
   > "This report summarizes experimental proxy metrics. It is not decoded mental content or a clinical evaluation."

### Closing (20s)

> "The corridor is not a decoded mental image. It is an adaptive scaffold driven by experimental proxy metrics."

## 5-Minute Script

### Live Session Extension

1. Go back and click **Start Dream Corridor Session**.
2. Choose "Simple Corridor Stabilization" with Guided mode.
3. Accept the disclaimer and complete calibration.
4. Show the self-report sliders:
   > "The user rates vividness, stability, focus, effort, fatigue, and distraction. Those values influence future estimates; they do not decode thought content."
5. Adjust sliders to show real-time scene response.
6. Raise fatigue or effort to show the safety monitor reducing intensity and strengthening the breathing reset.
7. End the session.

### Report Detail

1. View the session report.
2. Show average IQI, PID, max level, recommendation, timeline, and interpretation labels.
3. Open the JSON report and HTML report links.

### Closing

> "IMAGINA V2 is a complete local-first MVP with a FastAPI backend, Next.js frontend, WebSocket streaming, adaptive curriculum, safety monitoring, deterministic replay, and reports. All metrics are experimental proxies. The corridor is adaptive feedback, not decoded thought."

## Key Points to Emphasize

- Research prototype, not a product
- Proxy metrics, not ground truth
- Simulated signals in V1
- The corridor is feedback scaffolding, not a reconstruction of imagery
- Local-first, no cloud, no accounts
- Safety disclaimers visible throughout
- V2 can add real LSL, OpenBCI, Muse, MNE preprocessing, and artifact-aware bandpower features

## Technical Evaluator V2 Workflow

1. Open `/profile` and create a local profile.
2. Open `/experiments`, choose **Adaptive guided corridor**, and create a run.
3. Click **Create Next Session**, then open the linked session.
4. Point out the session metadata: local profile, simulated provider, scenario, task, experiment run, and consent.
5. Complete calibration and show the quality score:
   > "Calibration is session-local normalization for proxy metrics. It is not reading or reconstructing mental imagery."
6. Run the session, stop it, then open the report.
7. Show calibration metadata, provider/scenario, experiment linkage, export buttons, and profile progress.
8. Return to `/experiments` and show run progress plus experiment summary export.

Close with:

> "V2 completes the research workflow around a simulated provider. The next engineering step is optional real LSL/OpenBCI integration, not dream decoding."
