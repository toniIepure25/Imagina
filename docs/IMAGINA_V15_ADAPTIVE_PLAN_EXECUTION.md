# IMAGINA V15 — Adaptive Plan Execution + Longitudinal Progress Reports

## What V15 Adds

V15 makes the adaptive training loop operational. V14 generated the plan; V15 lets the user actually execute it day by day, log subjective check-ins, attach recalibration checkpoints, analyze adherence and PID response, and generate longitudinal progress reports that span multiple plans over time.

## V14 vs V15

| | V14 | V15 |
|---|-----|-----|
| **Plan** | Generates 7-day plan | Same |
| **Execution** | None | Day-by-day tracking + check-ins |
| **Checkpoints** | Planned but unused | Attach real calibration sessions |
| **Analytics** | PID trend across all sessions | Per-execution adherence + response |
| **Reporting** | Progress report (profile-based) | Longitudinal report (all history) |

## Execution Architecture

```
V14 Adaptive Plan
      ↓
start_plan_execution(user_id)
      ↓
Active Execution (7 days, all pending)
      ↓
┌─────────────────────────────────┐
│  Day 1 → complete → check-in    │
│  Day 2 → complete → check-in    │
│  Day 3 → skip                   │
│  Day 4 → complete → attach cal  │ ← recalibration checkpoint
│  Day 5 → pending                │
│  Day 6 → pending                │
│  Day 7 → pending                │
└─────────────────────────────────┘
      ↓
close_plan_execution()
      ↓
analyze_plan_execution() → response_category, adherence, PID change
      ↓
longitudinal_progress_report → JSON + Markdown
```

## Daily Check-in Schema

```json
{
  "completed": true,
  "duration_minutes_actual": 10,
  "difficulty_rating": 6,
  "clarity_rating": 7,
  "fatigue_rating": 3,
  "focus_quality": 7,
  "notes": "Clear session."
}
```

## Response Categories

| Category | Condition |
|----------|-----------|
| strong_positive_response | PID decrease > 0.10 |
| mild_positive_response | PID decrease > 0.05 |
| stable_response | PID change < 0.03 |
| fatigue_limited_response | avg_fatigue > 7 |
| negative_response | PID increase > 0.05 |
| insufficient_checkpoint_data | < 2 calibration checkpoints |

## Storage

```
data/imagina/adaptive_executions/{user_id}/{execution_id}/manifest.json
data/imagina/adaptive_executions/{user_id}/{execution_id}/daily_logs.jsonl
data/imagina/reports/{user_id}/longitudinal_progress_report.json
data/imagina/reports/{user_id}/longitudinal_progress_report.md
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/adaptive/execution/{user_id}/start` | POST | Start execution from plan |
| `/adaptive/execution/{user_id}/latest` | GET | Get latest active/completed execution |
| `/adaptive/execution/{user_id}/{execution_id}` | GET | Get specific execution |
| `/adaptive/executions/{user_id}` | GET | List all executions |
| `/adaptive/execution/{user_id}/{eid}/day/{day}/complete` | POST | Complete/skip day with check-in |
| `/adaptive/execution/{user_id}/{eid}/day/{day}/attach-calibration` | POST | Attach calibration to checkpoint day |
| `/adaptive/execution/{user_id}/{eid}/close` | POST | Close and finalize execution |
| `/adaptive/execution/{user_id}/{eid}/analysis` | GET | Analyze single execution |
| `/adaptive/executions/{user_id}/analysis` | GET | Analyze all executions |
| `/adaptive/longitudinal-report/{user_id}` | GET | Generate longitudinal report |

## UI Panels

### AdaptiveExecutionPanel (New)
- Active execution status with day-by-day grid
- Complete/Skip day buttons with inline check-in form
- Slider inputs: difficulty, clarity, fatigue, focus quality, duration
- Calibration checkpoint indicators with PID display
- Adherence rate and summary counters
- Close execution button
- Embedded analysis: response category, PID change, interpretation
- Collapsible check-in form per pending day

### LongitudinalProgressPanel (New)
- Summary grid: calibrations, executions, PID trend
- First vs latest PID with change direction
- Best training focus highlight
- Timeline: [C] calibration events + [E] execution events
- Recommendations list
- Regenerate report button

## How to Run the Test

```bash
cd backend
python3 -m ruff check .
python3 -m app.cli.imagina_v13_pid_calibration_test
python3 -m app.cli.imagina_v14_adaptive_loop_test
python3 -m app.cli.imagina_v15_execution_loop_test
```

The V15 test:
1. Creates synthetic calibration sessions for v15_test
2. Builds adaptive plan (V14 integration)
3. Starts execution (7 days, 3 checkpoint days)
4. Blocks duplicate start (active execution protection)
5. Completes day 1 with check-in + attaches calibration
6. Completes day 2
7. Skips day 3
8. Completes day 4 with calibration attached
9. Blocks re-completion of already-handled day
10. Closes execution
11. Analyzes execution (adherence 0.43, negative_response due to PID increasing from 0.036 to 0.1)
12. Analyzes all executions
13. Generates longitudinal report (8 calibrations, 2 executions, 10 timeline events)
14. Verifies personal profile contains execution_summary
15. Lists executions
16. Verifies safety flags
17. Tests sparse user behavior

## Safety Boundaries

All V15 artifacts include:
- `analysis_mode: "personal_exploratory_training"`
- `not_clinical: true`, `not_diagnostic: true`
- `not_mind_reading: true`, `not_bci_claim: true`
- `production_valid: false`
- Scientific boundary disclaimer

## Future V16 Direction

- Multi-plan longitudinal comparisons (A/B plan testing)
- Fatigue trend detection across multiple executions
- Automated next-plan recommendation based on response history
- Push notifications for daily check-in reminders
- PDF export of longitudinal reports
- Integration with real sensor data behind safety gates

---

*IMAGINA V15 makes the adaptive imagery-training loop operational: it lets users execute personalized PID-based training plans day by day, log subjective check-ins, attach recalibration checkpoints, analyze adherence and PID response, and generate longitudinal progress reports. It remains non-clinical, non-diagnostic, non-BCI, and not mind-reading.*
