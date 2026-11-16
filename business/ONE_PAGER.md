# IMAGINA/ANIMUS — one-pager

**Local-first research instrumentation for imagination and source monitoring.**

## Problem

Labs that study mental imagery, reality monitoring, and aphantasia often assemble a task, a stimulus
tool, a spreadsheet, and a separate analysis script. The result is hard to audit: the scene, the
version, the exclusion rule, and the model assumption live in different places. Generative image tools
optimize the output, not the inspectability of the process.

## Product

ANIMUS is a local-first workspace with three surfaces:

- **Studio:** compose a symbolic scene, stage a candidate, correct it, and keep immutable versions.
- **Lumen:** walk through a first-person world assembled from a brief and a conditioning vector.
- **Evidence:** run behavioural tasks, inspect uncertainty, and export a session with its provenance.

The backend runs on the lab's machine. No account, no telemetry, no raw neural data, and no external
inference service are required.

## Why now

- Imagery and aphantasia research is growing, but measurement tools remain fragmented.
- Neurotech privacy pressure makes local-first infrastructure more attractive.
- Reproducibility requirements make provenance a feature, not an afterthought.

## Evidence status

- Engineering: 69-job CI, canonical artifact ledger, release compose, local-first design.
- Science: CRT is simulation-only; target-scale NUTS/SBC is `BLOCKED`; no human participants have
  been run.
- Commercial: no customer discovery is recorded yet; no LOI or paid pilot exists.

We do not claim clinical benefit, decoding, or a validated measure of imagination.

## Business model (hypothesis)

1. Self-hosted lab licence.
2. Study setup and support.
3. Analysis/validation services for neurotech teams.

Pricing is not validated. The first goal is three paid pilots or LOIs, not a large subscription base.

## Ask

- Research labs willing to run a 45-minute workflow interview and a pilot.
- A university/ethics partner for the CRT study.
- Non-dilutive grant partners for target-scale compute and calibration.

Contact: [open a research inquiry](https://github.com/toniIepure25/Imagina/issues).
