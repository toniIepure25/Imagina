"""C3XC Phase 1 experimental-contract certification (all subjects).

Reads the extracted arrays and certifies per subject:
  IMAGERY: 360 samples, 72 videos, 5 sessions, 5 reps/video, and the SESSION UNIT
           CONTRACT (each of the 5 sessions contains all 72 videos exactly once) ->
           independence unit balanced. Violation => BLOCKED_D2_UNIT_CONTRACT.
  PERCEPTION: 72 videos x 5 reps = 360 samples.
  CORRESPONDENCE: imagery content-id set == perception content-id set == 72 (exact),
           certified from video identity (imageryID/stimID), NOT row order.
Writes results/c3xc/subject_certification.json and correspondence_audit.json.
No geometry, no reliability here.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np

SUBS = ["S1", "S2", "S3", "S4", "S5", "S6"]


def certify(subj, ext):
    sd = ext / subj
    ic = np.load(sd / "testImagery" / "content.npy")
    isess = np.load(sd / "testImagery" / "session.npy")
    pc = np.load(sd / "testPerception" / "content.npy")
    iu, icnt = np.unique(ic, return_counts=True)
    pu, pcnt = np.unique(pc, return_counts=True)

    # session unit contract: each session all 72 videos exactly once
    unit_ok = len(set(isess.tolist())) == 5
    per_session = {}
    for s in sorted(set(isess.tolist())):
        u, c = np.unique(ic[isess == s], return_counts=True)
        ok = (len(u) == 72 and bool((c == 1).all()))
        unit_ok &= ok
        per_session[int(s)] = {"n_videos": int(len(u)), "each_once": bool((c == 1).all())}

    imagery_ok = (len(iu) == 72 and bool((icnt == 5).all()) and ic.shape[0] == 360 and unit_ok)
    perception_ok = (len(pu) == 72 and bool((pcnt == 5).all()) and pc.shape[0] == 360)
    shared = set(iu.tolist()) & set(pu.tolist())
    corr_ok = (len(shared) == 72 and len(iu) == 72 and len(pu) == 72)

    if not unit_ok:
        status = "BLOCKED_D2_UNIT_CONTRACT"
    elif not (imagery_ok and perception_ok and corr_ok):
        status = "BLOCKED_D2_DATA_CONTRACT"
    else:
        status = "CERTIFIED"

    # ROI voxel counts (from any extracted X_*.npy)
    roi_counts = {}
    for r in ("VC", "earlyVC", "LVC", "HVC"):
        f = sd / "testImagery" / f"X_{r}.npy"
        if f.exists():
            roi_counts[r] = int(np.load(f, mmap_mode="r").shape[1])

    out = {"subject": subj, "status": status,
           "imagery": {"n_samples": int(ic.shape[0]), "n_videos": int(len(iu)),
                       "reps_min": int(icnt.min()), "reps_max": int(icnt.max()),
                       "n_sessions": int(len(set(isess.tolist()))),
                       "session_unit_contract_ok": bool(unit_ok), "contract_ok": bool(imagery_ok)},
           "perception": {"n_samples": int(pc.shape[0]), "n_videos": int(len(pu)),
                          "reps_min": int(pcnt.min()), "reps_max": int(pcnt.max()),
                          "contract_ok": bool(perception_ok)},
           "correspondence": {"imagery_videos": int(len(iu)), "perception_videos": int(len(pu)),
                              "shared": int(len(shared)), "is_72_of_72": bool(corr_ok),
                              "certified_from": "video identity (imageryID/stimID), NOT row order"},
           "roi_voxel_counts_VC_earlyVC_LVC_HVC": roi_counts,
           "per_session": per_session}
    out["self_hash"] = hashlib.sha256(json.dumps(out, sort_keys=True, default=str).encode()).hexdigest()
    return out


def main() -> None:
    ext = Path(os.environ["C3XC_EXTRACT_DIR"])
    out_dir = Path(os.environ.get("C3XC_OUT_DIR", "results/c3xc"))
    out_dir.mkdir(parents=True, exist_ok=True)
    subs = os.environ.get("C3XC_SUBJECTS_CERT", ",".join(SUBS)).split(",")
    cert = {"artifact": "C3XC_SUBJECT_CERTIFICATION",
            "dataset": "Mind Captioning ds005191 v1.0.2 / figshare 25808179 v2",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "subjects": {}}
    corr = {"artifact": "C3XC_CORRESPONDENCE_AUDIT",
            "level": "video identity (semantic/event video-recall); 72 test videos", "subjects": {}}
    n_cert = 0
    for s in subs:
        c = certify(s, ext)
        cert["subjects"][s] = c
        corr["subjects"][s] = c["correspondence"]
        n_cert += int(c["status"] == "CERTIFIED")
        print(f"[{s}] {c['status']} imagery_ok={c['imagery']['contract_ok']} "
              f"unit_ok={c['imagery']['session_unit_contract_ok']} "
              f"perc_ok={c['perception']['contract_ok']} corr72={c['correspondence']['is_72_of_72']} "
              f"VC={c['roi_voxel_counts_VC_earlyVC_LVC_HVC'].get('VC')}")
    cert["n_certified"] = n_cert
    cert["all_certified"] = bool(n_cert == len(subs))
    for obj, name in [(cert, "subject_certification.json"), (corr, "correspondence_audit.json")]:
        obj["self_hash"] = hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()
        json.dump(obj, open(out_dir / name, "w"), indent=2)
    print(f"certified {n_cert}/{len(subs)}")


if __name__ == "__main__":
    main()
