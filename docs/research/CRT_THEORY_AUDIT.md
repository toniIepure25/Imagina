# CRT Theory Audit and Rapid Scoping Review

## Status

- **Date:** 2026-10-30.
- **Scope:** Counterfactual Reality Testing (CRT), `ANIMUS-CRT-v1`.
- **Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.
- **Review type:** rapid, non-systematic scoping review. It is **not** PRISMA-compliant, has no dual
  screening, and does not support a priority or "first" claim.
- **Purpose:** decide whether CRT has a distinctive, falsifiable prediction before adding more
  simulation or collecting human data.

## 1. Search log

Indexes: Europe PMC REST, PubMed, OpenAlex, Crossref, OSF preprints. Searches were run on 2026-10-30.
Counts are raw hit counts before deduplication or screening.

| Query | Index | Hits |
| --- | --- | ---: |
| `("reality monitoring" OR "source monitoring") AND ("active inference" OR "prediction error" OR "counterfactual")` | Europe PMC | 179 |
| `("reality monitoring" OR "source monitoring") AND (Bayesian OR "computational model" OR precision)` | Europe PMC | 609 |
| `("metacognitive" AND "information search") OR ("expected information gain" AND decision)` | Europe PMC | 461 |
| `("source monitoring" OR "reality monitoring") AND ("measurement invariance" OR "test-retest")` | Europe PMC | 86 |
| `("counterfactual" AND "sense of agency")` | Europe PMC | 111 |
| `("reality monitoring" OR "source monitoring") AND "prediction error"` | Europe PMC | 132 |
| `("reality monitoring" OR "source monitoring") AND ("sense of agency" OR "sensory attenuation")` | Europe PMC | 104 |
| `("reality monitoring" OR "source monitoring") AND (intervention OR controllability)` | Europe PMC | 490 |
| `("active learning" OR "information seeking") AND ("source memory" OR "reality monitoring")` | Europe PMC | 21 |
| `("counterfactual" AND "reality monitoring")` | Europe PMC | 18 |
| `("metacognition" AND "source monitoring")` | Europe PMC | 96 |
| `("reality monitoring" OR "source monitoring") AND ("active inference" OR "generative model")` | Europe PMC | 44 |
| `"reality monitoring" AND (prediction OR precision OR Bayesian)` | PubMed | 52 |
| `"source monitoring" AND metacognition AND confidence` | PubMed | 3 |

OpenAlex queries for broad combinations were noisy and are not used as screening counts. Exact-title
queries were used only to retrieve metadata. The counts show that the component literatures are large,
but the combination of prospective test-outcome prediction, meta-EIG selection, and source attribution
is not a well-populated direct literature.

## 2. Evidence table

