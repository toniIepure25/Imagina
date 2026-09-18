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

## What is CURRENTLY REAL (ANIMUS-P1)
- Behavioral feedback (closer/farther, pairwise, attribute/object corrections, free-text, confidence,
  re-imagination).
- Symbolic / adaptive feedback surfaces (the Dream Corridor becomes one surface, not the center).
- Deterministic, replayable loop control (typed state machine).
- Local-first user-preference learning.
- Generative candidate iteration (deterministic + mock/local adapters).
- **Simulated** neural observations (a synthetic digital twin), used to build and validate the loop.

## What is FUTURE / PLUGGABLE
- A **validated** neural content decoder (behind a stable interface, unused in P1).
- Neural latent alignment; neural-informed candidate generation.
- Dream / spontaneous imagery.

## Honesty guarantees
- The UI never implies that synthetic or behavioral observations are decoded thoughts.
- A machine-readable **claim level** (L0 simulated / L1 behavioral-assisted) gates every label and export;
  ANIMUS-P1 operates only at L0/L1. Higher levels require a future scientific gate — no manual bypass.
- Product code consults a **scientific evidence registry** that references the immutable C3XAT-R1 / C3XRP /
  C3XRA results **without reinterpreting them**, so the product can never outrun the science.

## Why build the loop now
The future neural decoder is just one more **observation source**. Building the entire loop today —
observation → belief → generation → feedback → belief update → controller → next candidate — means the
system does not need a redesign when a validated decoder becomes real: it plugs into
`FutureNeuralDecoderProvider` behind the same interface.
