# The evidence instrument — Glass Box 4.0

Status: implemented frontend-only in IMAGINA 4.0. Claim ceiling remains `L1_BEHAVIORAL_ASSISTED`.

## Why it exists

IMAGINA renders many numbers: proxy metrics, simulated estimates, curriculum levels, calibration summaries, dataset
readiness, and study-plan previews. A number without a source, method, uncertainty statement, and explicit “cannot
show” boundary invites over-reading. The Glass Box makes those four fields part of the interface rather than a
separate methodology page that nobody opens.

Every rendered metric is paired with a **24×24 evidence mark**. The letter states the evidence kind:

| Letter | Kind | Meaning |
| --- | --- | --- |
| M | Measured | Read directly from a recorded artifact or completed task output. |
| D | Derived | Computed from other values; the method is available. |
| S | Simulated | Produced by a generator or synthetic runtime, not a human. |
| N | Narrative | Interpretive copy or a boundary statement; not a measurement. |

The mark is a button. It opens a focus-trapped drawer with **what it is**, **source**, **method**, **uncertainty**,
**what it cannot show**, surfaces where it appears, and a link into the Falsification Studio. The drawer is not a
tooltip: it must be reachable by keyboard and readable by a screen reader.

## Single source of truth

```
frontend/lib/evidence/registry.json      # 22 entries, schema IMAGINA-EVIDENCE-REGISTRY-v1
frontend/lib/evidence/registry.ts        # typed lookup, surface matching, counts
frontend/lib/evidence/types.ts           # EvidenceEntry, EvidenceKind, GlassBoxPreference
frontend/lib/evidence/glassboxStore.ts   # localStorage: imagina.glassbox = auto | on | off
frontend/lib/evidence/audit.json         # generated artifact, schema IMAGINA-EVIDENCE-AUDIT-v1
```

An entry carries:

```json
{
  "id": "iqi.proxy",
  "label": "IQI",
  "kind": "derived",
  "what": "…",
  "method": "…",
  "source": "…",
  "uncertainty": "…",
  "cannot": "…",
  "surfaces": ["/science", "/reports/[sessionId]"],
  "studyEligible": false
}
```

`evidenceId` is always the literal prop passed to `EvidenceMark`; the audit script scans the TypeScript AST for that
prop, so indirection such as a runtime variable is invisible to the audit. Add marks through literal ids.

## Surfaces

- `/method` — **Method Atlas**: counts by kind, legend, registry cards, search/kind filters, anchor links, the latest
  audit artifact, and study-designer links. Keyboard and print friendly.
- `/science`, `/profile`, `/reports/[sessionId]`, `/multimodal`, `/datasets`, `/research/analysis`,
  `/animus/profile`, and `/animus/observatory/[sessionId]` — metric-level marks. `/animus/imagine` carries
  `imagine.scene` for the local first-person preview. The registry also carries `imagine.diffusion` for the
  fail-closed skybox lane; the immersive route stays intentionally quiet.
- The header toggle exposes `auto | on | off`. `auto` enables marks on research/report surfaces and disables them on
  participant, session, replay, Studio, and Imagine-lab routes so immersive surfaces stay quiet.

## Claim audit

`frontend/scripts/audit-claims.cjs` performs a static, negation-aware scan:

```bash
cd frontend
node scripts/audit-claims.cjs          # report only
node scripts/audit-claims.cjs --write  # regenerate lib/evidence/audit.json
```

It checks:

1. prohibited phrases (mind reading, dream decoding, clinically validated, composite imagery score, etc.);
2. whether a phrase is negated or presented as a boundary;
3. `evidenceId` literals, registry membership, and orphans.

The current audit covers 194 files, finds 11 phrase matches (all boundary/negated), sees 11 distinct evidence ids
referenced by code, and has 0 orphans. The script fails on any affirmative prohibited phrase or unknown id. It is a text audit, not a
substitute for human review.

## Performance and accessibility

- The Atlas and drawer use semantic tokens, 11px minimum visible text, 24px icon targets, and 44px primary actions.
  `scripts/verify-platform-ui.cjs` audits 26 static routes at 1440 and 390 px for console errors, overflow, sub-11px
  text, and undersized targets.
- The drawer traps focus, restores focus on close, locks body scroll, closes on Escape, and labels its dialog.
- Charts use `ChartFrame`: the visual chart is `aria-hidden`, and a real `<table>` is available under “View as
  table”. A chart without a table is not considered complete.
- Long event timelines use `VirtualList`; only a viewport window of rows is mounted.
- 3D canvases cap DPR at 1.5, pause to `demand` when the tab is hidden, and show a recoverable message when the
  WebGL context is lost.
- `npm run budget:bundle` reads the production manifests and enforces measured regression ceilings: shared 220 KB
  gzip, non-3D route 340 KB, 3D route 540 KB. These are regression ceilings for the current Next 16 / React 19
  baseline, not a claim that the original aspirational 120/180/350 targets were met.

## Limits

- The registry is curated by hand. A complete registry is not evidence that an entry is valid.
- Evidence marks describe provenance and method; they do not make a proxy metric psychometrically validated.
- The audit is textual and static; it cannot detect an affirmative claim expressed without a listed phrase.
- Glass Box preference is local-only. No telemetry is collected.
