# TASK_BRIEF.md — Task Brief Template

> Edit this template before starting a complex AI-assisted development task. Keep it focused.

---

## Goal

*[One sentence: what are we building/fixing and why?]*

## Why This Matters

*[1-2 sentences: how does this advance IMAGINA's research goals?]*

## Scope

*[Bullet list of specific changes]*

## Non-Goals

*[What we explicitly will NOT do in this task]*

## Relevant Files

- *[Paths to files that will be touched or referenced]*

## Constraints

- [ ] No prohibited scientific claims (mind reading, dream decoding, cures, diagnosis, clinical validation)
- [ ] No raw EEG/neural data sent to external APIs
- [ ] No hardcoded secrets
- [ ] No bypassing safety monitors, fatigue checks, or cooldowns
- [ ] Follow existing code conventions in the touched files
- [ ] Small, focused diffs — no unrelated rewrites

## Acceptance Criteria

- [ ] *[Criterion 1]*
- [ ] *[Criterion 2]*
- [ ] `scripts/verify.sh` passes for relevant checks
- [ ] No new lint errors introduced
- [ ] Safety boundaries intact (if touching session/safety logic)

## Verification Commands

```bash
# Backend
cd backend && python3 -m pytest app/tests/ -q
cd backend && python3 -m ruff check .

# Frontend
cd frontend && npm run lint
cd frontend && npm run build

# Full
bash scripts/verify.sh
```

## Safety/Privacy Notes

- [ ] No changes to `.env` files or secrets
- [ ] No external API calls for neural data
- [ ] Safety monitor not bypassed
- [ ] Scientific disclaimer language preserved or strengthened

## Documentation Updates Required

- [ ] `docs/ai/SESSION_LOG.md` — log this task
- [ ] `docs/ai/DECISIONS.md` — if any architectural decision was made/changed
- [ ] `docs/ai/KNOWN_ISSUES.md` — if new risks discovered
- [ ] Project-level docs — if metrics, architecture, or claims changed

---

*Template last updated: 2026-05-07*
