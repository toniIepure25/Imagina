#!/usr/bin/env bash
#
# ai_context.sh — Generate an AI context snapshot of the IMAGINA repository
#
# Uses repomix to create a packed repository snapshot in docs/ai/repo_snapshot.md
# that AI agents can read for full project context without loading every file.
#
# Prerequisites: repomix (install with: npm install -g repomix)
#
# Usage: bash scripts/ai_context.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "IMAGINA AI Context Snapshot Generator"
echo "======================================"
echo ""

if ! command -v repomix &>/dev/null; then
    echo "ERROR: repomix is not installed."
    echo ""
    echo "Install it with:"
    echo "  npm install -g repomix"
    echo ""
    echo "Or use npx:"
    echo "  npx repomix --config repomix.config.json"
    exit 1
fi

if [ ! -f "repomix.config.json" ]; then
    echo "ERROR: repomix.config.json not found in project root."
    echo "Run this script from the IMAGINA project root directory."
    exit 1
fi

echo "Running repomix with config repomix.config.json..."
echo ""

repomix --config repomix.config.json

echo ""
echo "Snapshot generated at docs/ai/repo_snapshot.md"
echo ""

SNAPSHOT_FILE="docs/ai/repo_snapshot.md"

if [ -f "$SNAPSHOT_FILE" ]; then
    SNAPSHOT_SIZE=$(wc -c < "$SNAPSHOT_FILE")
    SNAPSHOT_LINES=$(wc -l < "$SNAPSHOT_FILE")
    echo "Snapshot size: ${SNAPSHOT_SIZE} bytes, ${SNAPSHOT_LINES} lines"

    # Check for actual nested git internals (frontend/.git/ with trailing
    # slash matches dir contents like objects/, hooks/, config, HEAD, index).
    # This intentionally does NOT match frontend/.gitignore or doc references
    # to frontend/.git (no trailing slash) which are false positives.
    NESTED_GIT_PATTERN='<file path="frontend/\.git/(objects|hooks|info|logs|refs|COMMIT_EDITMSG|config|description|HEAD|index|packed-refs)'

    if grep -qE "$NESTED_GIT_PATTERN" "$SNAPSHOT_FILE" 2>/dev/null; then
        NESTED_GIT_COUNT=$(grep -cE "$NESTED_GIT_PATTERN" "$SNAPSHOT_FILE" 2>/dev/null)
    else
        NESTED_GIT_COUNT=0
    fi

    if [ "$NESTED_GIT_COUNT" -gt 0 ]; then
        echo ""
        echo "============================================================"
        echo "  WARNING: Snapshot contains $NESTED_GIT_COUNT references to"
        echo "  frontend/.git internal files — nested git should be excluded."
        echo "  Check repomix.config.json ignore patterns."
        echo "============================================================"
        exit 1
    fi
	echo ""
    echo "Snapshot is clean — no nested .git paths detected."
    echo "Done."
else
    echo "WARNING: Snapshot file was not created. Check repomix output for errors."
    exit 1
fi
