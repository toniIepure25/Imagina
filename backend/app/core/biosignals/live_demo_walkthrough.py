"""IMAGINA V32 — Live Demo Walkthrough Generator."""

import os
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina", "live_control_room")

SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "not_neurofeedback_claim": True,
    "production_valid": False,
}


def generate_live_demo_walkthrough(user_id="demo_user"):
    md = """# IMAGINA Live Control Room — Demo Walkthrough

## What This Shows
- **Signal Status**: SQI (signal quality index), gate state (open/caution/degraded/blocked)
- **Adaptive State**: Self-report-driven state (ready, stable_practice, deepening, fatigue_risk, etc.)
- **Policy Preview**: What the system would recommend if adaptive feedback were enabled
- **Event Timeline**: All live events — phase changes, check-ins, signal quality samples, fusion states
- **Safe Export**: Export a demo pack with derived summaries only

## How to Start a Demo
1. Open http://localhost:3000/imagina/live
2. Click "Start Live Demo"
3. Click "Step" to advance the live session
4. Submit check-in values for vividness, stability, effort, etc.
5. Click "Complete" when done

## What Each Card Means
- **SQI (0-1)**: Derived signal quality from simulated biosignal stream
- **Gate State**: Whether biosignal quality is usable for exploration
- **Adaptive State**: Fused self-report + context state (e.g., "deepening", "fatigue_risk")
- **Policy Action**: Preview recommendation (e.g., "continue_current_task", "reduce_visual_complexity")

## What This System DOES NOT Claim
- NOT neural decoding or mind-reading
- NOT BCI or neurofeedback validation
- NOT clinical diagnosis or therapy
- NOT mental content reconstruction
- All metrics are self-report proxies and derived engineering summaries

## Commands
```
# Backend test
cd backend && python3 -m app.cli.imagina_v31_live_control_room_test

# Frontend
cd frontend && npm run dev
Open http://localhost:3000/imagina/live
```
"""
    d = os.path.join(BASE, user_id)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "LIVE_DEMO_WALKTHROUGH.md"), "w") as f:
        f.write(md)
    return {"walkthrough_id": str(uuid4()), "user_id": user_id,
            "markdown_path": os.path.join(d, "LIVE_DEMO_WALKTHROUGH.md"), **SAFETY}
