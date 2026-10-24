# ANIMUS — Claims Boundary

ANIMUS-P1 makes **no** neural-content-decoding claim. This document is the contract; the code enforces it.

## Claim levels (machine-readable, `claims.py`)
| Level | Meaning | Allowed in P1 |
|---|---|---|
| `L0_SIMULATED` | Simulated loop; no biosignals, no decoded thoughts | ✅ |
| `L1_BEHAVIORAL_ASSISTED` | Behavioral-assisted amplifier; no decoded neural content | ✅ |
| `L2_BIOSIGNAL_ASSISTED_EXPERIMENTAL` | Experimental biosignal-assisted; research only | ❌ (future gate) |
| `L3_NEURAL_CONTENT_INFORMED_VALIDATED` | Validated neural-content-informed | ❌ (future gate) |

The operating ceiling is **L1**. `ClaimAuthorization.enforce` fails closed above it; there is **no manual
bypass**. UI labels and exports derive strings from the claim level only.

## What ANIMUS-P1 may say
- "Behavioral-assisted imagination amplifier (no decoded neural content)."
- "Your representation became more stable and clarified across this session." (based on allowed metrics)
- "Simulated neural observation" — clearly labeled as synthetic.

## What ANIMUS-P1 must never say
- "We read your thought" / "mind reading" / "neural reconstruction of your image" / "we know what you
  imagined." These phrases are enumerated and auditable (`audit_text_for_forbidden_claims`).

## Benchmark-only vs real-user metrics
Ground-truth similarity, attribute/object accuracy, scene-graph edit distance and `loop_gain` require a
hidden target and are **evaluator-only** (MODE B / benchmark). They must never surface in real-user mode
(MODE A amplifier), where the imagined target is unknown. Real-user metrics are uncertainty reduction,
self-reported clarity/confidence progression, candidate change magnitude, controller action entropy, and
stability across re-imagination.

## Scientific status (mirrors `evidence_registry.py`)
- Imagery reliability: **LIMITED** cohort evidence (C3XAT-R1).
- Independent replication: **not yet executed** (C3XRA acquisition-ready; C3XRP human replication not run).
- Content decoder: **not validated**. Geometry (C3XAG): **not authorized**. Neural reconstruction:
  **not validated**.

No frozen C3XAT/C3XRP/C3XRA result is modified or reinterpreted by ANIMUS. C3XAT reliability values are
measurement evidence only and are never converted into content information.

---

# Studio (P1.5) — enforced product envelope

The Studio is an authoring loop over a **symbolic scene**. It does not add neural input, an image model,
or a new claim level.

## Enforced capabilities (`studio/claims.py`, returned by `/animus/studio/capabilities`)
| Capability | Value |
|---|---|
| Scene graph | `ANIMUS-SG-v1` |
| Renderer | `procedural-local` (React Three Fiber, no textures/downloads) |
| Image generation | `DISABLED` |
| Neural content | `UNAUTHORIZED` |
| Dream content | `UNAUTHORIZED` |
| Neural reconstruction | `UNAUTHORIZED` |
| Network calls during studio use | `DISABLED` |
| Uploads | `DISABLED` |
| Privacy scope | `local_only` |
| Behavioural profile | `EXPERIMENTAL` |
| Behavioural reconstruction | `EXPERIMENTAL` |
| Adaptive practice | `EXPERIMENTAL` |
| Epistemic interview | `EXPERIMENTAL` |
| Scene Threshold observatory | `EXPERIMENTAL` |
| Clinical use | `DISABLED` |
| Claim ceiling | `L1_BEHAVIORAL_ASSISTED` |

## Copy guard
`enforce_studio_text` runs on session title, intention, world name, and correction text. It normalises
case/whitespace and rejects phrases that assert mind-reading, dream decoding, neural reconstruction,
clinical validity, or consciousness measurement. The parser also rejects unknown operations and values,
so the UI cannot smuggle a stronger claim through an attribute.

## What the Studio may say
- "Describe a scene, see a procedural candidate, correct it, lock what is right, and keep or explore."
- "Behavioural-assisted imagery scaffold; claim ceiling L1."
- "Every candidate is a symbolic, editable preview — not a neural reconstruction."

## What it must never say
- That a candidate shows, reads, decodes, or reconstructs the user's imagined content.
- That the system validates or treats a clinical condition.
- That image generation or neural content is active.

---

# Measurement layer (P1.6) — experimental behavioural profile

The profile is a **separate** evidence surface. It records performance on deterministic scene tasks and
confidence calibration. It does not change the scene, feed a decoder, or raise the claim ceiling.

## Allowed
- "Experimental behavioural estimates from local scene practice."
- "Separate estimates for scene stability, discrimination, spatial view, control, and confidence
  calibration."
- "This estimate comes from `n` trials and has this uncertainty."
- "Aphantasia and hypophantasia are variations, not deficits."
- "This is not a diagnosis or a measure of imagery strength."

