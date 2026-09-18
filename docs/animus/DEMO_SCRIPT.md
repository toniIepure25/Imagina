# ANIMUS-P1 — Demo Script (understand the product in < 5 minutes)

Everything below is deterministic and uses **no human or neural data**.

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

## 4. Frontend workspace
Open `/imagina/animus`. Start a session, generate a candidate, apply corrections (closer/farther,
attribute/object edits), and watch the belief, uncertainty, iteration timeline, controller action, evidence
sources, amplification progress, and the claim-level provenance badge update live.

## What to look for
- The loop is the product: candidate → correct → re-imagine → amplify.
- Every candidate is versioned/immutable; you can compare and restore previous versions.
- The provenance badge always shows the claim level (L0/L1) — never "decoded thoughts."
- A fixed seed reproduces the exact same session (replay hash).
