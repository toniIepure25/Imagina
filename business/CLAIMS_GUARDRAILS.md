# Claims guardrails for business and paper text

**Status:** operating rule. This is not a semantic proof; it is a review gate.

## 1. Allowed

- "local-first research instrumentation"
- "simulation-only evidence"
- "experimental behavioural assay"
- "not validated in humans"
- "does not decode imagined content"
- "designed to test whether ..."
- "pre-registered" only after registration exists

## 2. Prohibited

- Prohibited: "reads your mind", "decodes your dreams", "shows what you are imagining"
- Prohibited: "cures aphantasia", "guarantees lucid dreaming"
- Prohibited: "clinically validated", "diagnoses", "treats"
- Prohibited: "measures consciousness objectively"
- Prohibited: "neural reconstruction" as a product claim
- Prohibited: "first", "revolutionary", "proven", "breakthrough" without a bibliographic review and editor approval
- Prohibited: "validated" before the measurement gates pass

## 3. Evidence rule

Every quantitative claim in a deck, one-pager, or paper must point to:

1. a canonical artifact path;
2. a gate status;
3. a date and code SHA; or
4. an interview/LOI record that exists.

If the source does not exist, remove the number.

## 4. Review process

1. Run `python scripts/audit_public_claims.py`.
2. Read the sentence aloud with "we claim that" in front.
3. Ask: what would falsify it?
4. Ask: is this simulation, pilot, or human evidence?
5. If the answer is unclear, label it "hypothesis" or delete it.

## 5. Escalation

A claim that implies clinical, decoding, or consciousness capability is blocked until the PI and an
independent reviewer approve it in writing. No sales exception.
