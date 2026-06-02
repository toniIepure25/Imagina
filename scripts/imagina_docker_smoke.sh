#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== IMAGINA V27 Docker Smoke Test ==="

cd "$ROOT_DIR"

if ! command -v docker &> /dev/null; then
    echo "[SKIP] Docker not available. Install Docker to run this smoke test."
    exit 0
fi

echo "[1/7] Building containers..."
docker compose -f docker-compose.release.yml build --quiet 2>&1 | tail -3

echo "[2/7] Starting services..."
docker compose -f docker-compose.release.yml up -d 2>&1 | tail -3

echo "[3/7] Waiting for backend health..."
for i in $(seq 1 30); do
    if curl -s -o /dev/null http://localhost:8000/api/imagina/system/health 2>/dev/null; then
        echo "  Backend healthy after ${i}s"
        break
    fi
    sleep 1
done

echo "[4/7] Seeding demo data..."
docker compose -f docker-compose.release.yml run --rm imagina-demo-seed python3 -m app.cli.imagina_demo full 2>&1 | tail -3

echo "[5/7] Building showcase..."
curl -s -X POST http://localhost:8000/api/imagina/showcase/demo_user/build | python3 -m json.tool 2>/dev/null | head -3

echo "[6/7] Checking frontend..."
for i in $(seq 1 30); do
    if curl -s -o /dev/null http://localhost:3000/imagina/showcase 2>/dev/null; then
        echo "  Frontend ready after ${i}s"
        break
    fi
    sleep 1
done

echo ""
echo "=== IMAGINA URLs ==="
echo "  Frontend:    http://localhost:3000/imagina"
echo "  Showcase:    http://localhost:3000/imagina/showcase"
echo "  Backend API: http://localhost:8000/docs"
echo "====================="
