# CRT Stage 0G Scoping-Review Protocol

**Status:** protocol drafted after a rapid scoping search on 2026-10-30. It is **not registered**, not
PRISMA-compliant, and has no dual screening yet. It is a plan for the review that Stage 0G requires, plus
a transparent record of the rapid search already performed. It cannot support a priority, “first”, or
“revolutionary” claim.

**Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`.
**Decision supported:** whether the Stage 0G theory adjudication and trial-level model are worth
building, and which competing accounts must be represented.

## 1. Question

> In humans, does prospective prediction of a source-diagnostic test consequence causally change source
> attribution in reality monitoring, and which computational account explains the pattern?

Population: healthy human adults in behavioural, EEG, MEG, fMRI, or lesion studies.
Exposure/manipulation: prospective prediction, expectation, prediction error, counterfactual simulation,
or active test selection before a source judgment.
Outcome: source attribution (seen/imagined/described/new), source sensitivity, false-seen rate,
confidence calibration, or test selection.
Comparator: no prediction, yoked prediction, non-diagnostic prediction, passive exposure, or a
computational alternative.
Design: experimental, quasi-experimental, or computational-theoretical. Clinical case reports and
non-human-only studies are excluded from primary evidence but may be cited as boundary context.

## 2. Eligibility

**Include**

- Peer-reviewed empirical studies of human reality monitoring, source monitoring, imagination
  inflation, prediction error, expectation violation, or metacognitive information search.
- Theoretical or computational papers that make falsifiable claims about reality monitoring.
- Studies published 2010–2026 in English.
- Preprints only when flagged as preprints and used for discovery or theory, not as primary efficacy
  evidence.

**Exclude**

- Clinical case reports, treatment trials, and diagnostic-validation claims.
- Non-human studies unless they directly constrain a computational claim.
- AI/LLM, machine-learning, and generic signal-processing papers with no source-attribution outcome.
- Opinion pieces without a testable model, except as framing.

## 3. Sources and search strings

Primary indexes: PubMed, Europe PMC, OpenAlex, Crossref. Preprint servers: OSF Preprints and arXiv,
kept separate. No PsycINFO/Scopus/Web of Science access is assumed; if unavailable, say so and label the
review **rapid**.

Core strings (adapt per index; record exact syntax and date):

```text
("reality monitoring" OR "source monitoring")
AND ("prediction" OR "predictive" OR "prediction error" OR "expectation")

("reality monitoring" OR "source monitoring")
AND ("active testing" OR "test selection" OR "information search" OR "active inference")

("imagination inflation" OR "counterfactual imagination")
AND ("source" OR "reality" OR "prediction")

("reality monitoring" OR "source monitoring")
AND ("computational model" OR "Bayesian" OR "precision")

("metacognitive" OR "metacognition")
AND ("information search" OR "test selection" OR "expected information gain")

