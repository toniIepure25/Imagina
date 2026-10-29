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
v014–v021) on startup. No account, network service, or API key is required. The backend defaults to
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
| `/animus/studio/[sessionId]` | Versioned workbench: Stage, Structure, Ledger, direct transforms, candidate/version preview |
| `/animus/imagine` | Imagine 2.0: stage-first first-person lab, 16D conditioning, adaptive trace/scenarios, fail-closed diffusion lane |
| `/animus/practice/[sessionId]` | Adaptive scene practice; deterministic tasks and local scoring |
| `/animus/interview/[sessionId]` | Epistemic interview; binary probes, posterior reconstruction, and uncertainty |
| `/animus/observatory/[sessionId]` | Scene Threshold contrast task, confidence atlas, evidence trail, and test–retest reliability |
| `/animus/profile` | Experimental behavioural estimates, calibration, and limits |
| `/animus/worlds` | Saved world library; reopen or delete |
| `/animus/about` | Capability envelope and scientific boundaries |

The legacy `/imagina/animus` route redirects to `/animus`. The P1 research API under `/animus/*` is
unchanged and remains available for its own clients.

## Workbench

The Studio is three synchronized views over one immutable version graph. **Stage** supports orbit, selection,
direct transform, lock, and correction; **Structure** is a top-down, keyboard-operable move and relation editor;
**Ledger** shows branch lanes, preview, and branching. Preview is explicitly read-only: a candidate or historical
version can be inspected without changing the head. Keep commits a candidate; Branch creates a branch from a
previewed version; Return restores the head. A first-look gate asks for a starting image before a new scene is
revealed, and its notes never leave the tab.

Stage also carries a **Timecode** strip for in-place version preview, spatial **Changes/Sources** rings, a
**Palimpsest** trace of moved and removed entities’ previous positions, a **Comparison Chamber** for a
shared-camera side-by-side look at head and preview, and a **Shot** deck (Wide, Eye, Detail, Top). Preview
comparisons are explicitly head-relative, and a local `?version=…` link restores the inspected state after reload.
The chamber can be opened from the preview banner/panel, the command palette, or `C`; it never discards or commits
the preview. The research basis and its limits are in [RESEARCH_2_0.md](RESEARCH_2_0.md) and
[COMPARISON_RESEARCH.md](COMPARISON_RESEARCH.md).

Keyboard: `1/2/3` switch views, `[`/`]` step versions, `C` compare preview with head, `G/R/S` select transform
mode, `F` focus, `L` lock, `Esc` close the chamber before the preview, `?` shortcuts, `Ctrl/Cmd+K` command palette.
Transform commands clamp position to `±256` and scale to `0.01–64`; failed commands restore the prior visual state.
See [WORKBENCH_SPEC.md](WORKBENCH_SPEC.md) for the state model, accessibility contract, and verification matrix.

## Experimental measurement

`/animus/profile` reports five separate behavioural estimates from adaptive scene practice: object detail,
discrimination, spatial structure, edit control, and confidence calibration. Object reconstruction uses a
token bank and F1; spatial layout uses normalized placement and position error. Each estimate shows its
trial count, uncertainty, and status; there is no composite score. A descriptive error signature reports
omissions, intrusions, and mean spatial error. Tasks are deterministic and scored on the server, so answers,
target flags, and target positions are not sent to the browser before submission. The model, the task
simplifications, and the claim limits are in [MEASUREMENT_MODEL.md](MEASUREMENT_MODEL.md) and
[RECONSTRUCTION_SPEC.md](RECONSTRUCTION_SPEC.md); the selection rule is in
[ADAPTIVE_POLICY.md](ADAPTIVE_POLICY.md); the proposed independent study is in
[VALIDATION_PROTOCOL.md](VALIDATION_PROTOCOL.md). The profile is experimental and `clinical_use = DISABLED`.

