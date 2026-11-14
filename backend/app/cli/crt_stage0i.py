"""Stage 0I CRT source-integrity, identifiability, design, and policy package.

All outputs are simulation-only. Human data collection remains blocked. A PASS on one artifact does
not authorize a study or upgrade a claim.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.crt.design_optimization import (  # noqa: E402
    DEFAULT_CANDIDATES,
    HierarchicalDesignConfig,
    run_hierarchical_design_optimization,
)
from analysis.crt.design_optimization import (  # noqa: E402
    write_artifact as write_design,
)
from analysis.crt.full_model import (  # noqa: E402
    FULL_MODELS,
    FullModelConfig,
    run_full_recovery,
    run_full_sbc_all,
)
from analysis.crt.identifiability import (  # noqa: E402
    IdentifiabilityConfig,
    run_identifiability,
    write_artifact,
)
from analysis.crt.inference import InferenceConfig, run_backend_check  # noqa: E402
from analysis.crt.policy_model import (  # noqa: E402
    PolicyConfig,
    run_policy_parameter_sbc,
    run_policy_recovery,
    run_policy_sbc,
)
from analysis.crt.policy_model import (  # noqa: E402
    write_artifact as write_policy,
)
from analysis.crt.target_design import (  # noqa: E402
    TargetProjectionConfig,
    run_target_design_projection,
)

OUT_DIR = ROOT / "results/crt"
FILES = {
    "source_audit": "CRT_STAGE0I_SOURCE_AUDIT.json",
    "inference": "CRT_STAGE0I_INFERENCE_BACKEND.json",
    "identifiability": "CRT_STAGE0I_IDENTIFIABILITY.json",
    "design": "CRT_STAGE0I_DESIGN_ADO.json",
    "target_design": "CRT_STAGE0I_TARGET_DESIGN_PROJECTION.json",
    "policy_sbc": "CRT_STAGE0I_POLICY_SBC.json",
    "policy_parameter_sbc": "CRT_STAGE0I_POLICY_PARAMETER_SBC.json",
    "policy_recovery": "CRT_STAGE0I_POLICY_RECOVERY.json",
    "full_sbc": "CRT_STAGE0I_FULL_MODEL_SBC.json",
    "full_recovery": "CRT_STAGE0I_FULL_MODEL_RECOVERY.json",
    "package": "CRT_STAGE0I_PACKAGE.json",
}

SOURCES = [
    {
        "id": "cavagnaro_2010",
        "doi": "10.1162/neco.2009.02-09-959",
        "pmid": "20028226",
        "title": (
            "Adaptive design optimization: a mutual information-based approach "
            "to model discrimination in cognitive science"
        ),
        "type": "peer_reviewed",
        "verified": True,
        "used_for": "adaptive design optimization; mutual-information design utility",
    },
    {
        "id": "myung_2013",
        "doi": "10.1016/j.jmp.2013.05.005",
        "pmid": "23997275",
        "title": "A Tutorial on Adaptive Design Optimization",
        "type": "peer_reviewed",
        "verified": True,
        "used_for": "design optimization and model-discrimination tutorial",
    },
    {
        "id": "kim_2014",
        "doi": "10.1162/neco_a_00654",
        "pmid": "25149697",
        "title": "A hierarchical adaptive approach to optimal experimental design",
        "type": "peer_reviewed",
        "verified": True,
        "used_for": "hierarchical design optimization",
    },
    {
        "id": "rainforth_2024",
        "doi": "10.1214/23-sts915",
        "pmid": None,
        "title": "Modern Bayesian Experimental Design",
        "type": "peer_reviewed",
        "verified": True,
        "used_for": "Bayesian experimental design framing",
    },
    {
        "id": "adopy_2020",
        "doi": "10.3758/s13428-020-01386-4",
        "pmid": None,
        "title": "ADOpy: a python package for adaptive design optimization",
        "type": "peer_reviewed",
        "verified": True,
        "used_for": "implementation reference for ADO",
    },
    {
        "id": "modrak_2025",
        "doi": "10.1214/23-ba1404",
        "pmid": "41049725",
        "title": (
            "Simulation-Based Calibration Checking for Bayesian Computation: "
            "The Choice of Test Quantities Shapes Sensitivity"
        ),
        "type": "peer_reviewed",
        "verified": True,
        "used_for": "joint-likelihood SBC test quantity",
    },
    {
        "id": "corcoran_2023",
        "doi": "10.1016/j.neuron.2023.08.027",
        "pmid": "37738981",
        "title": "Accelerating scientific progress through Bayesian adversarial collaboration",
        "type": "peer_reviewed",
        "verified": True,
        "used_for": "Bayesian adversarial collaboration method",
        "correction": (
            "Previously mislabelled as an active-inference/source-monitoring empirical paper; "
            "now used only as a method reference."
        ),
    },
    {
        "id": "parr_2022",
        "doi": "10.7551/mitpress/12441.001.0001",
        "pmid": None,
        "title": "Active Inference: The Free Energy Principle in Mind, Brain, and Behavior",
        "type": "book",
        "verified": True,
        "used_for": "active-inference background only",
    },
    {
        "id": "seyr_2026",
        "doi": "10.3390/publications14030047",
        "pmid": None,
        "title": "Thus We Are Agreed! A Systematic Mapping Review of Adversarial Collaborations in Science",
        "type": "peer_reviewed",
        "verified": True,
        "used_for": "adversarial-collaboration landscape",
    },
    {
        "id": "dijkstra_fleming_2025_preprint",
        "doi": "10.31234/osf.io/36xdz_v2",
        "pmid": None,
        "title": "Perceptual reality monitoring as higher-order inference on sensory precision",
        "type": "preprint",
        "verified": True,
        "used_for": "higher-order precision competitor; not treated as peer-reviewed",
    },
]


def source_audit_payload() -> dict[str, Any]:
    unresolved = [source["id"] for source in SOURCES if not source["verified"]]
    return {
        "analysis": "stage0i_source_audit",
        "scope": "metadata_and_status_audit_not_systematic_review",
        "retrieved_at": "2026-10-31",
        "sources": SOURCES,
        "unresolved": unresolved,
        "corrections": [
            "Corcoran et al. 2023 title and role corrected.",
            "Active-inference background now points to Parr et al. 2022, not Corcoran et al.",
        ],
        "tooling_note": (
            "Crossref returned a Unicode encoding error for 10.1214/23-ba1404; the PubMed and "
            "Europe PMC records were used to verify the SBC record."
        ),
        "decision": (
            "CRT_STAGE0I_SOURCE_INTEGRITY_PASS"
            if not unresolved
            else "CRT_STAGE0I_SOURCE_INTEGRITY_REVIEW"
        ),
        "note": "Absence of an indexed PubMed notice is not proof of clean status.",
    }


def inference_payload() -> dict[str, Any]:
    payload = run_backend_check(InferenceConfig())
    payload["analysis"] = "stage0i_inference_backend"
    payload["scope"] = "inference_backend_readiness_not_human_evidence"
    return payload


def package_payload(out_dir: Path) -> dict[str, Any]:
    artifacts = {key: out_dir / name for key, name in FILES.items() if key != "package"}
    blockers: list[str] = []
    decisions: dict[str, str] = {}
    for key, path in artifacts.items():
        if not path.exists():
            blockers.append(f"missing {path.name}")
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        decision = str(payload.get("decision", "UNKNOWN"))
        decisions[key] = decision
        expected = {
            "source_audit": "CRT_STAGE0I_SOURCE_INTEGRITY_PASS",
            "inference": "CRT_STAGE0I_INFERENCE_BACKEND_READY",
            "identifiability": "CRT_STAGE0I_IDENTIFIABILITY_PASS",
            "design": "CRT_STAGE0I_DESIGN_ADO_PASS",
            "target_design": "CRT_STAGE0I_TARGET_DESIGN_PROJECTION_PASS",
            "policy_sbc": "CRT_STAGE0I_POLICY_SBC_PASS",
            "policy_parameter_sbc": "CRT_STAGE0I_POLICY_PARAMETER_SBC_PASS",
            "policy_recovery": "CRT_STAGE0I_POLICY_RECOVERY_PASS",
            "full_sbc": "CRT_STAGE0I_FULL_MODEL_SBC_PASS",
            "full_recovery": "CRT_STAGE0I_FULL_MODEL_RECOVERY_PASS",
        }[key]
        if decision != expected:
            blockers.append(f"{key}={decision}")
    blockers.extend(
        [
            "independent PI/statistician review not complete",
            "adversarial-collaboration agreement not signed",
            "calibration N=80 not run",
            "target-scale N=432/T=240 full fit and SBC not run",
            "ethics approval and registration not present",
        ]
    )
    return {
        "analysis": "stage0i_package",
        "protocol": "ANIMUS-CRT-v1",
        "scope": "documentation_and_computational_readiness_not_human_evidence",
        "status": "READY_FOR_INDEPENDENT_REVIEW" if not blockers else "BLOCKED",
        "decisions": decisions,
        "blockers": blockers,
        "note": "A READY status would not authorize human data collection or upgrade the claim ceiling.",
    }


def build_reports(*, quick: bool) -> dict[str, dict[str, Any]]:
    if quick:
        ident_config = IdentifiabilityConfig(
            n_participants=6,
            n_trials=20,
            n_simulations=1,
            n_posterior_draws=20,
            max_iter=80,
        )
        design_config = HierarchicalDesignConfig(
            n_participants=6,
            n_trials=20,
            n_replicates=1,
            models=("M0", "M6"),
            candidates=DEFAULT_CANDIDATES[:2],
            max_iter=60,
        )
        policy_config = PolicyConfig(
            n_participants=4,
            n_trials=12,
            n_simulations=1,
            n_parameter_sbc=2,
            n_parameter_draws=20,
        )
        full_config = FullModelConfig(
            n_participants=6,
            n_trials=20,
            n_sbc=1,
            n_posterior_draws=20,
            n_recovery=1,
            max_iter=60,
        )
        target_config = TargetProjectionConfig(
            pilot_n=6,
            pilot_trials=20,
            target_n=432,
            target_trials=240,
            n_replicates=2,
            candidates=DEFAULT_CANDIDATES[:1],
            max_iter=60,
        )
    else:
        ident_config = IdentifiabilityConfig(
            n_participants=24,
            n_trials=80,
            n_simulations=3,
            n_posterior_draws=30,
            max_iter=200,
        )
        design_config = HierarchicalDesignConfig(
            n_participants=24,
            n_trials=80,
            n_replicates=1,
            models=("M0", "M2", "M6"),
            candidates=DEFAULT_CANDIDATES[:3],
            max_iter=200,
        )
        policy_config = PolicyConfig(
            n_participants=8,
            n_trials=24,
            n_simulations=1,
            n_parameter_sbc=10,
            n_parameter_draws=50,
        )
        full_config = FullModelConfig(
            n_participants=8,
            n_trials=30,
            n_sbc=2,
            n_posterior_draws=20,
            n_recovery=1,
            max_iter=100,
        )
        target_config = TargetProjectionConfig(
            pilot_n=12,
            pilot_trials=40,
            target_n=432,
            target_trials=240,
            n_replicates=2,
            candidates=DEFAULT_CANDIDATES[:2],
            max_iter=120,
        )
    return {
        "source_audit": source_audit_payload(),
        "inference": inference_payload(),
        "identifiability": run_identifiability(ident_config),
        "design": run_hierarchical_design_optimization(design_config),
        "target_design": run_target_design_projection(target_config),
        "policy_sbc": run_policy_sbc(policy_config),
        "policy_parameter_sbc": run_policy_parameter_sbc(policy_config),
        "policy_recovery": run_policy_recovery(policy_config),
        "full_sbc": run_full_sbc_all(full_config, models=FULL_MODELS),
        "full_recovery": run_full_recovery(full_config, model_set=FULL_MODELS, analysis_prefix="stage0i"),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)
    if not args.check and not args.write:
        parser.print_help()
        return 0
    reports = build_reports(quick=args.quick)
    if args.write:
        for key, payload in reports.items():
            if key == "inference":
                _write_json(args.out_dir / FILES[key], payload)
            elif key in {"identifiability"}:
                write_artifact(payload, args.out_dir / FILES[key])
            elif key in {"design"}:
                write_design(payload, args.out_dir / FILES[key])
            else:
                write_policy(payload, args.out_dir / FILES[key])
        package = package_payload(args.out_dir)
        _write_json(args.out_dir / FILES["package"], package)
        reports["package"] = package
    for key, payload in reports.items():
        print(f"{key}: {payload.get('decision', payload.get('status'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
