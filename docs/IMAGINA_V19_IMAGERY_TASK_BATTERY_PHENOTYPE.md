# IMAGINA V19 — Imagery Task Battery + Cognitive Phenotype Engine

## What V19 Adds

V19 returns IMAGINA to its core imagination mission. After V13-V18 built the infrastructure for calibration, training, execution, optimization, experiments, and evidence, V19 defines a standardized mental imagery task battery with 30+ tasks across 10 categories and converts task performance into a personal trainable imagery phenotype.

## V18 vs V19

| | V18 | V19 |
|---|-----|-----|
| **Focus** | Evidence dashboard + export | Core imagery profiling |
| **Tasks** | None | 30 tasks, 10 categories |
| **Profiling** | PID/execution based | Self-report dimension scores |
| **Phenotype** | None | 9-dimension personal profile |
| **Gaps** | Quality audit | Imagery dimension gap analysis |
| **Training** | Adaptive/optimized plans | Task-based imagery plans |

## Task Battery (30 Tasks, 10 Categories)

| # | Category | Tasks |
|---|----------|-------|
| 1 | **Basic Vividness** | Red Circle, Blue Cube, Candle Flame |
| 2 | **Color Control** | Color Shift, Saturation, Brightness |
| 3 | **Spatial Stability** | Static Cube, Rotating Cube, Room Layout |
| 4 | **Detail Generation** | Apple Detail, Face Detail, Forest Scene |
| 5 | **Perspective Control** | First Person, Third Person, Perspective Shift |
| 6 | **Motion Imagery** | Rotating Object, Falling Leaf, Walking Path |
| 7 | **Emotional Tone** | Calm Scene, Joyful Memory, Neutral Object |
| 8 | **Scene Construction** | Simple Room, Beach Scene, Symbolic Doorway |
| 9 | **Multisensory** | Visual+Sound, Visual+Touch, Visual+Smell |
| 10 | **Meta-Control** | Hold 30s, Blur-Refocus, Switch Images |

## Imagery Dimensions (9)

- **vividness** — Clarity and photographic quality of mental images
- **stability** — Ability to hold an image without drifting
- **color_control** — Control over color, saturation, and brightness
- **spatial_control** — Position, depth, perspective, and 3D awareness
- **detail** — Generation of fine details and texture
- **motion** — Smooth controlled motion in mental imagery
- **emotion** — Emotional tone perception and control
- **multisensory** — Integration of visual with other senses
- **meta_control** — Intentional manipulation (blur, switch, hold)

## Task Session Lifecycle

```
Start Session → Build mental image → Submit rating (9 dims + effort/fatigue/confidence)
              → Complete → Dimension scores computed (adjusted for effort/fatigue)
              → Persisted to imagery_task_sessions/{session_id}/
```

## Phenotype Labels

| Label | Profile |
|-------|---------|
| vivid_visualizer | Strong vividness, clear images |
| stable_constructor | Strong spatial stability and construction |
| detail_builder | Strong detail generation |
| motion_imager | Strong motion imagery |
| emotional_scene_imager | Strong emotional tone imagery |
| multisensory_imager | Strong multisensory integration |
| emerging_imager | Early development, scores < 0.45 |
| mixed_profile | Balanced across dimensions |
| effortful_imager | Requires significant effort |

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/imagery/tasks` | GET | List 30 tasks (optional `?category=`) |
| `/imagery/tasks/{task_id}` | GET | Get single task |
| `/imagery/sessions/{uid}/start/{tid}` | POST | Start task session |
| `/imagery/sessions/{sid}/rating` | POST | Submit rating payload |
| `/imagery/sessions/{sid}/complete` | POST | Complete session + compute scores |
| `/imagery/sessions/{sid}` | GET | Get session |
| `/imagery/sessions/user/{uid}` | GET | List user sessions |
| `/imagery/phenotype/{uid}` | GET | Build/refresh phenotype |
| `/imagery/gaps/{uid}` | GET | Analyze imagery gaps |
| `/imagery/task-plan/{uid}` | POST | Generate task-based plan |

## UI Panels

### ImageryTaskBatteryPanel
- Category filter dropdown
- Task list with difficulty, category, start button
- Active session rating form (6 dimension sliders)
- Rate & Complete button

### ImageryPhenotypePanel
- Phenotype label display
- 9 dimension score bars with confidence badges
- Strongest/weakest dimensions
- Interpretation text
- Analyze Gaps button

### ImageryGapPanel
- Primary/secondary gap display
- Ranked gap list with severity and priority
- Recommended training focus
- Generate Task Plan button

### TaskBasedPlanPanel
- Daily task schedule (7 days)
- Target dimension per day
- Task difficulty and duration
- Why-chosen rationale
- Expected outcome text

## Test Results

```
V19 IMAGERY PHENOTYPE ENGINE: ALL TESTS PASSED
  30 tasks, 10 categories ✓
  All safety flags: ✓
  6 sessions completed across dimensions ✓
  Phenotype: mixed_profile, 9 dimensions scored ✓
  Gaps: 7 ranked gaps ✓
  Task plan: 7 days generated ✓
  Personal profile: phenotype_summary present ✓
  Sparse user: Handled ✓

V13-V18 regression: ALL TESTS PASSED
ruff: clean, frontend: compiled, verify.sh: 7/8 pass
```

## Final Claim

> IMAGINA V19 returns the project to its core imagination mission: it adds a standardized mental imagery task battery, converts task performance into a personal trainable imagery phenotype, identifies the user's strongest and weakest imagery dimensions, and generates targeted task-based training plans. It remains non-clinical, non-diagnostic, non-BCI, and not mind-reading.