The epistemic interview is a separate behavioural surface. After a timed scene preview, it asks binary
object-presence and spatial-relation probes against the hidden symbolic scene, updates a Beta posterior from the answer and
confidence, and selects later probes by expected information gain. It reports object/spatial accuracy,
mean Brier, coverage, abstention, overconfidence, and entropy separately. There is no composite score and no
claim that the posterior is a neural image. See [EPISTEMIC_INTERVIEW_SPEC.md](EPISTEMIC_INTERVIEW_SPEC.md).

Scene Threshold adds a contrastive 2-AFC task. After one timed encoding view, the person sees pairs that
differ only in object presence, spatial position, or colour. An adaptive 2-down/1-up staircase concentrates
trials near the person's threshold, while the reported estimate comes from a fitted 75%-correct
psychometric function. The summary separates d′, side bias, per-feature thresholds, Brier/overconfidence,
and coverage. The observatory overlays the belief layer, evidence provenance, and test–retest reliability
without a composite score. See [CONTRAST_SPEC.md](CONTRAST_SPEC.md) and
[OBSERVATORY_SPEC.md](OBSERVATORY_SPEC.md).

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
  app/tests/test_animus_studio_integrity.py app/tests/test_animus_studio_claims.py `
  app/tests/test_animus_studio_reconstruction.py app/tests/test_animus_studio_adaptive.py `
  app/tests/test_animus_studio_simulation.py app/tests/test_animus_epistemic.py `
  app/tests/test_animus_epistemic_api.py app/tests/test_animus_epistemic_sim.py `
  app/tests/test_animus_contrast.py app/tests/test_animus_contrast_api.py `
  app/tests/test_animus_observatory.py app/tests/test_animus_contrast_sim.py `
  -q -p no:cacheprovider
python -m ruff check --no-cache app/core/animus app/api/animus_studio.py app/schemas/animus_studio.py
```

Frontend (from `frontend/`):

```powershell
node node_modules/typescript/bin/tsc --noEmit --incremental false
node node_modules/eslint/bin/eslint.js app/animus components/animus lib/animusStudioApi.ts lib/useAnimusStudio.ts
node node_modules/vitest/vitest.mjs run
node node_modules/next/dist/bin/next build
node scripts/verify-animus-ui.cjs
```

`verify-animus-ui.cjs` drives a real local Chrome/Edge through the full loop (intention, correction,
element lock, candidate generation, comparison chamber, keep, undo, save world, reload, worlds library, redirect,
about page, mobile overflow) and fails on browser console errors. It writes screenshots to
`docs/animus/01–06-*.png`, including `03d-studio-chamber.png`. The Imagine lab captures are
`07-imagine-desktop.png`, `07b-animus-imagine-entry.png`, `07c-imagine-mobile.png`, and
`07d-imagine-adaptive.png`.

## Documentation

- [Product vision](ANIMUS_PRODUCT_VISION.md)
- [Interface principles](INTERFACE_PRINCIPLES.md)
- [Comparison chamber research](COMPARISON_RESEARCH.md)
- [Imagine lab and diffusion handoff](IMAGINE_LAB.md)
- [A100 diffusion worker runbook](DIFFUSION_WORKER.md)
- [Architecture](ANIMUS_ARCHITECTURE.md)
- [API contract](API_CONTRACT.md)
- [Reconstruction spec](RECONSTRUCTION_SPEC.md)
- [Adaptive policy](ADAPTIVE_POLICY.md)
- [Epistemic interview spec](EPISTEMIC_INTERVIEW_SPEC.md)
- [Scene Threshold spec](CONTRAST_SPEC.md)
- [Observatory spec](OBSERVATORY_SPEC.md)
- [Measurement model](MEASUREMENT_MODEL.md)
- [Claims boundary](ANIMUS_CLAIMS_BOUNDARY.md)
- [Roadmap](ANIMUS_ROADMAP.md)
- [Demo script](DEMO_SCRIPT.md)
