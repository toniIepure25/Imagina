"""V7.7 — Defense Presentation & Demo Finalization Pack.

Final 12-slide content, 12-min script, live demo script,
50 defense flashcards, committee handout, frontend export.
Reads existing artifacts only. No experiments.
"""

import json
import os
import sys
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
FRONTEND = os.path.join(BASE, "..", "..", "..", "demo_thesis")


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.eeg_v77_defense_pack")
    p.add_argument("--mode", default="all",
                   choices=["script", "slides", "demo", "cards", "handout", "frontend", "all"])
    p.add_argument("--output-prefix", default="eeg_v77")
    return p


def _safety():
    return {"analysis_mode": "experimental_hypothesis_only",
            "not_for_scientific_claims": True, "production_valid": False,
            "production_unlock_allowed": False, "no_raw_eeg_exposed": True}


def _save_md(fn, content):
    with open(os.path.join(EXPORTS, fn), "w") as f:
        f.write(content)


def _save_json(fn, data):
    with open(os.path.join(EXPORTS, fn), "w") as f:
        json.dump({**_safety(), "tool": fn.replace(".json", ""),
                    "generated_at": datetime.now(timezone.utc).isoformat(), **data},
                  f, indent=2, default=str)


def run_script():
    md = """# Final Defense Presentation Script (10-12 minutes)

## 1. Opening Hook — 30s
**(Slide 1 — Title)**

Good morning. My thesis examines an uncomfortable truth in EEG research:
a classifier can appear to decode imagined movement with high accuracy when
it is merely recovering the experimental structure — trial order, stimulus
identity, event codes — without any genuine neural signal detection.

---

## 2. Research Question — 30s
**(Slide 2 — Motivation)**

Can we build a pipeline that catches these metadata confounds before they
become false claims, and then establish a defensible baseline on a clean
dataset? That is the question I set out to answer.

---

## 3. OpenMIIR Initial Direction — 45s
**(Slide 3)**

I began with OpenMIIR, a public dataset of 10 subjects listening to and
imagining music. MATLAB source code confirmed the trigger semantics:
trigger 1 = perception, trigger 2 = cued imagery, trigger 3 = uncued
imagery, trigger 4 = noise. The event codes (11 through 44) appeared to
encode stimulus group and trigger type.

Initial SSL encoders achieved 0.93 to 0.96 balanced accuracy under
leave-one-subject-out evaluation. These looked like strong results.

---

## 4. The High-Score Trap — 45s
**(Slide 4 — The Big Reveal)**

But I ran a simple test that changed everything. I built a classifier
that uses ONLY metadata — subject ID, stimulus group, event code. No EEG
at all.

Combined metadata achieved **1.0 balanced accuracy** across ALL six
condition tasks. Event code alone achieved 1.0 within stimulus groups.
The 0.93-to-0.96 SSL scores were learning trial structure, not neural
activity.

*(Pause. Let this sink in.)*

---

## 5. Forensic Audit — 45s
**(Slide 5 — Negative Control)**

I redesigned 8 tasks to control metadata — within-stimulus-group
comparisons, balanced sampling. All 8 failed. The event codes structurally
encode condition labels in OpenMIIR's experimental design.

I reclassified OpenMIIR as a negative-control dataset. This was NOT a
failure. It proved that the confound-audit framework correctly identifies
structurally confounded tasks.

---

## 6. Dataset Replacement — 30s
**(Slide 6)**

I selected PhysioNet EEG Motor Movement/Imagery Database — 109 subjects,
64 EEG channels, motor execution and imagery tasks. I defined a metadata
preflight protocol that separates label-source metadata from nuisance
metadata.

The left/right fist motor imagery task passed: nuisance metadata (run ID,
trial index) achieves only 0.48 — well below the 0.60 threshold.

---

## 7. Preflight & Train Gate — 30s
**(Slide 7)**

The key insight: event codes DEFINE the labels. They are not a confound.
Run ID, trial index, file ID — those are the nuisance metadata that must
NOT predict the label. Training is blocked unless nuisance baselines
stay near chance. PhysioNet passed this gate.

---

## 8. Final Baseline — 60s
**(Slide 8)**

The validated method is **filter-bank log-power**. Per-channel FFT log-power
in 5 frequency bands (4-30 Hz), concatenated, classified with
LogisticRegression under leave-one-subject-out CV.

This is explicitly NOT CSP. I tested true MNE CSP — it achieved only
0.482, near chance. True FBCSP was computationally constrained and not
validated. I report this honestly.

---

## 9. Final Result — 45s
**(Slide 9 — The Number)**

| Metric | Value |
|--------|-------|
| Method | Filter-bank log-power |
| Score | 0.628 |
| 95% CI | [0.581, 0.677] |
| p-value | < 0.001 |
| Subjects | 15 |
| CV | LOSO |

This beats the metadata baseline (0.482) by a large margin and passes
permutation testing with p<0.001.

---

## 10. CSP/FBCSP Correction — 30s
**(Slide 10)**

I attempted CSP and FBCSP across multiple versions. An MNE API bug was
discovered and fixed. True CSP (0.482) did not beat the baseline. True
FBCSP did not complete. I label the method honestly: filter-bank log-power,
NOT CSP/FBCSP. The label correction is itself a contribution.

---

## 11. What This Proofs — 30s
**(Slide 11 — Claim Ledger)**

This project proves:
- Metadata baselines can invalidate confounded EEG tasks
- Filter-bank log-power captures motor-imagery signal above chance
- A defensible score is achievable when confounds are controlled

It does NOT prove:
- Production BCI, clinical validity, real-time control
- Mind-reading, dream decoding, imagery decoding
- CSP/FBCSP superiority

---

## 12. Limitations & Contribution — 60s
**(Slide 12 — Final)**

Limitations: N=15, single dataset, binary task, not production-ready.

But the strongest contribution is not the 0.628. The strongest contribution
is the refusal to treat a high score as scientific evidence until metadata
baselines have been defeated. The validation methodology is what future
EEG work should adopt.

Thank you. I welcome your questions.
"""
    _save_md("eeg_v77_final_presentation_script.md", md)
    _save_json("eeg_v77_final_presentation_script.json", {"duration": "10-12 min", "sections": 12})
    print("Presentation script: 12 sections", file=sys.stderr)


