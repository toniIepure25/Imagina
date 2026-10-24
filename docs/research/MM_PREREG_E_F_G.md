# Preregistration drafts — Protocols E, F, G (multimodal imagery feedback)

Status: **DRAFT, NOT REGISTERED, NOT AUTHORIZED.** No participant may be enrolled under these designs until (1) an ethics
board approves the specific protocol, (2) the hardware checklist (`docs/hardware_validation_checklist.json`) gating
items are signed off for any device used, and (3) a `FeedbackAuthorization` is completed. Structure follows
`docs/preregistration.md`. Nothing here implies clinical efficacy; the system is not a medical device.

Shared elements (all three protocols)

- **Population.** Healthy adults 18–65, normal or corrected vision. Exclusions: self-reported neurological or psychiatric
  diagnosis, photosensitive epilepsy, current psychoactive medication, history of dissociative episodes, or a score above
  the screening cut-off on a dissociation screening scale chosen by the ethics board.
- **Primary outcome measure.** Change in **cue-free probe vividness** (1–5 self-report, rescaled 0–1) from the pre-training
  independent evaluation session to the post-training one. Probe trials present no visual or audio cues and no adaptive
  feedback (`training.Curriculum` probe trials, cue cap 0). This separates the participant's own imagery from vividness
  carried by the displayed scene.
- **Key secondary outcomes.** Objective object-rotation accuracy on probe trials (has a correct answer); VVIQ-2 total
  (questionnaire, administered pre/post); probe-trial stability ratings.
- **Not outcomes.** Cued-trial ratings, IQI, PID and every physiological proxy are process measures, reported descriptively.
  The perception-imagination distance is never an optimization target (`objective_allowed=False`).
- **Blinding check.** At the end, participants guess their arm; guess accuracy is reported, and the primary analysis is
  repeated with guess as a covariate.
- **Expectancy.** Credibility/expectancy questionnaire after session 1; included as a covariate in a sensitivity analysis.
- **Safety monitoring (all arms).** Reality-orientation and discomfort ratings every 5 trials; distress keywords in free
  text; fatigue estimate; session cap 20 min. Any controller SAFE_FALLBACK or TERMINATED event is logged as a safety event
  (persisted in `mm_safety_events`). Adverse events (headache, dizziness, derealization, distress) are recorded with
  severity and relatedness by the supervisor. **Stopping rules:** a participant stops on any moderate or severe adverse
  event or two derealization reports; the study pauses for review after any serious adverse event or if ≥ 10% of enrolled
  participants report a related adverse event.
- **Analysis software.** `app.multimodal.protocols.analyze_two_arm` (Welch t on change scores, Hedges g, participant
  bootstrap CI, Holm across the two primary-family tests) on the frozen code commit recorded at registration.
- **Missing data.** Primary analysis on completers; sensitivity analysis with multiple imputation under MAR and a
  worst-case (no change) imputation for dropouts in the active arm.

## E — Adaptive neurofeedback vs yoked sham

- **Question.** Does closed-loop adaptation of the Dream Corridor to the participant's own physiological/EEG state improve
  cue-free imagery more than an identical-looking feedback stream that is unrelated to their state?
- **Arms.** (1) Adaptive: `bounded_rules` policy driven by the participant's estimates. (2) Sham: `sham_yoked` replays the
  action sequence recorded from a previous adaptive participant (yoked by enrolment order). Allocation 1:1 by
  `training.assign_arm` (sealed study seed), participant-blind; the supervisor is unblinded for safety.
- **Sessions.** Baseline evaluation (no feedback) → 6 training sessions over 2–3 weeks → post evaluation → 4-week
  follow-up evaluation (persistence; secondary).
- **Hypothesis.** H_E: mean change (adaptive − sham) > 0. **SESOI** 0.10 on the 0–1 scale (≈ 0.4 points on 1–5).
- **Decision rule.** Supported if the Holm-adjusted test is significant and the lower 95% CI bound of (adaptive − sham)
  is > 0; declared smaller than the SESOI if the upper 95% CI bound is < 0.10; otherwise inconclusive.
- **Confound control.** Yoked sham matches feedback amount and variability; identical displays and instructions.

## F — Feedback training vs no-feedback training

- **Question.** Does training with feedback (adaptive) improve cue-free imagery more than the same exercises without any
  feedback?
- **Arms.** (1) Adaptive feedback, (2) No feedback (same curriculum, cue fading and rest periods; scene static).
  Not blind to participants (unavoidable); expectancy covariate mandatory.
- Sessions, outcomes, SESOI and analysis as E.

## G — Longitudinal improvement and transfer

- **Question.** Do probe-trial outcomes improve across sessions, and does improvement transfer to untrained exercises and
  persist at follow-up?
- **Design.** Within the E/F cohorts: probe outcomes at every session; untrained exercise set (`auditory`, `distraction`)
  evaluated only at baseline, post and follow-up.
- **Primary.** Difference in per-participant probe slope between arms (`analyze_two_arm` slope test); transfer = change on
  untrained exercises; persistence = follow-up minus post.
- **Caution.** Practice and test familiarity improve scores in every arm; only between-arm differences are interpreted.

## Sample size

Design simulation (`results/phase2/prereg_power_simulation.json`, `app.multimodal.protocols.design_operating_characteristics`,
1000 simulations per cell, assumed between-participant SD 0.15 and session noise SD 0.10 on the 0–1 scale — these SDs are
assumptions to be replaced by pilot estimates):

| n per arm | type-I (effect 0) | power, effect 0.05 | power, effect 0.10 (SESOI) | power, effect 0.15 |
|---|---|---|---|---|
| 20 | 0.047 | 0.18 | 0.53 | 0.85 |
| 30 | 0.048 | 0.25 | 0.73 | 0.97 |
| 40 | 0.042 | 0.32 | 0.85 | 0.99 |
| 60 | 0.060 | 0.44 | 0.95 | 1.00 |

Under these assumptions, **40 completers per arm** give ~85% power at the SESOI (two-sided α = 0.05, Welch test on
change scores); allowing 15% attrition, enrol 47 per arm. Type-I error stays near nominal (0.042–0.060, Monte Carlo).

Registration requires a pilot (n ≈ 10, not analysed for efficacy) to estimate the SDs, then re-running this simulation.

## What the current software can and cannot support

- Implemented: randomization, yoked sham, cue-free probes, curriculum, safety gating, persistence of every decision and
  safety event, deterministic replay of controller decisions.
- Not established: that any physiological estimate tracks imagery vividness (see `docs/EEG_MEG_FMRI_VALIDATION.md`,
  protocol B, and the earlier C1 gate). The "adaptive" arm therefore adapts to experimental proxies and self-report, and
  the study tests that scaffold, not neural decoding.
