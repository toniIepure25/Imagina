# ANIMUS — Product Roadmap

Every stage lists the **scientific authorization** it requires. Stages above P1 are gated by science that
is not yet in hand; ANIMUS never advances a claim level on product effort alone.

| Stage | Description | Claim level | Scientific authorization required |
|---|---|---|---|
| **P1** | Closed-loop amplification engine | L0 / L1 | none (simulated / behavioral) |
| **P1.5** | **ANIMUS Studio** — local symbolic scene product loop (shipped) | L1 | none; no neural or image-model content |
| **P1.6** | **Behavioural instrument** — adaptive scene practice + experimental profile (implemented; unvalidated) | L1 | none; behavioural tasks only |
| **P1.7** | **Reconstruction instrument** — object/spatial reconstruction + info-gain policy (implemented; unvalidated) | L1 | none; behavioural tasks only |
| **P1.8** | **Epistemic interview** — binary probes, Beta posterior, entropy/calibration/coverage (implemented; unvalidated) | L1 | none; behavioural elicitation only |
| P2 | Validated **perception**-content adapter | L2→L3 | validated perception decoder on independent data |
| P3 | Validated **imagery**-content adapter | L3 | **C3XRP independent replication QUALIFIED** + validated imagery decoder |
| P4 | Neural + behavioral multimodal fusion | L3 | validated multimodal decoder + calibration protocol |
| P5 | Real-time personalized amplification | L3 | real-time decoding validated within safety bounds |
| P6 | Continuous visual latent control | L3 | validated continuous latent decoding |
| P7 | Video / spatial / 3D imagination | L3 | validated dynamic/spatial decoding |
| P8 | Memory / counterfactual workspace | L3 | validated retrieval/imagery separation |
| P9 | Spontaneous imagery | L3 | validated spontaneous-imagery detection |
| P10 | Dream-interface research | L3 | dedicated ethics + validated sleep-imagery science |

## P1.5 — Studio product surface (shipped locally)
The Studio turns the P1 loop into a usable product: `/animus` intention composer, symbolic scene graph,
procedural candidate variants, typed corrections, locks, immutable versions, undo/redo, branches, saved
worlds, and restart-safe SQLite persistence. It deliberately adds **no** new scientific capability:
`image_generation = DISABLED`, `neural_content = UNAUTHORIZED`, `dream_content = UNAUTHORIZED`,
`neural_reconstruction = UNAUTHORIZED`, `network_calls = DISABLED`, `uploads = DISABLED`, privacy
`local_only`. The claim ceiling remains L1.

## P1.6 — Behavioural instrument (implemented, not validated)
The instrument adds five separate behavioural estimates (`stability`, `discrimination`, `spatial`,
`control`, `calibration`), deterministic server-scored tasks, a local protocol library, and a profile
surface. It deliberately has **no composite score**, no diagnosis, no imagery-strength claim, no neural
input, and no far-transfer claim. The model and its assumptions are in
[MEASUREMENT_MODEL.md](MEASUREMENT_MODEL.md); the proposed independent study is in
[VALIDATION_PROTOCOL.md](VALIDATION_PROTOCOL.md). Until that study is run, the profile is
`EXPERIMENTAL` and `clinical_use = DISABLED`.

## P1.7 — Reconstruction instrument (implemented, not validated)
The next product level replaces some multiple-choice probes with reconstruction: a token bank for object
detail and a normalized placement board for spatial layout, both scored server-side against the symbolic
scene. It also replaces coverage-first selection with a coverage floor plus expected information gain, and
adds a descriptive error signature. The exact scoring is in
[RECONSTRUCTION_SPEC.md](RECONSTRUCTION_SPEC.md); the policy is in
[ADAPTIVE_POLICY.md](ADAPTIVE_POLICY.md); migration **v019** stores task family, response kind, scoring
version, and error profile. This is still a behavioural proxy: no neural decoding, no image generation, no
clinical claim. Validation remains the gate before any construct interpretation.

## P1.8 — Epistemic interview (implemented, not validated)
The interview asks binary questions about a hidden symbolic scene: object presence and left/right spatial
relations. A mean-field Beta belief is updated from the answer and confidence; after one object and one
spatial probe for coverage, the next probe maximises expected information gain. It reports object/spatial
accuracy, Brier, coverage, abstention, overconfidence, and entropy separately, with no composite. The model
and its limits are in [EPISTEMIC_INTERVIEW_SPEC.md](EPISTEMIC_INTERVIEW_SPEC.md); migration **v020** stores
the interview header and probe metadata. A posterior is not a picture: no neural decoding, no image
generation, no clinical claim. Human validity and calibration fit remain untested.

## P1.9 — Scene Threshold and observatory (implemented, not validated)
Scene Threshold turns the same symbolic scene into a contrastive 2-AFC task: object presence, spatial
position, or colour changes are applied to one option, and an adaptive 2-down/1-up staircase concentrates
trials near the person's threshold. Scoring separates d′, side bias, fitted 75%-correct thresholds,
Brier/overconfidence, and coverage; 2-AFC does not identify a yes/no criterion. The observatory overlays
the ERI belief layer with evidence provenance, leave-one-out sensitivity, and a feature-level test–retest
panel. Migration **v021** stores contrast sessions and trials. The model is in
[CONTRAST_SPEC.md](CONTRAST_SPEC.md) and [OBSERVATORY_SPEC.md](OBSERVATORY_SPEC.md). Thresholds are
within-scene only; no imagery-strength, neural, clinical, or far-transfer claim is made. Human validation
and test–retest with more than two feature types remain open.

## P1 → P2/P3 bridge
The single interface that unlocks the ladder is `NeuralContentDecoder` / `FutureNeuralDecoderProvider`. When
a validated decoder exists **and** a scientific gate authorizes the corresponding claim level, it is injected
as an observation source. The controller, belief model, generation, feedback, personalization, and UI do not
change — only the evidence source and the authorized claim ceiling.

## Non-goals for P1/P1.5 (explicit)
No decoding validation, no neural reconstruction, no geometry (C3XAG), no dream decoding, no use of real
participant data, no human neural data collection, no external image model.