def run_slides():
    slides = [
        {"n": 1, "title": "Confound-Aware EEG Motor Imagery Validation",
         "subtitle": "When a classifier looks right but for the wrong reasons",
         "bullets": ["EEG motor imagery decoding", "Metadata confounds in published results",
                     "Two datasets, one validation framework"],
         "notes": "Opening hook: high scores can be empty. Start confident.",
         "figure": "eeg_v74_final_method_comparison.png",
         "risk": "None", "takeaway": "We build a pipeline that catches confounds before they become false claims."},
        {"n": 2, "title": "Why EEG Decoding Needs Metadata Baselines",
         "subtitle": "The hidden confound problem",
         "bullets": ["Classifiers exploit any structure that distinguishes classes",
                     "Trial order, stimulus IDs, event codes — all can leak the label",
                     "Metadata-only baseline is the simplest validity test"],
         "notes": "Framed as a universal problem, not specific to our work.",
         "figure": "openmiir_v51_old_vs_metadata_baseline.png",
         "risk": "None", "takeaway": "If metadata predicts your label, you are not decoding neural activity."},
        {"n": 3, "title": "OpenMIIR: Why It Looked Promising",
         "subtitle": "10 subjects, music perception/imagery, 52 event codes",
         "bullets": ["MATLAB confirmed trigger 1=perception, 2=cued, 3=uncued, 4=noise",
                     "SSL encoders reached 0.93-0.96 under nested LOSO",
                     "These looked like strong, publishable results"],
         "notes": "Set up expectations. The twist is coming in Slide 4.",
         "figure": None, "risk": "Do NOT claim these scores were valid.",
         "takeaway": "High EEG scores without metadata baselines are uncalibrated measurements."},
        {"n": 4, "title": "Forensic Audit: The Metadata Trap",
         "subtitle": "Combined metadata baseline = 1.0 across ALL tasks",
         "bullets": ["Subject ID + stimulus group + event code = 1.0 accuracy (no EEG)",
                     "Event code ALONE = 1.0 within stimulus groups",
                     "8 redesigned tasks — ALL failed metadata validation (V5.0)"],
         "notes": "This is the key slide. Speak slowly. Let them absorb 1.0=1.0.",
         "figure": "openmiir_v51_old_vs_metadata_baseline.png",
         "risk": "None", "takeaway": "Trivial metadata recovers the label perfectly. EEG is irrelevant."},
        {"n": 5, "title": "OpenMIIR: Negative Control, Not Failure",
         "subtitle": "Reclassified as calibration case for the audit framework",
         "bullets": ["OpenMIIR proved the audit framework works",
                     "Valuable for representational analysis and confound methodology",
                     "A negative result that strengthens, not weakens, the contribution"],
         "notes": "Pivot from 'we failed' to 'we proved it works'. Confident, not apologetic.",
         "figure": "openmiir_v51_project_status_flow.png",
         "risk": "None", "takeaway": "OpenMIIR proved that metadata baselines detect real confounds."},
        {"n": 6, "title": "Dataset Replacement: PhysioNet EEGMMI",
         "subtitle": "109 subjects, 64 channels, motor execution + imagery",
         "bullets": ["Selected after V6.0-V6.2 candidate evaluation",
                     "Left/right fist imagery task passed train gate",
                     "Nuisance metadata baseline = 0.48 (< 0.60 threshold)"],
         "notes": "Emphasize the corrected preflight protocol.",
         "figure": None, "risk": "None",
         "takeaway": "PhysioNet passes preflight where OpenMIIR failed."},
        {"n": 7, "title": "Metadata Preflight & Train Gate",
         "subtitle": "Event code = label source (defines y), NOT a confound",
         "bullets": ["Label-source metadata defines y — not tested as confound",
                     "Nuisance metadata (run ID, trial index, file ID) is the confound target",
                     "Training allowed only when combined nuisance baseline <= 0.60"],
         "notes": "V6.1 corrected protocol. This distinction is important.",
         "figure": None, "risk": "Make sure audience understands label-source vs. nuisance.",
         "takeaway": "Event codes are NOT automatically confounds. Nuisance metadata is the real target."},
        {"n": 8, "title": "Final Baseline: Filter-Bank Log-Power",
         "subtitle": "NOT CSP/FBCSP — honest labeling is deliberate",
         "bullets": ["Per-channel FFT log-power in 5 bands (4-30 Hz)",
                     "LogisticRegression/LinearSVC under LOSO",
                     "True MNE CSP (0.482) does NOT beat this baseline",
                     "True FBCSP not validated — honest label maintained"],
         "notes": "Emphasize deliberate honest labeling. It is a contribution.",
         "figure": "eeg_v74_final_method_comparison.png",
         "risk": "Do NOT call this CSP or FBCSP.",
         "takeaway": "Frequency features outperform spatial filters. Label it honestly."},
        {"n": 9, "title": "Final Result",
         "subtitle": "0.628 balanced accuracy [0.581, 0.677], p<0.001, N=15, LOSO",
         "bullets": ["Method: filter-bank log-power", "Score: 0.628", "95% CI: [0.581, 0.677]",
                     "p-value: <0.001", "Subjects: 15", "CV: leave-one-subject-out"],
         "notes": "Put the comparison table on this slide. Metadata=0.48, Quality=0.49.",
         "figure": "eeg_v74_final_method_comparison.png",
         "risk": "Do NOT call 0.628 'high'. It is 'above chance with strong significance'.",
         "takeaway": "0.628 is above chance, beats metadata, but is not production-grade."},
        {"n": 10, "title": "CSP/FBCSP Correction History",
         "subtitle": "V7.0-V7.3: tested, debugged, honestly reported",
         "bullets": ["V7.0-7.1: MNE CSP API bug discovered (verbose in constructor)",
                     "V7.2: API fixed; CSP runs correctly",
                     "V7.3: True CSP = 0.482 (near chance); FBCSP not completed",
                     "V7.4: Final label lock — NOT CSP/FBCSP"],
         "notes": "Show the rigorous debugging process. It adds credibility.",
         "figure": None, "risk": "None",
         "takeaway": "CSP was tested, failed to beat baseline. We report this honestly."},
        {"n": 11, "title": "Claim Ledger: Allowed vs. Forbidden",
         "subtitle": "6 supported, 2 invalidated, 2 forbidden — deliberate discipline",
         "bullets": ["SUPPORTED: exploratory MI baseline, metadata preflight, honest labeling",
                     "FORBIDDEN: production BCI, clinical, mind-reading, dream decoding",
                     "Thesis positioning: validation methodology as contribution"],
         "notes": "This slide is the ethical core. End strong.",
         "figure": "eeg_v74_claim_status_summary.png",
         "risk": "None",
         "takeaway": "Scientific honesty means knowing what you cannot claim."},
        {"n": 12, "title": "Contribution & Future Work",
         "subtitle": "The methodology, not the score, is the contribution",
         "bullets": ["Metadata preflight as universal first step for EEG decoding",
                     "Honest labeling prevents false claims",
                     "Future: more subjects, multi-class, cross-dataset",
                     "SSL only as exploratory comparison after classical baselines"],
         "notes": "End with confidence and honesty.",
         "figure": None, "risk": "None",
         "takeaway": "The validation framework is the lasting scientific contribution."},
    ]
    md = "# Final Defense Slide Content\n\n"
    for s in slides:
        md += f"## Slide {s['n']}: {s['title']}\n"
        md += f"**Subtitle**: {s['subtitle']}\n\n"
        for b in s["bullets"]:
            md += f"- {b}\n"
        md += f"\n**Speaker notes**: {s['notes']}\n"
        md += f"**Figure**: {s['figure'] or 'N/A'}\n"
        md += f"**Risk**: {s['risk']}\n"
        md += f"**Takeaway**: {s['takeaway']}\n\n---\n\n"
    _save_md("eeg_v77_final_slide_content.md", md)
    _save_json("eeg_v77_final_slide_content.json", {"n_slides": 12})
    print("Slide content: 12 slides", file=sys.stderr)


