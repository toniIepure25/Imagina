# IMAGINA V22 — Interactive Mental Scene Simulator + Session Replay Engine

## What V22 Adds

V22 makes IMAGINA visually demonstrable by turning guided session self-report proxies into a symbolic adaptive scene. The scene is not a reconstruction of thoughts or neural activity; it is an interactive training aid that reflects clarity, stability, fatigue, and difficulty trends during an imagery practice session.

## V21 vs V22

| | V21 | V22 |
|---|-----|-----|
| **Visual** | None | Symbolic scene renderer |
| **Feedback** | Text/scene params only | Visual scene update per check-in |
| **History** | Text-based | Visual replay of full session |
| **Demonstration** | Numbers | Visual scene evolution + replay |

## Scene Template Registry (11 templates)

| Template | Category | Compatible Tasks |
|----------|----------|-----------------|
| red_circle_field | basic | red_circle_vividness |
| blue_cube_space | spatial | cube/room/rotation tasks |
| candle_flame_room | basic | candle_flame_vividness |
| apple_detail_table | object | apple_detail_generation |
| forest_scene | nature | forest, walking path |
| beach_scene | nature | beach, multisensory |
| doorway_symbol | symbolic | symbolic doorway, emotional |
| falling_leaf_scene | nature | falling leaf |
| walking_path_scene | nature | walking path |
| multisensory_food | object | smell, touch objects |
| default_dark_field | basic | fallback |

## Scene State Mapping

```
Feedback.scene_feedback.clarity          → clarity
Feedback.scene_feedback.fog              → fog (inverse of clarity)
Feedback.scene_feedback.brightness       → brightness
Feedback.scene_feedback.color_saturation → color_saturation
Feedback.scene_feedback.motion_speed     → motion_speed
Feedback.scene_feedback.stability_anchor → stability_anchor
Feedback.scene_feedback.detail_density   → detail_density
Stability × clarity                      → object_sharpness
PID proxy                                → visual_noise
1 - fatigue/10                           → breathing_rate
```

## Test Results

```
V22 SCENE SIMULATOR: 11 templates, task mapping ✓
  Check-in → scene_state in response ✓
  Clarity improved: 0.80 → 1.00 ✓
  Fog increased with low vividness: 0.20 → 0.70 ✓
  Scene persisted + summary + replay: ✓
  Replay: 6 frames, clarity_chg=-0.200 ✓
  Unknown task → default fallback ✓
  Safety flags: All OK ✓

V13-V21 regression: ALL TESTS PASSED
ruff: clean, frontend: compiled
```

## Final Claim

> IMAGINA V22 makes guided imagery training visually demonstrable: it maps self-report IQI/PID proxies and adaptive feedback into symbolic scene states, renders an interactive mental scene simulator, stores scene evolution over time, and builds session replays. It remains a visualization/training aid only — non-clinical, non-diagnostic, non-BCI, and not mind-reading.
