# Falsification Studio and Participant Mode

Status: frontend-only local tooling. No study is run, no data is persisted, and no ethics approval is implied.

## Falsification Studio — `/research/design`

The designer forces the order **claim → measure → design → analysis → review** before any data exist. It writes a
versioned JSON plan and a Markdown plan to the local machine; it does not upload anything.

### Schema

- `schema`: `IMAGINA-PREREG-v1`
- `appVersion`: `4.0.0`
- Export envelope: `IMAGINA-PREREG-EXPORT-v1`
- Draft storage: `sessionStorage["imagina.studyDraft.v1"]` (per-tab, discarded when the tab closes)

### Modes and ceilings

| Mode | Ceiling |
| --- | --- |
| `explore` | Hypothesis-generating only. No confirmatory p-values or efficacy language. |
| `personal` | Descriptive case report, or a randomization test only when the plan was fixed before data and the data are complete. |
| `research` | External protocol review and ethics approval are required before any collection. |

The ceiling is shown on later steps and in the exported plan. Exporting does not raise it.

### Validation

Blocking errors include: a title shorter than 5 characters, a question shorter than 20 characters, a non-eligible
primary outcome, a non-positive minimum meaningful change, a secondary outcome equal to the primary, block length or
block count below 1, negative washout, a seed shorter than 3 characters, unnamed conditions, and empty estimand,
test, effect measure, rationale, missing-data rule, stopping rule, or support threshold.

Warnings include fewer than four blocks, zero washout, explore/research ceiling reminders, more than four secondary
outcomes, a non-immediate expected shape, and an unset planning SD. Warnings never block locking; they are part of the
export.

### Allocation preview

`lib/randomization.ts` implements FNV-1a + mulberry32 with balanced blocks. `block` shuffles each block;
`counterbalance` alternates a block with its mirror. The preview is deterministic for the committed seed and reports
per-condition counts and imbalance. It is explicitly **not** a randomization service and does not guarantee balance
in a real trial.

### Planning precision, not power

The designer reports a normal-approximation 95% interval half-width:

```
1.96 × planning SD / sqrt(pairs)
```

It is labelled “not power”. Randomization-test power depends on autocorrelation, effect size, measurement count,
baseline length, carryover, and gradual effects; a single “80% power” number would be misleading. No p-values,
effect estimates, or conclusions are produced.

### Locking and export

- Locking computes a SHA-256 of the canonical JSON design and increments the revision.
- The exported Markdown states registration status: **not a registry entry, not ethics approval, not a Registered
  Report**.
- Downloads are generated locally with `downloadText`; no network call.
- A locked plan can be revised with `withNewRevision`, which clears the lock and increments the revision.

## Participant Mode — `/research/participant`

A local demonstration of the participant-facing loop: intro → consent → three trials → summary. It is **not** a live
study.

- No pseudonym, account, email, or participant identifier.
- No persistence, no network, no telemetry.
- A participant can stop at any point; the declined state is explicit and is not treated as missing data.
- The summary reports trial-level ratings, missingness, and a plain statement that the data never left the tab.
- Export is a local `IMAGINA-PARTICIPANT-DEMO-v1` JSON file.
- Controls are at least 44px; the task has a fixation interval, keyboard support, and an ARIA live status.

## Tests

```bash
cd frontend
node node_modules/vitest/vitest.mjs run lib/__tests__/studyDesign.test.ts \
  lib/__tests__/randomization.test.ts lib/__tests__/preregistration.test.ts
node scripts/audit-claims.cjs
```

Unit tests cover schema defaults, validation, eligible outcomes, session counts, precision, locking/revising,
deterministic allocation, balance, counterbalance, hash stability, export boundaries, and safe filenames. E2E covers
route load, overflow at 390/1440px, Glass Box provenance, and local locking.

## Limits

- The designer is a planning aid, not a registry, IRB, or statistical-analysis engine.
- The preview assumes independent pairs; it does not model carryover or autocorrelation.
- Participant Mode demonstrates interaction and export only; it cannot support a scientific claim.
- No backend, database, schema, or API change was made for these surfaces.
