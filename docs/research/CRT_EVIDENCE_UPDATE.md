# CRT Evidence Update — Stage 0E

## Status

- **Date:** 2026-10-30.
- **Review type:** rapid, non-systematic evidence update. It is **not** a systematic review, has no
  dual screening, and cannot support a priority or "first" claim.
- **Scope:** evidence relevant to prediction, source monitoring, metacognitive information search, and
  the Stage 0E model repair.
- **Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.

## 1. What changed in Stage 0E

The Stage 0D simulation result was generated with oracle prediction and prediction/outcome double
counting. Stage 0E removes both. The evidence update therefore separates:

1. **Design evidence** — the task can be simulated and the model is internally calibrated.
2. **Construct evidence** — the predicted behavioural signature is present in simulation.
3. **Human evidence** — none. No human data were collected.

The Stage 0E audit downgrades the Stage 0D specificity gate and the Stage 0E counterfactual and policy
gates to `LIMITED`.

## 2. Literature anchors

| Source | Type | Relevance | Boundary |
| --- | --- | --- | --- |
| [Dijkstra, Kok & Fleming 2022](https://doi.org/10.1016/j.neubiorev.2022.104557) | Peer-reviewed review | No single factor dissociates imagination from perception; higher-level evaluation matters. | CRT cannot claim a single prediction signal. |
| [Dijkstra, Fleming & Shea 2026](https://doi.org/10.1093/nc/niag048) | Peer-reviewed functional analysis | Task demands shape how the imagination-reality problem is solved. | Prediction must be manipulated as a task demand, not assumed. |
| [Dijkstra & Fleming 2026 preprint](https://doi.org/10.31234/osf.io/36xdz_v4) | Preprint; not peer-reviewed | Higher-order precision account is the primary competitor. | Must be tested as a competing model, not dismissed. |
| [Dijkstra et al. 2024](https://doi.org/10.1167/jov.24.5.13) | Peer-reviewed | Confidence ratings alone do not distinguish imagination from reality. | Confidence cannot be the sole CRT index. |
| [Hu et al. 2026](https://doi.org/10.1016/j.cognition.2025.106410) | Peer-reviewed, five experiments, N=477 | Metacognitive sensitivity predicts information-search quality. | Meta-EIG needs model-free and working-memory controls. |
| [Zhang, Nash & Otgaar 2023](https://doi.org/10.1080/09658211.2023.2216910) | Peer-reviewed | Cheap-strategy bias: cost can outweigh reliability in source monitoring. | A normative meta-EIG claim must beat cost-only. Stage 0E does not. |
| [Boeltzig et al. 2025](https://doi.org/10.1016/j.neuroimage.2025.121375) | Peer-reviewed | Larger prediction errors can improve source memory for mismatching targets. | Supports studying prediction error, not double counting it as evidence. |
| [Schulz, Fleming & Dayan 2023](https://doi.org/10.1037/rev0000401) | Peer-reviewed | Joint models of confidence, control, and information search. | CRT should be compared with this class of model. |
| [Coenen et al. 2015](https://doi.org/10.1016/j.cogpsych.2015.02.004) | Peer-reviewed | People adaptively select interventions on causal systems. | Adaptive intervention is a baseline, not direct CRT evidence. |
| [Gong et al. 2023](https://doi.org/10.1016/j.cogpsych.2022.101542) | Peer-reviewed | Active causal structure learning in continuous time. | Meta-EIG must add value beyond adaptive causal learning. |

## 3. Search boundary

Earlier searches (2026-10-30) returned:

- exact phrase `"counterfactual reality testing"`: 0 PubMed hits;
- exact phrase `"counterfactual reality monitoring"`: 0 PubMed hits;
- exact phrase `"active source monitoring"`: 0 PubMed hits;
- source monitoring + test selection: 0 PubMed hits;
- prediction error + source memory: 6 PubMed hits;
- source monitoring + metacognition/confidence: 45 PubMed hits;
- information search + metacognition: 46 PubMed hits;
- Europe PMC source monitoring + active inference/EIG: 1 hit;
- OpenAlex exact phrase: 0 hits.

These are **gap indicators**, not priority evidence. Indexing lag, vocabulary mismatch, and the rapid
search design mean the absence of a direct hit cannot support a "first" claim.

## 4. What the evidence supports

- Prediction error is a plausible contributor to source memory, but the literature does not establish
  that a prediction generated from a source belief is independent evidence.
- Metacognitive sensitivity and information search are related, but the direction and specificity are
  debated.
- Cost and cheap heuristics are serious competitors to normative meta-EIG.
- Confidence alone is insufficient.
- Higher-order precision is a credible alternative model.

## 5. What the evidence does not support

- A claim that CRT improves source accuracy in humans.
- A claim that meta-EIG is the normative policy people use.
- A claim that dual-hypothesis prediction is necessary for reality monitoring.
- A claim of priority, novelty, or "revolutionary" status.
- A clinical, diagnostic, or training claim.

## 6. Stage 0E implications

1. **Report oracle inflation.** The Stage 0D 0.160 specificity gain was generated with oracle
   prediction; the belief-based source accuracy gain is 0.026 and diagnostic prediction accuracy is
   0.505.
2. **Use prospective reality testing as the default label.** "Counterfactual" is provisional until the
   dual-prediction gate passes.
3. **Treat meta-EIG as descriptive.** It beats cost-only by 0.060 but loses to the best competing
   policy by 0.012.
4. **Keep the test-facet result as simulation-only.** Minimum relative reliability 0.843 is a design
   property, not a human estimate.
5. **Do not register a human study yet.** The next step is model fitting, policy-level dual
   manipulation, and hierarchical SBC.

## 7. Next evidence tasks

- Independent second screener and a formal risk-of-bias assessment.
- Search PsycINFO, Scopus, and Web of Science.
- Retrieve full texts for the prediction-error/source-memory papers and extract effect sizes.
- Test the higher-order precision model against CRT in a pre-registered model comparison.
- Freeze the likelihood table from an independent calibration sample.

## 8. Limitations

- Rapid, non-systematic, single screener.
- No formal quality appraisal or publication-bias assessment.
- Several 2026 sources are very recent; one is a preprint.
- The search counts are sensitive to database vocabulary and date.
- The evidence update cannot adjudicate mechanism or causality.
