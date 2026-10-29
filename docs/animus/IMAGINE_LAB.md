# Imagine lab 2.0 — stage-first, adaptive, diffusion-ready

Status: **local procedural default; diffusion lane blocked until an A100 worker exists**. Route: `/animus/imagine`.
Claim ceiling: `L1_BEHAVIORAL_ASSISTED`.

The lab is a design instrument for the scene-generation target, not a running diffusion service. It makes four things
concrete today:

1. an initial text description is a first-class input;
2. a 16-dimensional derived conditioning vector is visible, inspectable, and mapped to aesthetic controls;
3. the scene is viewed in first person, with pointer lock, touch movement, collision, reset, and fullscreen;
4. a fail-closed backend contract and a mock-tested job state machine are ready for the future worker.

The renderer is now the **Lumen** layered world engine on top of the ANIMUS symbolic `SceneGraph` renderer. No image,
video, or latent diffusion model is loaded. The local scene is still symbolic geometry, not generated imagery. See
[`LUMEN_WORLD_ENGINE.md`](./LUMEN_WORLD_ENGINE.md) for the grammar, composer, presets, renderer, and staged diffusion
path.

## What runs now

```text
text brief ─► prompt compiler ─┐
                              ├─► local procedural SceneGraph ─► first-person R3F
16D conditioning ─► policy ───┘                 │
                                                └─► IMAGINA-DIFFUSION-REQUEST-v2 (opt-in, blocked without worker)
```

- `frontend/lib/imagineScene.ts` — brief types, diffusion job/request helpers, legacy compatibility, and the
  `buildImagineScene` facade that delegates to the Lumen composer.
- `frontend/lib/imagine/world.ts` — deterministic world grammar and `WorldSpec`.
- `frontend/lib/imagine/composeWorld.ts` — layered, provenance-bearing `SceneGraph` composition.
- `frontend/lib/imagine/presets.ts` — five starter worlds and `?preset=` lookup.
- `frontend/lib/imagine/conditioning.ts` — 16D vector, quality gate, aesthetic controls.
- `frontend/lib/imagine/policy.ts` — capped adaptive policy with deadband, hysteresis, dwell, and safety holds.
- `frontend/lib/imagine/scenarios.ts` — `steady`, `drift`, `load`, `settle`, all simulated.
- `frontend/lib/imagine/request.ts` — request v2 builder.
- `frontend/lib/imagine/client.ts` — capabilities, jobs, cancellation, asset URL.
- `frontend/lib/imagine/manifest.ts` — manifest validation and local-origin asset allowlist.
- `frontend/components/imagine/ImagineLab.tsx` — stage-first shell, world strip, composer, tabs, adaptive trace,
  diffusion lane.
- `frontend/components/imagine/ImagineStage.tsx` — first-person chrome, scene lens, touch joystick, coach mark,
  badges.
- `frontend/components/animus/world/` — sky, terrain/path, practical lights, motes, architecture bodies, bloom.
- `backend/app/api/imagine.py` — capabilities, jobs, cancel/delete, local asset serving.
- `backend/app/core/imagine/` — service, file store, remote provider boundary.

## Stage-first UI

Desktop layout: a 68 px top bar, a composer rail (322 px), the stage in the center, and an instrument rail (372 px)
with four tabs:

- **Signals** — radar of the 16 dimensions, six primary sliders, quality gate, bands/physiology accordion;
- **Adaptive** — target, loop switch, coherence, trace, reason, simulated scenarios;
- **Diffusion** — capabilities, consent, job states, preview, skybox toggle, request download;
- **Provenance** — geometry and texture provenance, controls, model/seed when a manifest exists.

The stage adds a world strip above the prompt, a scene-read overlay (desktop), a Scene/Signals/Off lens, a walk/look
coach mark, and a refined first-person crosshair.

Mobile: the stage comes first at 64 vh, followed by the world strip and composer. The instrument rail opens as a
full-height sheet from the **Signals** button, with an explicit **Close** action. The touch joystick appears in first
person. The layout has no horizontal overflow at 390 px.

## 16D conditioning

| Group | Dimensions |
| --- | --- |
| State proxies | attention, arousal, valence, vividness, fatigue, confidence |
| Band proxies | theta, alpha, beta, gamma |
| Physiology proxies | hrv, eda |
| Meta | signal_quality, uncertainty, trend, stability |

`signal_quality` is a demo control. The quality gate holds influence below 0.35, so a noisy or degraded vector does
not silently drive the scene. `trend` and `stability` are computed from a 30-sample history; they are not clinical
measurements.

The eight aesthetic controls are `clarity`, `fog`, `motion`, `saturation`, `detail`, `glow`, `cameraPace`, and
`depthFalloff`. Text owns semantics. Signals tune atmosphere and pace; they never choose objects, people, or meaning.

## Signal mapping

| Channel | Scene effect | Honest status |
| --- | --- | --- |
| Attention | fine structure and far-field clarity | demo control |
| Arousal | motion, shimmer, camera pace | demo control |
| Valence | warm/cool palette and saturation | demo control |
| Vividness | density, emissive light, glow | demo control |
| Fatigue | fog, reduced clarity, safety stop | demo control |
| Confidence | stability and color confidence | demo control |
| Theta / alpha / beta / gamma | drift, glow, detail, shimmer | exposed for future conditioning |
| HRV / EDA | motion smoothness, arousal coupling | exposed for future conditioning |
| Quality / uncertainty / trend / stability | gating and provenance | derived demo meta |

