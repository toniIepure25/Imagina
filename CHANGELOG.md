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

### Changed

- Release container definitions are being brought in line with the development
  images (install from the project metadata, run production servers, non-root).

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
