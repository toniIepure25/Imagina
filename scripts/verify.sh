#!/usr/bin/env bash
# Thin wrapper around scripts/verify.py for bash users.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "python not found" >&2
    exit 127
fi
exec "$PY" "$DIR/verify.py" "$@"
