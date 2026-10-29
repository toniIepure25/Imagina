# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
semantic versioning.

## [Unreleased]

### Added

- Repository governance baseline: `LICENSE` (Apache-2.0), `LICENSE-DOCS`
  (CC BY 4.0), `CITATION.cff`, `CONTRIBUTING.md`, `SECURITY.md`,
  `GOVERNANCE.md`, `CODE_OF_CONDUCT.md`, `.editorconfig`.
- `.gitattributes` for line-ending and binary-file normalization.
- `.dockerignore` files for backend and frontend build contexts.
- Canonical claim registry (`science/registry/`) and hash-chained result ledger
  (`backend/app/research/ledger.py`) that generate `docs/program/PROGRAM_STATUS.md`
  and `results/ledger.json`.
- JSON Schemas for claims, result envelopes, and ledger snapshots.
- Cross-platform `scripts/verify.py` with `--quick`, `--ci`, and `--full`
  modes, plus `check_docs_links.py` for local Markdown links.

### Changed

- Release container definitions now install from the project metadata, run
  production servers as a non-root user, and are built/started/health-checked
  in CI.
- Canonical ANIMUS-P2 status is `BLOCKED` (confirmatory cohort not executed);
  P2's `VALIDATED` label is retained only as a historical pilot artifact and
  is superseded by P2R. The perception-content claim is `PILOT`; imagery
  content, geometry, and clinical use remain `BLOCKED`.

### Fixed

- Removed the release Dockerfile's dependency on a nonexistent
  `backend/requirements.txt`.

## [0.5.0] - 2026-10-26

### Added

- ANIMUS Studio scene graph, Lumen world engine, epistemic interview, Scene
  Threshold, and Observatory surfaces.
- Evidence-gated claim envelope and forbidden-phrase audit.
- C3/C3M real-data pipelines, C3XAT-R1 report, and ANIMUS P2/P2R artifacts.

### Notes

- Claim ceiling remains `L1_BEHAVIORAL_ASSISTED`.
- No human participants have been run; all instruments are experimental and
  not study-eligible.
