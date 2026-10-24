# Neural CI Dependency Hardening — MNE 1.12.1 Pin — Final Report

**Infrastructure / reproducibility repair. NOT a scientific gate.** No scientific outcome, threshold,
estimator, dataset contract, ROI definition, seal, or prior decision was modified. `C3XAT_BLOCKED_EXECUTION`
stands unchanged, and the earlier red overall run is **not** reinterpreted as a scientific failure.

## Provenance
- Branch: `infra/pin-mne-reproducible-ci`
- Starting SHA: `f55898c` (C3XAT tip)
- CI-tested SHA: `3cf3299`  (this docs-report commit follows it; the repair itself is validated at `3cf3299`)
- Commits:
  - `ff0b41f` infra(deps): pin MNE 1.12.1 for reproducible neural CI
  - `35c4b4f` test(deps): assert frozen neural dependency provenance
  - `3cf3299` docs(ci): document MNE 1.13.1 regression and compatibility pin

## The change
- Old MNE constraint: `mne>=1.7,<2`
- New MNE constraint: `mne==1.12.1` (exact pin, in the `neural` optional-dependency group only)
- Rationale: CI run `34617415944` resolved MNE **1.13.1** on Python 3.12.14, which raised
  `SyntaxError` importing `mne/_fiff/utils.py` and broke every MNE-importing job. The open range made the
  resolved version non-deterministic. 1.12.1 is the last known stable release before the regression; the
  exact pin gives deterministic CI reproduction. This is a CI-compatibility pin, **not** a claim that
  MNE 1.13.x is scientifically invalid.

## Environment / validation
- Python version: **3.12.14** (CI) and a matching local Py 3.12.14 venv (`pip install -e ".[dev,science,neural]"`)
- Resolved MNE version: **1.12.1**
- Direct MNE import / `RawArray` smoke (local Py 3.12.14 venv):
  `mne.io.RawArray(zeros(1,250), create_info(["Cz"],250,"eeg"))` → `n_times == 250`, `mne.__version__ == "1.12.1"` → **OK**
- Local venv suite results: guard **3 passed**; `test_neural_preprocessing.py` **12 passed**.
  (`test_neural_yoto_adapter.py` showed 6 Windows-only `tmp_path` fixture-setup errors — a local pytest/
  temp-dir quirk, **not** the MNE SyntaxError and unrelated to the pin; CI runs this suite green on Linux.)

## CI results — run `34619189693`, SHA `3cf3299` (overall **SUCCESS**, all jobs green)
- `neural-dependency-provenance`: **PASS** (new guard; prints Python/MNE, asserts pin==installed, RawArray smoke)
- `c1-preprocessing-determinism`: **PASS** (previously failing)
- `c1-dataset-contract`: **PASS** (previously failing)
- `c3xat-atlas-imagery`: **PASS**
- `backend-core`: **PASS**
- All other deterministic jobs: unchanged / green

## science-api-cooperative-abort
**PASS** on this run. The earlier `sqlite3.OperationalError: database is locked` did not reproduce, so per
procedure it is recorded as a **historical flake**; no code change was made and no separate branch was
opened.

## Drift guard
`backend/app/tests/test_neural_dependency_provenance.py` reads the exact `mne==` pin from `pyproject.toml`
(single source of truth) and fails with **`NEURAL_DEPENDENCY_PROVENANCE_MISMATCH`** if the installed
version drifts, before any scientific test runs. Wired into the single reusable CI job
`neural-dependency-provenance` (not duplicated per job).

## Scope / immutability
- Scientific files changed = **0** (nothing under `results/`, `reports/c1..c3*`, `app/research/`, or any
  C3* decision/seal artifact was touched; verified by diff — only `pyproject.toml`, `.github/workflows/ci.yml`,
  the new guard test, and the two infra docs changed).
- Scientific decisions changed = **0** (`C3XAT_BLOCKED_EXECUTION` preserved; all prior gates immutable).
- Dependency scope: **MNE only** — no other package (torch, numpy, scipy, scikit-learn, pytest, FastAPI)
  was pinned or updated; none needed a new constraint to make the MNE 1.12.1 environment install.

## STOP after the dependency repair
No C3XAT execution in this branch; no scientific seals modified; no C3XAG.
