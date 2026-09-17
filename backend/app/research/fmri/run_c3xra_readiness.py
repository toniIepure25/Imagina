"""C3XRA readiness decision + CI guard (design-only; NO human data).

Verifies every readiness gate and the safety invariants, then writes
results/c3xra/C3XRA_READINESS_DECISION.json (self-hashed):
  * immutability of the referenced C3XAT-R1 / C3XRP / Wang25 artifacts (recorded hash == current file hash),
  * all C3XRA seals present and self-hash-valid,
  * schedule / timing / task / BIDS / analysis contracts pass,
  * C3XAG NOT authorized; no raw neural data or PII committed; ethics files carry only placeholders
    (no fabricated approval / PI / facility / compensation),
  * stimulus provenance not blocked.
Exit non-zero if any gate fails (fail-closed) so CI blocks on regressions. Decision is
C3XRA_ACQUISITION_READY only if every gate passes; otherwise C3XRA_BLOCKED_<reason>.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
RESULTS = os.path.join(ROOT, "results", "c3xra")
REPORTS = os.path.join(ROOT, "reports", "c3xra")


def _sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _self_hash(obj):
    o = dict(obj)
    o.pop("self_hash", None)
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


def check_immutability(anchor):
    """Each referenced prior artifact must still hash to its recorded file_sha256."""
    bad = []
    for key, ref in anchor["immutable_referenced_artifacts"].items():
        path = os.path.join(ROOT, ref["path"])
        if not os.path.exists(path):
            bad.append(f"missing:{ref['path']}")
            continue
        if _sha256_file(path) != ref["file_sha256"]:
            bad.append(f"changed:{ref['path']}")
    return bad


def check_seals():
    names = ["c3xra_anchor.json", "participant_plan.json", "final_measurement_schedule_decision.json",
             "schedule_contract.json", "stimulus_provenance.json", "timing_design_audit.json",
             "mri_sequence_contract.json", "task_dryrun_validation.json", "bids_dryrun_validation.json",
             "acquisition_qc_seal.json", "preprocessing_execution_seal.json",
             "behavior_secondary_seal.json", "spatial_specificity_freeze.json",
             "acquisition_resource_model.json"]
    bad = []
    for n in names:
        p = os.path.join(RESULTS, n)
        if not os.path.exists(p):
            bad.append(f"missing:{n}")
            continue
        obj = _load(p)
        if obj.get("self_hash") != _self_hash(obj):
            bad.append(f"self_hash:{n}")
    return bad


def check_no_raw_neural_or_pii():
    """No committed NIfTI/DICOM under results|reports|stimuli, and no PII-looking fields."""
    problems = []
    for pat in ("*.nii", "*.nii.gz", "*.dcm", "*.ima"):
        for d in (RESULTS, REPORTS, os.path.join(ROOT, "stimuli")):
            hits = glob.glob(os.path.join(d, "**", pat), recursive=True)
            problems += [f"raw_data:{os.path.relpath(h, ROOT)}" for h in hits]
    pii = re.compile(r"\b(\d{3}-\d{2}-\d{4}|patient_name|date_of_birth|\bMRN\b)\b", re.I)
    for f in glob.glob(os.path.join(RESULTS, "*.json")):
        if pii.search(open(f, encoding="utf-8").read()):
            problems.append(f"pii:{os.path.basename(f)}")
    return problems


def check_ethics_placeholders():
    """Ethics drafts must be drafts: contain placeholders and no fabricated approval number."""
    problems = []
    files = ["ETHICS_PROTOCOL_DRAFT.md", "PARTICIPANT_INFORMATION_DRAFT.md", "CONSENT_FORM_DRAFT.md",
             "MRI_SAFETY_SCREENING_DRAFT.md"]
    for n in files:
        p = os.path.join(REPORTS, n)
        if not os.path.exists(p):
            problems.append(f"missing:{n}")
            continue
        txt = open(p, encoding="utf-8").read()
        if "{{" not in txt:
            problems.append(f"no_placeholders:{n}")
        if re.search(r"ethics\s+(ref|reference|approval)\s*[:#]\s*[0-9]{3,}", txt, re.I):
            problems.append(f"fabricated_ethics_number:{n}")
    return problems


def main():
    gates = {}
    anchor = _load(os.path.join(RESULTS, "c3xra_anchor.json"))

    immut = check_immutability(anchor)
    gates["immutable_prior_artifacts"] = (immut == [], immut)
    gates["c3xag_not_authorized"] = (anchor.get("c3xag_authorized") is False, [])

    seals = check_seals()
    gates["seals_present_and_self_hashed"] = (seals == [], seals)

    sc = _load(os.path.join(RESULTS, "schedule_contract.json"))
    gates["schedule_contract"] = (bool(sc["contract_pass"]), [])
    ta = _load(os.path.join(RESULTS, "timing_design_audit.json"))
    gates["timing_design"] = (bool(ta["audit_pass"] and ta["rank_deficiency"] == 0), [])
    td = _load(os.path.join(RESULTS, "task_dryrun_validation.json"))
    gates["task_dryrun"] = (bool(td["pass"]), [])
    bd = _load(os.path.join(RESULTS, "bids_dryrun_validation.json"))
    gates["bids_dryrun"] = (bool(bd["pass"] and bd["structural_error_count"] == 0), [])

    prov = _load(os.path.join(RESULTS, "stimulus_provenance.json"))
    gates["stimulus_provenance_not_blocked"] = (prov["blocked"] is False, [prov.get("block_code")])

    pp = _load(os.path.join(RESULTS, "participant_plan.json"))
    gates["reliability_not_used_for_exclusion"] = (
        pp["vividness_not_inclusion_criterion"] and pp["no_responder_enrichment"], [])

    # optional: E2E replay result if present (produced by run_c3xra_e2e_replay.py)
    e2e_path = os.path.join(RESULTS, "synthetic_e2e_replay.json")
    if os.path.exists(e2e_path):
        e2e = _load(e2e_path)
        gates["synthetic_e2e_replay"] = (bool(e2e["pass"]), [])
    else:
        gates["synthetic_e2e_replay"] = (None, ["not_run_locally"])

    safety = check_no_raw_neural_or_pii()
    gates["no_raw_neural_or_pii"] = (safety == [], safety)
    ethics = check_ethics_placeholders()
    gates["ethics_drafts_are_placeholders"] = (ethics == [], ethics)

    hard = {k: v for k, v in gates.items() if v[0] is not None}
    all_pass = all(v[0] for v in hard.values())
    failed = [k for k, v in hard.items() if not v[0]]
    if all_pass:
        decision = "C3XRA_ACQUISITION_READY"
    else:
        decision = "C3XRA_BLOCKED_" + failed[0].upper()

    out = {"artifact": "C3XRA_READINESS_DECISION", "gate": "C3XRA", "design_only": True,
           "decision": decision, "all_gates_pass": all_pass, "failed_gates": failed,
           "gates": {k: {"pass": v[0], "detail": v[1]} for k, v in gates.items()},
           "external_prerequisites_before_participant_001": [
               "independent ethics approval (drafts only; no number asserted)",
               "MRI facility authorization and confirmed/phantom-tested sequence",
               "recruitment authorization",
               "final naturalistic stimulus corpus licensed or produced (replaces proxy 1:1)",
               "fresh explicit user authorization to begin acquisition"],
           "acquisition_authorized": False}
    out["self_hash"] = _self_hash(out)
    with open(os.path.join(RESULTS, "C3XRA_READINESS_DECISION.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)

    for k, v in gates.items():
        mark = "SKIP" if v[0] is None else ("PASS" if v[0] else "FAIL")
        print(f"  [{mark}] {k} {v[1] if (v[0] is False) else ''}", flush=True)
    print(f"DECISION: {decision} (all_pass={all_pass})", flush=True)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
