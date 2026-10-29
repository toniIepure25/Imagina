# Comparison Chamber: research and design rationale

**Status:** design note, not an empirical validation  
**Date:** 2026-10-24  
**Scope:** ANIMUS Studio, symbolic scene versions, local-only frontend  
**Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`

## 1. Question

When a person inspects a candidate or a historical version, what makes a **side-by-side comparison** more useful
than the existing single-pane preview with rings, traces, counts, and path rows?

The practical problem is not "show two scenes." It is:

- keep the comparison basis honest when the head, a candidate source, and a historical parent are different things;
- make the changed element findable without asking the person to remember the first scene;
- avoid turning "only differences" into a second, misleading scene;
- keep the interface usable with a keyboard, a screen reader, and reduced motion;
- avoid claiming that the layout improves perception, memory, or creative judgement.

## 2. What the literature supports

| Source | Finding used here | What it does **not** establish |
|---|---|---|
| Furnas (1986), *Generalized fisheye views*, DOI [10.1145/22627.22342](https://doi.org/10.1145/22627.22342) | A view can trade local detail against global context; focus and context are a design tension, not a binary. | That a 3D scene comparison chamber improves comprehension. |
| Shneiderman (1996), *The eyes have it*, DOI [10.1109/VL.1996.545307](https://doi.org/10.1109/VL.1996.545307) | Overview, zoom, filter, and details-on-demand are distinct information-seeking tasks. | That filtering unchanged entities is always helpful. |
| Simons & Levin (1997), *Change blindness*, DOI [10.1016/S1364-6613(97)01080-2](https://doi.org/10.1016/S1364-6613(97)01080-2) | People can miss substantial visual changes when the change is not attended or locally signaled. | That any particular side-by-side layout fixes change blindness. |
| Rensink, O'Regan & Clark (1997), *To see or not to see*, DOI [10.1111/j.1467-9280.1997.tb00427.x](https://doi.org/10.1111/j.1467-9280.1997.tb00427.x) | Change detection depends on attention and transient information, not merely on the presence of two images. | That a shared camera or a diff ring is sufficient. |
| Baldonado, Woodruff & Kuchinsky (2000), *Guidelines for using multiple views in information visualization*, DOI [10.1145/345513.345271](https://doi.org/10.1145/345513.345271) | Multiple views should be coordinated, consistent, and used when the task genuinely needs them; more views add cost. | That two WebGL panes are the right implementation for this task. |
| WCAG 2.2 SC 1.4.1, *Use of Color* | Colour must not be the only way to convey information. | That the interface is accessible without user testing. |

A search for direct empirical work on **side-by-side comparison of 3D scene versions** did not produce a
task-specific study. The design therefore borrows from focus+context, information-seeking, change blindness, and
coordinated multiple views, and treats the result as an interaction hypothesis. Confidence in the general
direction is **moderate**; confidence in any outcome claim is **low**.

## 3. Design decisions

### 3.1 One camera, two states

Both panes receive the same `cameraView` (position, target, field of view) from the head scene. Orbiting one pane
would make a moved object look changed for a camera reason, so the chamber is deliberately static and
non-interactive. The camera is a **controlled comparison variable**, not a second navigation surface.

This follows the coordination principle in Baldonado et al.: views should be consistent where the task requires
comparison. It does not prove that users will notice more changes; change-blindness work says attention and
transient cues still matter.

### 3.2 Explicit comparison basis

The chamber labels the left pane **Head** and the right pane **Preview** or **Candidate**, and states the basis:

- historical version or current preview: **Since head**;
- candidate: **Head vs candidate**, with a note that the preview panel reports the candidate's source-relative
  diff.

A candidate's backend diff is relative to its declared source version. Relabelling that diff as head-relative
would describe a comparison the person is not making. The chamber therefore uses the same client-side
`compareScenes(head, preview)` as the Stage for both pane content and counts, while the existing panel keeps the
candidate's semantic source-relative explanation. The two claims are visibly separated.

### 3.3 Only differences is a filter, not a truth claim

When enabled, each pane receives a `visibleIds` set:

- head: changed + removed entity IDs;
- preview: changed + added entity IDs.

The trace of removed or moved entities is still drawn from the head scene even when its entity is filtered out.
Counts remain based on the full comparison, not the filtered view.

The filter can hide the context needed to understand **why** something changed. It is therefore an explicit,
default-off control with a visible label. When the comparison contains only scene-level changes (for example a
sky colour or fog density), no entity can be isolated; the chamber keeps all elements visible and says so. This
avoids the failure mode where "Only differences" produces two empty scenes.

### 3.4 Redundant encoding

The chamber reuses the Stage vocabulary:

- solid mint ring: added;
- dashed amber ring: changed;
- red trace: removed or moved-from position;
- grey: unchanged.

The legend names each encoding in text. The dialog title, basis line, counts, pane labels, and screen-reader
summary carry the same information without relying on colour. This follows WCAG 2.2 SC 1.4.1 at the design level;
it is not an accessibility certification.

### 3.5 Scene-level changes are first-class rows

The client comparison now reports scene-level changes (`title`, `style`, atmosphere, lighting, camera, dynamics)
with `entity_id: null`. They count toward the changed total and appear in the panel as disabled rows, because
there is no entity to focus. The Stage cannot draw a ring for them. The chamber states that they are not attached
to an element and keeps context visible.

This closes a real gap found during end-to-end verification: a version that changed only the sky previously
reported zero differences, which made the chamber say "No differences" while the two renders visibly differed.

### 3.6 Modal, keyboard, and failure behaviour

- The chamber is a modal dialog with `aria-modal`, a labelled title, a summary, body scroll lock, Tab trapping,
  focus return, and Escape close.
- Escape closes the chamber before it closes the preview; closing the chamber does not discard the preview.
- The main Stage's Shot label clears when the person manually orbits, so a named shot is not shown as active after
  the camera has moved.
- Two canvases use `frameloop="demand"`, a device-pixel-ratio cap, and no animation. If measured performance on a
  target device is poor, the documented fallback is a single-pane toggle rather than removing the comparison.
- A failed WebGL context is already handled by `SceneBoundary`; the chamber does not claim that the fallback shows
  spatial differences.

## 4. Limits

- No usability study, A/B test, eye-tracking study, or psychometric validation was run.
- The cited work is about 2D visualizations, word recall, or general change detection, not this 3D workbench.
- The client comparison covers the symbolic scene-graph fields the frontend exposes; it is not the backend's
  canonical diff or content hash.
- Scene-level rows are descriptive. They do not localize a change in space.
- Two canvases cost more than one. The demand-rendering and DPR choices are engineering mitigations, not a
  measured performance guarantee.
- The filter can remove context. The interface mitigates this with a default-off control and a scene-level note,
  but it cannot guarantee that a person interprets the comparison correctly.
- No claim is made about improved imagery, memory, creativity, trust, or clinical benefit.

## 5. Testable next experiments

| Question | Minimal design | Primary measure | Guardrail |
|---|---|---|---|
| Does a shared-camera chamber improve change localization over the single-pane preview? | Within-subject, counterbalanced: single pane + rings/trace vs chamber; 12–20 participants; symbolic scenes with controlled changes. | Time to locate a named change; false "unchanged" judgments; correction accuracy. | No loss of accuracy; no increase in NASA-TLX workload. |
| Does "Only differences" help or harm? | Chamber with filter off vs on; same scenes; counterbalanced. | Detection accuracy; time; confidence calibration; reported loss of context. | Scene-level-only changes keep all elements visible. |
| Is the comparison basis understood? | Show historical and candidate previews; ask which state the right pane is compared against. | Correct basis identification; confidence–accuracy gap. | Candidate and version bases remain visibly distinct. |
| Do scene-level rows prevent a false "no differences" conclusion? | Sky/lighting-only changes with and without scene rows. | Correct detection that a change exists; correct attribution to a non-entity field. | No invented spatial marker. |
| Is the chamber usable with keyboard and screen reader? | Moderated task with keyboard-only and screen-reader users. | Task completion; focus order; reported ambiguity. | Escape closes chamber before preview; focus returns. |

These are proposed studies. They require review against
[`../scientific_claims.md`](../scientific_claims.md) before recruitment or publication. None of them is evidence
that ANIMUS improves imagery ability or clinical outcomes.

## 6. Verification hooks

The implementation is covered by:

- `frontend/lib/__tests__/scene-compare.test.ts` — entity and scene-level comparison, deduplicated ID sets;
- `frontend/components/animus/workbench/__tests__/CompareChamber.test.tsx` — labels, basis, counts, filter,
  no-difference state, candidate note, close;
- `frontend/components/animus/workbench/__tests__/PreviewPanel.test.tsx` — compare entry point;
- `frontend/scripts/verify-animus-ui.cjs` — opens the chamber, checks both panes, basis, legend, scene-level note,
  filter, Escape behaviour, screenshot, console errors, and mobile overflow.
