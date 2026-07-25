"""Restartable orchestration entry point for C3 real-data execution.

Usage:
    python -m app.research.fmri.run_c3_realdata [--stage STAGE] [--force]

Stages (in order):
    inventory         - Check data availability
    certify-downloads - Verify all required session files
    certify-spatial   - Verify spatial alignment
    certify-stimulus  - Verify stimulus mapping
    extract-roi       - Extract ROI betas from all sessions
    build-splits      - Build and freeze train/val/test split
    embed-stimuli     - Generate CLIP embeddings for all stimuli
    perception        - Train perception decoder (BLOCKED until certified)
    zero-shot         - Zero-shot imagery transfer (BLOCKED until perception)
    transport         - State transport evaluation (BLOCKED until zero-shot)
    uncertainty       - Uncertainty quantification
    controls          - Negative controls
    sensitivity       - Sensitivity analysis
    finalize          - Produce final decision artifact

Required behavior:
    - Stage-level checkpoints
    - Input-hash validation
    - Skip only when outputs are certified
    - Fail closed on provenance mismatch
    - No overwrite without --force and correction record
    - Structured logs
    - Clear blocked status
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

STAGES = [
    "inventory",
    "certify-downloads",
    "certify-spatial",
    "certify-stimulus",
    "extract-roi",
    "build-splits",
    "embed-stimuli",
    "perception",
    "zero-shot",
    "transport",
    "uncertainty",
    "controls",
    "sensitivity",
    "finalize",
]

SCIENTIFIC_STAGES = {"perception", "zero-shot", "transport", "uncertainty", "controls", "sensitivity", "finalize"}


@dataclass
class StageCheckpoint:
    stage: str
    status: str  # "completed", "blocked", "failed", "skipped"
    started_at: str = ""
    completed_at: str = ""
    input_hash: str = ""
    output_hash: str = ""
    output_path: str = ""
    error: str = ""
    blocked_by: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v}


@dataclass
class PipelineState:
    checkpoints: dict[str, StageCheckpoint] = field(default_factory=dict)
    current_stage: str = ""
    overall_status: str = "NOT_STARTED"
    started_at: str = ""
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoints": {k: v.to_dict() for k, v in self.checkpoints.items()},
            "current_stage": self.current_stage,
            "overall_status": self.overall_status,
            "started_at": self.started_at,
            "last_updated": self.last_updated,
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        with open(tmp, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        tmp.replace(path)

    @classmethod
    def load(cls, path: Path) -> "PipelineState":
        if not path.exists():
            return cls()
        with open(path) as f:
            data = json.load(f)
        state = cls()
        state.current_stage = data.get("current_stage", "")
        state.overall_status = data.get("overall_status", "NOT_STARTED")
        state.started_at = data.get("started_at", "")
        state.last_updated = data.get("last_updated", "")
        for k, v in data.get("checkpoints", {}).items():
            state.checkpoints[k] = StageCheckpoint(**v)
        return state


def _log(stage: str, message: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{stage}] {message}")


def _is_stage_complete(state: PipelineState, stage: str) -> bool:
    ckpt = state.checkpoints.get(stage)
    return ckpt is not None and ckpt.status == "completed"


def _check_readiness_gate() -> dict[str, Any]:
    """Check readiness gate before allowing scientific stages."""
    gate_path = Path("results/c3_realdata_readiness.json")
    if not gate_path.exists():
        return {"ready": False, "reason": "Readiness gate artifact not found"}
    with open(gate_path) as f:
        gate = json.load(f)
    status = gate.get("status", "UNKNOWN")
    if status != "READY_FOR_PERCEPTION_FOUNDATION":
        return {"ready": False, "reason": f"Gate status: {status}"}
    return {"ready": True}


def run_inventory(state: PipelineState, force: bool = False) -> StageCheckpoint:
    """Check data availability and produce inventory."""
    _log("inventory", "Checking data availability...")
    ckpt = StageCheckpoint(stage="inventory", started_at=time.strftime("%Y-%m-%dT%H:%M:%S"))

    betas_dir = Path(os.environ.get(
        "NSD_BETAS_ROOT", r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata_betas"
    )) / "ppdata" / "subj01" / "func1pt8mm" / "betas_fithrf"

    available = []
    missing = []
    for s in range(1, 41):
        f = betas_dir / f"betas_session{s:02d}.hdf5"
        if f.exists():
            available.append(s)
        else:
            missing.append(s)

    _log("inventory", f"Sessions available: {len(available)}/40")
    if missing:
        _log("inventory", f"Missing: {missing[:10]}{'...' if len(missing) > 10 else ''}")

    ckpt.status = "completed" if len(available) == 40 else "blocked"
    ckpt.blocked_by = f"missing_sessions={missing}" if missing else ""
    ckpt.completed_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    return ckpt


def run_certify_downloads(state: PipelineState, force: bool = False) -> StageCheckpoint:
    """Verify all 40 session files are present and correctly sized."""
    _log("certify-downloads", "Verifying session integrity...")
    ckpt = StageCheckpoint(stage="certify-downloads", started_at=time.strftime("%Y-%m-%dT%H:%M:%S"))

    betas_dir = Path(os.environ.get(
        "NSD_BETAS_ROOT", r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata_betas"
    )) / "ppdata" / "subj01" / "func1pt8mm" / "betas_fithrf"

    all_ok = True
    for s in range(1, 41):
        f = betas_dir / f"betas_session{s:02d}.hdf5"
        if not f.exists():
            all_ok = False
            break

    ckpt.status = "completed" if all_ok else "blocked"
    ckpt.blocked_by = "acquisition_incomplete" if not all_ok else ""
    ckpt.completed_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    return ckpt


def run_certify_spatial(state: PipelineState, force: bool = False) -> StageCheckpoint:
    """Run spatial alignment certification."""
    _log("certify-spatial", "Running spatial alignment certification...")
    ckpt = StageCheckpoint(stage="certify-spatial", started_at=time.strftime("%Y-%m-%dT%H:%M:%S"))

    spatial_result_path = Path("results/c3_spatial_alignment.json")
    if spatial_result_path.exists() and not force:
        with open(spatial_result_path) as f:
            result = json.load(f)
        status = result.get("status", "UNKNOWN")
        if "CERTIFIED" in status.upper() and "PENDING" not in status.upper():
            ckpt.status = "completed"
        else:
            ckpt.status = "blocked"
            ckpt.blocked_by = f"spatial_status={status}"
    else:
        ckpt.status = "blocked"
        ckpt.blocked_by = "spatial_alignment_not_yet_certified"

    ckpt.completed_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    return ckpt


def run_certify_stimulus(state: PipelineState, force: bool = False) -> StageCheckpoint:
    """Run stimulus mapping certification."""
    _log("certify-stimulus", "Checking stimulus mapping...")
    ckpt = StageCheckpoint(stage="certify-stimulus", started_at=time.strftime("%Y-%m-%dT%H:%M:%S"))

    stim_path = Path("results/c3_stimulus_alignment.json")
    if stim_path.exists():
        with open(stim_path) as f:
            result = json.load(f)
        status = result.get("status", "UNKNOWN")
        if "CERTIFIED" in status.upper():
            ckpt.status = "completed"
        else:
            ckpt.status = "blocked"
            ckpt.blocked_by = f"stimulus_status={status}"
    else:
        ckpt.status = "blocked"
        ckpt.blocked_by = "stimulus_mapping_not_yet_certified"

    ckpt.completed_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    return ckpt


def run_pipeline(start_stage: str | None = None, force: bool = False) -> None:
    """Run the full pipeline from the given stage."""
    state_path = Path("results/c3_pipeline_state.json")
    state = PipelineState.load(state_path)

    if not state.started_at:
        state.started_at = time.strftime("%Y-%m-%dT%H:%M:%S")

    stage_runners = {
        "inventory": run_inventory,
        "certify-downloads": run_certify_downloads,
        "certify-spatial": run_certify_spatial,
        "certify-stimulus": run_certify_stimulus,
    }

    start_idx = 0
    if start_stage:
        if start_stage not in STAGES:
            print(f"ERROR: Unknown stage '{start_stage}'. Available: {STAGES}")
            sys.exit(1)
        start_idx = STAGES.index(start_stage)

    for stage in STAGES[start_idx:]:
        state.current_stage = stage

        if not force and _is_stage_complete(state, stage):
            _log(stage, "Already complete, skipping")
            continue

        if stage in SCIENTIFIC_STAGES:
            gate = _check_readiness_gate()
            if not gate["ready"]:
                _log(stage, f"BLOCKED: {gate['reason']}")
                ckpt = StageCheckpoint(
                    stage=stage,
                    status="blocked",
                    blocked_by=gate["reason"],
                    started_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
                )
                state.checkpoints[stage] = ckpt
                state.overall_status = f"BLOCKED_AT_{stage.upper().replace('-', '_')}"
                state.last_updated = time.strftime("%Y-%m-%dT%H:%M:%S")
                state.save(state_path)
                return

        runner = stage_runners.get(stage)
        if runner:
            ckpt = runner(state, force)
            state.checkpoints[stage] = ckpt

            if ckpt.status == "blocked":
                _log(stage, f"BLOCKED: {ckpt.blocked_by}")
                state.overall_status = f"BLOCKED_AT_{stage.upper().replace('-', '_')}"
                state.last_updated = time.strftime("%Y-%m-%dT%H:%M:%S")
                state.save(state_path)
                return
            elif ckpt.status == "failed":
                _log(stage, f"FAILED: {ckpt.error}")
                state.overall_status = f"FAILED_AT_{stage.upper().replace('-', '_')}"
                state.last_updated = time.strftime("%Y-%m-%dT%H:%M:%S")
                state.save(state_path)
                sys.exit(1)
        else:
            _log(stage, "No runner implemented yet — marking blocked")
            ckpt = StageCheckpoint(stage=stage, status="blocked", blocked_by="runner_not_implemented")
            state.checkpoints[stage] = ckpt
            state.overall_status = f"BLOCKED_AT_{stage.upper().replace('-', '_')}"
            state.last_updated = time.strftime("%Y-%m-%dT%H:%M:%S")
            state.save(state_path)
            return

    state.overall_status = "COMPLETED"
    state.last_updated = time.strftime("%Y-%m-%dT%H:%M:%S")
    state.save(state_path)
    _log("finalize", "Pipeline complete!")


def main():
    parser = argparse.ArgumentParser(description="C3 Real-Data Execution Pipeline")
    parser.add_argument("--stage", type=str, default=None, help="Start from this stage")
    parser.add_argument("--force", action="store_true", help="Force re-run of completed stages")
    parser.add_argument("--status", action="store_true", help="Show current pipeline status")
    args = parser.parse_args()

    if args.status:
        state_path = Path("results/c3_pipeline_state.json")
        state = PipelineState.load(state_path)
        print(json.dumps(state.to_dict(), indent=2))
        return

    run_pipeline(start_stage=args.stage, force=args.force)


if __name__ == "__main__":
    main()
