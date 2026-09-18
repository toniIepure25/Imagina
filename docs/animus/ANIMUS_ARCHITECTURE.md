# ANIMUS — Architecture (P1)

ANIMUS sits **above** IMAGINA's observation, belief, generation, feedback, and control layers and reuses
the existing runtime (event store, WebSocket, session/safety patterns). It does not fork a parallel app.

## Layers (`backend/app/core/animus/`)
| Module | Responsibility |
|---|---|
| `claims.py` | Claim-level ladder (L0–L3) + authorization ceiling (L1) + forbidden-phrase audit |
| `vocab.py` | Versioned structured-attribute + object vocabulary (IBS-v1) |
| `models.py` | `ImaginationBeliefState` (IBS-v1), embeddings, observation/feedback/candidate envelopes, hashing |
| `belief_state.py` | `BeliefFusionEngine` — Gaussian + categorical + comparative updates; named `FusionConfig` |
| `synthetic_imaginer.py` | Digital twin (hidden `z_target`, noisy responses) — evaluator-only |
| `decoder.py` | `NeuralContentDecoder` contract + `SyntheticNeuralDecoder` (future-pluggable) |
| `observation.py` | `ObservationProvider`s: behavioral / simulated-neural / replay / future-neural (fail-closed) |
| `feedback.py` | Normalize all feedback channels → `FeedbackEvidence`; free-text → structured |
| `candidate_generator.py` | Generators + `BeliefToGenerationSpec` **privacy boundary** |
| `controller.py` | `AnimusActiveController` + baselines (static/random/greedy) + `AnimusPolicyConfig` |
| `metrics.py` | Benchmark-only vs real-user metrics; `AmplificationSessionSummary` |
| `personalization.py` | `AnimusUserModel` (local-first, non-clinical) |
| `loop_runtime.py` | First-class state machine (INITIALIZE…COMPLETE/ABORT), events, replay hashes |
| `benchmark.py` | Blind-target campaign + `TwinRespondent` |
| `replay.py` | `AnimusReplayManifest` + determinism verification |
| `evidence_registry.py` | Science→product boundary (references C3XAT/C3XRP/C3XRA, no reinterpretation) |
| `service.py` / `sdk.py` | Session registry + typed SDK facade |

## The loop as a state machine
`INITIALIZE → CALIBRATE → (OBSERVE → INFER → GENERATE → PRESENT → COLLECT_FEEDBACK → UPDATE_BELIEF →
SELECT_NEXT_ACTION → CHECK_CONVERGENCE → CONTINUE)* → COMPLETE | ABORT`. Every transition is typed,
timestamped, event-logged, and deterministic under a seed; belief hashes are recorded per step so a session
replays bit-exactly.

## Central representation — IBS-v1
Model-independent belief: Gaussian **visual** + **semantic** embeddings (mean + diagonal variance, each with
an `EmbeddingSpec` so CLIP is not assumed permanent), categorical **scene attributes**, **object** presence
probabilities, **spatial relations**, per-component confidence, and a global uncertainty. The system never
pretends to know one exact mental image — candidates are generated from the belief distribution.

## Pluggable neural boundary
`ObservationProvider` unifies evidence sources. A future validated decoder implements `NeuralContentDecoder`
and is exposed via `FutureNeuralDecoderProvider` — the controller and loop are unchanged. In P1 that
provider **fails closed** (no validated decoder, no scientific authorization).

## Privacy boundary
Generators receive only a sanitized `GenerationSpec` (semantic summary, scene graph, approved small
embedding, seed). Raw neural arrays, biosignal time series, and identifiers can never reach a generator —
enforced by `assert_no_forbidden_content` and a privacy test. No cloud API; CI uses deterministic adapters.

## API / SDK / events
`app/api/animus.py` exposes sessions, step/observe/feedback, belief/candidates/timeline/replay, and a
bounded benchmark run. Events (`animus.session.started`, `.observation.received`, `.belief.updated`,
`.candidate.generated/presented`, `.feedback.received`, `.controller.action`, `.convergence.updated`,
`.safety.event`, `.session.completed`) are persisted and drive the live workspace.
