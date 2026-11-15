"""Optional publication-grade inference backend checks for CRT Stage 0I.

NumPyro/JAX is an optional extra. When it is absent the Stage 0I gate is BLOCKED; the Laplace
approximation remains available for screening but must never be labelled confirmatory.
"""
from __future__ import annotations

import json
import platform
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

SCOPE = "inference_backend_readiness_not_human_evidence"


@dataclass(frozen=True)
class InferenceConfig:
    backend: str = "numpyro"
    chains: int = 4
    warmup: int = 2000
    draws: int = 2000
    seed: int = 20261031
    target_accept: float = 0.95

    def __post_init__(self) -> None:
        if self.backend not in {"numpyro", "laplace"}:
            raise ValueError("backend must be 'numpyro' or 'laplace'")
        if self.chains < 1 or self.warmup < 1 or self.draws < 1:
            raise ValueError("chains, warmup, and draws must be positive")
        if not 0 < self.target_accept < 1:
            raise ValueError("target_accept must be in (0, 1)")


def backend_status() -> dict[str, Any]:
    try:
        import numpyro  # type: ignore
        import jax  # type: ignore

        numpyro_version = getattr(numpyro, "__version__", "unknown")
        jax_version = getattr(jax, "__version__", "unknown")
        available = True
    except Exception:  # pragma: no cover - exercised only when dependency is absent
        numpyro_version = None
        jax_version = None
        available = False
    return {
        "analysis": "stage0i_inference_backend",
        "scope": SCOPE,
        "backend": "numpyro",
        "available": available,
        "implementation": "analysis/crt/numpyro_model.py",
        "implementation_present": True,
        "numpyro_version": numpyro_version,
        "jax_version": jax_version,
        "python": platform.python_version(),
        "laplace_role": "screening_only_not_confirmatory",
        "decision": (
            "CRT_STAGE0I_INFERENCE_BACKEND_READY"
            if available
            else "CRT_STAGE0I_INFERENCE_BACKEND_BLOCKED"
        ),
        "note": (
            "The NUTS full-joint implementation is present and has a likelihood-parity test. A ready "
            "backend still requires the target-scale SBC/recovery run; absence of NumPyro blocks the "
            "confirmatory gate but does not invalidate prior screening."
        ),
    }


def run_backend_check(config: InferenceConfig | None = None) -> dict[str, Any]:
    cfg = config or InferenceConfig()
    status = backend_status()
    payload = {
        **status,
        "config": asdict(cfg),
        "requested_backend": cfg.backend,
        "decision": (
            "CRT_STAGE0I_INFERENCE_BACKEND_READY"
            if status["available"] and cfg.backend == "numpyro"
            else "CRT_STAGE0I_INFERENCE_BACKEND_BLOCKED"
        ),
    }
    return payload


def write_artifact(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    payload = run_backend_check()
    print(json.dumps({"decision": payload["decision"], "available": payload["available"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
