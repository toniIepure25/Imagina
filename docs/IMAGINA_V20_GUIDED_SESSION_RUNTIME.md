# IMAGINA V20 — Guided Imagery Session Runtime + Adaptive Feedback Loop

## What V20 Adds

V20 turns IMAGINA from a task/profiling system into a guided closed-loop mental imagery training runtime. V19 told you what task to do and what dimension to train. V20 actually runs the task as a guided session with phases, micro-check-ins, live IQI/PID self-report proxies, adaptive feedback, safety monitoring, session reports, and guided plan execution.

## V19 vs V20

| | V19 | V20 |
|---|-----|-----|
| **Tasks** | 30 tasks, 10 categories | Same, but now run as guided sessions |
| **Execution** | Simple start/rate/complete | 10-phase guided session runtime |
| **Check-ins** | None | Micro-check-ins per phase |
| **Proxies** | None | Live IQI/PID/stability self-report proxies |
| **Feedback** | None | Adaptive guidance + scene feedback params |
| **Safety** | None | Auto-stop on high discomfort, pause on high fatigue |
| **Plan Execution** | Static plan | Guided plan runner with day-by-day progress |

## Guided Session Phases (10)

```
preparation → grounding → image_generation → stabilization → deepening
→ manipulation → micro_checkin → adaptive_feedback → integration → completion
```

## Micro-Check-in Fields

- vividness (1-10)
- stability (1-10)
- effort (1-10)
- fatigue (1-10)
- confidence (1-10)
- discomfort (1-10)
- free_note (optional)

## Live Proxy Estimator

```
IQI = vividness×0.35 + stability×0.25 + confidence×0.20 + (1-effort)×0.10 + (1-fatigue)×0.10
PID = 1 - IQI (+ adjustments for phenotype gap, low confidence, high fatigue)
Stability proxy = stability × (1 - fatigue × 0.3)
```

All proxies include the disclaimer: "Self-report proxy only — not neural measurement, not BCI, not mind-reading."

## Safety State Machine

| Condition | State |
|-----------|-------|
| discomfort ≥ 8 | stop |
| fatigue ≥ 8 | pause |
| fatigue ≥ 6 or effort ≥ 8 | slow_down |
| otherwise | continue |

## Adaptive Feedback

Generates guidance text and scene feedback parameters:
- clarity, fog, brightness, color_saturation
- motion_speed, stability_anchor, detail_density, audio_calmness

Rules adapt based on: current phase, target dimensions, latest check-in, IQI/PID proxy, fatigue, safety state.

## Guided Plan Runner

```
Task-based plan → start_next_guided_task_from_plan()
               → runs the guided session
               → complete → mark_guided_plan_day_completed()
               → advances to next day
               → tracks adherence
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/guided/schema` | GET | Session schema |
| `/guided/session/{uid}/start/{tid}` | POST | Start guided session |
| `/guided/session/{sid}` | GET | Get session |
| `/guided/session/{sid}/advance` | POST | Advance phase |
| `/guided/session/{sid}/checkin` | POST | Submit micro-check-in |
| `/guided/session/{sid}/pause` | POST | Pause session |
| `/guided/session/{sid}/resume` | POST | Resume session |
| `/guided/session/{sid}/complete` | POST | Complete + finalize |
| `/guided/session/{sid}/abort` | POST | Abort with reason |
| `/guided/sessions/{uid}` | GET | List user sessions |
| `/guided/session/{sid}/report` | GET | Session report |
| `/guided/session/{sid}/export-task-rating` | POST | Export as V19 rating |
| `/guided/plan/{uid}/start-next` | POST | Start next plan task |
| `/guided/plan/{uid}/progress` | GET | Plan progress |
| `/guided/plan/{uid}/complete-day/{sid}` | POST | Complete plan day |

## UI Panels

### GuidedImagerySessionPanel
- Start session from task ID input
- Phase progress bar
- Micro-check-in sliders (6 dims)
- Live IQI/PID/stability proxy display
- Adaptive guidance text overlay
- Phase advance, pause, resume, complete buttons

### LiveImageryFeedbackPanel
- IQI/PID/stability numeric display
- Fatigue risk + safety state
- Scene feedback bar chart (8 parameters)
- Modality disclaimer

### GuidedSessionReportPanel
- Task title + category
- Average vividness, stability, effort, fatigue
- Final IQI/PID proxy
- Recommended next task/dimension
- Export as task rating button

### GuidedPlanRunnerPanel
- Current plan day + adherence
- Start next task / Complete day buttons
- Completed days list

## Test Results

```
V20 GUIDED IMAGERY SESSION RUNTIME: ALL TESTS PASSED
  Session: start → advance → check-in (IQI=0.69, PID=0.34) ✓
  High fatigue triggers safety pause: ✓
  Adaptive feedback generated: ✓
  Session auto-paused + resumed: ✓
  Session completed + report: ✓
  Export as V19 task rating: ✓
  Plan runner: start next → complete day → adherence tracking ✓
  Profile: guided_imagery_summary present ✓
  Safety flags: All OK ✓

V13-V19 regression: ALL TESTS PASSED
ruff: clean, frontend: compiled, verify.sh: 7/8 pass
```

## Final Claim

> IMAGINA V20 turns the project into a guided closed-loop mental imagery training runtime: it runs imagery tasks phase-by-phase, collects micro-check-ins, estimates live self-report IQI/PID proxies, adapts guidance and feedback, generates session reports, and feeds results back into the phenotype and evidence system. It remains non-clinical, non-diagnostic, non-BCI, and not mind-reading.
