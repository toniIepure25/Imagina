# ANIMUS 2.0 — Research Synthesis for a Spatial, Temporal Workbench

**Status:** design research, not an efficacy study.
**Access date:** 2026-10-24.
**Claim ceiling:** `L1_BEHAVIORAL_ASSISTED`. Nothing here validates ANIMUS, improves imagery, or establishes a
clinical, neural, or creative outcome.

## 1. Research question

How can a local, symbolic scene workbench make **history** and **provenance** inspectable in the same spatial
surface as the scene, without turning the interface into an oracle, a dashboard of composite scores, or a
prompt-and-wait generator?

The decision this review informs: which interface slice should follow the versioned workbench (Stage, Structure,
Ledger) and why.

## 2. Inclusion criteria

- Human–computer interaction, CSCW, visualization, and cognitive-science work relevant to version history,
  provenance, metacognition, and spatial material.
- Peer-reviewed work preferred; one 2026 preprint is included and explicitly marked.
- 2022–2026, with older foundational claims only where already documented in
  [`INTERFACE_PRINCIPLES.md`](./INTERFACE_PRINCIPLES.md).
- Excluded: neural decoding, diagnosis, image-generation benchmarks, engagement optimization, and any source that
  would require a claim above the project ceiling.

This is a **rapid, abstract-level review**, not a systematic review. It does not pool effect sizes. Several claims
below are design inferences, not findings.

## 3. Sources and what they actually report