("reality monitoring" OR "source monitoring")
AND ("measurement invariance" OR "test-retest" OR "reliability")
```

## 4. Screening and extraction

1. Deduplicate by DOI, PMID, and normalized title.
2. Two independent reviewers screen titles/abstracts. If only one reviewer is available, a second
   reviewer audits a random 20%; the review is then labeled **rapid**, not systematic.
3. Full-text screen disagreements; record reasons.
4. Extract: design, N, population, task, manipulation, comparator, outcome, model, effect size and
   uncertainty (where reported), limitations, source status.
5. Assess risk of bias with an adapted tool for experimental and observational studies; do not pool
   effect sizes unless tasks and outcomes are comparable.
6. Synthesize by mechanism, not by vote counting: signal strength, precision/confidence, active
   prediction, source-monitoring heuristic, and policy accounts.

## 5. Rapid search record already performed

Retrieval date: 2026-10-30 UTC. Europe PMC REST exact-query counts:

| Query | Hits | Note |
|---|---:|---|
| `"reality monitoring" AND ("information search" OR "active testing" OR "test selection")` | 0 | No exact indexed direct test |
| `"reality monitoring" AND "information search"` | 0 | No direct hit |
| `"reality monitoring" AND "test selection"` | 0 | No direct hit |
| `"prospective reality monitoring"` | 0 | No exact phrase |
| `"active reality monitoring"` | 1 | Unrelated |
| `"reality monitoring" AND "prediction error"` | 66 | Adjacent literature |
| `"source monitoring" AND "prediction error"` | 81 | Adjacent literature |
| `"reality monitoring" AND counterfactual` | 18 | Mostly theory, memory, or clinical framing |
| `"reality monitoring" AND ("computational model" OR "bayesian")` | 110 | Computational framing exists |
| `"imagination inflation" AND (prediction OR counterfactual)` | 28 | Includes registered-report work |

These are raw hit counts before deduplication or screening. OpenAlex was used for discovery and exact
title retrieval; its broad counts are noisy and are not used as screening counts. PubMed status was
checked for consequential PMIDs; absence of a notice is not proof of a clean record.

## 6. Current anchor set (not a completed systematic review)

| Source | Status | Use |
|---|---|---|
| Dijkstra & Fleming 2023, *Nature Communications*, doi:10.1038/s41467-023-37322-1, PMID 36959279 | Peer-reviewed | Signal-strength account |
| Dijkstra, von Rein, Kok & Fleming 2025, *Neuron*, doi:10.1016/j.neuron.2025.05.015, PMID 40480215 | Peer-reviewed | Neural basis of imagination–reality judgments |
| Fleming & Michel 2025, *Behavioral and Brain Sciences*, doi:10.1017/S0140525X25000068, PMID 40257183 | Peer-reviewed target article | Reality monitoring as a function of conscious vision |
| Peters 2026, *Behavioral and Brain Sciences*, doi:10.1017/S0140525X25103075, PMID 42342595 | Peer-reviewed commentary | Decision-policy critique |
| Dijkstra, Fleming & Shea 2026, *Neuroscience of Consciousness*, doi:10.1093/nc/niag048, PMID 42626409 | Peer-reviewed | Functional analysis |
| Dijkstra & Fleming 2025/2026, OSF preprint doi:10.31234/osf.io/36xdz_v2 | Preprint | Higher-order precision competitor |
| Zheng et al. 2025, *Psychonomic Bulletin & Review*, doi:10.3758/s13423-025-02715-4, PMID 40481295 | Peer-reviewed | Expectation violation improves short-term source memory |
| Boeltzig et al. 2025, *NeuroImage*, doi:10.1016/j.neuroimage.2025.121375, PMID 40675423 | Peer-reviewed | Prediction-error size and source memory |
| Dhammapeera et al. 2024, *Cognitive Neuroscience*, doi:10.1080/17588928.2024.2315814, PMID 38362597 | Peer-reviewed | Counterfactual imagination can impair action memory |
| Dudek & Polczyk 2025, *PLOS ONE*, doi:10.1371/journal.pone.0327638, PMID 40748997 | Peer-reviewed registered report | Imagination inflation boundary; memory distrust null |
| Martín-Luengo, Zinchenko & Dolgoarshinnaia 2026, *Human Brain Mapping*, doi:10.1002/hbm.70614, PMID 42524861 | Peer-reviewed meta-analysis | Neural differentiation of source/reality monitoring |

## 7. Deviations and limitations

- The search was performed before this protocol was written; it is a **rapid** scoping search, not a
  registered systematic review.
- No dual screening, no formal risk-of-bias assessment, no full-text extraction for every record.
- Indexing lag and vocabulary mismatch are likely; absence of an exact phrase is not evidence of no
  prior work.
- Several 2026 sources are recent; one core competitor is a preprint.
- The review cannot adjudicate mechanism or support a priority claim.

## 8. Outputs

- This protocol and the rapid search record.
- `docs/research/CRT_LITERATURE_POSITIONING.md` updated with the 2025–2026 evidence.
- `docs/program/CRT_THEORY_ADJUDICATION.md` with the three-account decision table.
- A future `evidence.csv` and `search_log.csv` only after dual screening; until then, no PRISMA claim.
