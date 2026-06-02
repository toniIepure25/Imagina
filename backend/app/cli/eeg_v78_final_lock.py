"""V7.8 — Final Consistency Audit & Submission Lock.

Scans all final artifacts for claim violations, score inconsistencies,
method label errors. Generates submission pack. No experiments.
"""

import json
import os
import sys
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.eeg_v78_final_lock")
    p.add_argument("--mode", default="all", choices=[
        "audit", "claim_scan", "score_scan", "method_scan",
        "artifact_index", "submission_pack", "all"])
    p.add_argument("--output-prefix", default="eeg_v78_final")
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


def _scan_files():
    files = []
    for fn in sorted(os.listdir(EXPORTS)):
        if fn.endswith(".md") or fn.endswith(".json"):
            files.append(os.path.join(EXPORTS, fn))
    # Also scan frontend TS
    ts_path = os.path.join(BASE, "..", "..", "..", "demo_thesis", "src", "data", "eegDefensePack.ts")
    if os.path.exists(ts_path):
        files.append(ts_path)
    return files


def _read_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def run_claim_scan():
    files = _scan_files()
    forbidden = [
        "production BCI", "production-ready", "BCI-ready",
        "mind-reading", "dream decoding", "decode dreams",
        "publication-ready FBCSP", "true FBCSP", "validated FBCSP",
        "CSP/FBCSP as final", "publication-ready",
    ]
    required = ["filter-bank log-power", "NOT CSP", "not CSP",
                "metadata baseline", "LOSO", "0.628", "exploratory"]
    unsafe_hits = []
    missing_required = {}
    warnings_list = []

    for fp in files:
        content = _read_file(fp)
        fn = os.path.basename(fp)
        # Skip raw intermediate artifacts
        if any(s in fn for s in ["v46", "v47", "v48", "v49", "v50", "v61", "v62", "v63", "v64", "v65", "v66", "v67"]):
            continue
        for phrase in forbidden:
            if phrase.lower() in content.lower():
                # Check if in forbidden claims section (allowed)
                if "forbidden" in content.lower() and phrase.lower() in content.lower().split("forbidden")[-1][:500]:
                    continue
                unsafe_hits.append({"file": fn, "phrase": phrase})
        missing = []
        for phrase in required:
            if phrase.lower() not in content.lower():
                missing.append(phrase)
        if missing:
            missing_required[fn] = missing

    status = "fail" if unsafe_hits else ("warnings" if missing_required else "pass")

    report = {
        "files_scanned": len(files),
        "unsafe_hits": unsafe_hits,
        "warning_hits": warnings_list,
        "missing_required": missing_required,
        "overall_status": status,
        "note": "Forbidden phrases checked. Missing required phrases flagged as warnings."
    }
    _save_json("eeg_v78_claim_safety_scan.json", report)

    md = f"# Claim Safety Scan — Status: {status.upper()}\n\n"
    if unsafe_hits:
        md += "## Unsafe Hits\n"
        for h in unsafe_hits:
            md += f"- {h['file']}: `{h['phrase']}`\n"
    if missing_required:
        md += "## Missing Required Phrases\n"
        for fn, phrases in missing_required.items():
            md += f"- {fn}: {phrases}\n"
    _save_md("eeg_v78_claim_safety_scan.md", md)
    print(f"Claim scan: {status} ({len(unsafe_hits)} unsafe, {len(missing_required)} missing required)",
          file=sys.stderr)


def run_score_scan():
    files = _scan_files()
    issues = []
    for fp in files:
        content = _read_file(fp)
        fn = os.path.basename(fp)
        # Check for old/confounded scores presented as valid
        if "0.614" in content and "V6.7" not in content and "mislabeled" not in content:
            issues.append({"file": fn, "issue": "0.614 mentioned without V6.7 context"})
        if "0.96" in content and "confound" not in content.lower() and "invalid" not in content.lower():
            issues.append({"file": fn, "issue": "0.96 mentioned without confound context"})
        if "0.93" in content and "confound" not in content.lower() and "0.96" not in content:
            issues.append({"file": fn, "issue": "0.93 mentioned without confound context"})

    report = {"files_scanned": len(files), "score_issues": issues,
              "status": "pass" if not issues else "warnings",
              "expected_final_score": 0.628, "expected_ci": [0.581, 0.677],
              "expected_p": "<0.001", "metadata_baseline": 0.482, "quality_baseline": 0.494}
    _save_json("eeg_v78_score_consistency_scan.json", report)

    md = f"# Score Consistency Scan — Status: {report['status'].upper()}\n\n"
    md += "**Expected final score**: 0.628 [0.581, 0.677], p<0.001\n\n"
    if issues:
        md += "## Issues Found\n"
        for i in issues:
            md += f"- {i['file']}: {i['issue']}\n"
    else:
        md += "No score inconsistencies detected.\n"
    _save_md("eeg_v78_score_consistency_scan.md", md)
    print(f"Score scan: {report['status']} ({len(issues)} issues)", file=sys.stderr)