All values are local UI state. Nothing is measured from a person, and no device is connected.

## First person

- Default view is first person.
- Click the stage to request pointer lock; `W A S D` or arrows move, `Shift` moves faster.
- Drag-look remains the fallback when pointer lock is denied or unavailable.
- Mobile: left joystick moves, drag on the stage looks.
- `R` resets to the scene start; `F` or **Exit first person** returns to orbit.
- Movement is clamped to corridor bounds and resolved against symbolic obstacles with sliding collision.
- Fullscreen uses the stage element; capture saves a local canvas still.
- `prefers-reduced-motion` disables non-essential motion.
- The orbit view remains available; Studio and comparison camera paths are unchanged.

## Adaptive policy

- targets: **Calm**, **Immersion**, **Exploration**;
- maximum step `0.12` per second;
- deadband `0.03`; two-window hysteresis; minimum dwell `2500 ms`;
- fatigue stop at `0.78`; quality hold below `0.35`;
- every decision carries a reason, confidence, coherence, and intervention flag;
- the trace is a 60-sample SVG with intervention and safety markers, plus a screen-reader table.

Simulated scenarios exercise the policy without a device:

| Scenario | What it shows |
| --- | --- |
| Steady | small natural variation around baseline |
| Drift | attention/valence fall while theta rises |
| Load | fatigue climbs toward the safety stop; quality drops late |
| Settle | starts loaded, then returns toward baseline |

The loop is deliberately slow, has no strobe, and is not framed as a treatment or as evidence that adaptation works.
It is not live neurofeedback.

## Backend contract

| Endpoint | Behaviour |
| --- | --- |
| `GET /animus/imagine/capabilities` | local ready; diffusion `blocked` or `ready`, reason, model slot, consent flag |
| `POST /animus/imagine/jobs` | `202` with a public job, or `503 diffusion_unavailable`; blocked requests write no job |
| `GET /animus/imagine/jobs` | bounded local history |
| `GET /animus/imagine/jobs/{id}` | lazy worker poll; three transient errors fail closed |
| `POST /animus/imagine/jobs/{id}/cancel` | idempotent terminal conflict |
| `DELETE /animus/imagine/jobs/{id}` | terminal jobs only; removes artifacts |
| `GET /animus/imagine/assets/{id}` | local PNG/JPEG/WebP only; `nosniff`, `ETag`, private cache |

Jobs and artifacts live under `data/imagine/` (gitignored), written atomically. Artifacts are capped at 64 MB,
checksum-verified, and restricted to worker-origin downloads. No database migration is involved.

Settings:

```text
imagine_enable_remote_diffusion = False
imagine_diffusion_url = ""
imagine_diffusion_token = ""
imagine_diffusion_timeout_seconds = 180
imagine_asset_ttl_hours = 24
imagine_data_dir = "./data/imagine"
```

The full worker runbook is [DIFFUSION_WORKER.md](DIFFUSION_WORKER.md).

## Diffusion output is a hybrid environment bundle

When a worker exists, v1 returns:

- a 4096×2048 equirectangular skybox;
- a 1280×720 preview;
- a manifest with model hash, seed, prompt hash, conditioning hash, controls, checksums, and expiry.

The skybox is applied to the existing sky sphere. Geometry, collision, first-person navigation, and the adaptive
trace stay local. The A/B toggle changes the environment texture only. The badge becomes
`diffusion-backed skybox` + `symbolic geometry`.

The generated texture is an aesthetic aid, not a reconstruction, a measurement, or a validated imagery score.

## What is not implemented

- No A100 pod, GPU worker, model weights, text encoder, or inference endpoint.
- No real text-to-image or video pass; no generated preview exists in this build.
- No learned signal adapter. The 16D mapping is a declared, deterministic v0.
- No live EEG, HRV, EDA, or other device input.
- No validation that adaptive feedback improves imagery, attention, or wellbeing.

## Boundaries

- The local scene is symbolic geometry, not reconstructed imagery.
- The signal vector is a demo control surface, not a measurement.
- The adaptive loop is a UI demonstration, not neurofeedback.
- The diffusion contract is a design target, not evidence that the pipeline works.
- A future skybox is generated environment texture, not neural content.
- The route must not claim thought reading, dream decoding, imagery reconstruction, diagnosis, treatment, or clinical
  validation.
- The claim ceiling stays `L1_BEHAVIORAL_ASSISTED`.

## Verification

- `frontend/lib/__tests__/imagine-*.test.ts` — determinism, 16D normalization, quality gate, policy hysteresis,
  safety holds, scenarios, manifest allowlist, collision, request v2.
- `backend/app/tests/test_imagine_api.py` — blocked default, no job written, mock success/cancel/failure, idempotency,
  privacy rejection, traversal rejection, local asset serving, expired/oversized manifests, checksum mismatch.
- `e2e/instrument-routes.spec.ts` — route load, 390/1440 overflow, local rebuild, first-person toggle.
- `e2e/imagine-diffusion.spec.ts` — consent, mocked success/skybox/provenance, offline download.
- `scripts/verify-platform-ui.cjs` includes `/animus/imagine`.
- `scripts/audit-claims.cjs` includes `imagine.scene` and `imagine.diffusion`.