def run_demo():
    md = """# Live Demo Script — Confound-Aware EEG Validation

## 1. Open Dashboard (30s)
*Narrate:* "This is the IMAGINA research dashboard showing the final
scientific status. OpenMIIR is flagged as a negative-control dataset.
PhysioNet EEGMMI is flagged as the valid replacement."

## 2. Show OpenMIIR Negative-Control Card (45s)
*Narrate:* "Click into OpenMIIR. Notice the status: 'invalid for condition
decoding'. The metadata confound is documented here — combined metadata
baseline = 1.0 accuracy. Eight redesigned tasks, all failed. This is
NOT a failure. It proves the audit works."

## 3. Show Metadata Confound Evidence (30s)
*Narrate:* "Here is the key forensic result. Event code alone achieves
1.0 accuracy within stimulus groups. The condition label is structurally
encoded in the experimental paradigm. No EEG is needed."

## 4. Show PhysioNet Baseline Card (30s)
*Narrate:* "Now switch to PhysioNet EEGMMI. The train gate is green —
allowed. The final validated baseline is filter-bank log-power at 0.628.
Notice the method label explicitly says: NOT CSP/FBCSP."

## 5. Show Final Claim Ledger (30s)
*Narrate:* "The claim ledger shows what we can and cannot say. Six
supported claims, two invalidated, two forbidden. Production BCI is
explicitly in the forbidden column."

## 6. Show Final Report (15s)
*Narrate:* "The final thesis report and one-page summary are available.
The project's primary contribution is the validation methodology, not
the score."

## 7. Close with Contribution (15s)
*Narrate:* "This project demonstrates that high EEG scores without
metadata baselines are uncalibrated. The pipeline catches confounds before
they become false claims. That is the lasting contribution."

## Fallback: No Frontend Available
- Open `eeg_v75_master_scientific_status.json` directly
- Open `eeg_v75_final_thesis_report.md` in a text editor
- Open `eeg_v74_final_method_comparison.json` for the comparison table
- Open `eeg_v76_examiner_qa_pack.md` if examiner asks questions

## What NOT to say during demo
- Never say "we decode imagined movement"
- Never say "this is BCI-ready"
- Never say "we achieved high accuracy"
- Never call the method CSP or FBCSP
- Never imply clinical or production validity
"""
    _save_md("eeg_v77_live_demo_script.md", md)
    _save_json("eeg_v77_live_demo_script.json", {"sections": 7, "has_fallback": True})
    print("Demo script: 7 sections with fallback", file=sys.stderr)


