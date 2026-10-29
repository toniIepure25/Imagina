# Release engineering

This document describes how to build, run, and verify the release containers.

## Images

| Image | Dockerfile | Notes |
|---|---|---|
| Backend | `backend/Dockerfile.release` | Python 3.12 slim, installs the project from `pyproject.toml`, runs as UID 10001 |
| Frontend | `frontend/Dockerfile.release` | Node 22 Alpine, multi-stage build, runs `next start`, runs as UID 10001 |

Both images define a `HEALTHCHECK`. The backend checks `/api/health`; the frontend checks `/`.

## Build

```bash
docker build -f backend/Dockerfile.release -t imagina-backend:local backend
docker build -f frontend/Dockerfile.release -t imagina-frontend:local frontend
```

The backend accepts optional extras, for example:

```bash
docker build -f backend/Dockerfile.release \
  --build-arg IMAGINA_EXTRAS="[science]" \
  -t imagina-backend:science backend
```

Do not include `neural` in a default release image unless the target machine is
expected to carry the full PyTorch/MNE stack; it substantially increases image
size and build time.

## Frontend API configuration

`NEXT_PUBLIC_*` variables are **inlined at build time**. Set them as build
arguments, not only as runtime environment variables:

```bash
docker build -f frontend/Dockerfile.release \
  --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 \
  --build-arg NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 \
  -t imagina-frontend:local frontend
```

The code currently reads both `NEXT_PUBLIC_API_URL` and
`NEXT_PUBLIC_API_BASE_URL` in different modules; set both until they are
unified.

## Run

```bash
docker compose -f docker-compose.release.yml up --build
```

Open `http://localhost:3000/animus`. The backend creates and migrates the
SQLite schema on startup. The compose stack mounts `./data` into `/app/data`.

## Verification

CI builds both release images, starts them, waits for health, and asserts that
neither container runs as root (`release-images` job). Locally:

```bash
docker build -f backend/Dockerfile.release -t imagina-backend:local backend
docker run --rm -d --name imagina-backend-local -p 8000:8000 imagina-backend:local
curl -sf http://localhost:8000/api/health
docker rm -f imagina-backend-local
```

A local Docker daemon is required; the repository's `verify.py` reports Docker
as SKIP when it is unavailable.

## Data and permissions

The image runs as a non-root user. On Linux, the mounted `./data` directory must
be writable by UID 10001:

```bash
sudo chown -R 10001:10001 data
```

Do not run release containers on an untrusted network. See `SECURITY.md`.
