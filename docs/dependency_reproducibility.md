# Neural CI dependency reproducibility — MNE compatibility pin

**Infrastructure / reproducibility repair. NOT a scientific gate.** This change modifies no scientific
outcome, threshold, estimator, dataset contract, ROI definition, seal, or prior decision. The C3XAT
scientific decision remains `C3XAT_BLOCKED_EXECUTION`.

## Observed regression
CI run **34617415944** (branch `research/d2-atlas-raw-imagery-c3xat`, SHA `b7a615d`) resolved
**MNE 1.13.1** on **Python 3.12.14**. That installed package raised, on import of the MNE FIFF utilities:

```text
mne/_fiff/utils.py line 53
SyntaxError: invalid syntax
```

The failure appeared at `mne.io.RawArray(...)` and broke every job that imports MNE — notably
`c1-preprocessing-determinism` and `c1-dataset-contract`. This is **dependency drift**, not a C1
scientific failure and not a C3XAT scientific failure: the same jobs passed on the immediately prior run
(34584982751) before the newer MNE release was published.

## Root cause
`backend/pyproject.toml` previously allowed any `mne>=1.7,<2`. Because the constraint was an open range,
a routine `pip install -e ".[dev,science,neural]"` in CI resolved a **newer** MNE (1.13.1) than earlier
runs, and that build is not importable in this environment. Unpinned ranges make CI non-deterministic:
the resolved version depends on when the environment is built.

## Repair
Exact pin in the `neural` optional-dependency group:

```text
old:  mne>=1.7,<2
new:  mne==1.12.1
```

An **exact** pin (not `mne<1.13`, `mne~=1.12`, or `mne>=1.12,<1.13`) is used deliberately: the goal is
**deterministic CI reproduction**, so that every environment build installs the identical MNE, not merely
one that happens to avoid the currently-broken 1.13.1.

## Why 1.12.1
MNE 1.12.1 is selected as the last known stable release compatible with this environment, preceding the
observed 1.13.1 regression. **This does not claim MNE 1.13.x is scientifically invalid** — it is
specifically a reproducibility / CI-compatibility pin. When a future MNE release is verified importable
and compatible, the pin can be advanced deliberately (and this guard updated in lockstep).

## Drift guard
`backend/app/tests/test_neural_dependency_provenance.py` reads the exact `mne==` pin from
`pyproject.toml` (single source of truth) and asserts the installed `mne.__version__` matches, failing
with **`NEURAL_DEPENDENCY_PROVENANCE_MISMATCH`** if they diverge, plus a direct
`mne.io.RawArray` smoke. It runs in the dedicated CI job `neural-dependency-provenance` so drift fails
early and explicitly instead of deep inside a scientific test.

## Scope
Only MNE is constrained. No other package (torch, numpy, scipy, scikit-learn, pytest, FastAPI, …) was
pinned or updated; none required a new constraint to make the MNE 1.12.1 environment install.

## Validation
The authoritative validation is the CI job on Python 3.12.14 (`neural-dependency-provenance`, plus the
previously-failing `c1-preprocessing-determinism` and `c1-dataset-contract`). Results are recorded in
`reports/infra/MNE_PIN_REPORT.md`.