def run_cards():
    cards = [
        ("Why is 0.628 not higher?", "N=15, moderate sample, single dataset, no subject calibration. Above chance is sufficient for an exploratory baseline.", "low", "Above chance, scientifically valid, not ceiling."),
        ("Why should we trust PhysioNet if OpenMIIR failed?", "PhysioNet passed metadata preflight. Nuisance metadata baseline = 0.48 (chance). OpenMIIR was 1.0. The preflight protocol distinguishes clean from confounded.", "low", "Preflight separates clean from confounded."),
        ("Why did CSP fail?", "CSP achieved 0.482 (near chance) under LOSO. With 52 channels and 14 train subjects per fold, covariance estimation is noisy. Frequency features already capture motor-band signal.", "medium", "CSP was tested, did not beat baseline."),
        ("Why did you not use deep learning?", "SSL was tested (V6.6, 0.535). Classical FBCSP (0.614) was better. Deep learning should only be added after classical baselines are stable.", "medium", "Classical baselines beat SSL under fair LOSO."),
        ("Can this control a BCI?", "No. 0.628 is above chance but insufficient for reliable real-time BCI. The pipeline is a research validation protocol.", "high", "NOT production BCI. Research validation only."),
        ("Why 15 subjects, not 109?", "The full 109 may be used in future work. N=15 was chosen to keep training/validation runtime manageable for this exploratory phase.", "low", "Scaling to N=30-109 is future work."),
        ("What makes metadata preflight different from feature selection?", "Preflight tests whether the label prediction task is even valid before any EEG model is trained. Feature selection is done after training within folds.", "medium", "Preflight gates validity. Feature selection follows."),
        ("Is filter-bank log-power the same as FBCSP?", "No. FBCSP applies CSP spatial filters within each frequency band. Filter-bank log-power computes per-channel band energy without any spatial filter.", "high", "NOT CSP/FBCSP. Honest labeling is deliberate."),
        ("What is the main contribution?", "The validation methodology, not the score. Metadata preflight, task invalidation, honest labeling, transparent claim discipline.", "low", "Methodology over score."),
        ("Would more subjects improve the score?", "Likely yes. More subjects mean more stable LOSO folds and better generalization estimates. But confound-free methodology must remain.", "low", "Scale subjects, keep methodology."),
        ("Why is event_code not a confound in V6.1+?", "Event codes DEFINE the task labels (T1=left, T2=right). They are label-source metadata, not model features. We test nuisance metadata instead.", "high", "Label-source vs. nuisance distinction is critical."),
        ("Could you have fixed CSP?", "The API bug was fixed. CSP runs. But even with correct API, CSP (0.482) does not beat log-power (0.628). The limitation is not software — it's the data.", "medium", "CSP was fixed, tested, honestly reported."),
        ("Why report CSP failure so prominently?", "Because hiding negative results is exactly what confound-aware research fights against. CSP's failure is part of the evidence.", "low", "Honest reporting is a contribution."),
        ("Would Riemannian methods work better?", "Maybe. Riemannian baselines were attempted (V6.5, 0.555, p=0.02) but did not exceed filter-bank log-power (0.614 at the time).", "medium", "Riemannian was tested, did not beat baseline."),
        ("Is this project a success?", "Yes. It proved that metadata baselines catch confounds, demonstrated honest labeling, and established a defensible exploratory baseline.", "low", "Yes — methodology contribution, not score."),
        ("What would make the claim stronger?", "Independent dataset replication, N>30, multi-class tasks, pre-registered analysis, held-out-session validation.", "low", "Replication cements the methodology."),
        ("Did you consider multi-class motor imagery?", "The train gate for task_vs_rest_imagery also passed. Multi-class extension is future work but requires balanced class counts.", "low", "Binary task valued for scientific clarity."),
        ("How long did the project take?", "V1 through V7.7 across multiple phases: confound discovery (V4-V5), dataset replacement (V6), classical baselines (V6-V7), and finalization (V7.4-V7.7).", "low", "Roughly V1 through V7.7 iterative validation."),
        ("What would you tell a new EEG researcher?", "Run metadata baselines first. Test whether subject ID, trial index, or event codes predict your labels. Do not train a single model before this check.", "low", "Metadata baselines first, always."),
        ("Is this thesis-ready?", "Yes. V7.6 provides a complete thesis chapter. V7.7 provides defense materials, 35 Q&A questions, and a one-page summary.", "low", "V7.6 + V7.7 = complete thesis defense pack."),
        ("Is OpenMIIR useless now?", "No. It is the negative control that calibrates the audit framework. It remains valuable for representational analysis and methodology demonstration.", "low", "Negative control is scientifically valuable."),
        ("Why not use both datasets for the thesis?", "I do. OpenMIIR demonstrates confound detection. PhysioNet demonstrates valid baseline establishment. Both are essential to the narrative.", "low", "Both datasets — one for validity, one for invalidity."),
        ("What does p<0.001 mean in context?", "After 200 label permutations under LOSO, no null sample exceeded the observed 0.628. The result is highly unlikely under the null hypothesis.", "low", "Strong statistical evidence against chance."),
        ("Is 0.628 really balanced accuracy?", "Yes. Balanced accuracy = (sensitivity + specificity) / 2. Robust to class imbalance.", "low", "Balanced accuracy is the standard metric."),
        ("Why not report plain accuracy?", "Balanced accuracy prevents inflated scores from class imbalance. It is the standard in EEG classification literature.", "low", "Balanced accuracy is more informative."),
        ("Did you use any external data?", "Only public datasets: OpenMIIR (GitHub) and PhysioNet EEGMMI (physionet.org). No proprietary or subject-identifiable data.", "low", "Public data only."),
        ("Is the code available?", "Yes, in the IMAGINA backend repository. All analysis scripts, preflight protocols, and benchmark CLIs are version-controlled.", "low", "Code is open and version-controlled."),
        ("What is the next step after this thesis?", "Scale to N=30+, add multi-class MI, implement proper true FBCSP, test Riemannian geometry, cross-dataset validation.", "low", "Scale up with same methodology discipline."),
        ("Could a random forest beat 0.628?", "RandomForest was tested as a secondary classifier. LogisticRegression and LinearSVC performed comparably or better.", "low", "Linear models were sufficient."),
        ("Why is leave-one-subject-out the right protocol?", "It ensures no epoch from the test subject contaminates training. This prevents subject-specific confounds and tests generalization.", "low", "LOSO tests generalization across subjects."),
        ("Do you expect cross-dataset results to match?", "Not necessarily. Motor imagery datasets vary in paradigm, channel count, and subject pool. The methodology, not the number, should transfer.", "medium", "Methodology transfers; exact scores may vary."),
        ("What if PhysioNet scores drop with more subjects?", "Then the signal is fragile and I would report that honestly. The methodology is stronger than any single score.", "high", "Honest reporting is non-negotiable."),
        ("Why did SSL not work better?", "SSL (V6.6, 0.535) trained with only 675 epochs across 15 subjects. Limited data, simple encoder. Classical features already capture MI signal well.", "medium", "Data scale limits SSL. Classical suffices."),
        ("Is there any confound you missed?", "Session effects (all runs from same session per subject) and possible muscle artifact are acknowledged limitations. Future work should add session-held-out validation.", "high", "Session effects are acknowledged, not hidden."),
        ("Why is the thesis called 'confound-aware'?", "Because the primary contribution is detecting and preventing confounds, not achieving the highest decoding score.", "low", "Confound awareness is the thesis identity."),
        ("Would you build on this for a PhD?", "Yes. Scale to larger datasets, multi-class MI, proper FBCSP, Riemannian geometry, cross-dataset validation, pre-registered analysis.", "low", "This is a strong foundation for further work."),
        ("How do you respond to criticism of the score?", "A 0.628 that passes metadata preflight and maintains honest labeling is scientifically more valuable than a 0.96 that is confounded. Methodology over score.", "high", "Valid<br>confound-free > high confounded."),
        ("What is the one sentence a committee member should remember?", "Metadata baselines must be the first baseline for any EEG decoding task — before any model is trained.", "low", "Metadata baselines first, always."),
        ("What would you change if starting over?", "Test metadata baselines on Day 1. OpenMIIR would have been invalidated within the first week, saving months of SSL development on a confounded task.", "medium", "Start with auditor, not encoder."),
        ("Why did the project version go to V7.7?", "Iterative refinement: each version fixed a specific issue — confound detection (V4-V5), dataset replacement (V6), classical baselines (V6-V7), finalization (V7.4-V7.7).", "low", "Iterative refinement = scientific maturity."),
        ("Is IMAGINA the right name?", "IMAGINA was the code-name. The project outgrew it. The methodology is no longer tied to imagery decoding — it's a general EEG validation framework.", "low", "The methodology outgrew the project name."),
        ("Are the figures reproducible?", "Yes. All figures are generated by reproducible CLI scripts using fixed random seeds and deterministic pipelines.", "low", "Fully reproducible."),
        ("What software stack was used?", "Python, FastAPI, scikit-learn, MNE, NumPy, SciPy, PyTorch, Matplotlib. All dependencies are pinned in pyproject.toml.", "low", "Standard scientific Python stack."),
        ("Where should future EEG work start?", "With the V6.1 preflight protocol. Load your dataset. Define label-source vs. nuisance metadata. Run metadata baselines under LOSO. Block training if baselines exceed 0.60.", "low", "Start with preflight, always."),
        ("Is there anything you would retract?", "The V6.7 claim that filter-bank log-power was FBCSP. Corrected in V6.9. I would retract that one labeling error and have done so explicitly.", "medium", "V6.7 labeling error — corrected and owned."),
        ("What is your proudest scientific moment?", "When the metadata baseline for OpenMIIR returned 1.0. It was devastating for the score but validating for the methodology. I knew the framework worked.", "low", "The 1.0 was devastating for scores but validating for methodology."),
        ("If an examiner says 0.628 is too low?", "I would agree that it is moderate. But I would emphasize that it is above chance, beats metadata, passes permutation testing, and was achieved under honest labeling. A 0.628 that is trustworthy is worth more than a confounded 0.96.", "high", "Trustworthy moderate > confounded high."),
        ("Final question: should I trust EEG condition decoding?", "Only if the published result (a) reports metadata baselines, (b) uses LOSO or equivalent subject-out evaluation, (c) passes permutation testing, and (d) maintains honest labeling. If any of these is missing, demand them.", "high", "Trust EEG decoding only with full preflight."),
        ("Any final message?", "The most important methodological outcome is not the final balanced accuracy, but the validation discipline that must become standard in EEG research.", "low", "Methodology over metrics."),
        ("What about all the exploratory analysis?", "The project also tested SSL, subject-adversarial training, CSP, FBP-like methods, representational geometry. All of these are documented. None overshadow the validated baseline, but all add context. The project's breadth is a strength.", "low", "Exploratory breadth supports the main finding."),
    ]

    md = "# Defense Flashcards (50 cards)\n\n"
    for i, (q, a, risk, key) in enumerate(cards, 1):
        md += f"## Card {i}\n"
        md += f"**Q**: {q}\n\n"
        md += f"**A**: {a}\n\n"
        md += f"**Risk**: {risk} | **Key phrase**: {key}\n\n---\n\n"
    _save_md("eeg_v77_defense_flashcards.md", md)
    _save_json("eeg_v77_defense_flashcards.json", {"n_cards": len(cards)})
    print(f"Flashcards: {len(cards)} cards", file=sys.stderr)


