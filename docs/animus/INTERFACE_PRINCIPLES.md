# ANIMUS Interface Principles

**Status:** design rationale for the current frontend. Not an empirical validation of ANIMUS, its tasks, or its claims.
**Scope:** the interaction layer for `/animus`, `/animus/studio/[sessionId]`, `/animus/practice/[sessionId]`,
`/animus/interview/[sessionId]`, `/animus/observatory/[sessionId]`, `/animus/profile`, `/animus/worlds`, and
`/animus/about`.
**Decision this review informs:** what the next interface iteration should optimize, and which interaction
patterns should be rejected even if they look impressive.

---

## 1. Research question

> What interaction principles should govern a local-first, symbolic imagination instrument so that it preserves
> user authorship, makes uncertainty inspectable, and supports deliberate practice rather than replacing it?

The review deliberately separates:

- **reported findings** from the cited studies;
- **design inference** for ANIMUS;
- **claims about ANIMUS**, which remain at the project’s `L1_BEHAVIORAL_ASSISTED` ceiling.

## 2. Inclusion criteria

- HCI, cognitive psychology, and mental-imagery research published 2020–2026.
- Peer-reviewed venues or established preprint/review venues (CHI, DIS, ACM Collective Intelligence, Nature
  Reviews Psychology, Annual Review of Psychology, Virtual Reality, Frontiers in Computer Science).
- Focus on at least one of: generative-AI creativity support, metacognition, uncertainty communication,
  retrieval practice, spatial memory, or individual differences in imagery.
- Excluded: marketing material, product claims, clinical efficacy claims, and sources that would require a
  conclusion beyond their design.
- Search window: completed 2026-10-24.

## 3. Claim-to-source table

