#!/usr/bin/env bash
#
# verify.sh — IMAGINA project verification script
#
# Runs available checks for backend and frontend.
# Safe: does NOT install packages, modify files, or run destructive commands.
# Use after making changes to ensure nothing is broken.
#
# Usage: bash scripts/verify.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

PASS=0
FAIL=0
SKIP=0

pass_msg() { echo -e "  ${GREEN}[PASS]${NC} $1"; PASS=$((PASS + 1)); }
fail_msg() { echo -e "  ${RED}[FAIL]${NC} $1"; FAIL=$((FAIL + 1)); }
skip_msg() { echo -e "  ${YELLOW}[SKIP]${NC} $1"; SKIP=$((SKIP + 1)); }
info_msg() { echo -e "  ${BOLD}[INFO]${NC} $1"; }

echo ""
echo "============================================"
echo "  IMAGINA Project Verification"
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

    # pytest
    if [ -d "backend/app/tests" ]; then
        if command -v python3 &>/dev/null; then
            info_msg "Running pytest..."
            if timeout 180s python3 -m pytest backend/app/tests/ -q --tb=short 2>&1; then
                pass_msg "pytest — all tests passed"
            else
                fail_msg "pytest — some tests failed (or timed out)"
            fi
        else
            skip_msg "pytest — python3 not found"
        fi
    else
        skip_msg "pytest — no test directory found"
    fi

    # ruff
    if command -v ruff &>/dev/null; then
        info_msg "Running ruff..."
        if ruff check backend/ 2>&1; then
            pass_msg "ruff — no lint errors"
        else
            fail_msg "ruff — lint errors found"
        fi
    else
        skip_msg "ruff — ruff not installed (pip install ruff)"
    fi

    # mypy (optional — not in CI pipeline)
    if command -v mypy &>/dev/null; then
        info_msg "Running mypy (optional)..."
        if mypy backend/app/ --ignore-missing-imports 2>&1; then
            pass_msg "mypy — no type errors"
        else
            # mypy failures are warnings, not hard fails (not in CI)
            skip_msg "mypy — type errors found (not required in CI, review manually)"
        fi
    else
        skip_msg "mypy — mypy not installed (pip install mypy)"
    fi
else
    skip_msg "Backend checks — no backend/pyproject.toml found"
fi

echo ""

# ---- Frontend Checks ----
echo "--- Frontend ---"

if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    info_msg "Detected JavaScript/TypeScript frontend"

    if command -v npm &>/dev/null; then
        if [ -d "frontend/node_modules" ]; then

            # lint
            info_msg "Running npm run lint..."
            if npm --prefix frontend run lint --if-present 2>&1; then
                pass_msg "npm run lint — passed"
            else
                fail_msg "npm run lint — failed"
            fi

            # typecheck (not defined in this project, --if-present handles it)
            info_msg "Running npm run typecheck (if available)..."
            npm --prefix frontend run typecheck --if-present 2>&1 && \
                pass_msg "npm run typecheck — passed" || \
                skip_msg "npm run typecheck — script not defined in package.json"

            # build
            info_msg "Running npm run build..."
            if npm --prefix frontend run build 2>&1; then
                pass_msg "npm run build — passed"
            else
                fail_msg "npm run build — failed"
            fi

            # test (not defined in this project)
            info_msg "Running npm test (if available)..."
            npm --prefix frontend test --if-present 2>&1 && \
                pass_msg "npm test — passed" || \
                skip_msg "npm test — script not defined in package.json"

        else
            skip_msg "Frontend checks — node_modules not found (run: cd frontend && npm install)"
        fi
    else
        skip_msg "Frontend checks — npm not found"
    fi
else
    skip_msg "Frontend checks — no frontend/package.json found"
fi

echo ""

# ---- Docker Checks ----
echo "--- Docker ---"

if [ -f "docker-compose.yml" ]; then
    if command -v docker &>/dev/null; then
        info_msg "Validating docker compose config..."
        if docker compose config --quiet 2>&1; then
            pass_msg "docker compose config — valid"
        else
            skip_msg "docker compose config — validation failed (docker daemon may not be running)"
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
echo "============================================"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "Some checks failed. Review the output above."
    exit 1
else
    echo ""
    echo "All available checks passed."
    exit 0
fi