def run_handout():
    md = """# Confound-Aware EEG Motor Imagery Validation
### Thesis Defense — Committee Handout

**Candidate**: [Your Name]
**One-sentence contribution**: A rigorous pipeline for detecting metadata
confounds in EEG decoding and establishing a defensible classical baseline.

**Dataset trajectory**:
- OpenMIIR → audited, found structurally confounded (metadata = 1.0)
- OpenMIIR → reclassified as negative-control calibration case
- PhysioNet EEGMMI → preflight passed, train gate allowed

**Final validated baseline**:
- Task: Left/right fist motor imagery (N=15, 675 epochs)
- Method: Filter-bank log-power (NOT CSP/FBCSP)
- Score: 0.628 balanced accuracy [95% CI 0.581, 0.677]
- p-value: <0.001 (LOSO permutation test)
- Beats metadata baseline (0.482) and quality baseline (0.494)

**Main methodological lesson**: Metadata baselines must be tested before
any EEG decoding result is interpreted as neural evidence. Event codes may
define labels (label-source metadata); run ID, trial index, and file ID
are the true confound targets (nuisance metadata).

**Allowed claims**: Exploratory classical EEG baseline for motor imagery;
metadata preflight detects confounds; honest labeling prevents false claims.

**Forbidden claims**: Production BCI; clinical validity; real-time control;
mind-reading; dream decoding; general imagery decoding; publication-ready
FBCSP (method is not FBCSP).

**Final takeaway**: A trustworthy 0.628 is scientifically more valuable than
a confounded 0.96.
"""
    _save_md("eeg_v77_committee_handout.md", md)
    _save_json("eeg_v77_committee_handout.json", {"sections": 6})
    print("Committee handout generated", file=sys.stderr)


