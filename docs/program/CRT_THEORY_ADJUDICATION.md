# CRT Theory Adjudication

**Status:** Stage 0H working document, 2026-10-31. It defines the theory competition that the
trial-level readout, full joint model, design optimization, and registered report must test. It is not
evidence that CRT works in humans and does not support a priority or “revolutionary” claim.

**Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.

**Companion documents:** [Stage 0H protocol](CRT_STAGE0H_PROTOCOL.md),
[scoping protocol](../research/CRT_STAGE0G_SCOPING_PROTOCOL.md),
[literature positioning](../research/CRT_LITERATURE_POSITIONING.md),
[analysis plan](CRT_ANALYSIS_PLAN.md).

## 1. Why adjudication is the contribution

The literature already contains reality-monitoring research, prediction-error research, and
computational accounts of imagery–perception separation. A study that merely adds another task would be
incremental. The defensible contribution is to make three accounts compete on a **causal, calibrated,
model-based test** with a result that can reject CRT.

The three accounts are:

1. **Signal-strength threshold:** reality attribution reflects the strength of a sensory signal relative
   to a threshold; imagination is weaker or intermixed with perception.
2. **Higher-order precision inference:** reality monitoring is higher-order inference on the precision
   of sensory activity; confidence and precision, not prospective test prediction, carry the effect.
3. **Active prospective inference (CRT):** a person predicts the consequence of a source-diagnostic test,
   compares the prediction with the outcome, and updates source attribution; dual counterfactual
   prediction adds diagnostic value but also a source-confusion cost.

## 2. Evidence base and tensions