def run_method_scan():
    files = _scan_files()
    invalid_mentions = []
    allowed_mentions = []
    confirmed = True

    for fp in files:
        content = _read_file(fp)
        fn = os.path.basename(fp)
        # Skip raw intermediate artifacts
        if any(s in fn for s in ["v46", "v47", "v48", "v49", "v50"]):
            continue
        # Check for CSP/FBCSP used as final method claim
        for phrase in ["validated FBCSP", "publication-ready FBCSP", "true FBCSP best",
                       "final CSP", "CSP/FBCSP validated"]:
            if phrase.lower() in content.lower():
                invalid_mentions.append({"file": fn, "phrase": phrase})
                confirmed = False
        # Check CSP/FBCSP in correction context
        for phrase in ["NOT CSP", "not CSP", "not FBCSP", "NOT FBCSP",
                       "filter-bank log-power is not", "not validated as"]:
            if phrase in content:
                allowed_mentions.append({"file": fn, "phrase": phrase})

    report = {
        "method_label_status": "confirmed" if confirmed else "invalid",
        "final_method_confirmed": confirmed,
        "invalid_mentions": invalid_mentions,
        "allowed_context_mentions": allowed_mentions[:10],
    }
    _save_json("eeg_v78_method_label_scan.json", report)

    md = f"# Method Label Scan — Status: {report['method_label_status'].upper()}\n\n"
    md += "**Final method**: filter-bank log-power (NOT CSP/FBCSP)\n\n"
    if invalid_mentions:
        md += "## Invalid Mentions\n"
        for m in invalid_mentions:
            md += f"- {m['file']}: `{m['phrase']}`\n"
    if not invalid_mentions:
        md += "No invalid method label mentions found.\n"
    _save_md("eeg_v78_method_label_scan.md", md)
    print(f"Method scan: {report['method_label_status']} ({len(invalid_mentions)} invalid)",
          file=sys.stderr)


def run_artifact_index():
    safe = [
        "eeg_v76_thesis_chapter_final.md",
        "eeg_v77_final_presentation_script.md",
        "eeg_v77_final_slide_content.md",
        "eeg_v77_live_demo_script.md",
        "eeg_v77_defense_flashcards.md",
        "eeg_v77_committee_handout.md",
        "eeg_v74_final_validated_baseline.json",
        "eeg_v74_final_method_comparison.json",
        "eeg_v74_claim_ledger.json",
        "eeg_v75_master_scientific_status.json",
        "eeg_v75_dashboard_summary.json",
        "eeg_v75_final_thesis_report.md",
        "eeg_v78_claim_safety_scan.json",
        "eeg_v78_score_consistency_scan.json",
        "eeg_v78_method_label_scan.json",
    ]
    not_examiner = [
        "eeg_v63", "eeg_v64", "eeg_v65", "eeg_v66", "eeg_v67",
        "openmiir_ssl_v48", "openmiir_ssl_v49", "openmiir_v50",
    ]
    artifacts = []
    for fn in sorted(os.listdir(EXPORTS)):
        is_safe = fn in safe
        is_examiner = is_safe
        cat = "raw_experiments"
        if fn.startswith("eeg_v7") and fn.endswith(".md"):
            cat = "defense_materials" if "defense" in fn or "slide" in fn or "demo" in fn or "flashcard" in fn \
                 or "committee" in fn else "thesis_text" if "thesis" in fn or "chapter" in fn \
                 else "status_ledger" if "claim" in fn or "status" in fn else "raw_experiments"
        if fn.endswith(".png"):
            cat = "figures"
        if any(s in fn for s in not_examiner):
            is_examiner = False
            cat = "deprecated"
        artifacts.append({
            "filename": fn, "category": cat, "purpose": "",
            "safe_to_show": is_safe, "examiner_friendly": is_examiner,
        })

    index = {"n_artifacts": len(artifacts), "artifacts": artifacts}
    _save_json("eeg_v78_submission_artifact_index.json", index)
    print(f"Artifact index: {len(artifacts)} artifacts", file=sys.stderr)