| Source | Design / sample | Reported finding (abstract level) | Why it matters here | Main limitation |
|---|---|---|---|---|
| Sterman, Nicholas & Paulos (2022), *Towards Creative Version Control*, PACM HCI. [doi:10.1145/3555756](https://doi.org/10.1145/3555756) | 18 semi-structured interviews across creative domains; qualitative analysis organised by software version-control paradigms. | Creative practitioners use versions as **a palette of materials**, for **confidence and freedom to explore**, through **low-fidelity capture**, and for **reflection and reuse across long time scales**. The authors argue existing systems are not attuned to these behaviors. | History is not only backup or audit. It is working material. A version control surface should be continuously available and cheap to compare, not buried in an admin panel. | Qualitative, 18 participants; not a comparative usability test; domains vary. |
| Moll & Sykes (2022), *Optimized VR-based Method of Loci…*, *Virtual Reality*. [doi:10.1007/s10055-022-00700-z](https://doi.org/10.1007/s10055-022-00700-z) | Feasibility study; VR memory palace. Week 1 n=21; second-use analysis n=17. | Word recall increased from M=62.55 to M=82.91 in week 1, about **20.4% more** non-spatial information, t(20)=−2.34, p=.014; second use about **22.2% more**, t(16)=−2.142, p=.024. | Spatial continuity can support holding and revisiting material. ANIMUS already treats the scene as the shared object; this supports keeping history **in** that object rather than in a separate page. | Small feasibility study; word-list recall, not scene authoring; short training; no interface comparison; does **not** show that a 3D history UI improves design. |
| Edelsbrunner et al. (2025), *Visualization Badges*, IEEE TVCG. [doi:10.1109/TVCG.2025.3634782](https://doi.org/10.1109/TVCG.2025.3634782) | Co-design workshops; conceptual framework; catalogue of 132 badges. | Graphical labels placed **alongside** visualizations can communicate provenance and design considerations, with the stated aims of transparency, justified decisions, and fewer incorrect conclusions. | Put provenance next to the mark, not in a distant modal. Compact, repeated marks can carry source information without a second screen. | 2D visualization context; abstract does not report a controlled effect size for trust or interpretation; badge overload is a real risk. |
| Tankelevitch et al. (2024), *The Metacognitive Demands and Opportunities of Generative AI*, CHI. [doi:10.1145/3613904.3642902](https://doi.org/10.1145/3613904.3642902) | Conceptual synthesis of psychology, cognitive science, and recent GenAI user studies. | GenAI imposes **metacognitive demands** on users—monitoring and controlling prompting, evaluation, reliance, and workflow—and systems can support or reduce those demands through explainability and customizability. | The interface should externalize state (what changed, what is locked, what is a candidate) so the user does not have to reconstruct it from memory. | Conceptual paper; not a test of this UI. |
| Fernandes et al. (2025), *AI makes you smarter but none the wiser*, *Computers in Human Behavior*. [doi:10.1016/j.chb.2025.108779](https://doi.org/10.1016/j.chb.2025.108779) | Study 1 N=246, 20 LSAT logic problems with AI; Study 2 N=452 replication. | Performance improved by **3 points** versus a norm population, while participants **overestimated** performance by **4 points**. Higher AI literacy was associated with **less accurate** self-assessment. The usual Dunning–Kruger pattern disappeared with AI. | Fluency and ease are not calibration. Do not collapse performance, confidence, and quality into one score or one “good” badge. Keep boundaries and separate measures visible. | Logic-task performance, not creative scene work; a single composite “performance” framing; does not test ANIMUS. |
| Dalsgaard (2025), *Scaffolding Metacognition in Design with Generative AI*, IASDR. [doi:10.21606/iasdr.2025.426](https://doi.org/10.21606/iasdr.2025.426) | Design research paper. | The title and venue position GenAI as a possible scaffold for metacognition in design. **No abstract was available in the indexed record used here, so no finding is attributed.** | Supports the general design question of how to scaffold reflection rather than automate judgment. It is cited as framing only. | No result extracted; do not use as evidence of effectiveness. |
| Andersson & Elmqvist (2026), *Material for Thought: Generative AI as an Active Creative Medium*, arXiv preprint. [doi:10.48550/arXiv.2605.19832](https://doi.org/10.48550/arXiv.2605.19832) | Position paper; creative-writing probe “Loom”; proposes the SOSS framework. | Argues that the “human as judge of AI output” framing misdirects creative work toward evaluating correctness. Proposes treating GenAI as an active medium that humans **Shape, Observe, Stir, and Select**; humans contribute disruption and curation where the model converges. | The workbench should be a place to shape and compare material—direct manipulation, candidates, reversible versions—not only a prompt box that returns a verdict. | **Preprint, not peer-reviewed**; conceptual framework and probe, not a controlled study; does not validate this interface. |

## 4. Synthesis: five design propositions

### 4.1 History is material, not an audit trail

Sterman et al. describe versions as a palette, a source of confidence to explore, and something practitioners
revisit across long time scales. That reframes the Stage: the current head is one state among many, and stepping
through versions should be as direct as selecting an object.

**Design response:** a persistent **Timecode** strip on Stage. It shows the active branch’s versions in order,
marks the head, and previews a version in place without committing. The Ledger remains the place for branches and
long-range history. The Timecode is for the common, low-friction case: “what did this look like one move ago?”

This is a design hypothesis. The source supports the importance of cheap version access; it does not show that a
horizontal strip in a 3D editor is the best form.

### 4.2 Provenance belongs next to the mark

Visualization Badges supports labels that travel with the visualization and disclose design/provenance decisions.
ANIMUS already has a provenance chip in the inspector, but that requires selection and a second glance. The scene
itself can carry a thin outer ring whose color encodes the entity’s source.

**Design response:** when **Sources** is on, each entity gets a slim provenance ring (explicit, implied, candidate,
seed/procedural). A compact legend names the colors and states the scope: this is scene-graph source, not a claim
about the person’s imagery.

The risk is badge fatigue. Rings are quieter than text badges and only appear when the layer is explicitly on.
No “trust score” is added.

### 4.3 Diff should be spatial, not only numeric

The candidate and version panels already report added, changed, and removed counts and changed paths. But a count
does not tell the user **where** the change is. The scene can answer that directly.

**Design response:** when **Changes** is on and a preview is active, added entities get a mint outer ring and
changed entities an amber, dashed outer ring. Removed entities and moved entities also get a subdued
**previous-position trace** derived from the stored transform: a wireframe proxy at the old location, plus a
dashed connector for a moved entity. The trace is context, not a second live scene. It is capped at 16 proxies
and the legend reports `shown of total`; the preview panel lists the labels. The interface does not invent a
geometry or a position the version graph does not contain.

This is an inference from the value of direct spatial selection and from provenance adjacency. It is not tested.

### 4.4 Separate performance, confidence, and quality

Fernandes et al. show that AI assistance can improve task performance while worsening self-assessment, and that
greater AI literacy can be associated with less accurate calibration. A single “quality” or “confidence” score
would make exactly the wrong merge.

**Design response:** keep the claim ceiling, evidence counts, intervals, and “not imagery strength” boundaries
separate. Do not add a composite scene score, a “best version” badge, or an AI confidence number that looks like
quality. Preview is explicitly non-destructive and read-only.

### 4.5 Treat the workbench as a medium for shaping

The SOSS framing (Shape, Observe, Stir, Select) is a preprint and should be cited cautiously, but it matches the
existing ANIMUS position: candidates are material to compare, not answers to accept. Direct manipulation,
locks, reversible versions, and multiple camera views keep the human in the shaping loop.

**Design response:** a visible **Shot** deck (Wide, Eye, Detail, Top). “Detail” frames the selected element; the
others give stable, named viewpoints. This is craft language, not a cognitive claim. It makes the scene easier to
inspect and discuss without adding an “AI cinematographer.”

## 5. What is actually new in this slice

The distinctive move is not any one control. It is putting **time** and **source** into the same spatial surface
as the scene:

- a Timecode dock that previews history in place;
- outer rings that encode diff and provenance on the object itself;
- a head-relative **Palimpsest** trace of previous positions for moved and removed entities;
- a scene-lens legend that reports what the rings and trace mean;
- named shots that make the same scene legible from different standpoints;
- a local preview link that restores the inspected state after reload.

This is a coherent interface direction. It is **not** a validated breakthrough, and the word “revolutionary”
should not appear in product copy.

## 6. What we deliberately did not build

- No automatic “best version” ranking.
- No composite creativity, imagery, or scene-quality score.
- No generated summary that replaces inspecting the diff.
- No auto-commit, auto-branch, or hidden agent action.
- No image model, cloud call, telemetry, or neural input.
- No claim that the Timecode, rings, or shots improve memory, creativity, or imagery ability.

## 7. Testable next experiments

| Question | Minimal design | Primary measure | Guardrail |
|---|---|---|---|
| Does in-place Timecode reduce history navigation cost? | Within-subject: Ledger-only vs Timecode + Ledger; 12–20 participants; counterbalanced. | Time to locate a named prior version; wrong-version selections; context switches. | No loss of accuracy; no increase in NASA-TLX. |
| Do spatial diff rings improve correction targeting? | Preview with numeric diff only vs rings + legend. | Time to identify the changed entity; correction accuracy; false “unchanged” judgments. | Removed/moved entities trace only from stored transforms; nothing is invented. |
| Does provenance-on-scene support calibration? | Sources off vs inspector-only vs rings + legend. | Correct attribution of an entity’s source; confidence–accuracy gap. | No “trust score”; no inference about the person. |
| Does a named shot deck improve inspection? | Free orbit vs named shots for a review task. | Viewpoint reproducibility; time to return to a prior view; task completeness. | No claim of improved creativity or memory. |
| Does a previous-position trace improve change localization? | Preview with rings only vs rings + trace + legend; within-subject. | Time to locate where a removed/moved entity was; false "still here" judgments; perceived clutter. | Trace is capped and counted; no invented geometry; no claim that trace improves memory. |

These are proposed studies. They require review against [`../scientific_claims.md`](../scientific_claims.md)
before recruitment or publication.

## 8. Confidence and unresolved questions

**Confidence in the design direction: moderate.** The version-as-material and provenance-adjacency findings are
consistent and directly relevant. The metacognition literature supports separating state and judgment.

**Confidence in any outcome claim: low.** No study here tests this workbench. The MoL study is small and about word
recall. The badges paper is about 2D visualizations. The SOSS paper is a preprint. The Dalsgaard record yielded no
abstract, so it is framing only.

Unresolved:

- How many versions can the Timecode show before it becomes a second Ledger?
- Do rings remain legible when many entities are changed at once?
- Does Detail framing a selected entity help, or does it disorient users who lose the wider scene?
- Is a provenance ring understood without the legend, especially for color-vision differences?
- Does a previous-position trace clarify a removal, or does it read as a second live object?
- How much trace is useful before the Stage becomes a palimpsest of every edit?

The next iteration should answer those with task-based observation, not more interface surface.

## 9. 2026-10-24 addendum: previous-position context and comparison basis

This addendum records the design rationale for the Palimpsest trace, the head-relative comparison, and the
solid/dashed ring encoding. It is a design inference, not a new empirical result.

**Comparison basis.** A historical version's backend `diff` is relative to its parent; the current head may be
several versions later. Presenting that parent-relative diff as "what changed" would describe a different
comparison from the one the user is making. The workbench therefore computes a small, deterministic
head-to-preview comparison on the client for version previews. Candidate previews keep the backend candidate diff
because it is relative to the candidate's declared source version and carries the semantic explanation. The
preview panel states the basis in text: **Since head** or **Since source version**.

**Previous-position context.** Removed entities have no current geometry, and a moved entity's prior location is
not visible once it has moved. The old transform is already present in the head scene graph, so the Stage can draw
a wireframe proxy at that stored position. For moved entities, a dashed connector links old and new positions.
This is a focus+context pattern: the current object stays primary, and the old state is deliberately quiet. The
proxy is symbolic and does not claim to reconstruct hidden geometry.

**Limits.**
- The trace is a spatial aid, not evidence that users understand a diff better.
- The trace cap and the `shown of total` count prevent silent omission, but they also mean a large diff is not
  fully drawn.
- The client comparison covers the scene graph fields the workbench exposes; it is not a replacement for the
  backend's canonical diff or content hash.
- The solid/dashed ring distinction reduces colour-only encoding for added/changed, but it has not been tested
  with colour-vision-deficient users.
- The preview URL is local to the session and is not a sharing or persistence service.

**Related standards and sources.** The focus+context idea is longstanding in information visualization (Furnas,
1986); "details on demand" is one of Shneiderman's (1996) visual-information-seeking tasks. Both are cited here as
design vocabulary, not as tests of this workbench. WCAG 2.2 SC 1.4.1 (Use of Color) motivates the redundant
solid/dashed encoding. Onion skinning is an animation craft convention; no empirical claim is attached to it.
Bibliographic details should be checked against the original records before any external publication.

## 10. 2026-10-24 addendum: the Comparison Chamber

The Palimpsest trace answers "where was it?" but it still asks the person to alternate attention between the
live scene and a remembered state. The Comparison Chamber is a second, explicit view: head on the left, preview or
candidate on the right, both rendered with the same camera, and an optional filter that hides unchanged entities.
It is a **transient inspection mode**, not a new version, branch, or persistence surface.

**Why a second view.** Coordinated multiple views are appropriate when a task needs two states visible at once;
Baldonado et al. (2000) also warn that extra views add coordination cost. The chamber pays for a second canvas only
while the person asks for it. It keeps the camera identical in both panes so a viewpoint difference cannot be
mistaken for a scene difference. This is a design inference, not a measured improvement.

**What it does not solve.** Change-blindness work (Simons & Levin, 1997; Rensink et al., 1997) says attention and
transient cues matter; two static images are not a guarantee that a change will be seen. The chamber therefore
keeps counts, rings, trace, and the explicit basis visible. The "Only differences" filter is default-off because
hiding context can make a change harder to interpret, especially when the change is scene-level rather than
attached to an entity.

**Basis discipline.** Historical previews use `compareScenes(head, preview)` and say **Since head**. Candidate
previews say **Head vs candidate**; the existing panel continues to report the candidate's source-relative diff.
The chamber never relabels a source-relative candidate diff as head-relative. Candidate source changes are also
reported as disabled rows rather than as a second silent comparison.

**Scene-level changes.** A sky, fog, lighting, camera, or dynamics change has no entity to ring. The client
comparison now emits `entity_id: null` rows for these fields, which keeps the counts honest and prevents a false
"No differences" state. When only scene-level changes exist, the filter cannot isolate anything, so all elements
remain visible and a note says why. The rows describe a field; they do not localize it in space.

**Limits.** Two canvases cost more than one; rendering is demand-driven and DPR-capped, with a single-pane toggle
as the documented fallback if a target device measures poorly. There is no direct study of 3D scene-version
comparison, no usability test of this chamber, and no evidence that it improves change detection, memory, or
creative judgement. The detailed review, sources, and proposed experiments are in
[`COMPARISON_RESEARCH.md`](./COMPARISON_RESEARCH.md).

