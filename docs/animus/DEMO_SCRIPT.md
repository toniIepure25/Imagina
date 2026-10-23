# ANIMUS — Demo Script (understand the product in < 5 minutes)

Everything below is deterministic and uses **no human or neural data**.

## 0. Studio product loop (the primary product experience)
Start the local backend and frontend, then open `http://localhost:3000/animus`.

1. Enter: *"a white castle above a dark ocean at dusk"* → **Enter the studio**.
2. The studio shows a procedural candidate, a version (`v1`), and an editable element list.
3. Type: *"make the sky deep violet"* → **Apply** (`v2`, with resolutions listed).
4. Select the castle row → **Lock element**. Locking is a real versioned command (`v3`).
5. **Explore 3 variations** → three candidates. Their cards report how many locked paths were kept.
6. **Keep this** on a candidate (`v4`); **Undo** returns to `v3`. Open **history** → create branch
   `variation` → switch back to `Main`; reload the page and the version/branches persist.
7. **Save world** → open `/animus/worlds` → **Open studio** creates a new session rooted at that world.
8. `/animus/about` shows the capability envelope: image generation disabled, neural/dream content
   unauthorized, local only, claim ceiling L1.

The automated browser check for this exact loop is
`frontend/scripts/verify-animus-ui.cjs` (uses the existing Playwright dependency and local Chrome/Edge).
It writes screenshots to `docs/animus/01–06-*.png` and fails on any browser console error.

## 1. CLI demo (backend)
```bash
cd backend
PYTHONPATH=. python -m app.cli.animus_demo --mode blind-benchmark        # hidden-target convergence
PYTHONPATH=. python -m app.cli.animus_demo --mode imagination-amplifier  # interactive amplifier (MODE A)
PYTHONPATH=. python -m app.cli.animus_demo --mode synthetic-neural       # with simulated neural observations
PYTHONPATH=. python -m app.cli.animus_demo --mode behavioral-only        # behavioral evidence only
```

### Flagship scenario
Hidden target (the controller never sees it): *"a stone castle at night, in fog, with a red moon behind
it."* The blind-benchmark mode prints the similarity progression `v0 → v1 → … → v8` for STATIC, RANDOM and
ANIMUS_ACTIVE. Expect ANIMUS to climb fastest and highest — it actively probes uncertain attributes and
refines the visual embedding, while STATIC/RANDOM do not. (Similarity is evaluator-only; in the real
amplifier mode there is no target and no similarity is shown.)

## 2. Benchmark campaign + acceptance decision
```bash
cd backend
PYTHONPATH=. python app/research/animus/run_animus_p1_benchmark.py 100
```
Writes `results/animus_p1/{benchmark_summary,controller_comparison,privacy_audit,determinism_audit,
ANIMUS_P1_DECISION}.json` and prints each acceptance check. ANIMUS_ACTIVE must beat STATIC and RANDOM
(median loop gain ≥ 20 % better than RANDOM, fewer censored iterations to threshold), with privacy and
determinism audits passing.

## 3. API (backend running)
```bash
curl -s localhost:8000/animus/health
curl -s -X POST localhost:8000/animus/sessions -d '{"mode":"amplifier"}' -H 'content-type: application/json'
# → generate, feedback (channel=attribute_correction, direction=more_blue), timeline, replay
curl -s localhost:8000/animus/scientific-registry
```

## 4. Frontend surfaces
- **Studio:** `/animus` → `/animus/studio/{session_id}`. Describe, correct, inspect the element list,
  lock, regenerate, keep, undo/redo, branch, save.
- **Worlds:** `/animus/worlds` — reopen a saved world as a new session or delete it locally.
- **Boundaries:** `/animus/about` — what is active, disabled, or unauthorized.
- **P1 research workspace:** `/imagina/animus` redirects to `/animus`; the original P1 API remains at
  `/animus/*` for research tooling.

## What to look for
- The loop is the product: candidate → correct → lock → regenerate → keep or explore.
- Every version is immutable and hash-identified; undo/redo and branches are explicit.
- Locked content cannot be changed by regeneration or ordinary commands; unlock is explicit.
- The provenance badge always shows the claim level (L0/L1) — never a neural-content claim.
- A fixed seed reproduces the exact same session (replay hash).
