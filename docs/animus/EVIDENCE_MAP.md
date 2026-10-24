# ANIMUS — Evidence Map

This map separates **what the literature supports**, **what ANIMUS implements**, and **what remains
unvalidated**. It is a design aid, not a systematic review. Citations are anchors, not proof that ANIMUS
inherits their findings.

## Claims and status

| Claim | Evidence status | What ANIMUS may say | What it must not say |
|---|---|---|---|
| Visual imagery is perception-like and involves overlapping visual machinery | Supported, with debate about format and mechanism (Pearson, 2019) | Imagery is treated as an active, reconstructive process | "We read the image in your brain" |
| Imagery varies continuously in the population; aphantasia is not rare | Population estimate around 3.9% (Dance et al., 2021) | Aphantasia is a variation and a design constraint | "Aphantasia is a deficit" / "we cure it" |
| Imagery training improves metacognition more reliably than imagery strength | Rademaker & Pearson (2012) found improved metacognition, not strength | Practice may improve task strategy and confidence calibration | "Training boosts imagery strength" |
| Mental practice can support motor performance | Heterogeneous evidence, pooled SMD ≈ 0.39 (Goble et al., 2021); not universal (Rao et al., 2015, p = .06) | Use as a plausible scaffold, not a guaranteed intervention | "Guaranteed performance gain" |
| Cognitive training produces broad far transfer | Not supported (Melby-Lervåg et al., 2016) | No far-transfer claim | "Improves intelligence/memory in daily life" |
| Drawing from memory captures object and spatial scene content | Supported as a research method (Bainbridge et al., 2019) | A reconstruction proxy is worth testing | "Our task is a validated drawing measure" |
| Aphantasia can show lower object detail with preserved spatial accuracy | Reported in a drawing study (Bainbridge et al., 2021) | Separate object and spatial scores; variation framing | "Low object score means deficit" |
| Adaptive testing with posterior uncertainty can improve precision | Simulation evidence in multidimensional IRT (Fink et al., 2026) | Use information gain as an experimental policy | "Our policy is proven in humans" |
| Binary questions can recover coarse scene content when the answer is scored against a hidden scene | Plausible from scene-memory and drawing studies; no direct ERI validation | Treat object/spatial posteriors as a behavioural proxy | "The interview measures imagery" |
| Confidence ratings carry calibration information | Supported in metacognition research, but task-specific | Report Brier and overconfidence separately from accuracy | "Confidence proves the reconstruction is correct" |
| 2-AFC discrimination separates sensitivity from response-side bias | Standard SDT result; equal-variance Gaussian model is a simplifying assumption | Report d′ and signed side bias separately; do not report a yes/no criterion | "The threshold is an imagery-strength score" |
| Adaptive staircases can concentrate trials near a threshold | Established psychophysical method, but implementation-specific (Fink et al., 2026) | Use a bounded 2-down/1-up rule, then fit the threshold from all trials | "The staircase itself measures ability" |
| Scene memory supports coarse object and spatial change detection | Supported in scene-memory research, but no direct validation of this contrast task | Treat thresholds as within-scene behavioural estimates | "Thresholds compare across scenes or people" |
| Test–retest correlation across features estimates consistency | Feature-level Pearson r is possible only with enough aligned features | Report r, SEM, and MDC95 only when at least three features align; otherwise say insufficient | "A single session is a stable trait" |
| Self-report and objective imagery measures converge | Weak/minimal correlations reported (2024 mental comparison work) | Report them as different evidence streams | "VVIQ proves the task is valid" |
| Adaptive difficulty around an intermediate challenge can support practice | Plausible but heterogeneous; 2025 Challenge Point scoping review | Use a bounded heuristic and call it a heuristic | "Scientifically optimized learning" |
| A short local task can diagnose a clinical condition | Not supported by this instrument | Nothing | Any diagnosis or treatment claim |
| Neural decoding of imagined content is available here | Not implemented; no validated decoder | Nothing | "Neural reconstruction" / "mind reading" |

## Design decisions that follow

1. **No composite score.** Dimensions dissociate; a composite would hide the evidence.
2. **No neural claim.** The scene is symbolic and the task is behavioural; the neural boundary fails
   closed.
3. **No imagery-strength claim.** Tasks measure reconstruction/recall/discrimination/view inference/choice,
   not vividness or neural strength.
