# Scientific Gate C3M — Cross-Session Neural Alignment and Imagery-Transfer Mechanism

**Status:** OPEN (Phase 0 — protocol frozen before any alignment fitting)
**Branch:** `research/cross-session-alignment-c3m`
**Source SHA:** `1a3375549a1f42faa48965ede88d90b5793cab9a`
**Author:** Iepure Antoniu
**Date opened:** 2026-08-22

---

## 0. Relationship to C3 (this does NOT reopen C3)

C3 is a **completed, valid null result for STRICT ZERO-SHOT transfer** and remains so.
Its accepted decision is preserved verbatim and is not retrospectively changed:

```
C3_PERCEPTION_DECODING        = PASS
C3_IMAGERY_ROW_PROVENANCE     = PASS
C3_ZERO_SHOT_IMAGERY_TRANSFER = NULL_SUPPORTED_WITHIN_SENSITIVITY
C3_STATE_TRANSPORT            = NULL_OR_INCONCLUSIVE
C3_RECONSTRUCTION_READINESS   = BLOCKED
C3                            = COMPLETE_WITH_IMAGERY_TRANSFER_NULL
```

C3M is a **new gate** that investigates a *mechanism* left unresolved by C3, not the
perception→imagery question directly. The C3M decision never overwrites the C3 decision
artifacts (`results/c3_final_decision_realdata_v2.json` and predecessors).

### The precise claim boundary carried in from C3

C3 does **not** show that mental imagery contains no decodable visual information. It shows
that the *frozen perception-trained decoder* fails zero-shot on the NSD-Imagery session.
Critically, the **same decoder collapses even on actually SEEN NSD-Imagery vision trials**:

| Condition (subj01)             | Dominant-candidate collapse | 2AFC   | exact MRR p |
|--------------------------------|-----------------------------|--------|-------------|
| NSD-Imagery vision Set A (seen)| 48/48 → candidate 2         | 0.621  | 0.597 (ns)  |
| NSD-Imagery vision Set B (seen)| 45/48 → candidate 6         | 0.508  | 0.026       |
| NSD-Imagery imagery Set B      | 96/96 → candidate 6         | 0.424  | 0.0014      |
| NSD-Imagery imagery Set A      | 96/96 → candidate 2         | 0.631  | 0.313 (ns)  |

(Source: `results/c3_subj01_nsdimagery_vision_validation.json`,
`results/c3_zero_shot_transfer_realdata.json`.)

Because the decoder collapses on **seen** stimuli too, the dominant unresolved mechanism is
**cross-session nonstationarity** (a distribution shift between the core NSD perception
sessions and the single NSD-Imagery session), which sits **upstream** of the
perception→imagery question. The apparently-significant Set B exact-p values are artifacts of
one physical stimulus coinciding with the collapse target, not evidence of transfer.

---

## 1. Scientific questions

**PRIMARY.** Can a **low-capacity transformation learned WITHOUT imagery-content labels**
remove the NSD→NSD-Imagery session shift sufficiently to **restore stimulus-specific decoding
of actually seen stimuli** (the NSD-Imagery vision trials)?

**SECONDARY (conditional).** *If and only if* cross-session perception decoding is restored:
does the **same frozen session-alignment transformation** reveal stimulus-specific
perception→imagery transfer when applied to the imagery betas?

The primary gate is deliberately a **vision** gate: it can be validated against known seen
targets and is therefore falsifiable without ever touching imagery labels.

---

## 2. Hypotheses

- **C3M-H1 — Cross-session shift exists.** NSD-Imagery session betas differ systematically
  from core NSD perception betas in a way that explains the decoder collapse. Quantified in
  the mechanism decomposition (§6).

- **C3M-H2 — Low-capacity session alignment restores VISION decoding (PRIMARY GATE).** A
  transformation fit *without imagery labels* restores stimulus-specific decoding on
  **held-out NSD-Imagery vision targets**.

- **C3M-H3 — Alignment is content-independent.** Any improvement must not rely on target
  identity memorization; it must generalize to held-out target identities and must not be
  reproduced by a matched random transform.

- **C3M-H4 — Aligned imagery transfer (CONDITIONAL on H2 PASS only).** Applying the frozen
  session alignment to imagery betas and then the frozen perception decoder improves imagery
  retrieval relative to (1) the strict C3 identity/no-alignment baseline, (2) a matched random
  alignment, and (3) a mean-shift-only baseline.

---

## 3. Alignment supervision hierarchy

Alignment methods are split into two families by what information they are allowed to see.
This boundary is **frozen prospectively** and is the crux of the leakage discipline.

