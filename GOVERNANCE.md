# Governance

IMAGINA is a research project with a product surface (ANIMUS). Governance is
designed to keep scientific claims independent of product pressure.

## Roles

| Role | Responsibility |
|---|---|
| Principal investigator (PI) | Final authority on scientific claims, study protocols, ethics, and claim-ceiling changes |
| Maintainers | Code review, release management, security response, registry/ledger integrity |
| Contributors | Code, docs, analyses, and reproduction reports under this policy |
| Independent reviewer | Adversarial review of a sealed gate before a claim changes (may be external) |

Until a PI is named in `CITATION.cff`/`GOVERNANCE.md`, the maintainers act
jointly as PI for claim decisions. This is a temporary arrangement and should be
resolved before the first human study.

## Decision types

| Decision | Who decides | Record |
|---|---|---|
| Bug fix, refactor, test | Maintainer review | PR |
| Architecture, dependency, schema | Maintainer + ADR | `docs/ai/DECISIONS.md` |
| New instrument or task | PI + psychometric plan | ADR + registry entry |
| Claim status or claim ceiling | PI + sealed gate result + independent review | Ledger record + ADR |
| Study protocol, analysis plan | PI + preregistration | OSF + `docs/studies/` |
| Release | Maintainer | Tag + `CHANGELOG.md` |
| License change | PI + all significant contributors | `LICENSE` + ADR |

## Claims are gated, not voted

A claim changes status only when a sealed, preregistered analysis returns a
result that satisfies its decision rule. Consensus, enthusiasm, demos, and
investor pressure are not evidence. A positive result from one subject is a
case study, not a population claim.

The canonical claim registry and results ledger are the only sources of truth
for status. Prose in README, slides, or UI is generated from them or must link
to them.

## Conflicts of interest

Contributors must disclose financial or institutional interests that could
affect a claim decision. A reviewer with a conflict does not decide that claim.

## Amendments

Open a PR against this file with the proposed change and rationale. Changes to
the claims process require PI approval and an ADR.
