"""ANIMUS-P2-R CI guard (hermetic; no large datasets).

Verifies the re-seal changed ONLY the spatial-preprocessing provenance: P2/P2E history immutable, split /
target-encoder / decoder inherited unchanged, target space is exactly MNI152NLin2009cAsym, Wang25 unchanged,
fMRIPrep pinned by digest (no floating tags), participant denominator frozen without performance-based
selection, capability stays BLOCKED, imagery UNAUTHORIZED, and no raw neural data / secrets committed.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
P2 = os.path.join(ROOT, "results", "animus_p2")
P2R = os.path.join(ROOT, "results", "animus_p2r")


def _load(p):
    return json.load(open(p, encoding="utf-8"))


def _self_ok(p):
    o = _load(p)
    h = o.get("self_hash")
    o2 = dict(o)
    o2.pop("self_hash", None)
    return h == hashlib.sha256(json.dumps(o2, sort_keys=True, default=str).encode()).hexdigest()


def _norm_sha(p):
    return hashlib.sha256(open(p, "rb").read().replace(b"\r\n", b"\n")).hexdigest()


def main() -> int:
    problems = {}

    # immutability of prior history via the p2r anchor
    anc = _load(os.path.join(P2R, "p2r_anchor.json"))
    bad = []
    for k, ref in anc["immutable_referenced_artifacts"].items():
        p = os.path.join(ROOT, ref["path"])
        if not os.path.exists(p) or _norm_sha(p) != ref["file_sha256"]:
            bad.append(k)
    problems["history_immutable"] = bad
    problems["c3xag_unauthorized"] = [] if anc["c3xag_authorized"] is False else ["c3xag authorized"]

    seal = _load(os.path.join(P2R, "animus_p2r_protocol_seal.json"))
    problems["only_provenance_changed"] = [] if "PREPROCESSING PROVENANCE" in seal["only_scientific_change"] \
        else ["scope creep"]
    problems["target_space_mni2009c"] = [] if (
        seal["target_template"].startswith("MNI152NLin2009cAsym")
        and seal["fmriprep"]["output_space"] == "MNI152NLin2009cAsym:res-2") else ["wrong template"]
    problems["fmriprep_pinned_digest"] = [] if "@sha256:" in seal["fmriprep"]["digest"] else ["floating tag"]
    problems["no_smoothing"] = [] if seal["fmriprep"]["smoothing"] == "NONE" else ["smoothing added"]
    problems["primary_dataset_nod"] = [] if seal["inherited_unchanged"]["primary_dataset"] == "NOD ds004496" \
        else ["dataset switched"]

    # inheritance audits present + unchanged
    for name in ("split_inheritance_audit", "target_representation_inheritance", "decoder_inheritance"):
        f = os.path.join(P2R, f"{name}.json")
        problems[name] = [] if (os.path.exists(f) and _load(f).get("unchanged")) else ["missing/changed"]

    denom = _load(os.path.join(P2R, "participant_denominator_freeze.json"))
    problems["denominator_frozen"] = [] if (denom["no_performance_based_selection"]
                                            and denom["frozen_before_outcomes"]) else ["selection risk"]

    # capability stays blocked; imagery unauthorized
    dec = _load(os.path.join(P2, "ANIMUS_P2_SCIENTIFIC_DECISION.json"))
    problems["perception_blocked_pre_result"] = [] if dec["perception_status"] == "BLOCKED" else ["not blocked"]
    problems["imagery_unauthorized"] = [] if dec["imagery_remains_unauthorized"] else ["imagery authorized"]

    # no raw neural data / secrets committed
    sec = []
    for pat in ("*.nii", "*.nii.gz", "*.npz", "*.npy", "*.h5", "*kubeconfig*", "*.pem", "*license*.txt"):
        sec += glob.glob(os.path.join(P2R, "**", pat), recursive=True)
    problems["no_raw_or_secrets"] = [os.path.relpath(s, ROOT) for s in sec]

    # self-hash integrity
    shb = [os.path.basename(f) for f in glob.glob(os.path.join(P2R, "*.json")) if not _self_ok(f)]
    problems["self_hash_integrity"] = shb

    failed = {k: v for k, v in problems.items() if v}
    for k, v in problems.items():
        print(f"  [{'FAIL' if v else 'PASS'}] {k}{': ' + str(v[:3]) if v else ''}")
    if failed:
        print("ANIMUS-P2R CI GUARD: FAIL")
        return 1
    print("ANIMUS-P2R CI GUARD: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
