# IMAGINA V14 — Adaptive PID-Based Training Loop

## What V14 Adds

V14 closes the loop. IMAGINA no longer only measures perception-imagination distance (PID v2); it now uses PID v2 results to automatically generate personalized 7-day imagery training plans, schedule recalibration checkpoints, and track whether the PID gap improves over time.

## Why the Adaptive Loop Matters

V13 measures: *"How close is your imagined reconstruction to the perceived reference?"*

V14 closes the loop: *"Given your PID result, what should you practice next, and is it helping?"*

This transforms IMAGINA from a passive measurement tool into a personal exploratory adaptive training system.

## V13 vs V14

| | V13 | V14 |
|---|-----|-----|
| **Measurement** | PID v2 gap | Same |
| **Action** | None | Auto-generated 7-day training plan |
| **Focus** | What is the gap? | What should I do about it? |
| **Tracking** | Session history | Pre/post plan PID improvement |
| **Personalization** | None | Plan tailored to weakest dimension |

## PID → Gap → Plan → Calibration Loop

```
V13 Calibration → PID v2 result → Weakest dimension
                                      ↓
                              Adaptive Training Planner
                                      ↓
                              7-Day Training Plan
                              (personalized exercises)
                                      ↓
                    Day 1: Baseline Calibration
                    Day 4: Midpoint Calibration
                    Day 7: Final Calibration
                                      ↓
                              PID Improvement Tracker
                              (first vs latest, trend, meaningful change)
                                      ↓
                              Updated Personal Profile
                              (adaptive_training_summary)
```

## PID Dimension Mapping

| PID Gap | Training Focus | Exercise Family |
|---------|---------------|----------------|
| clarity_gap | vividness_foundation | Shape clarity, contrast, brightness |
| detail_gap | detail_generation | Texture mapping, progressive layering |
| color_gap | color_intensity_training | Saturation, hue transitions, low-light color |
| spatial_gap | spatial_stability_training | Position hold, depth estimation, anchoring |
| emotional_gap | emotional_tone_control | Neutral scenes, tone shift awareness |

### Automatic Overrides

| Condition | Focus Override |
|-----------|---------------|
| avg_fatigue > 7 | fatigue_resistance |
| avg_confidence < 4 | confidence_stabilization |
| mean_pid > 0.6 | baseline_rebuild |

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/imagina/adaptive/plan/{user_id}` | GET | Get current adaptive plan |
| `/api/imagina/adaptive/plan/{user_id}/generate` | POST | Generate new adaptive plan |
| `/api/imagina/adaptive/plan/{user_id}/regenerate` | POST | Regenerate with overrides |
| `/api/imagina/adaptive/plans/{user_id}` | GET | List plan history |
| `/api/imagina/adaptive/improvement/{user_id}` | GET | PID improvement analysis |
| `/api/imagina/adaptive/training-response/{user_id}` | GET | Training response vs plan |

## UI Panels

### AdaptiveTrainingPanel
- Displays current plan: title, focus, rationale
- Grid: mean PID, weakest dimension
- 7-day daily schedule with durations
- Calibration checkpoint timeline (Day 1/4/7)
- Improved/Stable/Needs attention badge
- Generate / Regenerate / Refresh buttons
- Scientific boundary disclaimer

### PidImprovementPanel
- First PID → Latest PID → Absolute/relative change
- Trend badge: improving/stable/declining
- Meaningful change indicator (≥0.05)
- Per-dimension gap changes
- Cautious interpretation text
- Refresh button

## Core Modules

### `backend/app/core/adaptive/adaptive_training_planner.py`

- `build_adaptive_training_plan(user_id)` — Main planner entry point
- `generate_daily_plan_from_focus(focus, dim_name, calib_task_id, days=7)` — Exercise scheduling
- `generate_exercises_for_focus(focus, dim_name, difficulty=2)` — Exercise family selection
- `save_adaptive_training_plan(user_id, plan)` — Persist to JSON
- `load_latest_adaptive_training_plan(user_id)` — Load current plan
- `list_adaptive_training_plans(user_id)` — History of plan snapshots

### `backend/app/core/adaptive/pid_improvement_tracker.py`

- `compute_pid_improvement(user_id)` — First vs latest, rolling means, per-dimension changes
- `compute_training_response(user_id, plan_id)` — Whether plan seems to help
- Uses cautious wording: "suggestive of," "consistent with," "personal observation"

### Exercise Families (9)

1. vividness_foundation: Clear shape, contrast enhancement, brightness gradients
2. detail_generation: Texture mapping, progressive layering, edge sharpness
3. color_intensity_training: Saturation, hue transitions, low-light color
4. spatial_stability_training: Fixed position hold, depth estimation, anchoring
5. emotional_tone_control: Neutral scene, symbolic tone shift
6. fatigue_resistance: Micro-sessions, recovery pacing
7. confidence_stabilization: Easy wins, self-rating calibration
8. scene_construction: Small scenes, memory room
9. baseline_rebuild: Return to simple reference, shape+position rebuild

## How to Run the Test

```bash
cd backend
python3 -m ruff check .
python3 -m app.cli.imagina_v13_pid_calibration_test
python3 -m app.cli.imagina_v14_adaptive_loop_test
```

The V14 test:
1. Creates 4 synthetic calibration sessions (improving PID: 0.65→0.35)
2. Builds adaptive training plan
3. Saves/loads/lists plans
4. Computes PID improvement (improving trend, meaningful change)
5. Computes training response (improved)
6. Rebuilds personal profile with adaptive training summary
7. Verifies safety flags
8. Tests sparse user behavior
9. Generates exercises for all foci

## Safety Boundaries

All V14 artifacts include:
- `analysis_mode: "personal_exploratory_training"`
- `not_clinical: true`
- `not_diagnostic: true`
- `not_mind_reading: true`
- `not_bci_claim: true`
- `production_valid: false`
- Scientific boundary: "Personal exploratory adaptive mental imagery training only. Not diagnosis, therapy, clinical treatment, mind-reading, dream decoding, or validated BCI."

## Future V15 Direction

- Adaptive plan completion tracking (mark days as done)
- PID improvement push notifications / reminders
- Multi-session adaptive protocol runs (longitudinal tracking)
- Integration with real sensor data (EEG/LSL) behind safety gates
- PDF export of training plan and progress reports
- Multi-user profile comparison (anonymized, local only)

---

*IMAGINA V14 closes the perception-imagination training loop. It uses PID v2 calibration results to identify the user's weakest imagery dimension, generate a personalized 7-day training plan, schedule recalibration checkpoints, and track whether perception-imagination distance improves over time. It remains non-clinical, non-diagnostic, non-BCI, and not mind-reading.*
