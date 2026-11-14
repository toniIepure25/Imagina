# CRT Test-Likelihood Calibration Protocol

**Status:** protocol only. Human calibration is gated by ethics, registration, and PI approval.
**Parent protocol:** `ANIMUS-CRT-v1`, version 0.5.0.
**Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.

## 1. Why calibration is needed

The model-based primary endpoint inverts a test-likelihood table, `p(test outcome | source)`. That table
cannot be assumed from task design. If tests are not diagnostic, or their diagnosticity changes across
occasions, the model-based endpoint is unidentified even when raw source accuracy looks acceptable.

The calibration sample therefore estimates the likelihood table and tests whether it is stable enough to
freeze. It is **not** a test of the CRT prediction effect and cannot support a CRT claim.

## 2. Design

- Independent sample, N=80, no overlap with the pilot (N=40), Stage 1D (N=160), or main study (N=480).
- One session, 120 trials, same six tests and four sources as the main task.
- Ground-truth source is induced by the experimenter, not inferred from the participant's response.
- Sources are balanced within participant: 30 `seen`, 30 `imagined`, 30 `described`, 30 `new`.
- Test order is randomized within participant; no performance feedback; no adaptive selection.
- Attention and instruction checks are administered before the first trial and every 40 trials.
- Primary calibration endpoint: the source-by-test accuracy matrix.
- Secondary: test–retest ICC on a random 40% of trials repeated after a 20-minute delay.

## 3. Analysis

For each test `j` and source `s`, fit a hierarchical beta-binomial model:

```
correct_ij ~ Binomial(n_ij, theta_ij)
logit(theta_ij) = mu_js + u_i + v_ij
u_i ~ Normal(0, sigma_u)
v_ij ~ Normal(0, sigma_v)
```

with weakly informative priors (`mu_js ~ Normal(0, 1.5)`, `sigma ~ HalfNormal(0.5)`). Report posterior
means and 95% credible intervals for each cell, plus the participant-level SD.

Calibration passes only if:

1. every test has at least one source with posterior mean diagnosticity at least 0.65;
2. the 95% credible interval width for each retained cell is at most 0.15;
3. the source-by-test matrix is measurement-invariant across the repeated block (maximum absolute
   standardized difference ≤0.25);
4. test–retest ICC is at least 0.70 for the retained tests;
5. posterior predictive checks show no systematic source or test misfit.

If any criterion fails, the model-based endpoint is **not** frozen. The analysis falls back to the
pre-registered raw source-accuracy endpoint, and the calibration failure is reported as a primary
measurement limitation. No post hoc table tuning is permitted.

## 4. Blinding and independence

- The calibration analyst does not analyse the main confirmatory dataset.
- The main analysis team receives only the frozen table and the calibration report, not calibration
  participant identifiers.
- The calibration report is dated and hashed before main-study unblinding.
- The N=80 sample is not reused for the main effect.

## 5. Artifacts

- [`CRT_STAGE0G_CALIBRATION_PROTOCOL.json`](../../results/crt/CRT_STAGE0G_CALIBRATION_PROTOCOL.json) —
  machine-readable design and pass/fail rules.
- `CRT_CALIBRATION_REPORT.json` — planned; generated only after human data collection.

No human calibration data exist. `ANIMUS_P5_CRT_CALIBRATION` refers to an earlier simulation-only
check; it is not this protocol and is not human evidence.

## 6. Boundaries

No clinical, diagnostic, decoding, training, or measurement-upgrade claim. Calibration is a
measurement-validity step inside a behavioural study, not a validation of IMAGINA as an instrument.
