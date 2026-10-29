# Science registry

This directory is the machine-readable source of truth for **what the project may claim** and **which
result file decides each gate**. Prose status documents are generated from it; they are not edited by
hand.

## Files

| Path | Purpose |
| --- | --- |
| `registry/claims.yaml` | Claim statements, status, claim level, evidence artifact ids, forbidden interpretations |
| `registry/artifacts.yaml` | One entry per registered result file: gate, dotted status path, raw-to-canonical status map, required provenance, supersession |
| `registry/gates.yaml` | Gate names, the one canonical artifact per gate, and the claims attached to the gate |
| `schemas/claim.schema.json` | Validation for each claim entry |
| `schemas/result.schema.json` | Envelope for **new** result artifacts; historical artifacts are mapped, not rewritten |
| `schemas/ledger.schema.json` | Validation for the generated snapshot |

Generated outputs:

- [`docs/program/PROGRAM_STATUS.md`](../docs/program/PROGRAM_STATUS.md)
- `results/ledger.json`

## Commands

From `backend/`:

```bash
python -m app.cli.science_ledger --check   # validate; non-zero on any contract violation
python -m app.cli.science_ledger --write   # regenerate PROGRAM_STATUS.md and ledger.json
python -m app.cli.science_ledger --json    # print the snapshot
```

The check fails on:

- a registered artifact that is missing or not valid JSON;
- a status path that is absent or not a string;
- a raw status that has no explicit mapping to the controlled vocabulary;
- missing required provenance fields;
- a gate with zero or more than one canonical artifact;
- a supersession link to an unknown artifact, a canonical artifact that is superseded, or a cycle;
- a claim that references an unknown gate or artifact;
- a claim status that its evidence cannot support (`VALIDATED` with null evidence, etc.);
- a validated claim above the operating ceiling;
- a generated document that is stale.

## Status vocabulary

Gate statuses are execution states, not truth claims:

| Status | Meaning |
| --- | --- |
| `NOT_STARTED` | No execution attempt |
| `RUNNING` | Execution in progress; not a result |
| `PASS` | The preregistered decision rule passed for this gate |
| `NULL` | The rule produced a valid null within sensitivity |
| `FAIL` | The rule produced a failure or the falsification criterion was met |
| `LIMITED` | Partial evidence, e.g. a subset of subjects, with an explicit limit |
| `PILOT` | Internal pilot-grade evidence only |
| `BLOCKED` | Execution could not produce a valid decision |
| `SUPERSEDED` | Historical marker; never canonical |

Claim statuses are interpretive and must be earned:

| Status | Minimum evidence |
| --- | --- |
| `UNVALIDATED` | No supporting artifact, or only descriptive material |
| `PILOT` | At least one pilot, limited, or passing artifact |
| `LIMITED` | At least one limited or passing artifact |
| `VALIDATED` | A passing canonical artifact at or below the operating ceiling |
| `REPLICATED` | An independent replication artifact |
| `DEPRECATED` | Retained for history; must not appear in primary surfaces |
| `BLOCKED` | Explicitly not authorized or not established |

## Adding a result

1. Write the artifact under `results/` with the provenance required by `schemas/result.schema.json`.
2. Add an `artifacts.yaml` entry. Use a **new** `artifact_id`; never rewrite a historical file to fit
   the current schema.
3. If it replaces an earlier decision, set `superseded_by` on the old entry and list the old id in the
   new entry's `supersedes`. Both directions are checked.
4. Set `authority: canonical` only for the one artifact that decides the gate. Historical and
   supporting artifacts must say what supersedes them.
5. Change a claim only after the gate status changes, and keep the claim's evidence list in sync.
6. Run `--check`, then `--write`, then the ledger tests. Commit the registry, the artifact, and the
   regenerated documents together.

## Adding a claim

A claim must state what is asserted, at what level, on what evidence, and what it must never be read
to mean. `forbidden_interpretations` is mandatory. A claim cannot be marked `VALIDATED` above
`L1_BEHAVIORAL_ASSISTED` while that is the operating ceiling.

## What this registry does not do

- It does not validate a claim; it records evidence and boundaries.
- It does not replace a preregistration, a sealed protocol, or an ethics approval.
- It does not cover every JSON file under `results/`; only canonical gate artifacts and explicitly
  registered historical/supporting artifacts are in scope.
- It does not resolve a blocked analysis by editing prose.
