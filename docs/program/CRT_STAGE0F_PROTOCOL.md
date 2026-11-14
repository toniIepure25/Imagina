# CRT Stage 0F: Protocol Integrity, Design Power, and Distortion Assay

**Status:** simulation and documentation only. No human data were collected. Human collection remains
blocked pending PI, ethics, registration, design power, and a trial-level CRT hierarchical SBC.

**Protocol:** `ANIMUS-CRT-v1`, version 0.4.0 (historical Stage 0F record). Stage 0G now uses version
0.5.0 with N=480/d=0.20; see [`CRT_THEORY_ADJUDICATION.md`](CRT_THEORY_ADJUDICATION.md).  
**Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`. No claim is upgraded by this stage.

## 1. Why Stage 0F exists

Stage 0E repaired the belief readout and added conditional recovery, but inspection of the Stage 1
documents found four defects that would have invalidated a registration:

1. The trial counts did not add up. The draft said 120 trials per occasion but listed 4 cells × 30
   plus 20 observe = 140; a second line said 60 per occasion with 15 per cell plus 10 observe = 70.
2. The primary prediction contrast compared `active_predict` with `active_intervene`, even though
   prediction can change test selection as well as source updating.
3. The active conditions used different selection policies, so a prediction effect could have been a
   policy effect.
4. The N=240 power claim for d=0.20 had no condition-contrast simulation behind it.

Stage 0F fixes the arithmetic, moves the primary prediction contrast to the **yoked** comparison,
labels the active contrast a package effect, and adds a design-power and distortion-assay audit.

## 2. Canonical design

- Two occasions, day 0 and day 14.
- 120 trials per occasion: four cells × 25 trials, plus 20 `observe` trials.
- 240 trials total.
- Cells: `active_intervene`, `active_predict`, `yoked_intervene`, `yoked_predict`.
- Primary contrast: `yoked_predict` minus `yoked_intervene`.
- Secondary contrast: `active_predict` minus `active_intervene`; this is a package effect.
- Six tests, at most two per trial, no replacement; fluency is the zero-diagnosticity trap.
- Estimated session duration is 40 minutes plus questionnaires, below the 75-minute cap.

The machine-readable source of truth is
[`science/protocols/crt-v1.yaml`](../../science/protocols/crt-v1.yaml). The validator in
`backend/app/research/crt/protocol.py` enforces the arithmetic, the yoked primary contrast, the
four-cell structure, the six tests, the fluency trap, and the session cap.

## 3. Artifacts

| Artifact | Purpose | Decision |
| --- | --- | --- |
| [`CRT_STAGE0F_PROTOCOL_AUDIT.json`](../../results/crt/CRT_STAGE0F_PROTOCOL_AUDIT.json) | Trial arithmetic and contrast integrity | `CRT_STAGE0F_PROTOCOL_PASS` |
| [`CRT_STAGE0F_DESIGN_POWER.json`](../../results/crt/CRT_STAGE0F_DESIGN_POWER.json) | Prediction, false-seen, and reliability power | `CRT_STAGE0F_DESIGN_REVIEW` |
| [`CRT_STAGE0F_DISTORTION.json`](../../results/crt/CRT_STAGE0F_DISTORTION.json) | Assay sensitivity to an injected false-seen shift | `CRT_STAGE0F_DISTORTION_PASS` |
| [`CRT_STAGE0F_HIERARCHICAL_SCREENING.json`](../../results/crt/CRT_STAGE0F_HIERARCHICAL_SCREENING.json) | Conditional group-mean recovery screening | `CRT_STAGE0F_HIERARCHICAL_SCREENING_PASS` (screening only) |
| [`CRT_STAGE0F_HIERARCHICAL_SBC.json`](../../results/crt/CRT_STAGE0F_HIERARCHICAL_SBC.json) | Endpoint-level full hierarchical SBC | `CRT_STAGE0F_HIERARCHICAL_ENDPOINT_PASS` |
| [`CRT_STAGE0F_MODEL_RECOVERY.json`](../../results/crt/CRT_STAGE0F_MODEL_RECOVERY.json) | Endpoint M0/M2/M3/M4 recovery | `CRT_STAGE0F_MODEL_RECOVERY_PASS` |
| [`CRT_STAGE0F_REGISTRATION_PACKAGE.json`](../../results/crt/CRT_STAGE0F_REGISTRATION_PACKAGE.json) | Registration readiness summary | `BLOCKED` |

## 4. Design-power result

The planning approximation simulates paired condition accuracy with between-person heterogeneity,
within-person correlation, trial-level binomial noise, and attrition. It is not the CRT generative
model and is not a human effect-size estimate.

At N=240, 25 trials per cell per occasion (50 trials per condition), 10% attrition, and a
standardized effect of d=0.20, power is approximately 0.61. A d=0.30 target at N=240 gives
approximately 0.93; a d=0.20 target requires roughly N=520 in the same approximation (0.92).

This is a **REVIEW**, not a pass. The registration is blocked until the PI chooses one of:

1. retain d=0.20 and increase N to approximately 520;
2. retain N=240 and pre-register d=0.30 as the smallest effect of interest, with d=0.20 as a
   sensitivity analysis;
3. replace the raw-accuracy primary endpoint with a model-based estimate that has a defensible
   precision target.

No option may be chosen after looking at human condition means. The choice must be written into the
registration before data collection.

## 5. Distortion-assay result

The current CRT model can be run in two ways. With the prediction-consistency bias fixed at zero
(`b_pi=0`), prediction is only a belief readout and the single-versus-dual false-seen contrast is
null. With `b_pi=0.4`, a separate bias channel produces a positive dual-versus-single shift. The assay
was validated against an **injected** +5 percentage-point false-seen shift in imagined items and
detected it with power above 0.80.

This does **not** show that dual prediction causes distortion in humans. It shows that the planned
paired false-seen assay can detect a shift of that size if one exists, and that the current model has
a candidate bias channel. The Stage 1D human study is the test of whether that channel exists.

## 6. Hierarchical SBC and model recovery

Stage 0F contains two hierarchical checks:

1. A **conditional screening** with participant-level `pi` variation. It uses the existing
   per-participant readout fit, not a joint hierarchical posterior, and is supporting evidence only.
2. A **full hierarchical Bayes model for the Stage 1D paired false-seen endpoint**, implemented in
   the standalone `analysis/crt/hierarchical_sbc.py` package. It models participant-level paired
   differences, group means, between-person SD, and known binomial standard errors. It uses 1,000
   prior draws.

Endpoint SBC results:

- primary endpoint: mean rank 0.505, coverage 0.936, chi-square 7.12 with 9 df (critical 21.666);
- second endpoint: mean rank 0.491, coverage 0.954, chi-square 5.52;
- model recovery balanced accuracy 0.855 for M0/M2/M3/M4.

The four model labels here are **endpoint parameterizations**:

- `M0`: no format effect;
- `M2`: common single-versus-dual format effect;
- `M3`: dual-specific effect with the nondiagnostic arm fixed at zero;
- `M4`: dual-specific plus nondiagnostic-demand effect.

These are not the Stage 0D theory models. Model recovery is just above threshold and the M3/M4
confusions are non-trivial. A trial-level CRT hierarchical SBC is still outstanding and remains a
registration blocker.

## 7. Commands

From `backend/`:

From the repository root:

```powershell
python -m analysis.crt.hierarchical_sbc --out results\crt\CRT_STAGE0F_HIERARCHICAL_SBC.json --recovery-out results\crt\CRT_STAGE0F_MODEL_RECOVERY.json
```

From `backend/`:

```powershell
python -m app.cli.crt_stage0f --check
python -m app.cli.crt_stage0f --write --out-dir ..\results\crt
```

`--check` is fast and fails only on protocol-integrity errors. `--write` runs the fuller design grid,
distortion assay, and hierarchical screening. `--strict` exits non-zero on any REVIEW/LIMITED
decision.

## 8. Boundaries

- No human data.
- No clinical sample.
- No neural data.
- No claim of a validated measure.
- No claim that dual prediction is beneficial or harmful in humans.
- No “first”, “revolutionary”, or priority claim.
- The `counterfactual_reality_testing` label remains provisional; the fallback is **prospective
  reality testing**.