| Source | Type | What it establishes | Implication for CRT |
| --- | --- | --- | --- |
| [Dijkstra, Kok & Fleming 2022](https://doi.org/10.1016/j.neubiorev.2022.104557) | Peer-reviewed review | No single sensory or cognitive factor unambiguously dissociates imagination from perception; higher-level circuits evaluate first-order evidence. | CRT cannot claim a single "prediction signal." Prediction must be modelled as one factor and tested for incremental validity. |
| [Dijkstra, Fleming & Shea 2026](https://doi.org/10.1093/nc/niag048) | Peer-reviewed functional analysis | The demands of the task constrain how the imagination-reality problem is solved. | The experiment must manipulate what the prediction is for, not just whether a prediction occurs. |
| [Dijkstra & Fleming 2026 preprint](https://doi.org/10.31234/osf.io/36xdz_v4) | Preprint; not peer-reviewed | A generative-model account distinguishes imagery from perception through higher-order evaluation of sensory precision. | This is CRT's primary theoretical competitor. CRT must show out-of-sample value beyond a higher-order precision account. |
| [Kwon et al. 2022](https://doi.org/10.1162/jocn_a_01814) | Peer-reviewed | Lower episodic memory precision is associated with external misattribution. | Supports a precision parameter, but also predicts that precision alone may explain CRT effects. |
| [Espino & Byrne 2021](https://doi.org/10.1037/xlm0000965) | Peer-reviewed, seven experiments | People track the epistemic status of real and imagined counterfactual alternatives. | Supports prospective prediction, but warns that rich simulation can blur source tags. |
| [Dhammapeera et al. 2024](https://doi.org/10.1080/17588928.2024.2315814) | Peer-reviewed | Counterfactual imagination can impair memory for true actions. | CRT should use a sparse test-consequence prediction, not autobiographical counterfactual imagination. |
| [Dijkstra et al. 2024](https://doi.org/10.1167/jov.24.5.13) | Peer-reviewed | Confidence ratings alone do not distinguish imagination from reality. | Confidence cannot be the sole index of CRT. |
| [Hu et al. 2026](https://doi.org/10.1016/j.cognition.2025.106410) | Peer-reviewed, five experiments, N=477 | Metacognitive sensitivity predicts information-search quality; working memory engages sampling quality. | Meta-EIG needs a working-memory control and model-free validation. |
| [Yavuz et al. 2025](https://doi.org/10.1016/j.cognition.2025.106062) | Peer-reviewed, EEG | Rational choice and counterfactual option sets strengthen the sense of agency; P300/LPP correlates. | Supports a separate interventionist extension and an optional EEG add-on. |
| [Lavallé et al. 2023](https://doi.org/10.1002/hbm.26387) | Peer-reviewed meta-analysis | Reality and self-monitoring share cerebellar and medial prefrontal substrates. | Supports a separate neural collaboration, not a neural claim now. |
| [Coenen et al. 2015](https://doi.org/10.1016/j.cogpsych.2015.02.004) | Peer-reviewed | People adaptively select interventions on causal systems rather than intervening at random. | The CRT selection policy should be compared with an adaptive intervention baseline; this is not direct evidence for meta-EIG in source monitoring. |
| [Gong et al. 2023](https://doi.org/10.1016/j.cogpsych.2022.101542) | Peer-reviewed | People actively learn causal structure in continuous time. | Active selection is a plausible baseline; meta-EIG must add value beyond adaptive causal learning. |

## 3. What is genuinely new

The direct combination is not well populated, but "not found" is not "first." The defensible novelty is:

1. **Prospective counterfactual prediction as a measurement probe.** The participant predicts a
   source-diagnostic test consequence before seeing it. In the repaired model this prediction is a
   **readout and policy signal**, not independent source evidence: the source is updated from the
   outcome only, so the design avoids double counting. Prediction error can still be studied as an
   assay of the forward model and as a trigger for later error attribution.
2. **Meta-EIG as a normative assay of inquiry.** The instrument scores test selection against a
   computable meta-information baseline, not only against source accuracy. Stage 0E policy competition
   currently returns `LIMITED`, so this remains a descriptive not a normative claim.
3. **Specificity and causal controls.** A matched non-diagnostic prediction and a random-passive arm
   separate counterfactual prediction from generic engagement and active selection. Stage 0E shows the
   diagnostic-specificity advantage under belief-based prediction is `LIMITED`; the control is retained
   as a falsification test, not as a passing result.
4. **Psychometric upgrade.** Generalizability theory, test-likelihood calibration, measurement
   invariance, and a stricter reliability target.

The contribution is **not** "prediction improves source monitoring." That claim is too generic and is
already in tension with higher-order precision accounts. The current simulations do not establish that
prediction improves source accuracy; they establish a design in which that question can be tested
without oracle access.

## 3a. Stage 0E model-repair correction

The Stage 0D simulator gave the participant the true source when forming a prediction and then treated
the prediction as an independent likelihood. Both are oracle assumptions. Stage 0E replaces them with a
belief-based posterior-predictive readout and outcome-only source updating. Under the repaired model:

- Oracle prediction advantage is 0.128 versus 0.026 for belief prediction (oracle inflation 0.101).
- The Stage 0D diagnostic-specificity advantage does not reproduce (diagnostic prediction accuracy
  0.505; accuracy gain 0.026; gate floor 0.55).
- Dual-hypothesis prediction has a large perceived diagnosticity (0.476) but no accuracy gain over a
  single prediction on a fixed sequence.
- Meta-EIG beats cost-only by 0.060 but not the best competing policy (by -0.012).
- Test-facet relative reliability is 0.843 minimum in simulation.
- Posterior PIT calibration passes for the assumed generative model.

These are simulation-only corrections. They downgrade the Stage 0D specificity gate to `LIMITED` and
the Stage 0E counterfactual and policy gates to `LIMITED`.

## 4. What would falsify CRT

- The diagnostic-prediction advantage disappears against a matched non-diagnostic prediction.
- `CRTE_meta` adds no out-of-sample prediction beyond outcome EIG, working memory, `d'`, `meta-d'`, or a
  higher-order precision model.
- Active choice is no better than random-passive exposure.
- Test-retest reliability falls below the registered target.
- Imagination inflation is fully explained by guessing or response bias.
- The calibrated test battery does not separate seen from imagined.

## 5. Theory competition

| Model | Core claim | CRT-distinguishing prediction |
| --- | --- | --- |
| `crt_meta_eig` | Prospective prediction and meta-EIG selection add information beyond outcome-only testing. | Positive diagnostic-specificity gain; prediction-error update; meta-EIG efficiency. Under Stage 0E, the specificity and policy sub-claims are `LIMITED`. |
| `eig_only` | People select informative tests but do not use prospective prediction. | No prediction advantage; outcome-EIG policy fits. |
| `higher_order_precision` | A higher-order precision estimate drives reality monitoring; no prospective test-outcome prediction is required. | No diagnostic-specificity gain; precision/confidence explains attribution. |
| `sdt_confidence` | Source discrimination plus response bias and confidence explains the data. | No prediction advantage; no meta-EIG policy advantage. |
| `heuristic_source` | A fixed or feature-based source heuristic explains choices. | Fixed test choices; no meta-EIG efficiency. |

The Stage 0D signature analysis asks whether these predictions are separable under measurement noise.
It is a design check, not human model evidence. The Stage 0E repair changes the fitted model: the
prediction is not an independent likelihood, and the Stage 0D oracle signature cannot be reused as
evidence for `crt_meta_eig`.

## 6. Limitations of this audit

- No dual screening, no risk-of-bias assessment, no formal data extraction.
- Europe PMC and PubMed indexing lag and preprint coverage is incomplete.
- Several 2026 sources are very recent; the Dijkstra-Fleming preprint is not peer-reviewed.
- The search did not include PsycINFO, Scopus, or Web of Science.
- The audit cannot support a priority claim.

## 7. Next step

Write the model-prediction table into the Stage 0D protocol; recruit an independent second screener and
an adversarial collaborator before any human study. Until then, all novelty language is provisional.