def run_frontend():
    if not os.path.isdir(FRONTEND):
        _save_json("eeg_v77_frontend_export_skipped.json",
                   {"reason": "demo_thesis directory not found"})
        print("Frontend not found — skipped", file=sys.stderr)
        return

    data_dir = os.path.join(FRONTEND, "src", "data")
    os.makedirs(data_dir, exist_ok=True)
    ts = """// V7.7 Defense Pack
export const finalScore = 0.628;
export const finalCI = [0.581, 0.677];
export const finalPValue = "<0.001";
export const methodLabel = "Filter-bank log-power (NOT CSP/FBCSP)";
export const notCspFbcsp = true;
export const openmiirStatus = "negative_control";
export const physionetStatus = "valid_exploratory_baseline";
export const allowedClaims = [
  "Exploratory classical MI baseline",
  "Metadata preflight detects confounds",
  "Honest labeling prevents false claims",
];
export const forbiddenClaims = [
  "Production BCI", "Clinical validity",
  "Real-time control", "Mind-reading",
  "Dream decoding", "General imagery decoding",
];
export const presentationTakeaways = [
  "Metadata baselines first, always",
  "0.628 confound-free > 0.96 confounded",
  "Method is NOT CSP/FBCSP",
];
export const defenseWarnings = [
  "Do not call method FBCSP",
  "Do not claim production BCI",
  "Do not say scores are high",
  "Acknowledge limitations openly",
];
"""
    with open(os.path.join(data_dir, "eegDefensePack.ts"), "w") as f:
        f.write(ts)
    print("Frontend export: eegDefensePack.ts", file=sys.stderr)


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)
    print(f"V7.7 mode={args.mode}", file=sys.stderr)

    if args.mode in ("script", "all"):
        run_script()
    if args.mode in ("slides", "all"):
        run_slides()
    if args.mode in ("demo", "all"):
        run_demo()
    if args.mode in ("cards", "all"):
        run_cards()
    if args.mode in ("handout", "all"):
        run_handout()
    if args.mode in ("frontend", "all"):
        run_frontend()
    return 0


if __name__ == "__main__":
    sys.exit(main())
