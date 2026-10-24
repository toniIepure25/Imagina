# C3XC — Frozen D2 Contract Extraction (Rule 1)

Extracted from committed C3X/C3XA/C3XB artifacts **before** inspecting any D2 neural outcome.
This does NOT redefine D2; it quotes the repository's prospectively frozen record.

## Source artifacts (quoted)
- `results/c3x/c3x_candidate_inventory.json` → `d2`:
  `{"dataset":"ds005191 (Mind Captioning)","access":"PUBLIC OpenNeuro CC0","note":"acquired ONLY if
  D1 prospectively fails; semantic/video-recall paradigm with verbal-cue confound"}`
- `results/c3x/c3x_ranking.json` (FROZEN_BEFORE_ANY_NEURAL_RELIABILITY_OUTCOME):
  `D2_ds005191_MindCaptioning = "MEDIUM_PRIORITY"`; rationale D2 = *"public and rich, but imagery is
  RECALL of dynamic VIDEO with verbal preparation cues (semantic/cue confound); paradigm not directly
  comparable to static-image geometry. Evaluated ONLY if D1 prospectively fails."*; conditional_rule =
  *"inspect D2 neural outcomes ONLY if D1 does not reach DATASET_RELIABILITY_PASS; never to pick
  whichever dataset looks better (dataset-level outcome fishing forbidden)."*
- `results/c3x/c3x_decision.json`: `d2_inspected=false`, `d2_status="NOT INSPECTED (D1 qualified ->
  dataset hunting stops; D2 remains a future external replication/generalization dataset)"`.
- `reports/c3xb/c3xb_protocol_seal.json` → `d2_fallback`:
  `{"name":"Mind Captioning","openneuro":"ds005191","version":"1.0.2","frozen_before_god_outcomes":true,
  "inspect_only_if_god_fails":true,"do_not_inspect_if_god_qualifies":true}`
- `results/c3xb/c3xb_scope_registry.json` → `MindCaptioning`:
  modality `"natural-scene/sentence imagery (D2 fallback candidate)"`; role `"C3XB D2 fallback IF GOD
  fails"`; `imagery_qualified="NOT_INSPECTED"`; authorizes `"nothing yet; inspected only if GOD fails"`;
  claim_boundary `"Do NOT inspect if GOD qualifies. Has its own cue-only confound to control."`
- `results/c3xb/c3xb_decision.json` → `d2_fallback_if_fail` with `inspect=true` (C3XB decision =
  `C3XB_GOD_CATEGORY_IMAGERY_FAIL`, so the D2 inspection precondition is satisfied).

## Exact existing rule
1. **Ordering / trigger (SATISFIED):** D2 neural outcomes may be inspected ONLY because the prior
   qualification (C3XB / GOD) reached FAIL, not PASS. `c3xb_decision.json.decision =
   C3XB_GOD_CATEGORY_IMAGERY_FAIL`. Dataset-level outcome fishing is forbidden; D2 is inspected because
   it is the next ranked fallback, not because it "looks better".
2. **Permitted imagery scope (frozen description):** D2 imagery = **recall of dynamic VIDEO with verbal
   preparation cues** — a *semantic / video-recall / event* paradigm with an explicit **verbal-cue
   confound**. The frozen record states D2 is **NOT** comparable to static-image geometry. Therefore
   C3XC may qualify D2 only for a **semantic/event (video-recall) internally-generated content** scope —
   never static-image, category, or exact-image scope. Phase 2 must establish the honest content
   contract empirically (no terminology inflation).
3. **Required statistic / gate (INHERITED, not re-specified for D2):** D2 was ranked and frozen as a
   member of the C3X-family qualification program. No D2-specific estimator or thresholds were frozen;
   D2 inherits the frozen C3X-family reliability methodology:
   - **Estimator:** split-half reliability = Spearman-Brown-corrected Pearson r of concatenated
     content-mean multivoxel patterns across INDEPENDENT acquisition halves (`c3x_reliability.py`,
     sha256 `623c9236…`, frozen; and its run-pair specialization `c3xb_reliability.py`, sha256
     `33d483a1…`). The independent unit is **run/session-disjoint**; a run-PAIR unit is used only if D2
     has the same 2-run category-balancing structure as GOD (to be certified in Phase 1, else the
     general run-disjoint form applies).
   - **Inference:** permutation null ≥1000 (permute content labels within the independence structure);
     non-straddling hierarchical bootstrap ≥1000 (a physical trial never on both sides); split seeds
     base=20260901, +100, +200; N_REP_POINT=200.
   - **Subject gate (frozen `subject_reliability_gate`):** PASS iff R_I>0 AND perm p<0.05 AND bootstrap
     CI lower>0 AND min-over-seeds>0; else MARGINAL (R_I>0 but a criterion fails) or NOISE_FLOOR (R_I≤0).
   - **Dataset gate (frozen `dataset_gate`, ≥2 rule):** ≥2 subjects with imagery PASS AND matched
     perception PASS AND acceptable cue control → dataset qualified; exactly 1 → PROMISING/LIMITED;
     0 → FAIL; contract/cue unresolvable → BLOCKED.
   - **Perception positive control:** matched-perception reliability R_P (same estimator, matched
     content), attenuation A = R_I/R_P.
   - **Cue control:** vocabulary CUE_CLEAN / CUE_CONTROLLED / CUE_AMBIGUOUS / CUE_FAIL; primary
     reliability admissible only if CLEAN/CONTROLLED, else BLOCKED_BY_CUE_PROVENANCE. D2's own "verbal-
     cue confound" plus the later target-video presentation are the specific risks to audit.
   - **Integrity:** no geometry, no reconstruction, no C4; no raw neural data committed; seal before
     outcomes; frozen estimator unchanged (accelerator only if proven equivalent).
4. **Exact permitted downstream authorization (frozen):** the frozen record grants D2 **no pre-named
   downstream gate**. `scope_registry` states D2 "authorizes: nothing yet"; `c3x_decision` frames it as
   "a future external replication/generalization dataset". C3XB's FAIL means **no category/static-image
   geometry (C3XR / C3XR-CAT) is authorized by anything**, and D2 (semantic/event scope) cannot rescue
   or substitute for that. Therefore the MOST a C3XC PASS can do is authorize a **subsequently-
   prespecified, D2-content-scoped (semantic/event, video-recall) reliability-bounded analysis** — it
   does NOT authorize C3XR, C3XR-CAT, reconstruction, captioning, or C4. A FAIL/BLOCKED authorizes
   nothing. This conservative bound is used verbatim in the C3XC seal and decision.

## Ambiguity assessment
The **qualification mechanics** (estimator, inference, subject gate, dataset gate, cue vocabulary,
perception control, integrity) are unambiguous by inheritance from the frozen C3X-family. The only
under-specified element is the **downstream authorization label**, which the frozen record itself
bounds to "nothing yet / future replication". This is resolved **conservatively** (a PASS authorizes at
most a future D2-scoped prespecified analysis; never C3XR/reconstruction/C4) rather than by inventing a
new authorization level. Accordingly the contract is **NOT** declared
`C3XC_BLOCKED_D2_CONTRACT_AMBIGUOUS`; C3XC proceeds under the inherited contract with the conservative
downstream bound above.

A genuine BLOCK is still returned later if any Phase-0/1 STOP condition holds (dataset version
uncertifiable, raw/preprocessed provenance inconsistent, imagery targets unmappable, required
independent repetitions absent, cue/target-leakage invalidates the imagery window, ROI contract
unreconstructable, or the frozen statistic cannot be computed as defined).
