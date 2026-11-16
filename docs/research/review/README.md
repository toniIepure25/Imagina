# Systematic review workspace

**Status:** protocol and empty templates. **No systematic review has been executed.** Do not describe
this as PRISMA-compliant, systematic, or exhaustive until dual screening and the flow diagram exist.

## Question

In studies of source monitoring, reality monitoring, or imagination–reality discrimination, do
prospective predictions about a diagnostic test, active test selection, or higher-order precision
explain source attribution beyond sensory signal strength and confidence?

## Indexes

- PubMed
- Europe PMC (including preprints, flagged separately)
- OpenAlex
- Crossref for DOI verification

## Screening

- Two independent screeners.
- Title/abstract, then full text.
- Disagreements resolved by a third reviewer.
- Record every exclusion reason.
- Preprints are labelled and never counted as peer-reviewed evidence.

## Files

- [search_log.csv](search_log.csv) — query, index, date, hits.
- [screening.csv](screening.csv) — one row per deduplicated record.
- [evidence.csv](evidence.csv) — extracted evidence and risk-of-bias notes.

## Current scoping log

The [search_log.csv](search_log.csv) contains three scoping queries run on 2026-11-16. PubMed returned
2 records for the narrow tiab query; Europe PMC returned 202 for a broader free-text query; OpenAlex
returned 4,795 ranked results for a broad query. These are **not** screening counts and do not support
a PRISMA claim. They show that the narrow direct-match space is small and that broad searches are
dominated by unrelated clinical hallucination and philosophy papers.

## Rules

- Verify DOI/PMID and PubMed status for every included record.
- Do not use "first" or "novel" in a bibliographic sense before this is complete.
- A rapid scoping search is not a systematic review.
- The existing [CRT_LITERATURE_POSITIONING.md](../CRT_LITERATURE_POSITIONING.md) is a rapid,
  non-systematic review and must be labelled as such.

## Minimum completion

- Search log with reproducible queries and dates.
- Deduplicated count.
- PRISMA flow counts.
- Evidence table with design, N, construct, measure, result, limitation.
- Risk-of-bias assessment appropriate to the design.
- Narrative synthesis; meta-analysis only if the constructs are commensurable.