def run_submission_pack():
    md = """# V7.8 Submission Pack — Final Defense Checklist

## 1. Final Thesis-Safe Claim

Filter-bank log-power features achieve an above-chance exploratory classical
EEG baseline for left/right fist motor imagery on PhysioNet EEGMMI under LOSO
evaluation (balanced accuracy 0.628, 95% CI [0.581, 0.677], p<0.001), after
metadata-preflight validation. The main contribution is the confound-aware
validation methodology, not production BCI performance.

## 2. Final Result Table

| Metric | Value |
|--------|-------|
| Method | Filter-bank log-power (NOT CSP/FBCSP) |
| Balanced accuracy | 0.628 |
| 95% CI | [0.581, 0.677] |
| p-value | <0.001 |
| Subjects | 15 |
| CV | Leave-one-subject-out |
| Metadata baseline | 0.482 |
| Quality baseline | 0.494 |
| OpenMIIR status | Negative control (invalid) |

## 3. What to Show in Defense

- Slide 4: metadata = 1.0 (key reveal)
- Slide 9: final result table
- Slide 11: claim ledger
- Slide 12: contribution

## 4. What NOT to Show Unless Asked

- Raw V4.8 OpenMIIR SSL results (confounded)
- V6.7 mislabeled FBCSP attempt
- Intermediate CSP/FBCSP partial runs
- Any artifact marked as "deprecated" in the submission index

## 5. What to Say if Asked About OpenMIIR

"OpenMIIR was the first dataset I tested. After discovering that metadata
baselines could predict condition labels with perfect accuracy, I reclassified
it as a negative-control dataset — the case that proves the audit framework
works."

## 6. What to Say if Asked About CSP/FBCSP

"I tested true MNE CSP (0.482) and it did not beat the filter-bank log-power
baseline (0.628). True FBCSP was computationally constrained and not validated.
The final method is filter-bank log-power, and I label it explicitly as NOT
CSP/FBCSP. Honest labeling is deliberate."

## 7. What to Say if Asked Why 0.628 is Moderate

"0.628 is above chance (p<0.001), beats the metadata baseline by a large
margin (0.146), and was achieved under honest labeling with no confounds.
A trustworthy 0.628 is scientifically more valuable than a confounded 0.96."

## 8. What to Say if Asked About Production BCI

"This is not a production BCI. The result is an exploratory classical EEG
baseline validated under LOSO. Real-time BCI would require >80% accuracy,
multi-session stability, and calibration-free adaptation — all beyond the
scope of this project."

## 9. Last-Minute Defense Checklist

- [ ] Committee handout printed (use V7.7 committee_handout.md)
- [ ] Slides reviewed (use V7.7 slide_content.md)
- [ ] Script rehearsed (use V7.7 presentation_script.md)
- [ ] Flashcards reviewed (use V7.7 flashcards.md)
- [ ] Demo tested (use V7.7 live_demo_script.md)
- [ ] Q&A pack reviewed (use V7.6 examiner_qa_pack.md)
- [ ] Final claim memorized (see Section 1 above)
- [ ] Forbidden claims memorized (never say "production BCI", "clinical",
  "mind-reading", "dream decoding", "FBCSP validated")

## 10. Final One-Sentence Closing

"Metadata baselines must be the first baseline for any EEG decoding claim —
before any model is trained, before any score is reported, before any paper
is submitted."
"""
    _save_md("eeg_v78_submission_pack.md", md)
    _save_json("eeg_v78_submission_pack.json", {"sections": 10})
    print("Submission pack generated", file=sys.stderr)


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)
    print(f"V7.8 mode={args.mode}", file=sys.stderr)

    if args.mode in ("audit", "claim_scan", "all"):
        run_claim_scan()
    if args.mode in ("score_scan", "all"):
        run_score_scan()
    if args.mode in ("method_scan", "all"):
        run_method_scan()
    if args.mode in ("artifact_index", "all"):
        run_artifact_index()
    if args.mode in ("submission_pack", "all"):
        run_submission_pack()
    return 0


if __name__ == "__main__":
    sys.exit(main())