| Finding | Source | Tension for CRT |
|---|---|---|
| Reality judgments track the strength of imagery/perception signals | Dijkstra & Fleming 2023, *Nature Communications*, [doi:10.1038/s41467-023-37322-1](https://doi.org/10.1038/s41467-023-37322-1), PMID 36959279 | A prediction effect could be a vividness/signal-strength effect |
| Fusiform activity predicts imagery–perception confusions; frontal reality judgments interact with it | Dijkstra et al. 2025, *Neuron*, [doi:10.1016/j.neuron.2025.05.015](https://doi.org/10.1016/j.neuron.2025.05.015), PMID 40480215 | Neural evidence supports a strength/monitoring account, not prospective test prediction |
| Conscious vision may function as reality monitoring for offline simulation | Fleming & Michel 2025, *Behavioral and Brain Sciences*, [doi:10.1017/S0140525X25000068](https://doi.org/10.1017/S0140525X25000068), PMID 40257183 | The function is broad; CRT must show a specific mechanism |
| Reality-monitoring decision policy need not be a slow winner-take-all tag | Peters 2026, *Behavioral and Brain Sciences*, [doi:10.1017/S0140525X25103075](https://doi.org/10.1017/S0140525X25103075), PMID 42342595 | Policy models must be compared, not assumed |
| Higher-order precision may explain reality monitoring without a dedicated tag | Dijkstra & Fleming preprint, [doi:10.31234/osf.io/36xdz_v2](https://doi.org/10.31234/osf.io/36xdz_v2) | Preprint; strongest theoretical competitor |
| Expectation violation improves short-term source memory | Zheng et al. 2025, *Psychonomic Bulletin & Review*, [doi:10.3758/s13423-025-02715-4](https://doi.org/10.3758/s13423-025-02715-4), PMID 40481295 | Prediction error can help; CRT must explain when it harms |
| Prediction-error size guides memory reshaping | Boeltzig et al. 2025, *NeuroImage*, [doi:10.1016/j.neuroimage.2025.121375](https://doi.org/10.1016/j.neuroimage.2025.121375), PMID 40675423 | Supports error as a mechanism, not necessarily a source-attribution mechanism |
| Counterfactual imagination can impair memory for true actions | Dhammapeera et al. 2024, *Cognitive Neuroscience*, [doi:10.1080/17588928.2024.2315814](https://doi.org/10.1080/17588928.2024.2315814), PMID 38362597 | Supports the cost side of the double-edged hypothesis |
| Memory distrust did not moderate imagination inflation | Dudek & Polczyk 2025, *PLOS ONE*, [doi:10.1371/journal.pone.0327638](https://doi.org/10.1371/journal.pone.0327638), PMID 40748997 | Individual-difference claims must stay exploratory |
| Source and reality monitoring have partially distinct neural correlates | Martín-Luengo et al. 2026, *Human Brain Mapping*, [doi:10.1002/hbm.70614](https://doi.org/10.1002/hbm.70614), PMID 42524861 | Neural add-ons are a separate stage, not current evidence |

The central tension is that **externally generated prediction error often improves source memory**, while
**self-generated counterfactual simulation can contaminate it**. CRT’s specific hypothesis is that the
difference is not prediction error per se but whether the prediction is a diagnostic test consequence
that is later disambiguated from the source.

## 3. Three-account predictions

| Prediction | A. Signal strength | B. Higher-order precision | C. Active prospective inference |
|---|---|---|---|
| P1. Yoked prediction improves model-based source sensitivity | No; mediated by vividness | Maybe; via precision | Yes |
| P2. Dual prediction increases false-seen for imagined items | No | No | Yes |
| P3. Dual cost scales with counterfactual discrepancy | No | No | Yes |
| P4. Effect is source-asymmetric (imagined > seen) | No | No | Yes |
| P5. Prediction effect survives vividness/signal-strength adjustment | No | Partly | Yes |
| P6. Active-prospective model beats A and B out of sample | No | No | Yes |
| P7. Vividness and confidence manipulations identify M6 and M7 | M6 identified; M7 not | M7 identified; M6 not | Neither should absorb the other |
| P8. The design separates M2/M4/M6/M7 before human data | Not applicable | Not applicable | Required for a confirmatory claim |

These are **joint tests**. A single significant accuracy difference is not enough. The registered report
must pre-specify the model comparison and the adjustment set. P7/P8 are **design-identifiability**
predictions, not human outcomes.

## 4. Model mapping

The trial-level model space in [CRT_ANALYSIS_PLAN.md](CRT_ANALYSIS_PLAN.md) maps to the accounts:

- `M0`: outcome-only; no prediction effect.
- `M1`: prediction precision only.
- `M2`: single belief-based prediction.
- `M3`: dual counterfactual prediction.
- `M4`: dual prediction plus later error attribution.
- `M5`: prediction-induced source bias (`b_pi`).
- `M6`: signal-strength threshold; vividness/signal strength mediates the effect.
- `M7`: higher-order precision; source-general precision/confidence.

The confirmatory comparison is not “does M3 beat M0?” alone. It is whether **M3/M5 add out-of-sample
information beyond M6/M7** and whether the predicted interaction pattern is present.

Stage 0H implements M6 and M7 in the trial-level readout and in a full joint latent-source model.
The confirmatory set is **M0/M2/M4/M6/M7**; M1/M3/M5 remain exploratory. The readout and full-model
SBC/recovery are simulation checks, not human evidence. The full joint model still treats test choice
as observed, so it is not the policy POMDP; the scope string records that boundary.

The design-optimization result is a gate, not a result: if the chosen trial composition does not
separate M2/M4/M6/M7, the correct decision is `REVIEW` and no human data.

## 5. Critical tests and falsification

1. **Causal yoked test:** `yoked_predict − yoked_intervene` on model-based source sensitivity. A null or
   reverse effect rejects the simplest active-prospective claim.
2. **Cost test:** dual diagnostic minus single diagnostic on imagined false-seen rate, with the
   dual-nondiagnostic arm separating demand from content-specific simulation.
3. **Dose-response:** the dual cost should increase with counterfactual discrepancy. A flat relationship
   weakens the counterfactual mechanism.
4. **Source asymmetry:** imagined > seen; described/new intermediate. A source-general effect supports
   precision/engagement accounts instead.
5. **Incremental validity:** the prediction effect must survive adjustment for vividness, confidence,
   `d'`, and working memory. If it disappears, the signal-strength account wins.
6. **Out-of-sample model comparison:** M3/M5 must beat M6/M7 on LOO/WAIC with a pre-specified margin and
   pass recovery. If not, CRT is a measurement operationalization, not a new theory.

Pre-specified failure language:

- If P1 and P2 both fail, CRT is descriptive source monitoring.
- If P1 survives but P2 does not, prediction has a benefit without the proposed counterfactual cost.
- If P5 fails, the effect is a vividness/signal-strength effect.
- If P6 fails, the higher-order precision account is retained.

## 6. Design implications

- Keep the **yoked** primary contrast; the active contrast is a package effect.
- Use **single, dual, and dual-nondiagnostic** prediction arms for the cost test.
- Measure **vividness/signal strength**, prediction confidence, counterfactual discrepancy, response
  time, and source confidence; these are needed for the adjudication, not decoration.
- Calibrate the test-likelihood table independently; a hand-coded diagnostic matrix cannot adjudicate
  mechanisms.
- Use a **trial-level hierarchical model**; endpoint-only models cannot test source asymmetry or
  dose-response.
- Choose N=480 for d=0.20 (or N=360 with a pre-registered d=0.25 SESOI); do not retain N=240/d=0.20.
- Treat Stage 1D as the direct cost assay; do not infer cost from the main 2×2 alone.

## 7. Claim boundary

Allowed:

- “a preregistered adjudication of signal-strength, precision, and active-prospective accounts”
- “a causal test of prospective test-consequence prediction”
- “to our knowledge, no indexed study has directly combined …” only with the non-systematic search
  caveat.

Not allowed:

- “first”, “revolutionary”, “proves”, “decodes”, “diagnoses”, “validated”;
- any priority claim;
- any clinical, training, or neural-decoding claim.

## 8. Stage 0H artifacts

- `CRT_STAGE0H_MODEL_SPACE.json`
- `CRT_STAGE0H_DESIGN_OPTIMIZATION.json`
- `CRT_STAGE0H_FULL_MODEL_SBC.json`
- `CRT_STAGE0H_FULL_MODEL_RECOVERY.json`
- `CRT_STAGE0H_PACKAGE.json`
- Calibration protocol and independent likelihood table.
- Protocol version 0.6.0 with N=480/d=0.20 and the confirmatory M0/M2/M4/M6/M7 set.
- Registered-report package with adversarial-collaboration and independent-analyst agreements.

A `REVIEW` in design optimization or full-model recovery is a stop rule: revise the model/design,
not the claim.