| Source | Design / sample | Reported finding (as stated by the authors) | What it licenses in this interface | Limits |
|---|---|---|---|---|
| Tankelevitch et al. (2024), *The Metacognitive Demands and Opportunities of Generative AI*, CHI. [doi](https://doi.org/10.1145/3613904.3642902) | Conceptual argument grounded in psychology, cognitive science, and recent GenAI user studies. | GenAI systems impose metacognitive demands around prompting, evaluating, and relying on outputs; the authors propose integrating metacognitive support and targeting explainability and customizability. | Make the user’s next evaluation explicit; expose why a candidate exists and what changed; avoid a single “generate” button that hides evaluation. | A framing paper, not a controlled test of a specific UI. |
| Moruzzi & Margarido (2024), *A User-centered Framework for Human-AI Co-creativity*, CHI EA. [doi](https://doi.org/10.1145/3613905.3650929) | Framework paper with an actionable mobile-app customization proposal. | Identifies dimensions that modulate the balance between automation and human agency in co-creative processes. | Keep locks, versions, branches, and explicit “keep this” actions central; make automation adjustable rather than ambient. | The framework is a proposal; it does not establish outcome effects. |
| Cai et al. (2023), *DesignAID: Using Generative AI and Semantic Diversity for Design Inspiration*, ACM Collective Intelligence. [doi](https://doi.org/10.1145/3582269.3615596) | Study with 87 crowd-sourced designers; compared generated semantic inspiration with a Pinterest baseline. | Automatically generated **words** were rated significantly more inspirational, enjoyable, and useful than the baseline; automatically generating highly diverse **images** had less value. High diversity was somewhat better for inspiration but not on other dimensions. | Prefer a small set of semantically distinct candidates with readable differences over a wall of visual variations. Surface the diff, not just the image. | One design-task study; results may not transfer to mental-imagery practice. |
| Reyes, Batmaz & Kersten-Oertel (2025), *Trusting AI: does uncertainty visualization affect decision-making?*, Frontiers in Computer Science. [doi](https://doi.org/10.3389/fcomp.2025.1464348) | User study with 147 participants; static gaming scenarios; continuous vs binary AI output visualization. | Uncertainty visualization affected decisions and trust-related attitudes, with substantial individual variation; 31% of participants found the visualization useful. | Show uncertainty as a first-class, inspectable property; pair every visual with a plain-language boundary and evidence count. | Game-like decision tasks; not a clinical or imagery context. |
| McDermott (2020), *Practicing Retrieval Facilitates Learning*, Annual Review of Psychology. [doi](https://doi.org/10.1146/annurev-psych-010419-051019) | Review of retrieval-practice research across materials, ages, and abilities. | Retrieval practice shortly after experience can slow forgetting and benefit later retrieval. | Keep recall before feedback; do not let the interface answer for the user during practice. | Learning research, not a claim that ANIMUS improves imagery. |
| Muraki, Speed & Pexman (2023), *Insights into embodied cognition and mental imagery from aphantasia*, Nature Reviews Psychology. [doi](https://doi.org/10.1038/s44159-023-00221-9) | Review of aphantasia and imagery variation. | The review uses aphantasia to examine embodied cognition and mental imagery, implying that imagery experience varies substantially across people. | Offer multiple response modes (visual, spatial, verbal) and avoid deficit framing in copy and scoring. | Review, not a validated training protocol; the abstract was not available, so no specific result is attributed. |
| Hu et al. (2025), *Designing Interactions with Generative AI for Art and Creativity: A Systematic Review and Taxonomy*, DIS. [doi](https://doi.org/10.1145/3715336.3735843) | Systematic review of 189 HCI system designs. | The field lacks a holistic view of GenAI interaction designs; the authors propose a taxonomy and identify under-represented design spaces. | Treat interaction architecture as a design material, not a wrapper around a model; make the instrument’s roles and boundaries legible. | Literature taxonomy; does not rank interface patterns by effectiveness. |
| Moll & Sykes (2022), *Optimized virtual reality-based Method of Loci … a feasibility study*, Virtual Reality. [doi](https://doi.org/10.1007/s10055-022-00700-z) | Feasibility study, n=21, pre/post memory-palace task. | Participants remembered approximately 20.4% more information after the VR memory-palace condition than with traditional techniques; effects repeated in a second use. | Spatial structure can be a useful retrieval cue; keep the scene navigable and spatially inspectable. | Small feasibility sample; not evidence that ANIMUS improves memory or imagery. |

## 4. Synthesis

### 4.1 The interface is the metacognitive layer

The strongest convergent finding is not “use a better model.” It is that generative systems move work into
monitoring and evaluation: what was asked, what came back, whether it is good, and what to do next. ANIMUS is
unusual because its output is already inspectable — a typed scene graph, a diff, a version history. The interface
should exploit that advantage instead of hiding it behind a chat box.

**Design inference:** every screen should answer three questions without opening a manual:

1. What is the current state?
2. What changed, and why?
3. What is the next useful action?

### 4.2 Agency is a control surface, not a slogan

Co-creativity research describes control as something that must be modulated, not maximized. ANIMUS already has
the right primitives — locks, explicit commands, versions, branches, candidate selection. The interface should
make them feel like instruments: visible, reversible, and adjustable. A command palette and a persistent session
rail reduce navigational load; they do not automate the creative judgement.

### 4.3 Diversity must be semantic, not decorative

DesignAID’s nuance matters: generated semantic material was valued, while automatically generating highly diverse
images was not sufficient. ANIMUS candidates should therefore lead with *what changed* — added, altered, removed,
preserved — and keep the candidate set small enough to compare. A visual wall of variations would violate both the
research and the claim boundary.

### 4.4 Uncertainty needs a grammar

Uncertainty visualization can change confidence and decisions, but not uniformly. The interface therefore uses
three distinct registers:

- **evidence count** (“n trials”) for amount;
- **interval or censoring** (“≤ 0.020”) for precision;
- **plain-language boundary** (“within this scene; not imagery strength”) for scope.

No single composite score or traffic-light “imagery score” is introduced. The Observatory keeps sensitivity,
criterion, threshold, and reliability separate because they answer different questions.

### 4.5 Practice must preserve the generative effort

Retrieval research supports the value of producing an answer before seeing feedback. The practice and interview
flows already hide the scene and withhold per-trial correctness. The interface should protect that difficulty:
no autocomplete of the answer, no revealing the hidden target, and no “helpful” summary that removes the recall
attempt.

### 4.6 Spatial structure is a first-class interface

The scene is not a thumbnail; it is the shared object between the user and the system. Direct selection in the
scene, an index of entities, and a stable camera make the object easier to hold and inspect. The Method of Loci
feasibility study is only a small n=21 study, but it is consistent with the broader idea that spatial structure
can cue retrieval. ANIMUS uses this as an interaction hypothesis, not a memory-enhancement claim.

### 4.7 Individual differences are design requirements

Imagery is not one capacity. Aphantasia research cautions against deficit framing. The interface therefore offers
multiple routes into the same scene — visual inspection, spatial placement, verbal description, and metacognitive
confidence — and never converts a low score into a diagnosis or a statement about a person’s imagery.

## 5. North Star

> **A calibrated mirror, not an oracle.**
>
> ANIMUS should make the user’s own imagination more inspectable and more corrigible. It should never pretend to
> see the image, grade the person, or replace the effort of holding a scene in mind.

### Design principles

1. **Instrument, not oracle.** Every generated artifact is a candidate; every estimate is a measurement with a
   boundary.
2. **Show the state before the story.** Scene, version, locks, evidence, and uncertainty precede explanation.
3. **Make the next move legible.** One contextual recommendation, never a hidden autonomous decision.
4. **Preserve generative effort.** Recall before feedback; selection before synthesis; no answer leakage.
5. **Small, semantic candidate sets.** Compare differences, not volume.
6. **Spatial directness.** The scene is selectable, indexable, and stable.
7. **Boundaries travel with the numbers.** Claim ceiling, local-only status, and “not a diagnosis” are persistent,
   not buried in a modal.
8. **Quiet confidence.** The visual system should feel precise and composed; spectacle must not imply scientific
   authority.
9. **History is material.** Versions are a palette for exploration, not only an audit trail; stepping through
   them should be cheap, reversible, and available where the scene is.
10. **Source travels with the mark.** Provenance is shown next to the scene object, not only in an inspector or a
    modal, and it never becomes a trust score.
11. **Old state is context, not a second scene.** A previous position can be shown faintly when it helps explain a
    diff; it must never look editable, current, or like a recovered hidden image.
12. **Colour is never the only channel.** Diff, provenance, and warnings need a text, shape, or line-style
    redundancy; the legend must name what the mark means.

## 6. What changed in this iteration

- Added `AnimusShell`: a dedicated ANIMUS navigation frame with a persistent local-only status, claim ceiling,
  session-level instrument rail, skip link, responsive nav, and an accessible command palette (`⌘K` / `Ctrl+K`).
- Added `AnimusCommandPalette`: keyboard-first navigation to a new scene, the four session instruments, worlds,
  profile, and boundaries. No new dependency.
- Added `SceneNavigator`: a top-down, clickable index of visible entities with relation edges inside the studio
  scene, selected state, entity labels, and keyboard focus. This makes spatial selection direct rather than
  list-only.
- Added a “Next move” metacognitive card in the studio inspector. It reflects current state; it does not decide
  for the user.
- Added an instrument-suite map on `/animus` that presents Studio, Recall, Beliefs, and Threshold as separate
  measurements with separate boundaries.
- Refined global tokens, surfaces, typography, motion, focus handling, and the root metadata; removed the stale
  “V1/V2” branding from the global header/footer.
- Replaced the global `AppShell` on ANIMUS routes with the dedicated shell, so the ANIMUS surface no longer
  inherits unrelated product navigation.

## 7. What this does not establish

- No usability study, A/B test, or psychometric validation was run for this interface.
- The cited studies do not validate ANIMUS, ERI, Scene Threshold, or any training effect.
- The interface does not add neural input, image generation, dream decoding, diagnosis, or cloud processing.
- The command palette, scene index, and “Next move” card are interaction hypotheses. They require task-based
  evaluation before any claim of improved usability or outcomes.

## 8. Testable next experiments

| Question | Minimal design | Primary measure | Guardrail |
|---|---|---|---|
| Does the session rail reduce navigation errors? | Within-subject, counterbalanced: global nav vs ANIMUS shell; 12–20 participants. | Time to reach the correct instrument; wrong-route rate. | No difference in task accuracy or perceived pressure. |
| Does the scene index improve spatial selection? | Studio task with index visible vs hidden; counterbalanced. | Time to select a named entity; selection errors. | No increase in NASA-TLX workload. |
| Does “Next move” support metacognition without automating it? | Three conditions: no card, static help, state-aware card. | Self-reported clarity; rate of intentional lock/correct actions; trust calibration. | Users can always articulate their own next action. |
| Do semantic diffs reduce fixation? | Candidate set with diff-first cards vs image-first cards. | Number of distinct corrections; self-reported inspiration; selection spread. | No claim of increased creativity. |
| Is uncertainty legible without overconfidence? | Observatory summary with interval/censoring vs point estimate only. | Calibration of interpretation; correct identification of “not imagery strength.” | No composite score; no clinical framing. |

These are proposed studies. They are not evidence of efficacy, and they must be reviewed against
`docs/scientific_claims.md` before recruitment or publication.

## 9. Provenance and access

All sources were accessed on **2026-10-24** through OpenAlex metadata/abstracts and DOI records. Where the
abstract did not expose a result, the review does not attribute that result. Full texts should be consulted before
any claim stronger than the table above.

## 10. 2026 addendum: time and provenance as spatial surfaces

A second review, [`RESEARCH_2_0.md`](./RESEARCH_2_0.md), asked how history and provenance can live in the same
spatial surface as the scene. It adds three constraints to the principles above:

1. **Timecode, not a settings page.** Sterman, Nicholas, and Paulos (2022) interviewed 18 creative practitioners
   and describe versions as a palette of materials, a source of confidence to explore, low-fidelity captures, and
   objects revisited across long time scales. Stage therefore gets a persistent version strip that previews in
   place. The Ledger remains for branches and long-range history.
2. **Rings, not a second dashboard.** Edelsbrunner et al. (2025) show that graphical labels alongside a
   visualization can disclose provenance and design decisions. In ANIMUS, the Changes and Sources layers now add
   thin outer rings to entities, plus one compact legend. Counts stay in the preview panel; no composite score is
   added.
3. **Named shots, not an autonomous director.** Wide, Eye, Detail, and Top are stable craft viewpoints. “Detail”
   frames the selected element. They make inspection repeatable without claiming to improve creativity or memory.

The research is consistent with the direction, but it does not test this interface. The Method of Loci study is a
small word-recall feasibility study, the badges study is 2D, and the SOSS framing is a 2026 preprint. See
[`RESEARCH_2_0.md`](./RESEARCH_2_0.md) §8 for confidence and unresolved questions.

## 11. 2026-10-24 addendum: Palimpsest and comparison basis

The Scene Lens now answers a question that counts and rings cannot: **where was the thing that is no longer
there?** When a preview is open and `Changes` is on, the Stage draws a subdued wireframe at the stored previous
position of moved and removed entities, plus a dashed connector for a move. The old transform comes from the head
scene graph; the workbench does not invent geometry or position.

Four constraints keep the trace from becoming a second scene:

1. **Context is quiet.** The trace is low-opacity, non-interactive, and rendered before current entities. It cannot
   be selected, transformed, or mistaken for an editable object.
2. **The comparison is named.** Version previews compare against the **current head**, not the version's parent;
   candidate previews compare against their declared source. The panel says which basis is in use. A historical
   version's stored parent diff is not silently presented as a head diff.
3. **The omission is visible.** At most 16 traces are drawn, and the legend reports the shown/total count. A large
   diff never becomes a silent partial picture.
4. **Colour has a backing channel.** Added rings are solid; changed rings are dashed. The legend names both and
   still reports provenance separately. This follows WCAG 2.2 SC 1.4.1's “not colour alone” requirement.

A preview can also be linked locally (`?version=…` or `?candidate=…`), so a reload returns to the inspected state.
The link contains no account, telemetry, or server-side share token. It is a convenience for the local session.
These are interaction hypotheses. No study in this repository shows that trace improves change localization,
memory, or trust, and no such claim should be inferred.

## 12. 2026-10-24 addendum: comparison as a transient view

The Comparison Chamber adds a second view only while the person asks for it. It follows four interface rules:

1. **Shared camera.** Both panes use the head camera. A viewpoint difference must not be read as a scene change.
   The chamber is static and non-interactive for the same reason.
2. **Named basis.** Historical previews say **Since head**; candidate previews say **Head vs candidate** and keep
   the panel's source-relative explanation separate. The interface never conflates the two comparisons.
3. **Filter with a stated cost.** **Only differences** is default-off. When a change is scene-level rather than
   attached to an entity, the filter cannot isolate it, so all elements remain visible and the chamber explains
   why. Counts stay full-comparison counts.
4. **Redundant encoding and escape.** Solid/dashed rings, trace, text counts, and a screen-reader summary carry
   the same distinctions. Escape closes the chamber before the preview; focus returns to the control that opened
   it.

The chamber does not add a score, recommendation, automatic "best version," or claim of improved perception. The
research basis and proposed evaluation are in [`COMPARISON_RESEARCH.md`](./COMPARISON_RESEARCH.md).

## 13. 2026-10-26 addendum: evidence is an interface object

A metric is not finished when its number is correct. In IMAGINA 4.0 a metric is finished when a reader can open its
evidence mark and see what it is, where it came from, how it was produced, what its uncertainty is, and what it
cannot show. The Glass Box makes that record part of the surface, not a footnote.

Five rules follow:

1. **No orphan numbers.** A metric that matters carries an `evidenceId` from the registry. An unknown id is a
   visible `?`, never a silent omission.
2. **Kind is visible.** Measured, derived, simulated, and narrative evidence are distinguished by letter, label,
   and colour, so a simulated estimate cannot borrow the authority of a measured one.
3. **The boundary travels with the claim.** The drawer's “What it cannot show” section is not optional copy; it is
   the reason the mark exists.
4. **Charts have tables.** A visual encoding must have a text equivalent. `ChartFrame` keeps the chart
   `aria-hidden` and exposes the same rows in a real table.
5. **The plan precedes the data.** The Falsification Studio asks for the estimand, decision rule, missing-data
   rule, stopping rule, and boundaries before any result exists. Better framing does not make a weak study strong;
   it makes the weakness inspectable.

The Glass Box is deliberately quiet on participant, session, replay, Studio, and Imagine-lab routes. An instrument
should explain itself where a reader is interpreting results, not interrupt the act of imagining.

## 14. 2026-10-25 addendum: the first-person preview is not a generated image

The Imagine lab adds a first-person view before a diffusion worker exists. That order is deliberate: the body,
camera, text brief, signal vector, adaptive target, and handoff contract can be evaluated now; the model cannot. Four
rules keep the surface honest:

1. **The engine is named.** The stage says **local fallback** and **diffusion offline**. A symbolic renderer must
   never inherit the visual authority of a generative model.
2. **First person is a view, not a claim.** Walking the corridor is an interaction; it does not mean the scene is a
   reconstruction, a memory, or a measurement of the person walking it.
3. **The adaptive loop declares its input.** The loop moves a demo vector toward a target every 1.6 seconds and
   says it is not live neurofeedback. Manual slider movement stops it.
4. **The handoff is inspectable.** The blocked `IMAGINA-DIFFUSION-JOB-v1` contract exposes prompt, conditioning,
   render settings, seed, and boundary text so the future worker can be reviewed before it is connected.

The lab is an interaction hypothesis and an integration seam, not evidence that diffusion, first-person presence, or
adaptive feedback improves imagery. See [`IMAGINE_LAB.md`](./IMAGINE_LAB.md) and ADR-062.

## 15. 2026-10-25 addendum: a generated skybox is not a reconstruction

Imagine 2.0 makes the diffusion lane inspectable before a worker exists. Five rules follow:

1. **The stage names the engine.** `local procedural` and `diffusion skybox` are separate badges. A generated
   environment texture never inherits the wording of a reconstruction or a measurement.
2. **Text owns semantics.** The 16D vector tunes clarity, fog, motion, saturation, detail, glow, camera pace, and
   depth falloff. It does not choose objects, people, or meaning.
3. **Consent is specific.** The dialog lists the prompt, the 16 derived values, the vector hash, what is never sent
   (raw EEG/HRV/EDA and session id), and the local/worker retention windows.
4. **The lane fails closed.** With no worker, `POST /jobs` returns `503 diffusion_unavailable` and writes no job. A
   malformed or expired manifest keeps the procedural sky.
5. **The skybox is hybrid.** Geometry, collision, first-person navigation, and the adaptive trace stay local. Only the
   environment texture changes, and the provenance tab says so.

A generated skybox is an aesthetic aid. It is not imagined content, a memory, a diagnosis, or a validated imagery
score. See [`DIFFUSION_WORKER.md`](./DIFFUSION_WORKER.md).
