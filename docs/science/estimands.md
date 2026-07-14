# Causal Estimands — IMAGINA

> **Status:** Synthetic validation only. No human causal effects established.

## Primary Estimand

**Within-participant average treatment effect of adaptive versus yoked feedback on standardized objective imagery reconstruction error during post-baseline experimental trials.**

Formally: `E[Y(adaptive) - Y(yoked)]`

**Sign interpretation:** Negative effect means adaptive produces lower (better) error.

## Secondary Contrasts

| Contrast | Estimand |
|----------|----------|
| Adaptive vs. Fixed | `E[Y(adaptive) - Y(fixed)]` |
| Fixed vs. Yoked | `E[Y(fixed) - Y(yoked)]` |
| Condition x Session | Interaction of condition with session progression |
| Objective vs. Subjective | Dissociation between objective and subjective change |

## Analysis Populations

| Population | Definition |
|-----------|-----------|
| Intention-to-Treat (ITT) | All assigned synthetic sessions |
| Per-Protocol | Sessions completed without safety stops or protocol violations |
| Complete-Case | Participants who completed all three conditions |
| Safety-Eligible | Participants without safety-triggered terminations |

## Identification Assumptions

| Assumption | Status |
|-----------|--------|
| Consistency | Structurally enforced (deterministic runtime) |
| Positivity | Structurally enforced (Williams sequence ensures all conditions assigned) |
| No leakage | Structurally enforced (LeakageGuard) |
| Correct randomization | Structurally enforced (seeded Williams allocator) |
| No differential carryover | Empirically checkable (sensitivity analysis) |
| Missing-at-random | Untestable (sensitivity via complete-case) |
| Stable endpoint | Structurally enforced (versioned, frozen endpoints) |
| Blinded analysis | Structurally enforced (condition labels not used in scoring) |
