"""Multimodal platform demonstration on SYNTHETIC data.

Runs closed-loop sessions (shadow, simulated feedback, fault injection), verifies deterministic replay, runs
protocol runners A-D and the E-G design simulation, and writes one JSON report. Every number in the report is a
software/infrastructure result on generated data, never a participant outcome.

    python -m app.cli.multimodal_demo --out reports/multimodal/SYNTHETIC_DEMO_REPORT.json
"""
from __future__ import annotations

import argparse
import json
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

from app.multimodal.acquisition.base import FaultPlan
from app.multimodal.evaluation import SYNTHETIC_DISCLAIMER
from app.multimodal.fusion import IntermediateFusion, LateFusion, measure_latency, synthetic_fusion_dataset
from app.multimodal.protocols import (
    design_operating_characteristics,
    run_protocol_a,
    run_protocol_b,
    run_protocol_c,
    run_protocol_d,
)
from app.multimodal.runtime import ScriptedEvent, SessionConfig, replay_controller, run_session
from app.multimodal.schemas import Modality


def _session(name: str, cfg: SessionConfig) -> dict:
    t0 = time.perf_counter()
    s, summ = run_session(cfg)
    replay = replay_controller(json.loads(json.dumps(s.log)), cfg)
    return {"scenario": name, "wall_s": round(time.perf_counter() - t0, 2), "final_state": summ["final_state"],
            "n_ticks": summ["n_ticks"],
            "n_adaptive_feedback_delivered": summ["n_adaptive_feedback_delivered"],
            "n_fallback_rest_ticks": summ["n_fallback_rest_ticks"], "safety_codes": summ["safety_codes"],
            "transitions": summ["transitions"], "trace_valid": summ["trace_valid"],
            "replay_reproduced": replay["reproduced"], "tick_latency_ms": summ["latency_ms"],
            "max_alignment_uncertainty_ms": summ["sync_health"]["max_alignment_uncertainty_ms"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/multimodal/SYNTHETIC_DEMO_REPORT.json")
    ap.add_argument("--duration", type=float, default=180.0)
    args = ap.parse_args()
    warnings.simplefilter("ignore")
    d = args.duration
    sessions = [
        _session("shadow_default", SessionConfig(session_id="demo-shadow", duration_s=d)),
        _session("simulated_feedback_research", SessionConfig(session_id="demo-fb", duration_s=d,
                                                               mode="feedback_research")),
        _session("eeg_disconnect_fault", SessionConfig(
            session_id="demo-fault", duration_s=d, mode="feedback_research",
            faults={Modality.EEG: FaultPlan(disconnect_at_s=90.0, reconnect_after_s=1000.0),
                    Modality.ECG: FaultPlan(clock_drift_ppm=250.0, clock_offset_s=12.0, jitter_s=0.004)})),
        _session("scripted_distress_report", SessionConfig(
            session_id="demo-distress", duration_s=d, mode="feedback_research",
            events=[ScriptedEvent(t=100.0, kind="report_text", value="I feel detached and dizzy")])),
        _session("operator_emergency_stop", SessionConfig(
            session_id="demo-estop", duration_s=d, events=[ScriptedEvent(t=80.0, kind="emergency_stop")])),
    ]
    ds = synthetic_fusion_dataset(seed=0)
    latency = {"late_fusion": measure_latency(LateFusion().fit(ds), ds, 200),
               "intermediate_fusion": measure_latency(IntermediateFusion().fit(ds), ds, 200)}
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": SYNTHETIC_DISCLAIMER,
        "sessions": sessions,
        "fusion_inference_latency_ms": latency,
        "protocols": {"A": run_protocol_a(n_permutations=19), "B": run_protocol_b(), "C": run_protocol_c(),
                      "D": run_protocol_d(),
                      "E-G_design_operating_characteristics": design_operating_characteristics(
                          n_per_arm=20, effects=(0.0, 0.1, 0.2), n_sims=400)},
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=float))
    for s in sessions:
        print(f"{s['scenario']:30s} {s['final_state']:17s} feedback={s['n_adaptive_feedback_delivered']:3d} "
              f"rest={s['n_fallback_rest_ticks']:3d} replay={s['replay_reproduced']} "
              f"p50={s['tick_latency_ms']['p50']:.1f}ms codes={s['safety_codes']}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