4. **No far transfer.** Practice effects, if any, stay task-local until a separate study says otherwise.
5. **No clinical use.** `clinical_use = DISABLED` is enforced in the capability envelope.
6. **Aphantasia is a variation.** Low estimates are described as task performance, never as a defect.
7. **Reconstruction is a proxy.** Object F1 and spatial error are behavioural scores, not decoded content.
8. **Information gain is a hypothesis.** Its benefit is tested in simulation and then in a preregistered
   study, not assumed from the IRT literature.
9. **Abstention is data.** An abstention contributes to coverage and is not scored as a wrong answer.
10. **The interview is not a decoder.** Posterior probabilities over a symbolic scene are not a neural
    image, a dream reconstruction, or an objective imagery measure.
11. **2-AFC has no identified criterion.** The target side is counterbalanced; the product reports signed
    side bias, not a yes/no response criterion.
12. **Thresholds are local.** They are normalized within a scene and are not comparable across scenes,
    displays, forms, or people without a validated norm.
13. **Reliability is feature-level.** With two occasions and two continuous features, r is usually
    unidentifiable; the observatory says `insufficient` rather than reporting a misleading coefficient.
14. **No composite.** d′, threshold, side bias, Brier, coverage, and reliability stay separate.

## Open questions

- Are the five dimensions separable, or do they collapse into one general factor?
- Do object and spatial reconstruction scores separate as the aphantasia drawing literature predicts?
- Does information gain improve held-out precision relative to coverage-first and fixed selection?
- Does the Beta response model fit human confidence, or is it systematically overconfident?
- Is abstention used strategically, or does it track fatigue and task difficulty?
- How much do renderer, device, preview duration, and token-bank composition influence estimates?
- Are estimates stable across days and orders?
- Do self-report and task performance diverge in the same way as in laboratory studies?
- What is the minimal reliable trial count per dimension?

These are research questions, not marketing copy. Until they are answered, the profile is labelled
experimental.

## References

- Bainbridge, W. A., Hall, E. H., & Baker, C. I. (2019). *Nature Communications*.
- Bainbridge, W. A., & Baker, C. I. (2020). https://doi.org/10.1016/j.cub.2019.12.004
- Siena, M., & Simons, D. J. (2024). https://doi.org/10.1162/jocn_a_02120
- Reeder et al. (2024). https://doi.org/10.1016/j.cognition.2024.105907
- Lin, P.-H., & Oberauer, K. (2022). https://doi.org/10.1016/j.cogpsych.2022.101463
- Teng, S. (2025). https://doi.org/10.1016/j.neuropsychologia.2025.109331
- Rainforth, T., et al. (2024). https://doi.org/10.1214/23-sts915
  https://doi.org/10.1038/s41467-018-07830-6
- Bainbridge, W. A., et al. (2021). *Cortex*. https://doi.org/10.1016/j.cortex.2020.11.014
- Fink, A., König, C., & Frey, A. (2026). *Behavior Research Methods*.
  https://doi.org/10.3758/s13428-026-03123-9
- Jin, Z., Hsu, Y.-F., & Li, Y. (2024). *Vision*.
  https://doi.org/10.3390/vision8030056
- Pearson, J. (2019). *Nature Reviews Neuroscience*. https://doi.org/10.1038/s41583-019-0202-9
- Dance, C. J., et al. (2021). *Consciousness and Cognition*.
  https://doi.org/10.1016/j.concog.2021.103243
- Rademaker, R. L., & Pearson, J. (2012). *Frontiers in Psychology*.
  https://doi.org/10.3389/fpsyg.2012.00224
- Goble, D. J., et al. (2021). *HERD*. https://doi.org/10.1177/1553350621990480
- Rao, A., et al. (2015). *American Journal of Surgery*.
  https://doi.org/10.1016/j.amjsurg.2015.01.028
- Melby-Lervåg, M., et al. (2016). *Perspectives on Psychological Science*.
  https://doi.org/10.1177/1745691616635612
- Mental comparison task (2024). *Behavior Research Methods*.
  https://doi.org/10.3758/s13428-024-02496-z
- Challenge Point scoping review (2025). *Journal of Motor Behavior*.
  https://doi.org/10.1080/00222895.2025.2508283
- Butler, A. J., et al. (2012). MIQ-RS. https://doi.org/10.1155/2012/497289
