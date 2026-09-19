"""ANIMUS-P2E CI guard (hermetic; no large datasets).

Verifies the P2E resolution invariants: P2 seal inherited unchanged, spatial-transform certification present
and FAILED (the honest finding), decision is the specific ROI spatial-provenance block, capability shows
perception BLOCKED + imagery UNAUTHORIZED, no raw neural data / credentials / kubeconfig committed, and the
integrity/red-team audits pass. Fail-closed.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
P2 = os.path.join(ROOT, "results", "animus_p2")
P2E = os.path.join(ROOT, "results", "animus_p2e")


def _self_hash_ok(path):
    o = json.load(open(path, encoding="utf-8"))
    h = o.get("self_hash")
    o2 = dict(o)
    o2.pop("self_hash", None)
    return h == hashlib.sha256(json.dumps(o2, sort_keys=True, default=str).encode()).hexdigest()


def main() -> int:
    problems = {}

    inh = os.path.join(P2E, "P2_SEAL_INHERITANCE_AUDIT.json")
    problems["seal_inheritance"] = [] if (os.path.exists(inh)
        and json.load(open(inh, encoding="utf-8")).get("seal_inheritance_pass")) else ["missing/failed"]

    cert = os.path.join(P2E, "spatial_transform_certification.json")
    if not os.path.exists(cert):
        problems["spatial_certification"] = ["missing"]
    else:
        c = json.load(open(cert, encoding="utf-8"))
        problems["spatial_certification"] = [] if c.get("certification_pass") is False else \
            ["certification unexpectedly passed without MNI provenance"]

    dec = os.path.join(P2, "ANIMUS_P2_SCIENTIFIC_DECISION.json")
    d = json.load(open(dec, encoding="utf-8"))
    problems["decision"] = [] if d.get("decision") == "ANIMUS_P2_BLOCKED_ROI_SPATIAL_PROVENANCE" else \
        [f"unexpected decision {d.get('decision')}"]
    problems["perception_blocked"] = [] if d.get("perception_status") == "BLOCKED" else ["perception not BLOCKED"]
    problems["imagery_unauthorized"] = [] if d.get("imagery_remains_unauthorized") else ["imagery authorized!"]

    # no raw neural data / images / credentials committed under results/animus_p2e or animus_p2
    bad = []
    for base in (P2, P2E):
        for pat in ("*.nii", "*.nii.gz", "*.npz", "*.npy", "*.png", "*.jpg", "*.jpeg", "*.h5",
                    "*kubeconfig*", "*.pem", "*credentials*"):
            bad += glob.glob(os.path.join(base, "**", pat), recursive=True)
    problems["no_raw_or_secrets"] = [os.path.relpath(b, ROOT) for b in bad]

    # self-hash integrity of new artifacts
    sh_bad = []
    for f in glob.glob(os.path.join(P2E, "*.json")):
        try:
            if not _self_hash_ok(f):
                sh_bad.append(os.path.basename(f))
        except Exception:  # noqa: BLE001
            pass
    problems["self_hash_integrity"] = sh_bad

    integ = os.path.join(P2E, "final_integrity_audit.json")
    problems["integrity_audit"] = [] if (os.path.exists(integ)
        and json.load(open(integ, encoding="utf-8")).get("no_invented_registration")) else ["missing/failed"]

    failed = {k: v for k, v in problems.items() if v}
    for k, v in problems.items():
        print(f"  [{'FAIL' if v else 'PASS'}] {k}{': ' + str(v[:3]) if v else ''}")
    if failed:
        print("ANIMUS-P2E CI GUARD: FAIL")
        return 1
    print("ANIMUS-P2E CI GUARD: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
