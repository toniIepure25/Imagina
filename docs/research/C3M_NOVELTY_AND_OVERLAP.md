# C3M — Novelty and Overlap Audit

**Date:** 2026-08-22
**Branch:** `research/cross-session-alignment-c3m`
**Status:** AUDIT COMPLETE — Phase 0, before any alignment fitting
**Governing rule:** Do NOT claim novelty until this audit supports it. "Functional alignment
for imagery" is explicitly NOT claimed as novel (Spera et al. 2026 already performs latent
functional alignment on NSD-Imagery).

---

## 1. What C3M actually proposes (one paragraph)

C3M asks a **mechanistic** question that C3 exposed but did not answer: the frozen
perception decoder collapses to a single candidate **even on actually-seen NSD-Imagery vision
trials**, so the dominant failure is a **cross-session distribution shift**, upstream of the
perception→imagery question. C3M therefore attempts to remove that session shift with a
**low-capacity, target-blind transformation**, **validates it first on seen vision trials with
held-out target identities**, freezes exactly one alignment specification, and only then
unblinds imagery. This is a *session-shift-vs-imagery-state* decomposition, not a new
reconstruction method and not a new imagery-adaptation method.

---

## 2. Overlap matrix

| # | Work / method | Space transformed | Uses imagery labels to fit? | Validated on seen trials first? | Collapse-aware? | Held-out-target? | Overlap with C3M | Classification |
|---|---------------|-------------------|-----------------------------|--------------------------------|-----------------|------------------|------------------|----------------|
| 1 | Spera et al. 2026 (latent functional alignment, DynaDiff) | **decoder-output / diffusion-conditioning latent** | **Yes** — aligns imagery-evoked latent, with retrieval augmentation | No (aligns imagery directly) | Not reported | Not evident from abstract-level review | **HIGH on the imagery-alignment goal; LOW on the mechanism/method** | Distinct method, same goal |
| 2 | Kneeland et al. 2025 (NSD-Imagery benchmark) | none (evaluates frozen decoders) | No | No | No (reports 2WC only) | No | **MEDIUM** — same dataset/zero-shot framing | Benchmark, not alignment |
| 3 | Haxby/Guntupalli hyperalignment; Feilong et al. | shared response space, **cross-subject** | n/a (uses stimulus-driven responses) | n/a | No | n/a | **MEDIUM** — alignment machinery (Procrustes/SRM) | Method ancestor |
| 4 | CORAL (Sun et al. 2016); coral/whitening domain adaptation | feature covariance | No (unsupervised) | n/a | No | n/a | **MEDIUM** — M3 is CORAL | Method ancestor |
| 5 | Reduced-rank / ridge session mapping (encoding-model literature) | voxel space | varies | rarely | No | rarely | **MEDIUM** — M5/M6 machinery | Method ancestor |
| 6 | Cross-session / test-time domain adaptation (fMRI drift correction) | voxel space | typically unsupervised | sometimes | No | rarely | **MEDIUM** — same problem class (session drift) | Problem ancestor |
| 7 | C3-H4 (this program, state transport) | **decoder-output space** | fit on imagery pairs (LOSO) | No | No (pre-diagnostic) | Yes (nested LOTO) | **MEDIUM** — sibling analysis, different space | Superseded framing |

---

## 3. Axis-by-axis distinction from the nearest neighbor (Spera et al. 2026)

