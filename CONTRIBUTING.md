# Contributing to IMAGINA

IMAGINA is research software. Contributions are judged on **scientific validity,
reproducibility, and claim discipline** at least as much as on feature velocity.

## Before you start

- Read `AGENTS.md` (engineering and claims rules) and `docs/scientific_claims.md`
  (what the project is allowed to say).
- Read `docs/animus/ANIMUS_CLAIMS_BOUNDARY.md` for the current claim ceiling.
- For anything touching participant data, read `docs/ethics.md` and
  `docs/SCIENTIFIC_LIMITATIONS.md` first.

## Setup

```bash
# Backend (Python 3.10+; 3.12 recommended)
cd backend

# Reproducible resolve from backend/uv.lock (recommended)
uv sync --extra dev --extra science --extra neural

# pip fallback without the lock
python -m venv .venv
. .venv/Scripts/activate        # Windows
# . .venv/bin/activate          # macOS/Linux
pip install -e ".[dev,science,neural]"

# Frontend (Node 22+)
cd ../frontend
npm ci
```

## Verification

Run the narrowest check that proves your change, then the integration check:

```bash
python scripts/verify.py --quick     # lint + types + focused tests
python scripts/verify.py --ci        # what CI runs
python scripts/verify.py --full      # full matrix, slower
```

A pull request is not ready while `--ci` fails. Do not disable a test, widen a
lint ignore, or lower a coverage threshold to make a change pass without an
explicit, reviewed justification.

## Scientific rules

1. **No claim without evidence.** Every user-visible or exported claim must map
   to an entry in [`science/registry/claims.yaml`](science/registry/claims.yaml)
   and the canonical status in
   [`docs/program/PROGRAM_STATUS.md`](docs/program/PROGRAM_STATUS.md). Read
   [`science/README.md`](science/README.md) before adding or changing a claim.
2. **No new composite score.** PID/IQI and similar legacy composites are
   demo-only and must not appear in primary research surfaces.
3. **No target leakage.** Task targets, held-out labels, and decoder targets are
   server-side only. Client payloads are tested for leakage.
4. **Sealed confirmatory work.** Do not modify a frozen protocol, decision rule,
   or analysis plan after unblinding. Supersede it with a new version and a
   written rationale.
5. **Negative results are results.** Do not delete or overwrite a failed gate
   artifact; add a superseding record.
6. **No human data without ethics approval.** The repository must never contain
   identifiable participant data, raw neural data, or consent records.
7. **Do not call a rapid review systematic.** If you summarize literature, state
   the search strategy, indexes, dates, and limits.

## Code style

- Python: `ruff` (line length 120, `E/F/I/W`), type hints on public functions,
  `pytest` markers (`core`, `research`, `integration`, ...).
- TypeScript/React: `eslint`, `tsc --noEmit`, Vitest for logic, Playwright for
  end-to-end flows.
- Prefer pure functions and explicit data models over hidden global state.
- New behaviour needs a test that fails before the change and passes after it.

## Commits and pull requests

- Small, single-purpose commits. Imperative subject line, ≤72 characters.
- Explain **why** in the body; link the issue, ADR, or gate ID.
- Update the relevant docs in the same change:
  - `docs/ai/SESSION_LOG.md` for non-trivial work,
  - `docs/ai/DECISIONS.md` for architectural or scientific decisions,
  - `docs/ai/TASK_BRIEF.md` when the active task changes,
  - `docs/program/PROGRAM_STATUS.md` only through the ledger generator.
- PR checklist:
  - [ ] Tests added/updated and passing
  - [ ] Claims audit passes; no forbidden phrase introduced
  - [ ] Result artifacts carry code SHA, protocol hash, dataset hash, seed
  - [ ] No absolute paths, secrets, or raw data
  - [ ] Docs updated
  - [ ] Backwards compatibility or deprecation path stated

## Review and merge

- One maintainer approval for code; a second reviewer for anything that changes a
  scientific claim, decision rule, or claim ceiling.
- Squash-merge by default; preserve the PR description in the commit body.
- Release tags are created only from a green `main` with a completed
  `docs/program/PROGRAM_STATUS.md`.

## Reporting problems

- Bugs and feature requests: open an issue with a minimal reproduction.
- Security issues: follow `SECURITY.md`; do not open a public issue.
- Scientific disagreements: open a "claim review" issue citing the artifact,
  the registry entry, and the evidence you believe is missing.
