# Figures

Every figure is generated from a canonical artifact. Do not edit an SVG by hand and do not copy a
number from a slide.

```bash
python paper/scripts/build_figures.py \
  --input results/crt/CRT_STAGE0I_TARGET_DESIGN_READOUT.json \
  --out-dir paper/figures
```

Current figures:

| File | Source | What it shows | Status |
|---|---|---|---|
| `fig_stage0i_pairwise.svg` | `CRT_STAGE0I_TARGET_DESIGN_READOUT.json` | pairwise design accuracy against the 0.85 threshold | simulation-only; M0/M6 confusion visible |

Figures that require human data are not generated until the registered analysis exists:

- `fig_design.svg`
- `fig_sbc.svg`
- `fig_primary_contrast.svg`
- `fig_model_comparison.svg`
- `fig_false_seen.svg`
