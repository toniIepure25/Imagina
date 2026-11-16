# Paper workspace

**Status:** stage-1 skeleton. Nothing here is submitted, accepted, or peer reviewed. The empirical
paper is blocked on human data; the methods paper is blocked on target-scale SBC/recovery and a
systematic review.

## Two papers, one evidence base

1. **Methods/measurement paper (near-term).** Identifiability-first design and hierarchical Bayesian
   inference for active source-monitoring assays. Target: *Behavior Research Methods* or
   *Computational Brain & Behavior*. It can report the negative identifiability result honestly.
2. **Registered Report (after the human study).** An adversarial test of prospective prediction,
   signal strength, and confidence in source monitoring. Target: *Nature Human Behaviour*
   or *Psychological Science* Stage 1; fallback *Cortex* or *eLife*.

## Rules

- No result is written before its canonical artifact exists.
- No figure is hand-edited; `scripts/build_figures.py` reads canonical JSON.
- No "first", "revolutionary", "proven", or "validated" language.
- The claim ceiling remains `L1_BEHAVIORAL_ASSISTED`.
- Authorship, affiliations, COI, and CRediT are completed before submission.

## Files

- [manuscript.md](manuscript.md) — current skeleton, with explicit result placeholders.
- [supplement.md](supplement.md) — supplement outline.
- [references.bib](references.bib) — verified core references; expand after the systematic review.
- [figures/](figures/) — generated figures and their source mapping.
- [scripts/build_figures.py](scripts/build_figures.py) — stdlib SVG generator.
