"""ANIMUS-P2-XR CI guard (hermetic; no external datasets).

Verifies the replication re-seal changed ONLY the dataset I/O adapters + per-dataset denominators: the P2
method code is byte-unchanged (norm-SHA pins), the target encoder / ROI / space / fMRIPrep digest / no-
smoothing / permutation-bootstrap-seed / subject gate / dataset gate are inherited, NOD is closed, imagery /
C3XAG unauthorized, the power audit passes, the participant denominators are frozen pre-outcome, and NO real
replication decoding outcome exists before the implementation freeze (firewall). Fail-closed.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
XR = os.path.join(ROOT, "results", "animus_p2xr")


def _load(p):
    return json.load(open(p, encoding="utf-8"))


def _self_ok(p):
    o = _load(p)
    h = o.get("self_hash")
    o2 = dict(o)
    o2.pop("self_hash", None)
    return h == hashlib.sha256(json.dumps(o2, sort_keys=True, default=str).encode()).hexdigest()


def _norm_sha(rel):
    return hashlib.sha256(open(os.path.join(ROOT, rel), "rb").read().replace(b"\r\n", b"\n")).hexdigest()


def main() -> int:
    problems = {}
    seal_p = os.path.join(XR, "animus_p2xr_protocol_seal.json")
    if not os.path.exists(seal_p):
        print("  [FAIL] seal missing")
        print("ANIMUS-P2XR CI GUARD: FAIL")
        return 1
    seal = _load(seal_p)

    problems["only_adapters_and_denominators_changed"] = [] if (
        "DATASET I/O ADAPTERS" in seal["only_changes_vs_p2"]) else ["scope creep"]

    # inherited method code byte-unchanged since sealing
    code_map = {
        "gate": "backend/app/core/animus/p2/gate.py", "splits": "backend/app/core/animus/p2/splits.py",
        "decoder": "backend/app/core/animus/p2/decoder.py", "pipeline": "backend/app/core/animus/p2/pipeline.py",
        "metrics": "backend/app/core/animus/p2/metrics.py", "features": "backend/app/core/animus/p2/features.py",
        "target_representation": "backend/app/core/animus/p2/target_representation.py",
        "frozen_lsa_glm_extractor": "backend/app/research/animus_p2/extract_features_p2r.py",
    }
    drift = [k for k, rel in code_map.items()
             if _norm_sha(rel) != seal["inherited_code_norm_sha256"].get(k)]
    problems["inherited_method_code_unchanged"] = drift

    problems["fmriprep_pinned_digest"] = [] if "@sha256:" in seal["fmriprep_digest"] else ["floating tag"]
    problems["space_mni2009c_res2"] = [] if seal["roi"]["space"] == "MNI152NLin2009cAsym:res-2" else ["wrong"]
    problems["no_smoothing"] = [] if seal["smoothing"] == "NONE" else ["smoothing added"]
    problems["wang25_unchanged"] = [] if seal["roi"]["wang25_sha256"] == \
        "19b681ecba5c8d2aa323b8f6e15d36191d4036cea070d095663a790690c544fc" else ["wang25 changed"]
    enc = seal["target_encoder"]
    problems["encoder_inherited"] = [] if (enc["model_id"] == "open_clip:ViT-B-32"
        and enc["pretrained"] == "laion2b_s34b_b79k" and enc["embedding_dim"] == 512) else ["encoder changed"]
    problems["perm_boot_seeds_inherited"] = [] if (seal["permutation"]["n_perm"] == 1000
        and seal["identity_bootstrap"]["n_boot"] == 1000
        and seal["evaluation_seeds"] == [20260909, 20261009, 20261109]) else ["changed"]
    problems["dataset_gate_inherited"] = [] if "max(2,ceil(N_valid/3))" in seal["dataset_gate"] else ["changed"]
    problems["no_pooled_rescue"] = [] if seal["cross_dataset_decision"]["no_pooled_rescue"] else ["rescue!"]
    problems["nod_closed"] = [] if "CLOSED" in seal["nod_status"] else ["nod not closed"]
    problems["imagery_unauthorized"] = [] if (seal["imagery_dream_reconstruction"] == "UNAUTHORIZED"
        and seal["c3xag_authorized"] is False and seal["p3_execution"] is False) else ["imagery/c3xag/p3!"]

    # denominators frozen pre-outcome
    denom_p = os.path.join(XR, "participant_denominator_freeze.json")
    denom = _load(denom_p) if os.path.exists(denom_p) else {}
    problems["denominators_frozen"] = [] if (denom.get("frozen_before_outcomes")
        and denom.get("no_performance_based_selection") and denom.get("total_denominator") == 7) else ["bad"]

    # power audit passes
    pw_p = os.path.join(XR, "power_audit.json")
    problems["power_audit_pass"] = [] if (os.path.exists(pw_p)
        and _load(pw_p).get("all_checks_pass")) else ["power audit missing/failed"]

    # FIREWALL: no real replication decoding outcome may exist before the implementation freeze
    freeze_exists = os.path.exists(os.path.join(XR, "P2XR_CONFIRMATORY_IMPLEMENTATION_FREEZE.json"))
    outcome_markers = []
    if not freeze_exists:
        for f in glob.glob(os.path.join(XR, "**", "*.json"), recursive=True):
            try:
                o = _load(f)
            except Exception:  # noqa: BLE001
                continue
            blob = json.dumps(o)
            # a confirmatory outcome would carry per-subject margins / 2AFC / a cross-dataset decision
            if any(k in o for k in ("margin_M", "two_afc", "cross_dataset_decision_result")) or \
               "INDEPENDENT_REPLICATION_PASS" in blob and o.get("artifact") not in (
                   "ANIMUS_P2XR_POWER_AUDIT", "ANIMUS_P2XR_PROTOCOL_SEAL"):
                outcome_markers.append(os.path.relpath(f, ROOT))
    problems["firewall_no_premature_outcome"] = outcome_markers

    # no raw neural data / secrets committed
    sec = []
    for pat in ("*.nii", "*.nii.gz", "*.npz", "*.npy", "*.h5", "*kubeconfig*", "*.pem", "*license*.txt"):
        sec += glob.glob(os.path.join(XR, "**", pat), recursive=True)
    problems["no_raw_or_secrets"] = [os.path.relpath(s, ROOT) for s in sec]

    # self-hash integrity of all p2xr artifacts
    problems["self_hash_integrity"] = [os.path.basename(f)
        for f in glob.glob(os.path.join(XR, "*.json")) if not _self_ok(f)]

    failed = {k: v for k, v in problems.items() if v}
    for k, v in problems.items():
        print(f"  [{'FAIL' if v else 'PASS'}] {k}{': ' + str(v[:3]) if v else ''}")
    if failed:
        print("ANIMUS-P2XR CI GUARD: FAIL")
        return 1
    print("ANIMUS-P2XR CI GUARD: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
