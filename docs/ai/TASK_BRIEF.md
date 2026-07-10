# TASK_BRIEF.md — Merge Gate A: Research Platform Integrity Foundation

---

## Goal

Make the `research/scientific-platform` branch structurally honest, migration-safe,
governance-safe, and ready for the later synthetic runtime implementation (Merge Gate B).

## Why This Matters

The branch contains useful research scaffolding but has critical integrity gaps: undeclared
CI deps, unenforced foreign keys, fake safeguard checkmarks, participant-facing data leakage,
unbalanced randomization, and contradictory documentation. Fixing these makes the foundation
trustworthy before any runtime integration.

## Scope

- A1: CI truth — add pytest-timeout, strict markers, classified CI jobs, verify.sh --ci
- A2: Restore EEG validation dashboard, research route structure, rename BehavioralTask
- A3: Versioned DB migrations, FK enforcement, normalized research tables
- A4: Governance services — readiness gate, consent corrections, data classification
- A5: Balanced Williams crossover allocator, persisted and transactional
- A6: Public/operator API separation, blinding enforcement
- A7: Documentation truth — reconcile all docs with actual capability status
- A8: Tests for all new invariants
- A9: Final verification and SESSION_LOG

## Non-Goals

- Persistent experiment execution (Merge Gate B)
- Session runtime extraction / policy wiring into live loop (Merge Gate B)
- Fixed/yoked execution in the live loop (Merge Gate B)
- Synthetic end-to-end orchestration (Merge Gate B)
- Playwright end-to-end tests (Merge Gate B)
- Real EEG / MNE / BrainFlow (future)
- Objective behavioral tasks (future)
- Statistical model fitting (future)
- Human participant collection (future)

## Constraints

- [x] No prohibited scientific claims
- [x] No raw EEG/neural data sent to external APIs
- [x] No hardcoded secrets
- [x] No bypassing safety monitors
- [x] Follow existing code conventions
- [x] Small, focused diffs
- [x] Do not modify V8–V44 product/demo behavior

## Starting HEAD

`32d65ef6944fb62bed75bdb7a3b78114671fd4c6`

## Commit Sequence

1. ci: classify tests and enforce honest merge checks
2. fix(frontend): restore EEG validation route and research navigation
3. refactor(frontend): rename imagery self-report task and correct timing
4. feat(storage): add versioned migrations and foreign-key enforcement
5. feat(governance): add protocol, ethics, consent, and readiness models
6. feat(randomization): add transactional balanced crossover allocator
7. refactor(api): separate public and operator research views
8. test: add migration, governance, allocation, API, and frontend behavior coverage
9. docs: reconcile research platform capability status

---

*Created: 2026-07-10*