### Family A — UNSUPERVISED / TARGET-BLIND
Allowed: fMRI distributions, run/session identity, ROI coordinates, perception-training
statistics (the frozen decoder's `voxel_mean`/`voxel_std`).
**Forbidden:** imagery target identity, imagery cue identity, imagery CLIP embeddings, and the
identity of any final vision-test target.

- **M0** identity (no-op baseline == strict C3).
- **M1** global / per-voxel mean correction.
- **M2** per-voxel affine (shift + scale).
- **M3** shrinkage covariance alignment / CORAL.
- **M4** low-rank distribution alignment.

### Family B — VISION-CALIBRATED
May use a **training subset of NSD-Imagery VISION trials and their known seen targets** to fit
a session→session map. Still **forbidden** from using any imagery-state trial or any held-out
vision target.

- **M5** ridge voxel-space session map.
- **M6** regularized low-rank session map.
- **M7** orthogonal / Procrustes alignment (where dimensionally appropriate).

All Family-B methods are evaluated on **HELD-OUT VISION TARGETS** (§5). Never on held-out
repeats of a target that was seen during alignment fitting.

**Primary scientific generalization unit: held-out target identity.**

---

## 4. Critical anti-leakage rule (SEALED IMAGERY)

Imagery target labels are **SEALED** throughout alignment development.

- Do **not** compute any imagery MRR while developing C3M-H1/H2/H3.
- Do **not** select method, rank, regularization, ROI, centering strategy, or covariance
  shrinkage using imagery performance. **Method selection uses held-out VISION performance
  only.**
- Exactly **one** primary alignment specification is frozen (method + all hyperparameters +
  MEOI metric-of-interest) based on vision performance, and its identity + config hash is
  written to `results/c3m_alignment_seal.json` **before any aligned imagery result exists**.
- Only after that seal is written may imagery be unsealed (§8).

The seal is fail-closed: the imagery-unblinding runner refuses to run unless a valid
`c3m_alignment_seal.json` exists and its self-hash verifies.

---

## 5. Vision splits (held-out-target evaluation)

There are 12 ground-truth image targets: **6 simple (Set A)** and **6 complex (Set B)**.
Primary alignment evaluation emphasizes **Set B complex** targets (natural scenes; in-domain
for a natural-scene decoder). Set A simple (geometric bars/crosses) is reported **separately as
OOD**.

- Evaluation is **nested leave-one-target-out (LOTO)** — and, as a stricter secondary,
  **leave-two-targets-out (L2TO)** — over the 6 Set B target identities.
- No beta from a held-out target may enter: (a) transformation fitting, (b) any
  target-conditioned shift estimate, or (c) hyperparameter selection.
- **Unsupervised global statistics (Family A)** may use unlabeled vision-session betas only
  under the frozen rule that **no target information enters** — i.e. a global per-voxel mean
  over the pooled vision betas is permitted for M1/M2/M3/M4 because it is target-blind. This
  rule is fixed here, prospectively, and applies identically in every fold.
- The generalization unit is **target identity**, never a held-out repeat of a seen target.

---

## 6. Mechanism decomposition (C3M-H1)

For each of {core-NSD perception (reference), NSD-Imagery vision, NSD-Imagery imagery}, compare:

- **voxel-space:** per-voxel mean, per-voxel std, covariance eigen-spectrum, ROI-wise
  distributions, ncsnr-weighted shift.
- **decoder pre-normalization:** z-score distribution under the *frozen perception* stats,
  fraction of voxels outside the perception train range.
- **decoder output:** embedding norm, output mean vector, output covariance effective rank,
  pairwise cosine diversity, candidate-score entropy, dominant-candidate fraction.

Produce `results/c3m_shift_mechanism.json`.

### Counterfactual perturbation (mechanistic, NOT confirmatory)

1. **Inject** the measured NSD-Imagery session shift into held-out core-NSD perception betas.
   If this reproduces the same decoder-output collapse, that is strong mechanistic evidence
   that the shift *causes* the collapse.
2. **Remove** only that shift from NSD-Imagery vision betas. Check whether candidate diversity
   and retrieval return.

This is a perturbation analysis of the *collapse mechanism*, explicitly **not** confirmatory
imagery evidence and never reported as such.

---

## 7. Primary vision gate (frozen decision rule — MEOI frozen before results)

For every alignment method, on **held-out targets**, report: MRR, top-1, top-3, top-5,
median rank, true 2AFC, candidate entropy, dominant-candidate fraction, prediction-covariance
effective rank.

**A method FAILS even with a significant MRR if predictions remain degenerate.**

Primary success (VISION gate PASS) requires **ALL** of:

1. meaningful improvement over identity (M0),
2. **no** prediction collapse (dominant-candidate fraction not in the degenerate regime),
3. true 2AFC > 0.5,
4. improvement holds on **held-out targets**,
5. a **matched random transform** of the same capacity does **not** reproduce it.

The **MEOI** (primary metric-of-interest = held-out-target Set B MRR, with the four
guard conditions above) is frozen in `results/c3m_protocol_decision.json` **before** any
vision-alignment result is computed. A method is never selected merely because p < 0.05.

---

## 8. Imagery unblinding (only if the vision gate passes)

Only if the cross-session VISION gate passes is exactly **one** primary alignment pipeline
frozen and the imagery labels unsealed. The frozen pipeline is applied strictly:

```
imagery beta → frozen C3M session alignment → frozen C3 perception preprocessing
             → frozen C3 decoder → frozen 12-target CLIP retrieval
```

No imagery fitting. **The C3 decoder weights are never re-trained or modified.**

- **Primary imagery subset:** Set B complex, 96 trials, 6 targets × 16 repeats.
- **Secondary:** Set A simple (OOD).
- **Primary exact null:** 6! = 720 target-identity permutations, preserving all 16 repeats of
  each stimulus.
- Report: MRR, exact p, Δ vs strict C3 baseline, 2AFC, top-k, median rank, candidate entropy,
  collapse diagnostic.
- **A significant MRR with degenerate predictions remains invalid** (same rule as C3).

---

## 9. Multi-participant expansion (participant-level inference)

subj02, subj05, subj07 remain **prospectively eligible**. subj01's C3M outcome does **not**
determine their inclusion. Because local/ephemeral storage is insufficient to hold every raw
session (~40 GB/subject), acquisition uses **rolling extraction**:

```
for each perception session:
    download → certify → SHA-256 → extract frozen ROI union → hash extracted matrix
    → persist provenance → remove raw temporary object only once re-downloadability is proven
    → next session
```

Preserve the ROI union for: nsdgeneral, V1, V2, V3, hV4, ventral, lateral, parietal, and a
low-ncsnr control. This reduces permanent storage from ~40 GB/subject to a compact ROI
representation. Reproduce strict H1 and the C3M vision-alignment analysis for every
prospectively eligible subject. **Population inference remains participant-level** — subj01
alone never licenses a population claim.

---

## 10. Decision rules

- **Outcome A** — vision alignment PASS **and** aligned imagery transfer PASS:
  `C3M_CROSS_SESSION_ALIGNMENT = PASS`, `C3M_ALIGNED_IMAGERY_TRANSFER = PASS`,
  `C3M = COMPLETE_WITH_ALIGNED_IMAGERY_TRANSFER`. **Still do NOT begin C4** — require
  multi-participant replication first.
- **Outcome B** — vision alignment PASS but imagery still NULL_SUPPORTED:
  `C3M = COMPLETE_WITH_STATE_SPECIFIC_IMAGERY_NULL`. Scientifically strong: session shift
  fixed, seen-image decoding recovered, imagery content still fails to transfer.
- **Outcome C** — vision alignment cannot be restored:
  `C3M = COMPLETE_WITH_UNRESOLVED_SESSION_NONSTATIONARITY`.
- **Outcome D** — alignment works on seen targets but not held-out targets:
  `C3M = FAILED_BY_TARGET_MEMORIZATION`.
- **Outcome E** — leakage or post-hoc method selection detected:
  `C3M = FAILED_BY_LEAKAGE_OR_SELECTION_BIAS`.

---

## 11. Prohibitions

Do **NOT**: generate images; connect embeddings to diffusion; start C4; tune against imagery
results; change the frozen C3 decoder weights; train an imagery decoder; claim mind reading;
claim population evidence from subj01; adopt Spera et al.'s method and relabel it as novel.

---

## 12. Novelty posture

No novelty is claimed until the literature audit (`C3M_NOVELTY_AND_OVERLAP.md`) supports it.
"Functional alignment for imagery" is **not** claimed as novel — Spera et al. 2026 already
performs latent functional alignment on NSD-Imagery. Any C3M contribution must instead come
from the specific combination that survives the audit (target-blind session calibration,
vision-first falsification, prediction-collapse detection, held-out-target alignment
evaluation, mechanistic perturbation reproducing the collapse, participant-level validation,
reconstruction-readiness gating).
