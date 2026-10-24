# ANIMUS — Validation Protocol (proposed, not executed)

**Status:** protocol proposal for an eventual independent study. No participant data has been collected by
this repository. Nothing here authorizes a clinical or enhancement claim.

## Question

Can a short, local, scene-based practice loop produce **reliable and interpretable** behavioural estimates
of object reconstruction, spatial layout, discrimination, control, and confidence calibration — and does
uncertainty-aware selection improve measurement precision relative to coverage-first or fixed selection,
without harming calibration?

This is a measurement and feasibility question, not a question about neural decoding, imagery strength, or
training effects. Reconstruction scores are proxies for task performance, not hidden imagery.

## Design

A preregistered, within-subject, counterbalanced study with three session types:

| Arm | Procedure |
|---|---|
| Information gain | Coverage floor, then expected information gain (`ADAPTIVE_POLICY.md`) |
| Coverage first | Least-sampled dimension, same bounded difficulty controller |
| Fixed | Same task families in a fixed, matched sequence with the same difficulty schedule |

Order is counterbalanced across participants; sessions are separated by at least 24 hours and at most
7 days. Task content, preview duration, target count, decoy count, and total trial count are matched. The
primary comparison is **measurement quality**, not a claim that one arm makes people better at imagining.

A second, separate study would be needed for any training/transfer question. This protocol does not
authorize one.

## Participants

- Adults 18–65, recruited without selecting for imagery ability.
- Screen for neurological, psychiatric, or visual conditions that would confound task performance; do not
  recruit a clinical sample for a non-clinical instrument.
- Include people with self-reported aphantasia and hypophantasia; do not treat them as a deficit group.
- Target `N = 120` for the reliability study (at least 40 per order, with six possible orders), with a
  stated attrition allowance.
  This is a planning target, not a power calculation for an effect the instrument has not earned.
- No deception; no neural data; no biological sample.

## Measures

| Construct | Measure | Role |
|---|---|---|
| Object reconstruction | Token-selection F1, omissions, intrusions | Primary behavioural estimate |
| Spatial layout | Mean position score and mean normalized error | Primary behavioural estimate |
| Scene stability | Attribute-recall accuracy across delays | Secondary / legacy estimate |
| Discrimination | Forced-choice candidate comparison | Primary ability estimate |
| Spatial inference | Opposed-view choice | Secondary / legacy estimate |
| Control | Directed-change choice | Primary ability estimate |
| Calibration | Brier score from confidence | Primary metacognitive measure |
| Epistemic interview | Object/spatial posterior accuracy, Brier, coverage, abstention, entropy | Exploratory secondary measure |
| Scene Threshold | 2-AFC d′, per-feature threshold, side bias, Brier, coverage | Exploratory secondary measure |
| Test–retest | Feature-level r, SEM, MDC95 across two occasions | Exploratory reliability measure |
| Self-report | VVIQ or MIQ-RS | Convergent/divergent description only |
| Usability | Short post-session questionnaire | Feasibility |
| Adverse experience | Fatigue/frustration check | Safety and stop rule |

The VVIQ/MIQ-RS are not ground truth. The 2024 mental-comparison literature reports minimal correlations
between self-report and objective performance; disagreement is expected and must not be interpreted as
malingering.

## Analysis plan

1. Report completion, attrition, and adverse events before any model.
2. Estimate reliability with split-half or bootstrap internal consistency per dimension; report `n` and
   confidence intervals. Do not report a single coefficient without its interval.
3. Estimate the information-gain vs coverage-first vs fixed difference in **posterior RMSE against
   held-out trials**, **coverage** (trials per dimension), **estimate uncertainty**, and **calibration**,
   using a mixed model with participant as a random intercept and order as a fixed effect. Report
   standardized and raw differences.
4. Test the object/spatial dissociation directly: fit separate scores and report their correlation with
   an interval. Do not assume the dimensions are independent because the UI separates them.
5. Test measurement invariance only if the sample supports it; otherwise describe the limitation.
6. Treat self-report correlations as descriptive; do not use them to validate the task by fiat.
7. For the epistemic interview, test whether posterior accuracy and calibration improve with probe count,
   whether information-gain selection beats coverage-first at matched budget, and whether abstention is
   associated with difficulty or fatigue. Treat all of this as exploratory until a dedicated protocol.
8. For Scene Threshold, fit the threshold model to held-out trials and report recovery bias and censoring.
   Test whether the adaptive staircase improves threshold precision relative to a fixed-delta schedule at
   matched trial count. Estimate feature-level test–retest reliability across two occasions; with only two
   continuous features, this will usually be unidentifiable, so add feature types or occasions before
   claiming a reliability coefficient. Do not compare thresholds across scenes or people without norms.
9. Preregister the primary outcome and the analysis; label all else exploratory.
10. Publish the analysis code and a synthetic dataset; do not publish identifiable data.

## Controls and bias

- Counterbalance order and task variants.
- Counterbalance token order and decoy identity across participants; keep target count and decoy count
  matched across arms.
- Match preview duration and trial count across arms.
- Do not let the experimenter see condition during scoring; scoring is server-side and deterministic.
- Include a no-adaptive, fixed-difficulty arm to separate selection from difficulty.
- For Scene Threshold, counterbalance target side and form, match preview time and pair rendering, and
  report practice/fatigue and display conditions. Treat side bias as a response tendency, not a criterion.
- Check for device, input, and timing effects; log latency and browser/renderer metadata locally.
- Do not use engagement, streak, or leaderboard incentives.

## Stopping and safety

Stop a session on self-reported fatigue or frustration, or at the protocol time limit. There is no
penalty for stopping. A participant may withdraw and request deletion at any time. The study must have
ethics approval before recruitment; this document is not ethics approval.

## What would falsify the instrument

- Reliability near zero or unstable across sessions.
- Information-gain, coverage-first, and fixed arms indistinguishable on held-out RMSE or uncertainty, with
  no compensating benefit.
- Object and spatial reconstruction scores do not separate, or the error profile is not stable enough to
  interpret.
- Reconstruction performance is dominated by device/input/renderer effects rather than scene content.
- Calibration uncorrelated with ability or insensitive to overconfidence.
- Strong association with a general factor that makes the five dimensions redundant.
- Harms or systematic distress in aphantasic participants.

A negative result is informative and must be reported; it is not a reason to relabel the instrument.

## Explicit non-claims

- No diagnosis, treatment, cure, or clinical validation.
- No claim of increased imagery strength, vividness, or neural content.
- No claim of far transfer to memory, intelligence, creativity, or daily life.
- No claim that adaptive practice is superior for learning until the study supports it.
- No claim that the task measures "the mind's eye" rather than performance on a specific task.

## References

- Bainbridge et al. (2019). https://doi.org/10.1038/s41467-018-07830-6
- Bainbridge et al. (2021). https://doi.org/10.1016/j.cortex.2020.11.014
- Fink, König & Frey (2026). https://doi.org/10.3758/s13428-026-03123-9
- Pearson, J. (2019). https://doi.org/10.1038/s41583-019-0202-9
- Rademaker & Pearson (2012). https://doi.org/10.3389/fpsyg.2012.00224
- Melby-Lervåg et al. (2016). https://doi.org/10.1177/1745691616635612
- Dance et al. (2021). https://doi.org/10.1016/j.concog.2021.103243
- Mental comparison task (2024). https://doi.org/10.3758/s13428-024-02496-z
- Challenge Point scoping review (2025). https://doi.org/10.1080/00222895.2025.2508283
