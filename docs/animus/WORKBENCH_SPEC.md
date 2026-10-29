# ANIMUS Workbench Specification

**Version:** `ANIMUS-WB-v1`
**Status:** implemented interaction contract; not an empirical validation.
**Scope:** `/animus/studio/[sessionId]` and the shared measurement surfaces that reference the same scene.
**Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`. No neural decoding, image model, diagnosis, composite imagery score,
telemetry, or cloud call.

---

## 1. What the workbench is

The Studio is a **versioned symbolic workbench**, not a form beside a preview. One immutable version graph feeds
three synchronized views:

| View | Question it answers | Primary interaction |
|---|---|---|
| **Stage** | What does the candidate look like, and what can I correct directly? | Orbit, select, transform, lock, prompt |
| **Structure** | How is the scene arranged on the ground plane? | Drag or arrow-key move, add/remove relation |
| **Ledger** | What changed, and where can I return or branch? | Preview a version, branch, inspect intentions |

The scene graph (`ANIMUS-SG-v1`) is the single source of truth. Thumbnails (`SceneSketch`) and the structure map
are derived from it; neither is a second representation that can drift.

---

## 2. State model

`lib/workbenchState.ts` defines a small reducer:

| Field | Values | Rule |
|---|---|---|
| `view` | `stage`, `structure`, `ledger` | defaults to `stage` |
| `selectedId` | entity id or `null` | pruned when the displayed scene no longer contains it |
| `gizmoMode` | `translate`, `rotate`, `scale` | transforms require an unlocked selection |
| `layers` | relations, labels, locks, changes, provenance, grid | independent toggles; grid/provenance off by default |
| `focusMode` | boolean | hides non-essential chrome; cleared when a preview opens |
| `preview` | `null`, candidate, or version | read-only overlay; never mutates the head |

Preview is a first-class state, not a modal. Opening a preview:

1. stops focus mode;
2. disables prompts, transforms, relations, locks, and world saves;
3. shows a banner with the comparison basis, added/changed/removed counts, locked-untouched count, and stale
   status;
4. offers **Keep** (candidate), **Branch** (version), or **Return** (head);
5. draws the **Palimpsest** trace on Stage when `Changes` is on.

Version previews compare the displayed scene against the **current head** using the client-side
`compareScenes` helper. Candidate previews keep the backend candidate diff because it is relative to the
candidate's declared source version and carries the semantic explanation. The panel always states the basis:
**Since head** or **Since source version**. This avoids presenting a historical version's parent-relative backend
diff as if it were a head comparison.

A candidate is **stale** when its `source_version_id` differs from the active version. Stale candidates can be
previewed but not kept. Version details are cached with a small LRU (20) and aborted on unmount.

Preview and view state are mirrored to the local URL with `history.replaceState`: `?version=…`, `?candidate=…`,
and `?view=structure|ledger`. A reload reapplies the link once the snapshot is available. Invalid links are
cleared with an inline message. The link is local-only; it is not a share service and carries no identity.

---

## 3. Direct manipulation contract

Only `entity.locked` blocks a whole-entity transform. Attribute locks (for example, colour) do not disable the
gizmo; the locked attribute remains protected by the command layer.

| Property | Client clamp | Backend round |
|---|---|---|
| position | `-256 .. 256` per axis | 6 decimals |
| rotation | `-256 .. 256` per axis (backend allows wider) | 6 decimals |
| scale | `0.01 .. 64` per axis | 6 decimals |

`EntityMesh` renders `transform.scale * entitySize`, so the workbench divides the gizmo scale by `entitySize`
before sending `set_entity_transform`. On a failed command the prior position, rotation, and scale are restored
visually, and the user sees an inline error.

Keyboard map:

| Key | Action |
|---|---|
| `1` / `2` / `3` | Stage / Structure / Ledger |
| `G` / `R` / `S` | Move / Rotate / Scale (Stage, unlocked selection) |
| `F` | Toggle focus mode |
| `[` / `]` | Preview previous / next version in the active branch |
| `L` | Lock or unlock the selected element |
| `Escape` | Close preview, overlay, or palette |
| `Ctrl/Cmd+Z` | Undo |
| `Ctrl/Cmd+Shift+Z` | Redo |
| `?` | Shortcut overlay |
| `Ctrl/Cmd+K` | Command palette |
| Arrow keys | Nudge the focused Structure node by `0.2` scene units |

Shortcuts are ignored while typing in `input`, `textarea`, `select`, or `contenteditable`.

---

## 4. Structure view

The top-down map projects `(x, z)` into a fixed `720 × 380` view. Its bounds are derived from the scene at rest,
so dragging one entity does not rescale every other entity. If the pointer leaves the drawing area, the drag is
clamped to the padded plot.

- Pointer drag moves an unlocked node.
- Arrow keys nudge the focused node.
- The relation editor writes exactly one `set_relation` or `remove_relation` command.
- The accessible table lists every element with its `x` and `z`; it is not a duplicate editor.
- Locked nodes are labelled and cannot be dragged.
- Read-only previews disable the editor and drag handles.

---

## 5. Ledger view

`lib/versionGraph.ts` builds branch lanes from `VersionSummary` and `BranchSummary`:

- lane order: active branch first, then `created_at`;
- column order: `version.number`;
- edges: cubic paths from parent to child;
- active head and previewed version have distinct marks.

The Ledger shows the graph, recent versions, branch list, and intentions. **Branch from preview** is the only
action that creates a new branch; preview alone never writes.

---

## 6. Deliberate first look

On a new session with a single version, the scene is replaced by a gate that asks three optional prompts:

1. What must stay?
2. What is uncertain?
3. What would surprise you?

The user may reveal or skip at any time. Answers are held in component state, never persisted, scored, or
uploaded. The gate closes for the mount and records only a `sessionStorage` flag so a reload does not repeat it.
Sessions with more than one version skip the gate.

This is a **generative-effort preservation** mechanism, not a test and not a measure of imagination.

---

## 7. Candidate and version preview

Candidates are deterministic procedural variations of the scene, preserving locks and explicit edits. The
candidate strip leads with semantic differences, not a wall of images:

- `added`, `changed`, `removed`, and `locked_untouched` counts;
- static `SceneSketch` thumbnail;
- **Preview** and **Keep** are separate actions;
- **Keep** is disabled for stale candidates;
- no auto-selection, no re-ranking by engagement.

Version preview uses `getStudioVersion` with an abort signal. A previewed version is read-only and cannot be
kept as a new head; the user branches from it instead.

### 7.1 Stage lens: timecode, shots, and provenance

**Timecode** is a persistent strip on Stage when the active branch has more than one version. It lists versions
in `number` order, marks the live head, and previews a version in place. It never commits. `[` and `]` step to the
previous or next version; clicking the head returns to the live state. The Ledger remains the place for branch
topology and long-range history.

**Scene lens** gives the `Changes` and `Sources` layers a spatial meaning:

| Layer | On Stage |
|---|---|
| `Changes` | Added entities get a solid mint outer ring; changed entities get a dashed amber outer ring. A compact legend reports added/changed/removed counts and names the solid/dashed distinction. |
| `Sources` | Each entity gets a thin outer ring coloured by scene-graph provenance: explicit, implied, candidate, or seed/procedural. The legend names the colours and says this is source, not a claim about the person. |

The rings sit outside the selection and lock rings so the marks do not overwrite one another. Neither layer adds a
score, a ranking, or a recommendation.

### 7.2 Palimpsest: previous-position trace

When a preview is open and `Changes` is on, the Stage renders a subdued wireframe proxy at the **stored previous
position** of each moved or removed entity. Moved entities also get a dashed connector from old to new position.
The proxy is built from the head scene graph transform; it is not reconstructed imagery and it is not editable.

- The trace is non-interactive, low-opacity, `depthWrite={false}`, and drawn before current entities.
- At most 16 traces are drawn. Moved entities are listed before removed entities; the legend reports
  `trace: N of M previous positions` when the cap is reached.
- Attribute-only changes do not create a trace because there is no position change; the dashed ring and the
  changed-path rows carry them.
- Removed entities can be inspected in the panel, but cannot be focused in the current scene. Their trace is the
  spatial answer.
- The screen-reader description reports added/changed/removed counts and the number of traces.

This is a focus+context aid. It is not evidence that users understand a diff better, and it does not add a
“hidden geometry” or image-reconstruction claim.

### 7.3 Comparison Chamber

Opening **Compare** from the preview banner or panel presents a full-screen modal with two static panes:

| Pane | Content |
|---|---|
| Head | Current head scene, no diff rings, no trace |
| Preview / Candidate | The inspected scene with `Changes` rings and the trace of removed or moved-from positions |

Both panes use the same `cameraView` (position, target, fov) taken from the head scene, `interactive={false}`,
`frameloop="demand"`, no animation, and a capped device-pixel ratio. The chamber is temporarily modal: it traps
Tab, returns focus on close, locks body scroll, and closes on Escape or the backdrop. Escape closes the chamber
before it closes the preview; closing the chamber does **not** discard the preview.

The header states the comparison basis:

- historical version or ordinary preview: **Since head**;
- candidate: **Head vs candidate**, plus a note that the preview panel reports the candidate's source-relative
  diff.

The **Only differences** checkbox is default-off. When on, each pane filters to changed/removed (head) or
changed/added (preview) entity IDs; the trace still uses the full head scene. If the diff contains only
scene-level changes (`entity_id: null`), no entity can be isolated, so all elements stay visible and the chamber
says so. Counts are always for the full comparison, not the filtered view. The footer legend names solid added,
dashed changed, trace removed/moved-from, and unchanged.

The chamber is also available from the command palette (**Compare with head**) and `C`. The command is disabled
while the preview is loading or stale. Manual orbit clears the active Shot label on the main Stage, because a named
shot is no longer the current camera.

The chamber is an inspection hypothesis, not a claim that side-by-side comparison improves detection, memory, or
creative judgement. See [`COMPARISON_RESEARCH.md`](./COMPARISON_RESEARCH.md).

**Shot deck** exposes four stable camera views:

| Shot | Behaviour |
|---|---|
| `Wide` | Establishing view of the scene |
| `Eye` | Low eye-level view |
| `Detail` | Close view framed on the selected element, or the scene target when nothing is selected |
| `Top` | Overhead plan view |

Shots are craft controls, not an autonomous cinematographer. They do not alter the scene graph.

---

## 8. Dossier and measurement language

The profile page uses a paper dossier rather than dashboard gradients. Every dimension is shown separately with:

- estimate or Brier score;
- uncertainty band and reliability;
- trial count and status;
- a plain-language reading rule.

There is **no composite score**. Calibration is displayed separately and marked “lower is better”. Scene
Threshold shows threshold, d′, Brier, trial/coverage counts, and an explicit censoring note. Adaptive practice
shows the backend `adaptive.reason`, task family, difficulty, and expected gain when available.

---

## 9. Accessibility and failure behaviour

- All workbench tabs use `role="tab"` / `aria-selected`; panels are labelled.
- The command palette and shortcut overlay are modal dialogs with Escape handling, Tab trapping, and focus return.
- Added rings are solid and changed rings are dashed, so colour is not the sole added/changed encoding. The
  legend names both.
- The scene region's screen-reader description includes the comparison counts and trace count.
- Route-level `loading.tsx` and `error.tsx` exist for Studio, Recall, Beliefs, and Threshold.
- A failed WebGL context is caught by `SceneBoundary` and replaced by the static `SceneSketch`, with a message
  that the symbolic scene is unchanged. The preview panel still reports counts and basis; the trace is not
  claimed to be visible in the fallback.
- Reduced motion is read through `useSyncExternalStore`; no animation is required to understand a result, and the
  trace is static.
- Every interactive control has a visible focus ring and a text label or `aria-label`.

---

## 10. Verification contract

| Layer | Command | Coverage |
|---|---|---|
| Types | `node node_modules/typescript/bin/tsc --noEmit` | all components and libs |
| Lint | `eslint` on changed files | hooks, a11y rules, no unused vars |
| Unit | `vitest run` | reducer, version graph, scene contract, scene comparison/trace (including scene-level rows), URL links, focus trap, timecode, preview panel, comparison chamber, existing studio API |
| Build | `next build` | production compilation and route generation |
| UI | `node scripts/verify-animus-ui.cjs` | landing → studio → prompt → head-relative preview → trace legend/basis → comparison chamber (two panes, shared camera, basis, legend, scene-level note, filter, Escape) → linked reload → shot deck → lock → candidates → keep → undo → branch → save world → reload → world open/delete → mobile overflow |
| Backend | `pytest app/tests/test_animus_scene_revisions.py app/tests/test_animus_scene_commands.py` | scoped version IDs, transforms, relations |

What this contract does **not** establish: usability, learning gains, imagery improvement, clinical benefit, or
validity of any measurement model. Those require separate studies.
