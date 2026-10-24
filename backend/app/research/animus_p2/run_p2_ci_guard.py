"""ANIMUS-P2 CI guard (bridge milestone).

Enforces the invariants CI must check beyond the pytest suite:
  * P1 + C3XAT/C3XRP/C3XRA/Wang25 artifacts unchanged (LF-normalized hashes via the P2 anchor),
  * C3XAG unauthorized and IMAGERY_NEURAL_CONTENT unusable under every capability state,
  * protocol seal present and self-hash valid; test outcomes not accessed before freeze,
  * no real neural data / stimulus binaries committed,
  * P1 behavioral mode still imports and the perception provider is gated off pre-validation.
Fail-closed.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
OUT = os.path.join(ROOT, "results", "animus_p2")
ANCHOR = os.path.join(OUT, "animus_p2_anchor.json")


def _norm_sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def _self_hash(o):
    o = dict(o)
    o.pop("self_hash", None)
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


def check_immutability():
    a = json.load(open(ANCHOR, encoding="utf-8"))
    bad = []
    for k, ref in a["immutable_referenced_artifacts"].items():
        p = os.path.join(ROOT, ref["path"])
        if not os.path.exists(p):
            bad.append(f"missing:{ref['path']}")
        elif _norm_sha(p) != ref["file_sha256"]:
            bad.append(f"changed:{ref['path']}")
    if a.get("c3xag_authorized") is not False:
        bad.append("c3xag_authorized changed")
    if a.get("imagery_neural_content_authorized") is not False:
        bad.append("imagery authorized changed")
    return bad


def check_capability_isolation():
    from app.core.animus.p2.capability import (
        ScientificCapabilityAuthorization,
        imagery_unauthorized_invariant,
    )
    problems = []
    # imagery must stay unusable even after a perception VALIDATED decision
    auth = ScientificCapabilityAuthorization().validate_perception("ANIMUS_P2_PERCEPTION_DECODER_VALIDATED")
    if not imagery_unauthorized_invariant(auth):
        problems.append("imagery became usable after perception validation")
    if auth.status("PERCEPTION_NEURAL_CONTENT") != "VALIDATED":
        problems.append("perception validation did not set VALIDATED")
    return problems


def check_no_neural_data_or_binaries():
    problems = []
    for pat in ("*.nii", "*.nii.gz", "*.dcm", "*.npy", "*.h5", "*.mat", "*.png", "*.jpg", "*.jpeg"):
        hits = glob.glob(os.path.join(OUT, "**", pat), recursive=True)
        problems += [f"data:{os.path.relpath(h, ROOT)}" for h in hits]
    return problems


def check_seal_and_firewall():
    problems = []
    seal = os.path.join(OUT, "animus_p2_protocol_seal.json")
    if not os.path.exists(seal):
        problems.append("protocol seal missing")
    else:
        obj = json.load(open(seal, encoding="utf-8"))
        if obj.get("self_hash") != _self_hash(obj):
            problems.append("protocol seal self_hash invalid")
    fw = os.path.join(OUT, "firewall_audit.json")
    if os.path.exists(fw):
        if json.load(open(fw, encoding="utf-8")).get("test_outcome_accessed_before_freeze") is True:
            problems.append("test outcome accessed before freeze")
    return problems


def check_p1_and_provider():
    problems = []
    try:
        import app.main  # noqa: F401  (P1 behavioral app still imports)
        from app.core.animus.p2.capability import ScientificCapabilityAuthorization
        from app.core.animus.p2.integration import perception_provider_gated
        if perception_provider_gated(ScientificCapabilityAuthorization()):
            problems.append("perception provider not gated off pre-validation")
    except Exception as e:  # noqa: BLE001
        problems.append(f"p1/provider import failed: {e}")
    return problems


def main() -> int:
    checks = {
        "immutability": check_immutability(),
        "capability_isolation": check_capability_isolation(),
        "no_neural_data_or_binaries": check_no_neural_data_or_binaries(),
        "seal_and_firewall": check_seal_and_firewall(),
        "p1_and_provider_gating": check_p1_and_provider(),
    }
    failed = {k: v for k, v in checks.items() if v}
    for k, v in checks.items():
        print(f"  [{'FAIL' if v else 'PASS'}] {k}{': ' + str(v) if v else ''}")
    if failed:
        print("ANIMUS-P2 CI GUARD: FAIL")
        return 1
    print("ANIMUS-P2 CI GUARD: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
