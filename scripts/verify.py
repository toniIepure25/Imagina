#!/usr/bin/env python3
"""Cross-platform verification entry point for IMAGINA.

Modes
-----
quick : lint + focused backend tests (default developer loop)
ci    : lint, backend core/research tests, frontend lint/typecheck/unit/build,
        claim audit, Docker compose validation (strict about missing tools)
full  : ci plus the complete backend test suite

Examples
--------
    python scripts/verify.py --quick
    python scripts/verify.py --ci
    python scripts/verify.py --full --skip-frontend
    python scripts/verify.py --ci --mypy
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
IS_WINDOWS = os.name == "nt"
USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


GREEN, RED, YELLOW, BOLD = "32", "31", "33", "1"


@dataclass
class Result:
    name: str
    status: str  # pass | fail | skip
    detail: str = ""
    seconds: float = 0.0


@dataclass
class Runner:
    ci: bool
    results: list[Result] = field(default_factory=list)

    def record(self, name: str, status: str, detail: str = "", seconds: float = 0.0) -> None:
        self.results.append(Result(name, status, detail, seconds))
        color = {"pass": GREEN, "fail": RED, "skip": YELLOW}[status]
        label = {"pass": "PASS", "fail": "FAIL", "skip": "SKIP"}[status]
        suffix = f" ({seconds:.1f}s)" if seconds else ""
        print(f"  {_c(f'[{label}]', color)} {name}{suffix}")
        if detail and status != "pass":
            for line in detail.strip().splitlines()[-12:]:
                print(f"         {line}")

    def run(
        self,
        name: str,
        cmd: list[str],
        cwd: Path,
        timeout: int = 900,
        critical_in_ci: bool = True,
        env: dict[str, str] | None = None,
    ) -> bool:
        started = time.monotonic()
        merged = os.environ.copy()
        merged.setdefault("PYTHONIOENCODING", "utf-8")
        if env:
            merged.update(env)
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env=merged,
            )
        except FileNotFoundError:
            detail = f"command not found: {cmd[0]}"
            self.record(name, "fail" if (self.ci and critical_in_ci) else "skip", detail)
            return False
        except subprocess.TimeoutExpired:
            self.record(name, "fail", f"timed out after {timeout}s")
            return False
        elapsed = time.monotonic() - started
        output = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode == 0:
            self.record(name, "pass", seconds=elapsed)
            return True
        self.record(name, "fail", output, elapsed)
        return False

    def summary(self) -> int:
        passed = sum(r.status == "pass" for r in self.results)
        failed = sum(r.status == "fail" for r in self.results)
        skipped = sum(r.status == "skip" for r in self.results)
        print()
        print("=" * 60)
        print(f"  Total: {len(self.results)}  Passed: {passed}  Failed: {failed}  Skipped: {skipped}")
        print("=" * 60)
        return 1 if failed else 0


def find_python() -> str:
    return sys.executable


def find_npm() -> str | None:
    return shutil.which("npm") or shutil.which("npm.cmd")


def find_docker() -> str | None:
    return shutil.which("docker")


def backend_checks(runner: Runner, mode: str) -> None:
    print("\n--- Backend ---")
    py = find_python()

    runner.run(
        "ruff",
        [py, "-m", "ruff", "check", "."],
        cwd=BACKEND,
        timeout=180,
    )

    runner.run(
        "science ledger",
        [py, "-m", "app.cli.science_ledger", "--check"],
        cwd=BACKEND,
        timeout=120,
    )

    pytest_env = None
    if IS_WINDOWS:
        tmp_root = ROOT / ".pytest_tmp"
        tmp_root.mkdir(parents=True, exist_ok=True)
        pytest_env = {"TMP": str(tmp_root), "TEMP": str(tmp_root)}

    markers = "core or research"
    if mode == "full":
        runner.run(
            "pytest (full suite)",
            [py, "-m", "pytest", "app/tests", "-q", "--timeout=600"],
            cwd=BACKEND,
            timeout=3600,
            env=pytest_env,
        )
    else:
        runner.run(
            f"pytest ({markers})",
            [py, "-m", "pytest", "app/tests", "-m", markers, "-q", "--timeout=300"],
            cwd=BACKEND,
            timeout=1800,
            env=pytest_env,
        )

    if runner.ci:
        runner.run(
            "mypy (research core)",
            [
                py,
                "-m",
                "mypy",
                "app/research",
                "app/core/animus/studio",
                "--ignore-missing-imports",
                "--no-error-summary",
            ],
            cwd=BACKEND,
            timeout=600,
            critical_in_ci=False,
        )


def frontend_checks(runner: Runner, mode: str) -> None:
    print("\n--- Frontend ---")
    npm = find_npm()
    if npm is None:
        runner.record("frontend", "fail" if runner.ci else "skip", "npm not found")
        return
    if not (FRONTEND / "node_modules").is_dir():
        runner.record("frontend", "fail" if runner.ci else "skip", "node_modules missing; run npm ci")
        return

    runner.run("eslint", [npm, "run", "lint"], cwd=FRONTEND, timeout=600)
    runner.run("tsc", [npm, "run", "typecheck"], cwd=FRONTEND, timeout=600)
    runner.run("vitest", [npm, "run", "test"], cwd=FRONTEND, timeout=900)
    runner.run("claim audit", [npm, "run", "audit:claims"], cwd=FRONTEND, timeout=300)
    if mode in {"ci", "full"}:
        runner.run("next build", [npm, "run", "build"], cwd=FRONTEND, timeout=1800)


def docker_checks(runner: Runner) -> None:
    print("\n--- Docker ---")
    docker = find_docker()
    if docker is None:
        runner.record("docker", "fail" if runner.ci else "skip", "docker not found")
        return
    for compose_file in ("docker-compose.yml", "docker-compose.release.yml"):
        path = ROOT / compose_file
        if not path.is_file():
            runner.record(f"compose {compose_file}", "skip", "file missing")
            continue
        runner.run(
            f"compose {compose_file}",
            [docker, "compose", "-f", str(path), "config", "--quiet"],
            cwd=ROOT,
            timeout=120,
            critical_in_ci=False,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the IMAGINA repository.")
    parser.add_argument("--quick", action="store_true", help="lint + focused tests (default)")
    parser.add_argument("--ci", action="store_true", help="CI profile; missing critical tools fail")
    parser.add_argument("--full", action="store_true", help="CI profile + full backend test suite")
    parser.add_argument("--mypy", action="store_true", help="run mypy even outside CI")
    parser.add_argument("--skip-backend", action="store_true")
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument("--skip-docker", action="store_true")
    args = parser.parse_args()

    mode = "full" if args.full else ("ci" if args.ci else "quick")
    runner = Runner(ci=mode in {"ci", "full"})

    print()
    print("=" * 60)
    print(f"  IMAGINA verification - mode: {mode}")
    print(f"  root: {ROOT}")
    print("=" * 60)

    if not args.skip_backend:
        backend_checks(runner, mode)
    if not args.skip_frontend:
        frontend_checks(runner, mode)
    if not args.skip_docker:
        docker_checks(runner)

    return runner.summary()


if __name__ == "__main__":
    raise SystemExit(main())
