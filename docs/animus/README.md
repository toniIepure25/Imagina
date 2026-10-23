# ANIMUS Studio

A local-first, closed-loop imagination amplifier built on the existing IMAGINA platform.

The loop is the product:

```
describe → see a procedural candidate → correct → lock what is right →
regenerate controlled variations → keep / undo / branch → save a world → reopen
```

The scene is a symbolic, editable **ANIMUS-SG-v1** graph. Candidates are deterministic procedural
previews rendered with React Three Fiber — not images from a model, and not decoded neural content.

## Run locally

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

cd frontend
npm run dev
```

Open `http://localhost:3000/animus`. The backend creates/migrates the local SQLite schema (migrations
v014–v017) on startup. No account, network service, or API key is required. The backend defaults to
`127.0.0.1`, validates the `Host` header, and marks Studio responses `no-store`; do not bind it to a public
interface without adding authentication and an explicit `ALLOWED_HOSTS` value.

Mutations are serialized per session and persisted atomically. Before a non-empty database is upgraded, the
backend writes and integrity-checks a `VACUUM INTO` recovery copy under `<db_dir>/backups/` and keeps the
five newest; if that copy fails, startup aborts rather than migrating without a recovery point. The web
client sends
`X-Expected-Version` for optimistic concurrency, retries transient reads, distinguishes 404/503/timeout
states, and treats `409 stale_version` as "refresh and continue". Redo stacks and event history survive a
backend restart; durable event `seq` values let the client ignore duplicates and resync immediately on a
gap. See [API_CONTRACT.md](API_CONTRACT.md).

## Product routes

| Route | Purpose |
|---|---|
| `/animus` | Intention composer, recent sessions, saved worlds |
| `/animus/studio/[sessionId]` | Scene canvas, prompt bar, candidates, inspector, history |
| `/animus/worlds` | Saved world library; reopen or delete |
| `/animus/about` | Capability envelope and scientific boundaries |

The legacy `/imagina/animus` route redirects to `/animus`. The P1 research API under `/animus/*` is
unchanged and remains available for its own clients.

## What is intentionally absent

- No image-generation model, diffusion pipeline, or external renderer.
- No neural, dream, or imagery-content decoding.
- No uploads, accounts, telemetry, or cloud sync.
- No clinical or diagnostic claim; claim ceiling is `L1_BEHAVIORAL_ASSISTED`.

## Verification

Backend (from `backend/`):

```powershell
python -m pytest app/tests/test_animus_scene_model.py app/tests/test_animus_scene_commands.py `
  app/tests/test_animus_scene_revisions.py app/tests/test_animus_studio_intent.py `
  app/tests/test_animus_studio_persistence.py app/tests/test_animus_studio_api.py `
  app/tests/test_animus_studio_integrity.py app/tests/test_animus_studio_claims.py -q -p no:cacheprovider
python -m ruff check --no-cache app/core/animus app/api/animus_studio.py app/schemas/animus_studio.py
```

Frontend (from `frontend/`):

```powershell
node node_modules/typescript/bin/tsc --noEmit --incremental false
node node_modules/eslint/bin/eslint.js app/animus components/animus lib/animusStudioApi.ts lib/useAnimusStudio.ts
node node_modules/vitest/vitest.mjs run lib/__tests__/animus-studio.test.ts
node node_modules/next/dist/bin/next build
node scripts/verify-animus-ui.cjs
```

`verify-animus-ui.cjs` drives a real local Chrome/Edge through the full loop (intention, correction,
element lock, candidate generation, keep, undo, save world, reload, worlds library, redirect, about page,
mobile overflow) and fails on browser console errors. It writes screenshots to
`docs/animus/01–06-*.png`.

## Documentation

- [Product vision](ANIMUS_PRODUCT_VISION.md)
- [Architecture](ANIMUS_ARCHITECTURE.md)
- [API contract](API_CONTRACT.md)
- [Claims boundary](ANIMUS_CLAIMS_BOUNDARY.md)
- [Roadmap](ANIMUS_ROADMAP.md)
- [Demo script](DEMO_SCRIPT.md)
