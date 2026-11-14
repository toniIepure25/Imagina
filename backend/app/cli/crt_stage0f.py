"""Stage 0F protocol, power, distortion, and hierarchical-screening audit.

Examples:
    python -m app.cli.crt_stage0f --check
    python -m app.cli.crt_stage0f --write --out-dir ..\\results\\crt
    python -m app.cli.crt_stage0f --write --full --out-dir ..\\results\\crt
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.research.crt.design import (
    DesignPowerConfig,
    run_design_power_grid,
    simulate_design_power,
)
from app.research.crt.distortion import DistortionConfig, run_distortion_assay
from app.research.crt.hierarchical import (
    HierarchicalScreenConfig,
    run_hierarchical_screen,
)
from app.research.crt.protocol import run_protocol_audit

DEFAULT_OUT = Path("results/crt")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def _registration_package(
    audit: dict[str, object],
    design: dict[str, object],
    distortion: dict[str, object],
    hierarchy: dict[str, object],
) -> dict[str, object]:
    blockers: list[str] = []
    if audit.get("decision") != "CRT_STAGE0F_PROTOCOL_PASS":
        blockers.append("protocol audit")
    if design.get("decision") != "CRT_STAGE0F_DESIGN_PASS":
        blockers.append("design power")
    if distortion.get("decision") != "CRT_STAGE0F_DISTORTION_PASS":
        blockers.append("distortion assay")
    if hierarchy.get("decision") != "CRT_STAGE0F_HIERARCHICAL_SCREENING_PASS":
        blockers.append("hierarchical screening")
    blockers.append("trial-level CRT hierarchical SBC remains outstanding")
    return {
        "protocol": "ANIMUS-CRT-v1",
        "analysis": "stage0f_registration_readiness",
        "status": "BLOCKED" if blockers else "READY_FOR_INDEPENDENT_REVIEW",
        "blockers": blockers,
        "decisions": {
            "protocol": audit.get("decision"),
            "design_power": design.get("decision"),
            "distortion": distortion.get("decision"),
            "hierarchical_screening": hierarchy.get("decision"),
        },
        "note": (
            "Registration readiness is a documentation gate. A READY status would still require PI, "
            "statistician, adversarial review, and ethics approval before any human data collection."
        ),
    }


def build_reports(*, full: bool = False) -> dict[str, dict[str, object]]:
    audit = run_protocol_audit().as_dict()
    if full:
        design = run_design_power_grid(seed=20261030, n_simulations=400)
        distortion = run_distortion_assay(DistortionConfig(n_simulations=1000))
        hierarchy = run_hierarchical_screen(
            HierarchicalScreenConfig(n_participants=12, n_trials=60, n_replicates=40)
        )
    else:
        design = simulate_design_power(
            DesignPowerConfig(n_simulations=100)
        )
        distortion = run_distortion_assay(
            DistortionConfig(n_simulations=100, readout_n=6, readout_trials=30)
        )
        hierarchy = run_hierarchical_screen(
            HierarchicalScreenConfig(n_participants=8, n_trials=30, n_replicates=5)
        )
    registration = _registration_package(audit, design, distortion, hierarchy)
    return {
        "CRT_STAGE0F_PROTOCOL_AUDIT.json": audit,
        "CRT_STAGE0F_DESIGN_POWER.json": design,
        "CRT_STAGE0F_DISTORTION.json": distortion,
        "CRT_STAGE0F_HIERARCHICAL_SCREENING.json": hierarchy,
        "CRT_STAGE0F_REGISTRATION_PACKAGE.json": registration,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="run a fast Stage 0F audit")
    parser.add_argument("--write", action="store_true", help="write Stage 0F artifacts")
    parser.add_argument("--full", action="store_true", help="run the full Stage 0F grids")
    parser.add_argument("--strict", action="store_true", help="exit non-zero on any REVIEW decision")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    if not args.check and not args.write:
        parser.error("choose --check or --write")

    reports = build_reports(full=args.full or args.write)
    if args.write:
        for name, payload in reports.items():
            _write_json(args.out_dir / name, payload)

    for name, payload in reports.items():
        print(f"{name}: {payload.get('decision', payload.get('status', 'UNKNOWN'))}")
    audit = reports["CRT_STAGE0F_PROTOCOL_AUDIT.json"]
    if audit.get("decision") != "CRT_STAGE0F_PROTOCOL_PASS":
        print("protocol errors:")
        for error in audit.get("errors", []):
            print(f"  - {error}")
        return 1
    if args.strict:
        for name, payload in reports.items():
            if payload.get("decision") not in {
                "CRT_STAGE0F_PROTOCOL_PASS",
                "CRT_STAGE0F_DESIGN_PASS",
                "CRT_STAGE0F_DISTORTION_PASS",
                "CRT_STAGE0F_HIERARCHICAL_SCREENING_PASS",
                "READY_FOR_INDEPENDENT_REVIEW",
            }:
                print(f"strict failure: {name}")
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
