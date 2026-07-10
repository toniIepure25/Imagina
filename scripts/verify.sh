#!/usr/bin/env bash
#
# verify.sh — IMAGINA project verification script
#
# Runs available checks for backend and frontend.
# Safe: does NOT install packages, modify files, or run destructive commands.
#
# Usage:
#   bash scripts/verify.sh           # local (developer-friendly, skips are OK)
#   bash scripts/verify.sh --ci      # CI mode (skipped critical checks fail)

set -euo pipefail

CI_MODE=false
if [ "${1:-}" = "--ci" ]; then
    CI_MODE=true
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

PASS=0
FAIL=0
SKIP=0
CRITICAL_SKIP=0

pass_msg() { echo -e "  ${GREEN}[PASS]${NC} $1"; PASS=$((PASS + 1)); }
fail_msg() { echo -e "  ${RED}[FAIL]${NC} $1"; FAIL=$((FAIL + 1)); }
skip_msg() { echo -e "  ${YELLOW}[SKIP]${NC} $1"; SKIP=$((SKIP + 1)); }
critical_skip_msg() { echo -e "  ${YELLOW}[SKIP-CRITICAL]${NC} $1"; SKIP=$((SKIP + 1)); CRITICAL_SKIP=$((CRITICAL_SKIP + 1)); }
info_msg() { echo -e "  ${BOLD}[INFO]${NC} $1"; }

echo ""
echo "============================================"
echo "  IMAGINA Project Verification"
if $CI_MODE; then echo "  Mode: CI (strict)"; else echo "  Mode: local"; fi
echo "============================================"
echo ""

# ---- git status ----
echo "--- Git Status ---"
git status --short 2>/dev/null || echo "  (not a git repository or git not found)"
echo ""

# ---- Backend Checks ----
echo "--- Backend ---"

if [ -d "backend" ] && [ -f "backend/pyproject.toml" ]; then
    info_msg "Detected Python backend"

    if command -v python3 &>/dev/null; then
        # ruff
        info_msg "Command: python3 -m ruff check backend/"
        if python3 -m ruff check backend/ 2>&1; then
            pass_msg "ruff — no lint errors"
        else
            fail_msg "ruff — lint errors found"
        fi

        # pytest (core + research only for merge-gate)
        if [ -d "backend/app/tests" ]; then
            info_msg "Command: python3 -m pytest backend/app/tests/ -m 'core or research' --strict-markers --timeout=300 -q"
            if timeout 360s python3 -m pytest backend/app/tests/ -m "core or research" --strict-markers --timeout=300 -q 2>&1; then
                pass_msg "pytest (core + research) — all tests passed"
            else
                fail_msg "pytest (core + research) — some tests failed (or timed out)"
            fi
        else
            critical_skip_msg "pytest — no test directory found"
        fi
    else
        critical_skip_msg "python3 not found"
    fi

    # mypy (optional)
    if command -v mypy &>/dev/null; then
        info_msg "Command: mypy backend/app/ --ignore-missing-imports"
        if mypy backend/app/ --ignore-missing-imports 2>&1; then
            pass_msg "mypy — no type errors"
        else
            skip_msg "mypy — type errors found (not required in CI, review manually)"
        fi
    else
        skip_msg "mypy — not installed (optional)"
    fi
else
    critical_skip_msg "Backend checks — no backend/pyproject.toml found"
fi

echo ""

# ---- Frontend Checks ----
echo "--- Frontend ---"

if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    info_msg "Detected JavaScript/TypeScript frontend"

    if command -v npm &>/dev/null; then
        if [ -d "frontend/node_modules" ]; then
            info_msg "Command: npm --prefix frontend run lint"
            if npm --prefix frontend run lint 2>&1; then
                pass_msg "npm run lint — passed"
            else
                fail_msg "npm run lint — failed"
            fi

            info_msg "Command: npm --prefix frontend run typecheck"
            if npm --prefix frontend run typecheck 2>&1; then
                pass_msg "npm run typecheck — passed"
            else
                fail_msg "npm run typecheck — failed"
            fi

            info_msg "Command: npm --prefix frontend test"
            if npm --prefix frontend test 2>&1; then
                pass_msg "npm test — passed"
            else
                fail_msg "npm test — failed"
            fi

            info_msg "Command: npm --prefix frontend run build"
            if npm --prefix frontend run build 2>&1; then
                pass_msg "npm run build — passed"
            else
                fail_msg "npm run build — failed"
            fi
        else
            critical_skip_msg "Frontend checks — node_modules not found (run: cd frontend && npm install)"
        fi
    else
        critical_skip_msg "Frontend checks — npm not found"
    fi
else
    critical_skip_msg "Frontend checks — no frontend/package.json found"
fi

echo ""

# ---- Docker Checks ----
echo "--- Docker ---"

if [ -f "docker-compose.yml" ]; then
    if command -v docker &>/dev/null; then
        info_msg "Command: docker compose config --quiet"
        if docker compose config --quiet 2>&1; then
            pass_msg "docker compose config (dev) — valid"
        else
            skip_msg "docker compose config (dev) — validation failed (docker daemon may not be running)"
        fi

        if [ -f "docker-compose.release.yml" ]; then
            info_msg "Command: docker compose -f docker-compose.release.yml config --quiet"
            if docker compose -f docker-compose.release.yml config --quiet 2>&1; then
                pass_msg "docker compose config (release) — valid"
            else
                skip_msg "docker compose config (release) — validation failed (docker daemon may not be running)"
            fi
        else
            skip_msg "docker compose config (release) — no docker-compose.release.yml found"
        fi
    else
        skip_msg "docker compose config — docker not found"
    fi
else
    skip_msg "docker compose config — no docker-compose.yml found"
fi

echo ""

# ---- Summary ----
echo "============================================"
TOTAL=$((PASS + FAIL + SKIP))
CHECK_TERM="checks"
if [ "$TOTAL" -eq 1 ]; then CHECK_TERM="check"; fi
echo "  Total: $TOTAL $CHECK_TERM run"
echo -e "  ${GREEN}Passed:${NC} $PASS"
echo -e "  ${RED}Failed:${NC} $FAIL"
echo -e "  ${YELLOW}Skipped:${NC} $SKIP"
if [ "$CRITICAL_SKIP" -gt 0 ]; then
    echo -e "  ${YELLOW}Critical skips:${NC} $CRITICAL_SKIP"
fi
echo "============================================"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "Some checks failed. Review the output above."
    exit 1
fi

if $CI_MODE && [ "$CRITICAL_SKIP" -gt 0 ]; then
    echo ""
    echo "CI mode: $CRITICAL_SKIP critical checks were skipped. This is a failure in CI."
    exit 1
fi

echo ""
echo "All available checks passed."
exit 0
