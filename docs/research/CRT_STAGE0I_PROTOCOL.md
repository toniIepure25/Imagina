# CRT Stage 0I — identifiability-first protocol package

**Protocol:** `ANIMUS-CRT-v1` v0.7.1, stage `0I`
**Status:** computational screening only; human data collection remains **BLOCKED**.
**Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`; no decoding, clinical, priority, or measurement-upgrade
claim is authorized.

Stage 0I changes the question from “which model fits best?” to “is the confirmatory model space
identified at the planned design, and can the design be improved without hiding weak separation?”
It is a methods and governance stage, not a result.

## What changed

1. **Belief-weighted likelihood repair.** The prediction readout now uses the participant's
   sequential source posterior, `q_i(a) = sum_s m_i(s) * p_as`, and the trial likelihood marginalizes
   the latent source with the same `m_i(s)` rather than an unweighted mean. The source update is
   outcome-only. Regression tests cover non-uniform beliefs, source-free likelihood evaluation, and
   the `alpha_pi` count. The previous code used `mean_s p_as` for the likelihood while using a
   different object for prediction; that inconsistency is now removed.
2. **NumPyro/NUTS implementation.** `analysis/crt/numpyro_model.py` supplies a JAX/NumPyro
   implementation of the same joint model. Its likelihood is parity-tested against the NumPy model
   (`test_nuts_likelihood_matches_the_numpy_model`), and smoke tests run M0 and M6 when the optional
   backend is installed. Target-scale NUTS SBC and recovery remain unrun and blocked.
3. **Source-integrity audit.** The Corcoran et al. (2023) record was corrected and the active-inference
   attribution moved to Parr et al. (2022). See [CRT_SOURCE_AUDIT.md](CRT_SOURCE_AUDIT.md).
4. **Pairwise identifiability module.** `analysis/crt/identifiability.py` simulates each confirmatory
   model, fits all models, and reports per-model and pairwise balanced accuracy with Wilson lower
   bounds. A PASS requires all five confirmatory models and the lower-bound margin.
5. **Full-joint-model design screen.** `run_hierarchical_design_optimization` replaces the readout
   surrogate as the Stage 0I screen. A PASS requires the complete confirmatory model set.
6. **Policy layer.** `analysis/crt/policy_model.py` compares fixed, random, meta-EIG, outcome-EIG,
   positive-testing, and cost-only test selection. The reported “SBC” is explicitly a **discrete
   policy-model rank calibration**, not continuous-parameter SBC.
7. **Optional inference backend.** NumPyro/JAX is an optional `crt` extra. When absent, the backend
   gate is BLOCKED and Laplace remains screening-only. `analysis/crt/inference.py` reports that
   state rather than silently relabelling Laplace as confirmatory.
8. **Protocol/registry.** v0.7.1 adds the belief-weighted likelihood and NUTS implementation while
   preserving the v0.7.0 source-audit, identifiability, policy, and calibration fields. The seven
   Stage 0I gates are unchanged.

## Current artifact status

These are the **quick screening** artifacts written by
`python -m app.cli.crt_stage0i --write --quick`. They are not the target-scale run.

| Artifact | Gate | Status |
|---|---|---|
| `CRT_STAGE0I_SOURCE_AUDIT.json` | `ANIMUS_P5_CRT_STAGE0I_SOURCE_INTEGRITY` | **PASS** |
| `CRT_STAGE0I_INFERENCE_BACKEND.json` | `ANIMUS_P5_CRT_STAGE0I_INFERENCE_BACKEND` | **BLOCKED** locally; NUTS implementation present, target-scale SBC not run |
| `CRT_STAGE0I_IDENTIFIABILITY.json` | `ANIMUS_P5_CRT_STAGE0I_IDENTIFIABILITY` | **LIMITED** (tiny N=6/T=20 full set, 0.00 minimum pairwise) |
| `CRT_STAGE0I_DESIGN_ADO.json` | `ANIMUS_P5_CRT_STAGE0I_DESIGN_ADO` | **LIMITED** (M0/M6 subset only) |
| `CRT_STAGE0I_TARGET_DESIGN_PROJECTION.json` | `ANIMUS_P5_CRT_STAGE0I_TARGET_DESIGN_PROJECTION` | **LIMITED** (pilot N=6 projected to N=432; not a target fit) |
| `CRT_STAGE0I_TARGET_DESIGN_READOUT.json` | `ANIMUS_P5_CRT_STAGE0I_TARGET_DESIGN_READOUT` | **LIMITED** (N=432/T=240 combined-candidate readout, one replicate; minimum pairwise 0.50) |
| `CRT_STAGE0I_POLICY_SBC.json` | `ANIMUS_P5_CRT_STAGE0I_POLICY_SBC` | **LIMITED** (top-1 0.50) |
| `CRT_STAGE0I_POLICY_PARAMETER_SBC.json` | `ANIMUS_P5_CRT_STAGE0I_POLICY_PARAMETER_SBC` | **LIMITED** (Laplace coverage too wide) |
| `CRT_STAGE0I_POLICY_RECOVERY.json` | `ANIMUS_P5_CRT_STAGE0I_POLICY_RECOVERY` | **LIMITED** (0.00 minimum) |
| `CRT_STAGE0I_FULL_MODEL_SBC.json` | `ANIMUS_P5_CRT_STAGE0I_FULL_MODEL_SBC` | **LIMITED** (Laplace, 1 draw/model) |
| `CRT_STAGE0I_FULL_MODEL_RECOVERY.json` | `ANIMUS_P5_CRT_STAGE0I_FULL_MODEL_RECOVERY` | **LIMITED** (balanced accuracy 0.60) |
| `CRT_STAGE0I_PACKAGE.json` | `ANIMUS_P5_CRT_STAGE0I_READINESS` | **BLOCKED** |

The quick screen is deliberately too small to establish identifiability. It exercises the code paths
and records an honest negative/limited result; it must not be cited as evidence that the design works.

## Belief-weighted model contract

The fitted full model now implements the same object as the protocol:

```text
q_i(a)      = sum_s m_i(s) * p_as
P(P=1|a,m)  = sigmoid(pi_i * logit(q_i(a)))
m_i(s|o,a)  proportional to m_i(s) * P(o|a,s)
```

The trial likelihood marginalizes the latent source with `m_i(s)` (not a uniform mean), while the
source update uses the observed outcome only. `data.source` is not required to evaluate the full
model; it remains available in simulation as a generative audit. The NumPy implementation is in
`analysis/crt/full_model.py`; the NUTS mirror is in `analysis/crt/numpyro_model.py`.

The code-level regression tests that enforce this contract are:

- `test_prediction_probability_counts_alpha_pi_once`;
- `test_prediction_probability_uses_belief_weights_not_an_unweighted_mean`;
- `test_source_beliefs_without_history_are_uniform_and_sum_to_one`;
- `test_full_likelihood_marginalizes_the_latent_source_with_beliefs`;
- `test_nuts_likelihood_matches_the_numpy_model` (optional NumPyro backend).

A likelihood-parity test is not a calibration test. It shows that the two implementations compute the
same synthetic-data likelihood; it does not show that either model is true or that the design is
identified.

## Planned target-scale run

The approved Stage 0I plan specifies:

- main design: N=480 enrolled, 432 analysed at 10% attrition, 120 trials/occasion, 240 total;
- calibration: N=80, 120 trials;
- confirmatory models `M0`, `M2`, `M4`, `M6`, `M7`; exploratory `M1`, `M3`, `M5`;
- SBC target 1,000 draws; recovery target 20 replicates;
- design selection by maximin pairwise separation with a power floor, not by overall accuracy alone;
- full-model SBC for every confirmatory model, plus a policy-parameter SBC, both with a NUTS backend.

Those runs are **not** claimed here. A separate pilot-to-target BIC projection exists, but its
target decision is `REVIEW` (minimum projected pairwise 0.50) and it is not a target-scale fit. The
target-scale SBC/recovery/design execution remains a blocker, together with the NumPyro backend,
adversarial agreement, calibration, registration, and ethics.

### Target-scale readout screen

The v0.7.0 `CRT_STAGE0I_TARGET_DESIGN_READOUT.json` artifact evaluated only `balanced` and
`high_diagnosticity`. Both candidates had `confidence_spread = 0.0`, so M7's `gamma_c` had no
experimental support; the observed M7 recovery of 0.00 was a deterministic design defect, not an
empirical failure of M7.

The v0.7.1 readout now uses the `combined_manipulation` candidate (`vividness_spread = 0.35`,
`confidence_spread = 0.35`) at N=432/T=240 with one replicate and a bounded 80-iteration fit. M7 and
M2/M4/M6 recover at 1.00 in this screen, but M0 is misclassified as M6, so the minimum pairwise
accuracy is still 0.50 and the decision is `REVIEW`. This is a single-replicate, readout-surrogate
diagnosis: it shows that adding the manipulation removes the structural M7 blind spot, not that the
target design identifies the full model. A multi-replicate full-model/NUTS run remains required.

### Target projection, not target fit

`analysis/crt/target_design.py` fits the full joint model at a pilot size, estimates the per-observation
BIC separation between each pair of confirmatory models, and projects it to N=432/T=240 using a normal
approximation. The scaling factor in the current artifact is 864 (pilot N=6/T=20). This is a planning
calculation; it cannot establish target-scale identifiability, and the gate maps both PASS and REVIEW
to `LIMITED`. The current projection is `REVIEW`; its selected candidate is the
`combined_manipulation` design, chosen by maximin pairwise projection with a tie-break toward the
manipulated design. The projection is not a substitute for the target-scale SBC and recovery run.

## Interpretation rules

- A design PASS is not a hypothesis test and not human evidence.
- A model-recovery PASS only says the simulation design can distinguish the declared models under the
  stated generative assumptions.
- A policy-recovery PASS does not show that participants use that policy.
- The source audit is not a systematic review and does not establish novelty or priority.
- No threshold may be tuned after seeing a failing target-scale result; a negative identifiability
  result narrows the claim or blocks the study.

## Commands

```bash
# from backend/
python -m app.cli.crt_stage0i --check --quick
python -m app.cli.crt_stage0i --write --quick
python -m app.cli.science_ledger --check
```

Optional NUTS path (installed from the `crt` extra):

```bash
python -c "from analysis.crt.numpyro_model import run_nuts_smoke; ..."  # smoke only
python -c "from analysis.crt.numpyro_model import NutsSbcConfig, run_nuts_sbc; print(run_nuts_sbc('M0', NutsSbcConfig()))"
```

The smoke and small SBC commands are diagnostics. A target-scale SBC needs at least the configured
minimum number of replicates and must be run on the frozen design; a small run always reports
`CRT_NUTS_SBC_REVIEW`.

The non-quick option uses a larger screen but is still not the target-scale SBC; the target-scale
run must be launched deliberately and recorded with its compute/provenance manifest.

## Source trail

- ADO / Bayesian design: Cavagnaro 2010; Myung 2013; Rainforth 2024.
- Hierarchical design: Kim 2014.
- SBC test quantity: Modrák 2025.
- Adversarial collaboration: Corcoran 2023; Seyr 2026.
- Active inference: Parr 2022 (book).
- Higher-order precision competitor: Dijkstra & Fleming 2025 preprint (not peer-reviewed).

Full metadata and corrections: [CRT_SOURCE_AUDIT.md](CRT_SOURCE_AUDIT.md).
