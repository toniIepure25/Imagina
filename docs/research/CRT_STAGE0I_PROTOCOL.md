# CRT Stage 0I — identifiability-first protocol package

**Protocol:** `ANIMUS-CRT-v1` v0.7.0, stage `0I`
**Status:** computational screening only; human data collection remains **BLOCKED**.
**Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`; no decoding, clinical, priority, or measurement-upgrade
claim is authorized.

Stage 0I changes the question from “which model fits best?” to “is the confirmatory model space
identified at the planned design, and can the design be improved without hiding weak separation?”
It is a methods and governance stage, not a result.

## What changed

1. **Full-model prediction bug fixed.** The previous likelihood counted the prediction-source
   parameter twice (`expit(alpha_pi + effect + pi*logit(q))`). The model now uses
   `expit(pi * logit(q))` through one shared `prediction_probability` function, and a regression test
   checks the count.
2. **Source-integrity audit.** The Corcoran et al. (2023) record was corrected and the active-inference
   attribution moved to Parr et al. (2022). See [CRT_SOURCE_AUDIT.md](CRT_SOURCE_AUDIT.md).
3. **Pairwise identifiability module.** `analysis/crt/identifiability.py` simulates each confirmatory
   model, fits all models, and reports per-model and pairwise balanced accuracy with Wilson lower
   bounds. A PASS requires all five confirmatory models and the lower-bound margin.
4. **Full-joint-model design screen.** `run_hierarchical_design_optimization` replaces the readout
   surrogate as the Stage 0I screen. A PASS requires the complete confirmatory model set.
5. **Policy layer.** `analysis/crt/policy_model.py` compares fixed, random, meta-EIG, outcome-EIG,
   positive-testing, and cost-only test selection. The reported “SBC” is explicitly a **discrete
   policy-model rank calibration**, not continuous-parameter SBC.
6. **Optional inference backend.** NumPyro/JAX is an optional `crt` extra. When absent, the backend
   gate is BLOCKED and Laplace remains screening-only. `analysis/crt/inference.py` reports that
   state rather than silently relabelling Laplace as confirmatory.
7. **Protocol/registry.** v0.7.0 adds source-audit, identifiability, policy, inference, and
   calibration-table fields; seven Stage 0I gates were added.

## Current artifact status

These are the **quick screening** artifacts written by
`python -m app.cli.crt_stage0i --write --quick`. They are not the target-scale run.

| Artifact | Gate | Status |
|---|---|---|
| `CRT_STAGE0I_SOURCE_AUDIT.json` | `ANIMUS_P5_CRT_STAGE0I_SOURCE_INTEGRITY` | **PASS** |
| `CRT_STAGE0I_INFERENCE_BACKEND.json` | `ANIMUS_P5_CRT_STAGE0I_INFERENCE_BACKEND` | **BLOCKED** (NumPyro absent) |
| `CRT_STAGE0I_IDENTIFIABILITY.json` | `ANIMUS_P5_CRT_STAGE0I_IDENTIFIABILITY` | **LIMITED** (tiny N=6/T=20 full set, 0.00 minimum pairwise) |
| `CRT_STAGE0I_DESIGN_ADO.json` | `ANIMUS_P5_CRT_STAGE0I_DESIGN_ADO` | **LIMITED** (M0/M6 subset only) |
| `CRT_STAGE0I_TARGET_DESIGN_PROJECTION.json` | `ANIMUS_P5_CRT_STAGE0I_TARGET_DESIGN_PROJECTION` | **LIMITED** (pilot N=6 projected to N=432; not a target fit) |
| `CRT_STAGE0I_TARGET_DESIGN_READOUT.json` | `ANIMUS_P5_CRT_STAGE0I_TARGET_DESIGN_READOUT` | **LIMITED** (N=432/T=240 readout; minimum pairwise 0.50) |
| `CRT_STAGE0I_POLICY_SBC.json` | `ANIMUS_P5_CRT_STAGE0I_POLICY_SBC` | **LIMITED** (top-1 0.50) |
| `CRT_STAGE0I_POLICY_PARAMETER_SBC.json` | `ANIMUS_P5_CRT_STAGE0I_POLICY_PARAMETER_SBC` | **LIMITED** (Laplace coverage too wide) |
| `CRT_STAGE0I_POLICY_RECOVERY.json` | `ANIMUS_P5_CRT_STAGE0I_POLICY_RECOVERY` | **LIMITED** (0.00 minimum) |
| `CRT_STAGE0I_FULL_MODEL_SBC.json` | `ANIMUS_P5_CRT_STAGE0I_FULL_MODEL_SBC` | **LIMITED** (Laplace, 1 draw/model) |
| `CRT_STAGE0I_FULL_MODEL_RECOVERY.json` | `ANIMUS_P5_CRT_STAGE0I_FULL_MODEL_RECOVERY` | **LIMITED** (balanced accuracy 0.60) |
| `CRT_STAGE0I_PACKAGE.json` | `ANIMUS_P5_CRT_STAGE0I_READINESS` | **BLOCKED** |

The quick screen is deliberately too small to establish identifiability. It exercises the code paths
and records an honest negative/limited result; it must not be cited as evidence that the design works.

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

`CRT_STAGE0I_TARGET_DESIGN_READOUT.json` is a genuine N=432/T=240 hierarchical readout screen, not a
projection. It evaluates two candidates (balanced, high-diagnosticity) with the five confirmatory
models and `laplace=False`; random-effect optimization is bounded to prevent boundary overflow. The
bounded run takes about 11 minutes. The selected balanced design has minimum pairwise accuracy 0.50:
M0, M2, M4, and M6 recover at 1.00, but **M7 recovers at 0.00**, so the target design does not separate
the higher-order precision model. This is a design/model diagnosis for the readout surrogate, not a
full joint-model fit and not proof that the full model is unidentifiable.

### Target projection, not target fit

`analysis/crt/target_design.py` fits the full joint model at a pilot size, estimates the per-observation
BIC separation between each pair of confirmatory models, and projects it to N=432/T=240 using a normal
approximation. The scaling factor in the current artifact is 864 (pilot N=6/T=20). This is a planning
calculation; it cannot establish target-scale identifiability, and the gate maps both PASS and REVIEW
to `LIMITED`. The current projection is `REVIEW` with a minimum projected pairwise value of 0.50.

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
