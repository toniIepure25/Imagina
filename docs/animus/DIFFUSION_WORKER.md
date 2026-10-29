# Diffusion worker runbook (A100, not attached)

Status: **contract and deployment plan only**. Nothing in this repository downloads weights, starts a GPU, or calls
a remote model by default. `imagine_enable_remote_diffusion=False` is the shipped configuration.

The local app must remain honest when the worker is absent: capabilities report `blocked`, `POST /jobs` returns
`503 diffusion_unavailable`, no job file is written, and the first-person stage stays procedural.

## Why a separate worker

The IMAGINA backend is a local FastAPI process on `127.0.0.1:8000`. It owns the SQLite database, session stream, and
local-first privacy boundary. A diffusion model needs a GPU, large weights, and a different failure domain. Keeping
the worker separate means:

- the default install stays small and CPU-only;
- a GPU crash cannot take down the local session API;
- the worker has no database access and never receives raw signals;
- the contract can be tested with a mock before any GPU exists.

## Contract

The worker accepts `IMAGINA-DIFFUSION-REQUEST-v2` and returns a job id. The local backend polls and downloads
artifacts; the browser never talks to the worker directly.

### Worker endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | `200` with `{ "status": "ok", "model_slot": "scene-diffusion-v0" }` |
| `POST` | `/v1/jobs` | accept a request; `202` with `{ "job_id", "state": "queued", "stage" }` |
| `GET` | `/v1/jobs/{job_id}` | state, stage, optional manifest, optional error |
| `POST` | `/v1/jobs/{job_id}/cancel` | idempotent cancellation |
| `GET` | `/v1/jobs/{job_id}/assets/{name}` | skybox or preview bytes |

States: `queued`, `running`, `cancelling`, `cancelled`, `succeeded`, `failed`.

The worker must reject requests with unknown fields. The local `ImagineJobRequest` already forbids extras, so a
`session_id`, raw sample array, or arbitrary URL cannot be smuggled through.

### Request shape

The canonical request is defined in `backend/app/schemas/imagine.py` and built in
`frontend/lib/imagine/request.ts`. It contains:

- `brief`: prompt, negative prompt, style, seed;
- `conditioning`: 16 values, quality, uncertainty, trend, stability, adapter version, vector hash;
- `controls`: clarity, fog, motion, saturation, detail, glow, camera pace, depth falloff;
- `camera`: first-person start, one-point path, fov;
- `adaptive`: target id and slow-loop rate;
- `output`: skybox `4096×2048`, preview `1280×720`, no materials;
- `provenance`: composer, policy, app versions;
- `boundary`: the sentence the worker must preserve.

It does **not** contain `session_id`, raw EEG/HRV/EDA, participant identifiers, or free-form asset URLs.

### Manifest shape

`IMAGINA-DIFFUSION-MANIFEST-v1` is validated by `backend/app/schemas/imagine.py` and
`frontend/lib/imagine/manifest.ts`:

- `model_slot`, `model_hash`, `seed`, `prompt_hash`, `conditioning_hash`;
- `controls`;
- `skybox` and `preview` with `url`, `width`, `height`, `sha256`;
- `created_at`, `expires_at`;
- `provenance`.

The backend downloads both assets, verifies SHA-256, rejects non-PNG/JPEG/WebP bytes, rewrites the URLs to local
`/animus/imagine/assets/{asset_id}` paths, and stores them under `data/imagine/artifacts/`. The browser only sees
local asset URLs on the local API origin.

## Local configuration

Add to `backend/.env` (never commit it):

```text
IMAGINE_ENABLE_REMOTE_DIFFUSION=false
IMAGINE_DIFFUSION_URL=
IMAGINE_DIFFUSION_TOKEN=
IMAGINE_DIFFUSION_TIMEOUT_SECONDS=180
IMAGINE_ASSET_TTL_HOURS=24
IMAGINE_DATA_DIR=./data/imagine
```

Enable only after the worker health check is reachable from the backend host:

```text
IMAGINE_ENABLE_REMOTE_DIFFUSION=true
IMAGINE_DIFFUSION_URL=https://worker.example.internal
IMAGINE_DIFFUSION_TOKEN=<secret from the worker deployment>
```

The token is sent as `Authorization: Bearer …`. The backend does not log it. TLS is required outside localhost.

## Model slot

`scene-diffusion-v0` is a slot, not a benchmark result. Candidate stack:

- base: SDXL-Turbo for a single fast pass, with SDXL base as a fallback;
- control: depth and segmentation derived from the symbolic `SceneGraph`;
- panorama: tiled equirectangular sampling with seam blending;
- output: one skybox and one preview, no video in v1.

The slot may change only after measuring image validity, seam quality, prompt adherence, and runtime on the target
A100. No model/VRAM claim in this repository is a benchmark.

## Security and privacy

- Worker binds inside a private network or behind TLS; bearer token required for every route.
- The local backend is the only client. The browser never receives the worker token.
- The worker stores request metadata and artifacts for at most one hour, then deletes them.
- The local backend keeps jobs for 24 hours and deletes artifacts on job deletion or expiry.
- No raw neural or physiological stream, participant id, or database row is sent.
- The worker must not train on, retain for training, or republish user prompts.
- Artifact downloads are limited to 64 MB and to the worker origin. Redirects are not followed.
- A malformed or expired manifest fails closed: the UI stays on the procedural sky.

## Deployment acceptance

Before enabling the lane:

1. `GET /health` returns `ok` and the expected model slot from the backend host.
2. A request with the full 16D vector completes within 180 s.
3. Manifest checksums match downloaded bytes.
4. A cancelled job stops consuming GPU work.
5. Killing the worker mid-job yields `failed / worker_timeout`, not a hung UI.
6. The browser network panel shows no request to the worker origin.
7. The stage still works with the worker disabled.
8. Claim audit remains PASS and no copy calls the output a reconstruction or measurement.

## Rollback

Set `IMAGINE_ENABLE_REMOTE_DIFFUSION=false`, restart the backend, and delete `data/imagine`. The UI reads
capabilities on load and returns to the blocked state without a code change. No database migration is involved.
