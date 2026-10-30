# CRT Novelty and Overlap Matrix

## Status

- **Date:** 2026-10-30.
- **Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.
- **Use:** internal design review. This is not a priority claim and does not use "first" or
  "revolutionary."

## 1. Claim decomposition

| Candidate claim | What is already established | What CRT adds | Status |
| --- | --- | --- | --- |
| Reality monitoring is a higher-level inference | Reviews and computational accounts already argue this (Dijkstra et al., 2022; Dijkstra & Fleming, 2026 preprint). | A behavioural assay that makes the inference process observable through test selection and prediction. | Overlaps; needs incremental-validity test. |
| People use counterfactual prediction in source judgments | Counterfactual alternatives carry epistemic tags (Espino & Byrne, 2021); precision affects attribution (Kwon et al., 2022). | Prospective prediction of a **test consequence**, not a general counterfactual narrative. | Plausible, untested directly. |
| Active test selection improves source monitoring | Active Reality Testing and information-search work exist; matched yoking does not identify selection. | Random-passive and algorithm-adaptive controls decompose active choice from adaptive design. | Methodological contribution; empirical result unknown. |
| Meta-EIG is a useful assay of inquiry quality | Adaptive intervention selection and active causal learning are established (Coenen et al., 2015; Gong et al., 2023); metacognitive information search is established (Hu et al., 2026). | Applies meta-EIG to source monitoring and tests it against outcome EIG. | Incremental; model-dependent. Stage 0E policy gate `LIMITED` (meta-EIG loses to the best alternative by 0.012). |
| Prediction error is a readout of the forward model | Prediction-error accounts are common in predictive processing. | Belief-based prediction error as an assay, not a second source likelihood. | Stage 0E removes the current-source update; an `M4` later-attribution model remains future work. |
| CRT is a new clinical or training method | None. Training and clinical claims are blocked. | Nothing yet. | Not claimed. |

## 2. Overlap with higher-order precision

The Dijkstra-Fleming account is the strongest overlap. It proposes that reality monitoring depends on a
higher-order evaluation of sensory precision, not on a dedicated reality tag. CRT's `pi` parameter and
prediction-confidence terms can look like a re-description of that account.

The distinguishing question is therefore not "does precision matter?" It is:

> Does **prospective prediction of a source-diagnostic test consequence** add information about source
> attribution beyond a higher-order precision estimate, confidence, `d'`, and outcome EIG?

If the answer is no, CRT is a measurement operationalization, not a new theory. That is still publishable
as a psychometric contribution, but it must not be framed as a new model of reality monitoring.

## 3. Overlap with source-monitoring and SDT

Standard source monitoring already models source discriminability, guessing, and response bias. CRT adds:

- a forward prediction before the outcome;
- a meta-EIG policy over tests;
- a prediction-consistency bias.

Each addition needs a control:

| Addition | Generic alternative | Control |
| --- | --- | --- |
| Prediction | Engagement, attention, dual-task load | Matched non-diagnostic prediction |
| Meta-EIG | Outcome EIG, positive testing, fixed strategy | Out-of-sample policy comparison |
| Active choice | Adaptive design, extra information | Algorithm-adaptive and random-passive arms |
| Prediction error | Confidence or surprise | Continuous precision-weighted error; confidence-only model |
| Imagination inflation | Guessing or seen bias | Source-guessing model and response-bias parameters |

## 4. Novelty grades

| Component | Grade | Reason |
| --- | --- | --- |
| Prospective test-consequence prediction in source monitoring | B | Plausible new combination; no direct indexed match found, but search is non-systematic. |
| Meta-EIG scoring for source monitoring | B- | EIG is established; application is incremental and model-dependent. |
| Diagnostic-versus-non-diagnostic prediction control | A- | Directly addresses generic-prediction confound; appears uncommon in this literature. |
| Active-versus-random-passive decomposition | A- | Resolves the Stage 0C identifiability problem; strong methodological contribution. |
| Higher-order precision competition | A- | Necessary for a top-tier theoretical contribution; not yet run. |
| Interventionist reality testing (CIT) | B+ high risk | Conceptually novel, but no direct evidence and substantial demand-characteristic risk. |
| Neural add-on | B | Interesting, but separate collaboration and no decoding claim. |

Grades are design judgements, not bibliometric measures.

## 5. Publication positioning

1. **Measurement/methods paper:** test calibration, G-theory, invariance, specificity controls. Target
   *Behavior Research Methods* or *Psychological Methods*.
2. **Registered report:** diagnostic-specificity and active-selection tests. Target *Nature Human
   Behaviour* or *Psychological Science*; fallback *Cognition*.
3. **Theory paper:** CRT versus higher-order precision. Target *Neuroscience of Consciousness* or
   *Psychological Review* if the formal model is strong enough.
4. **High-risk CIT paper:** only after a separate preregistration. Target *Cognition* or *eLife*.

## 6. Language rules

Allowed:

- "a preregistered test of a prospective counterfactual measurement model"
- "a design hypothesis"
- "to our knowledge, no indexed study has directly combined ..."
- "the current search is non-systematic"

Not allowed:

- "first"
- "revolutionary"
- "proves"
- "diagnoses"
- "decodes"
- "validated" before the measurement gates pass
