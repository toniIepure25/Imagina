# CRT Model Predictions for the Stage 0D Tournament

## Status

- **Historical design hypotheses, not empirical findings.** The Stage 0D tournament used oracle
  prediction and a prediction-error source-update signature. Stage 0E replaces both; this table is
  retained for provenance and must not be used as the current model space.
- **Protocol:** `ANIMUS-CRT-v1`.
- **Historical artifact:** [`results/crt/CRT_STAGE0D_MODEL_TOURNAMENT.json`](../../results/crt/CRT_STAGE0D_MODEL_TOURNAMENT.json).
- **Current repair:** [`CRT_MODEL_REPAIR_AUDIT.md`](CRT_MODEL_REPAIR_AUDIT.md).

The five signatures are ordinal design predictions. They are not fitted to human data. Their purpose is
to make model disagreement explicit before the confirmatory study.

## Signature definitions

| Signature | Definition | Primary contrast |
| --- | --- | --- |
| `prediction_advantage` | Source accuracy gain from prospective prediction over outcome-only testing | `active_predict` minus `active_intervene` |
| `meta_eig_efficiency` | Normalized meta-EIG relative to greedy and random baselines | `CRTE_meta` |
| `active_selection_gain` | Accuracy gain from active choice over random-passive exposure | `active_predict` minus `random_passive` |
| `specificity_gain` | Diagnostic minus matched non-diagnostic prediction | `active_predict_diagnostic` minus `active_predict_nondiagnostic` |
| `prediction_readout_error` | Absolute error of the belief-based prediction; **not** a source-update term | `mean_prediction_error` |

The Stage 0D artifact's fifth column was `prediction_error_update` (posterior shift). That signature is
retired: the repaired model does not let the prediction update the current source posterior. A later
`M4` model may let prediction error affect **later** test selection or confidence, but that requires a
separate fit and is not part of the Stage 0D tournament.

## Predicted signatures (historical anchors)

| Model | Prediction advantage | Meta-EIG efficiency | Active selection | Specificity | Readout error |
| --- | ---: | ---: | ---: | ---: | ---: |
| `crt_meta_eig` | 0.12 | 0.55 | 0.03 | 0.08 | 0.15 |
| `eig_only` | 0.00 | 0.08 | 0.03 | 0.00 | 0.00 |
| `higher_order_precision` | 0.00 | 0.30 | 0.01 | 0.00 | 0.10 |
| `sdt_confidence` | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `heuristic_source` | 0.00 | -0.05 | -0.02 | 0.00 | 0.00 |

These values are **scenario anchors** chosen to represent directional disagreement. They are not effect
sizes for power analysis. The confirmatory study will estimate the signatures and compare model
predictions out of sample. The Stage 0D separability result does not carry over to the repaired model
until the tournament is rerun with belief-based prediction.

## Decisive contrasts

1. **Specificity:** `active_predict_diagnostic` versus `active_predict_nondiagnostic`. If equal, the
   prediction effect is generic engagement or evidence, not counterfactual prediction.
2. **Selection:** `active_predict` versus `random_passive`. If equal, active choice adds no measurable
   selection benefit.
3. **Adaptive design:** `algorithm_adaptive` versus `random_passive`. This estimates the value of
   adaptive test selection independent of human choice.
4. **Incremental validity:** CRT versus higher-order precision, SDT, and confidence-only models on
   held-out participants.
5. **Prediction-error form:** match/mismatch versus continuous absolute error versus precision-weighted
   error, tested only as a readout or as a later `M4` attribution term, never as a current source
   likelihood.

## Stage 0D result (historical oracle path)

The signature-separability analysis with 40 observations per model and 0.03 noise returned balanced
accuracy **0.90**:

| True model | Recovered correctly |
| --- | ---: |
| `crt_meta_eig` | 1.000 |
| `eig_only` | 0.900 |
| `higher_order_precision` | 1.000 |
| `sdt_confidence` | 0.825 |
| `heuristic_source` | 0.775 |

The heuristic model is the weakest diagonal. The result clears the 0.80 gate, but it is only a statement
about the separability of the **design signatures**. It does not show that the models are separable in
human data, and it does not estimate model evidence. Stage 0E shows that the oracle specificity signature
does not reproduce under belief-based prediction, so the `crt_meta_eig` column is not a current empirical
prediction.

## Falsification rules

- If `specificity_gain <= 0`, the CRT-specific claim fails.
- If `active_selection_gain <= 0`, no active-selection claim is allowed.
- If CRT does not outperform higher-order precision out of sample, narrow CRT to a measurement assay.
- If the signature confidence regions overlap, do not run a "decisive" human test; redesign first.

## Language

Call this a **model-signature separability analysis**, not "model recovery" or "model validation." The
latter would require fitting the models to human data and reporting posterior predictive checks.
