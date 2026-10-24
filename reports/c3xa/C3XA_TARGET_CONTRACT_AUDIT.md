# C3XA — DIR (ds001506) Imagery Target-Contract Audit

Authoritative audit of the Deep Image Reconstruction imagery target contract, to correct the C3X
qualification (which treated all 26 bdpy `Label` values as imagery contents and used only
perceptionNaturalImageTest as the matched control). **No geometry / no reliability outcome is used
to infer this contract.**

## Authoritative sources (priority order, access 2026-08-28)
1. **Shen, Horikawa, Majima, Kamitani (2019) PLOS Comput Biol 15(1):e1006633** (open access,
   doi:10.1371/journal.pcbi.1006633) — Methods "Mental imagery experiment".
2. OpenNeuro **ds001506** README + `task-imagery` events.tsv (event_type/category_id semantics).
3. KamitaniLab **DeepImageReconstruction** repo (`7_reconstruct_imagined_image.py`).
4. Figshare preprocessed release **DOI 10.6084/m9.figshare.7033577.v16** (bdpy metadata, decoded
   feature labels).

## Certified contract (verbatim paper)
- "subjects were required to visually imagine (recall) **one of 25 images** selected from those
  presented in the test natural image and artificial shape sessions ... (**10 natural images and 15
  artificial images**)."
- "The **26 blocks** consisted of **25 imagery trials and a fixation trial**, in which subjects were
  required to maintain a steady fixation **without any imagery**."
- Imagery block = 16 s (8 volumes), averaged after a 4 s (2-volume) hemodynamic shift.

## Verified from released data
- bdpy imagery `dataset` = **520 samples × voxels**; `Label`==`category_index` is a single column
  with **26 unique values (1–26), each appearing exactly 20 times** (one per run × 20 runs). `vmap`
  is empty ⇒ **Label is a condition-local ordinal, NOT a global stimulus identity**.
- OpenNeuro imagery events: each run has an initial rest (event_type −1) then **26 imagery blocks**
  (trial_no 2–27), category_id 1–26, one each; imagery period = event_type 2 (8 s). ⇒ 20 runs × 26
  = 520 = **500 target + 20 fixation** (one fixation block per run).
- Decoded-feature release enumerates **Img0001…Img0026** (26 items) ⇒ bdpy Label k ↔ Img{k:04d}.
- Behavioral `evaluation` (vividness) does NOT isolate the fixation block (all 26 category_ids carry
  ordinary 2–5 ratings), so fixation is identified from the target-contract ordering, not behavior.

## Family / fixation assignment (certified basis)
The KamitaniLab **official** reconstruction script `7_reconstruct_imagined_image.py` reconstructs
example imagery targets `Img0001,0003,0005,0008,0009,0010` (all ≤ 10) and `Img0020,0021,0022`
(in 11–25), consistent with the standard DIR convention and the paper's 10+15+1 contract:
- **Img0001–Img0010 (Label 1–10) = 10 NATURAL images** (matched to perceptionNaturalImageTest).
- **Img0011–Img0025 (Label 11–25) = 15 ARTIFICIAL shapes** (matched to perceptionArtificialImage).
- **Img0026 (Label 26) = FIXATION** (no imagery; excluded from all reliability).

**Certification level:** the *contract* (25 = 10 natural + 15 artificial + 1 fixation, 26 blocks) is
paper-certified; the *ordering* (natural 1–10 / artificial 11–25 / fixation 26) is certified by the
KamitaniLab official code + paper figure, NOT by numeric-label equality and NOT by any neural
result. The released bdpy does not expose per-target exact image filenames, so matched-perception
reliability is computed at the **family-condition** level (natural = perceptionNaturalImageTest,
artificial = perceptionArtificialImage), which is a conservative, appropriate matched control.

## Terminology (frozen)
Deep Image Reconstruction imagery cues refer to **specific memorized visual IMAGE exemplars**
(10 natural photographs + 15 artificial shapes), **NOT** semantic object categories. The Generic
Object Decoding (category) imagery paradigm is a **different study** and is **not** used here.
