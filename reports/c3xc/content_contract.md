# C3XC — Content Contract (Phase 2, honest scope)

## What is imagined
The imagery/test-imagery task is **cued RECALL of specific short natural VIDEO CLIPS** that subjects
had previously memorized. The 72 test targets are dynamic naturalistic video events drawn from the
**Cowen & Keltner (2017)** emotional-video collection (as used by Horikawa 2025, Mind Captioning; video
captions in the repo `data/caption/caption_ck20.csv`). During recall **no video is shown** (`stimID`=0,
`cueID`=0 in the imagery samples); the subject re-generates the remembered dynamic content internally
and rates accuracy and vividness.

## Honest content scope
- The content is **dynamic, multi-element, naturalistic video EVENTS** — motion, agents, actions,
  scenes, and often objects/humans/animals together. It is **semantic / event / scene-level** content.
- It is therefore best described as **internally-generated semantic/event (video-recall) content**.
- It is **NOT**: exact static-image content; single-object category content; pixel/exact-stimulus
  content. Any authorization must match this scope. **No terminology inflation:** C3XC does not call
  this "natural-object category imagery" (that was GOD/C3XB) nor "exact-image imagery" (DIR/C3XA).

## Composition (qualitative)
The Cowen–Keltner clips span many everyday and affective scenarios (people acting, animals, nature,
social interactions, objects in motion). A single clip typically contains **multiple** semantic
elements (e.g. a human performing an action within a scene), so the targets cannot be reduced to one
object/category label. Exact per-clip composition counts (fraction with humans / animals / objects /
scenes / actions) are derivable from `caption_ck20.csv` but are **not required** for the qualification
decision and are not used to select trials; they are noted here only to fix the honest scope. Any such
stratification is EXPLORATORY (`EXPLORATORY_CONTENT_STRATIFICATION`) and never redefines the gate.

## Scope binding used downstream
- Permitted qualification scope: **semantic/event video-recall imagery**, with **72/72 exact
  perception↔imagery correspondence** at the video-identity level.
- Maximum downstream authorization on a clean PASS (per frozen D2 contract, conservatively bounded):
  a **future, separately-prespecified, D2-content-scoped (semantic/event video-recall) reliability-
  bounded analysis** — never C3XR, C3XR-CAT, reconstruction, captioning, or C4. A FAIL/BLOCKED
  authorizes nothing.
