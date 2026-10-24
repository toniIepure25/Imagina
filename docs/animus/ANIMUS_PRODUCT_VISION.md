# ANIMUS — Product Vision

**IMAGINA** is the overall research + product platform. **ANIMUS** is its closed-loop imagination
inference / amplification engine. ANIMUS-P1 is the first vertical slice.

## North star
The product is **not** "brain → reconstructed image." It is a **closed human–AI loop** that helps a person
progressively **express, stabilize, clarify, inspect, modify, and amplify** an internally imagined
representation:

```
intention → internal imagery → observation → belief → candidate → the user perceives it →
re-imagine / correct / stabilize → new observation → belief update → better candidate → …
```

The loop — not one-shot reconstruction — is the core product.

## What is CURRENTLY REAL (ANIMUS-P1 + Studio)
- A usable **Studio** at `/animus`: describe → see a procedural candidate → correct → lock → regenerate →
  keep / undo / branch → save a world → reopen after restart.
- A versioned, hashable **symbolic scene graph** (ANIMUS-SG-v1) with explicit provenance and locks.
- Deterministic intention parsing and typed scene commands; no hidden target and no external model.
- Procedural React Three Fiber rendering of that state (castle, ocean, sky, weather, creatures, portals).
- Local SQLite persistence for sessions, versions, branches, candidates, and worlds.
- Behavioral feedback (closer/farther, pairwise, attribute/object corrections, free-text, confidence,
  re-imagination).
- Deterministic, replayable loop control (typed state machine).
- Local-first user-preference learning.
- **Simulated** neural observations (a synthetic digital twin), used to build and validate the loop.
- An **experimental behavioural instrument** at `/animus/profile`: deterministic scene and reconstruction
  tasks, a coverage floor plus information-gain practice policy, separate ability/calibration estimates,
  a descriptive error signature, and explicit uncertainty. No composite score and no diagnosis.

## What is FUTURE / PLUGGABLE
- A **validated** neural content decoder (behind a stable interface, unused in P1).
- Neural latent alignment; neural-informed candidate generation.
- Dream / spontaneous imagery.

## Honesty guarantees
- The UI never implies that synthetic or behavioral observations are decoded thoughts.
- The Studio makes **no image-generation claim**: every candidate is a symbolic, editable procedural
  preview. Its capability envelope is returned by the backend and displayed in the UI.
- The behavioural instrument reports task performance and confidence calibration, never imagery strength,
  neural content, diagnosis, or far transfer. Aphantasia is treated as a variation, not a deficit.
- A machine-readable **claim level** (L0 simulated / L1 behavioral-assisted) gates every label and export;
  ANIMUS-P1 and Studio operate only at L0/L1. Higher levels require a future scientific gate — no manual
  bypass.
- Product code consults a **scientific evidence registry** that references the immutable C3XAT-R1 / C3XRP /
  C3XRA results **without reinterpreting them**, so the product can never outrun the science.

## Why build the loop now
The future neural decoder is just one more **observation source**. Building the entire loop today —
observation → belief → generation → feedback → belief update → controller → next candidate — means the
system does not need a redesign when a validated decoder becomes real: it plugs into
`FutureNeuralDecoderProvider` behind the same interface.