## Forbidden
- "Imagination score", "imagery IQ", "vividness score", or any composite ranking.
- "Diagnoses aphantasia" / "treats aphantasia" / "cures" / "clinically validated".
- "Measures your mental image", "reads your mind", "neural reconstruction".
- "Boosts imagery strength", "increases vividness", "brain training", "far transfer".
- "Scientifically proven", "validated instrument", or norm-referenced comparisons.
- Any claim that low performance is a defect or that high performance is superiority.

## Presentation rules
1. An estimate is hidden until at least three trials exist.
2. Every displayed estimate shows `n`, uncertainty, status, and a limitation.
3. Calibration is shown as a Brier score and never as a standalone virtue.
4. The profile has no composite and no leaderboard.
5. The capability envelope returns `behavioral_profile = EXPERIMENTAL` and
   `clinical_use = DISABLED`; tests assert both.

---

# Reconstruction layer (P1.7) — behavioural reconstruction, not neural reconstruction

Reconstruction means the user rebuilds **their own scene** from memory using tokens or a placement board.
It is a behavioural task. It does not reconstruct an image from the brain.

## Allowed
- "Rebuild the object set or layout from memory; the server scores it against the symbolic scene."
- "Object F1, omissions, intrusions, and mean position error are descriptive behavioural scores."
- "The reconstruction score is experimental and not a validated measure of imagery."
- "Aphantasia is a variation, not a deficit."

## Forbidden
- "Neural reconstruction", "image reconstruction from brain activity", "decodes your mental image".
- "Validated reconstruction instrument", "objective imagery score", "imagery IQ".
- Any composite of object and spatial scores.
- Any clinical, diagnostic, enhancement, or far-transfer claim.
- Treating a low object score as a defect or a high score as superiority.

## Presentation rules
1. Token banks never include a target flag; target positions never leave the server before scoring.
2. The source scene is hidden during the question; the UI may reveal it only after feedback.
3. Object and spatial scores are displayed separately; the error signature is descriptive.
4. The claim ceiling remains `L1_BEHAVIORAL_ASSISTED`; `neural_reconstruction` remains `UNAUTHORIZED`.

---

# Epistemic interview layer (P1.8) — posterior belief, not a neural image

The interview asks binary questions about a hidden symbolic scene and reports a posterior over object
presence and spatial relations. It is a behavioural elicitation method. A probability is not a picture.

## Allowed
- "Binary probes are selected by expected information gain over a Beta belief state."
- "Confidence, Brier score, coverage, abstention, and entropy are reported separately."
- "The reconstruction is experimental and not a validated measure of imagery."
- "An abstention is data, not a failure; aphantasia is a variation, not a deficit."

## Forbidden
- "Neural reconstruction", "reads your mental image", "shows what you imagined", "dream decoding".
- "Objective imagery measure", "imagery IQ", "imagination score", "validated instrument".
- Any composite of accuracy, calibration, coverage, and entropy.
- Any clinical, diagnostic, enhancement, or far-transfer claim.
- Treating a high posterior or high accuracy as superiority.

## Presentation rules
1. The probe payload never includes the hidden answer or a target flag.
2. Abstention is available and excluded from Brier scoring while remaining in coverage.
3. Object and spatial accuracy, calibration, coverage, and entropy are displayed separately.
4. The claim ceiling remains `L1_BEHAVIORAL_ASSISTED`; `neural_reconstruction` remains `UNAUTHORIZED`.

---

# Scene Threshold layer (P1.9) — discrimination, not imagery strength

Scene Threshold is a 2-AFC contrast task over the symbolic scene. It reports sensitivity, a within-scene
threshold, side bias, calibration, coverage, and optional test–retest consistency. It does not report an
imagery-strength score, a neural image, or a diagnosis.

## Allowed
- "Two nearly identical scenes; choose the one that matches what you saw."
- "d′ describes 2-AFC sensitivity with a log-linear correction."
- "A lower threshold means finer discrimination within this scene."
- "Thresholds are within-scene units and are not comparable across scenes."
- "Reliability is estimated across aligned features and reported only when enough features exist."

## Forbidden
- "Imagery strength score", "objective imagery measure", "imagination IQ", "visual cortex threshold".
- "Neural decoding", "reconstructs what you saw", "dream detection", "reads your mind".
- "Diagnoses aphantasia", "cures aphantasia", "training boosts imagery", "far transfer".
- Comparing thresholds between people, scenes, displays, or forms without a validated norm.
- A composite of d′, threshold, Brier, coverage, and reliability.
- Treating side bias, abstention, or low confidence as a deficit.

## Presentation rules
1. The pair payload never includes the target side, changed entity, feature label, or delta.
2. No per-trial correctness feedback during the session; the aggregate result appears only at completion.
3. Sensitivity, threshold, side bias, calibration, and coverage are displayed separately.
4. A censored threshold is marked as censored; an insufficient threshold is withheld.
5. The claim ceiling remains `L1_BEHAVIORAL_ASSISTED`; `neural_reconstruction` remains `UNAUTHORIZED`.