Spera et al. 2026 ("Seeing the imagined: a latent functional alignment in visual imagery
decoding from fMRI data", arXiv:2604.15374) is the closest prior work and MUST NOT be
re-labeled as C3M's contribution.

| Axis | Spera et al. 2026 | C3M | Genuine difference? |
|---|---|---|---|
| Space aligned | latent / diffusion-conditioning space | **raw voxel space**, before the frozen decoder's own z-scoring | **Yes** — different operator location |
| Supervision for the alignment | imagery-perception pairs **+ retrieval augmentation** (imagery labels used) | **target-blind** (Family A) or **vision-target-only** (Family B); **imagery labels sealed** | **Yes, and central** — C3M never fits alignment on imagery |
| Primary validation signal | imagery reconstruction/retrieval metrics | **held-out-target SEEN-vision decoding** (a falsifiable proxy that cannot borrow imagery information) | **Yes** — vision-first falsification |
| Failure mode handling | not reported | **prediction-collapse detection is a first-class gate** (a significant MRR with collapse FAILS) | **Yes** — directly motivated by the C3 collapse artifact |
| Generalization unit | not evident at abstract level | **held-out target identity** (nested LOTO / L2TO) | Plausible; reported as "not confirmed absent in Spera" |
| Mechanistic claim | performance-oriented | **decomposes session-shift vs imagery-state shift**, with an inject/remove counterfactual reproducing the collapse | **Yes** — this is the mechanistic core |
| Backbone strength | strong (DynaDiff) | deliberately weak (frozen ridge) — the point is the *shift*, not peak performance | Different by design |
| Reconstruction | produces images | **prohibited** (retrieval only) | Yes (program constraint) |

**Honest determination.** The *idea* of aligning brain data to rescue imagery decoding is
**not novel** — Spera et al. own that. The *machinery* (CORAL, Procrustes/hyperalignment,
ridge/reduced-rank session maps) is all pre-existing. What is defensibly new in C3M is the
**combination and the discipline**, not any single component.

---

## 4. Candidate novelty — only what survives the audit

The following are the **only** contributions C3M may claim, and each is conditional on the
empirical result actually exercising it:

1. **Explicit session-shift vs imagery-state-shift decomposition** with a **counterfactual
   perturbation** (inject the measured shift into held-out perception betas to reproduce the
   collapse; remove it from imagery-vision betas to restore diversity). This is a mechanistic
   dissection, not a performance claim. *(Survives — no reviewed prior work does this for the
   NSD-Imagery collapse.)*
2. **Target-blind session calibration validated vision-first**: fitting the alignment with
   **no imagery labels** and gating on **held-out-target seen-vision** decoding before imagery
   is ever unsealed. *(Survives as a distinct protocol from Spera's imagery-supervised
   alignment.)*
3. **Prediction-collapse as a first-class, pre-registered failure mode** of cross-session
   transfer, with the explicit rule that permutation significance under collapse is invalid.
   *(Survives — introduced in C3, formalized as a gate in C3M.)*
4. **Held-out-target alignment evaluation** (nested LOTO/L2TO) for session alignment.
   *(Survives with the caveat that Spera's full held-out protocol is unconfirmed.)*
5. **Reconstruction-readiness gating** kept downstream of a participant-level replication
   requirement. *(Program-level discipline, not a scientific novelty on its own.)*

Explicitly **NOT** claimed as novel: functional/latent alignment for imagery; CORAL;
Procrustes/hyperalignment; ridge or reduced-rank session mapping; the zero-shot-imagery
question itself.

---

## 5. Most-likely outcome and why it is still worth doing

Given C3's collapse diagnostics and the published imagery nulls, the most probable outcome is
**Outcome B or C**:

- If a target-blind transform restores seen-vision decoding but imagery still fails
  (**Outcome B**), that is a **strong, clean dissociation**: the session shift was fixable,
  seen-image decoding recovered, yet imagery content still did not transfer — evidence that
  the imagery null is *not merely* a session-shift artifact.
- If even seen-vision decoding cannot be restored by a low-capacity transform
  (**Outcome C**), that localizes the failure to session nonstationarity that low-capacity
  alignment cannot fix, and constrains what any future imagery pipeline must first solve.

Either way the value is a **mechanistic** result, honestly reported, that neither Spera et al.
nor Kneeland et al. provide: *where* in the pipeline the perception→imagery failure actually
originates, established without ever fitting on imagery labels.
