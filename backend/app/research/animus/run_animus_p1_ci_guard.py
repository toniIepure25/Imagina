"""ANIMUS-P1 CI guard (product milestone, design-only).

Verifies the invariants CI must enforce beyond the pytest suite:
  * historical C3XAT/C3XRP/C3XRA artifacts unchanged (line-ending-agnostic hashes via the C3XRA anchor),
  * C3XAG still unauthorized,
  * no false neural-decoding claim anywhere in ANIMUS source/docs (forbidden-phrase scan),
  * scientific evidence registry ceiling is L1 (no content claim),
  * the acceptance decision artifact is PASS.
Fail-closed: exit non-zero on any violation.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys

from app.core.animus.claims import audit_text_for_forbidden_claims
from app.core.animus.evidence_registry import max_authorized_claim_level

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
ANCHOR = os.path.join(ROOT, "results", "c3xra", "c3xra_anchor.json")
DECISION = os.path.join(ROOT, "results", "animus_p1", "ANIMUS_P1_DECISION.json")


def _norm_sha(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def check_c3_immutability() -> list[str]:
    problems: list[str] = []
    if not os.path.exists(ANCHOR):
        return ["c3xra_anchor.json missing"]
    anchor = json.load(open(ANCHOR, encoding="utf-8"))
    for key, ref in anchor["immutable_referenced_artifacts"].items():
        p = os.path.join(ROOT, ref["path"])
        if not os.path.exists(p):
            problems.append(f"missing:{ref['path']}")
        elif _norm_sha(p) != ref["file_sha256"]:
            problems.append(f"changed:{ref['path']}")
    if anchor.get("c3xag_authorized") is not False:
        problems.append("c3xag_authorized changed")
    return problems


def check_no_false_claims() -> list[str]:
    problems: list[str] = []
    roots = [os.path.join(ROOT, "backend", "app", "core", "animus"),
             os.path.join(ROOT, "backend", "app", "api", "animus.py"),
             os.path.join(ROOT, "docs", "animus"),
             os.path.join(ROOT, "frontend", "app", "imagina", "animus")]
    files: list[str] = []
    for r in roots:
        if os.path.isdir(r):
            files += glob.glob(os.path.join(r, "**", "*.*"), recursive=True)
        elif os.path.isfile(r):
            files.append(r)
    for f in files:
        if not f.endswith((".py", ".md", ".ts", ".tsx")):
            continue
        try:
            text = open(f, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
        # ignore the enumerated forbidden-phrase list itself (claims.py) and the boundary doc which quote them
        base = os.path.basename(f)
        if base in ("claims.py", "ANIMUS_CLAIMS_BOUNDARY.md", "test_animus_p1.py"):
            continue
        hits = audit_text_for_forbidden_claims(text)
        if hits:
            problems.append(f"forbidden_claim:{os.path.relpath(f, ROOT)}:{hits}")
    return problems


def main() -> int:
    problems: dict[str, list[str]] = {}
    problems["c3_immutability"] = check_c3_immutability()
    problems["no_false_claims"] = check_no_false_claims()

    claim_ok = max_authorized_claim_level() == "L1_BEHAVIORAL_ASSISTED"
    if not claim_ok:
        problems["claim_ceiling"] = ["claim ceiling above L1"]

    decision_ok = False
    if os.path.exists(DECISION):
        dec = json.load(open(DECISION, encoding="utf-8"))
        decision_ok = dec.get("decision") == "ANIMUS_P1_VERTICAL_SLICE_PASS"
    if not decision_ok:
        problems["decision"] = ["ANIMUS_P1_DECISION not PASS or missing (run the benchmark runner first)"]

    failed = {k: v for k, v in problems.items() if v}
    for k, v in problems.items():
        print(f"  [{'FAIL' if v else 'PASS'}] {k}{': ' + str(v) if v else ''}")
    if failed:
        print("ANIMUS-P1 CI GUARD: FAIL")
        return 1
    print("ANIMUS-P1 CI GUARD: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
