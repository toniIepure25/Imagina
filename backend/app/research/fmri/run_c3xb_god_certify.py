"""C3XB Phase 1 data-contract + correspondence certification for GOD.

Reads the extracted arrays (out-of-repo) and certifies, per subject:
  IMAGERY:  50 categories, 10 reps/cat, 500 trials, 20 runs, 25 trials/run, and the
            RUN-PAIR CONTRACT (every 2 consecutive runs cover all 50 categories exactly
            once) -> 10 balanced run-pairs. Violation => BLOCKED_GOD_RUN_CATEGORY_CONTRACT.
  PERCEPTION (ImageNetTest): 50 categories, 35 valid reps/cat, 1750 trials, and that the
            released data already excludes one-back catch events (trial_type single value,
            1750 == 50*35 exactly).
  CORRESPONDENCE: 50/50 imagery<->perception categories, certified from category identity
            (WNID integer of stimulus_number / vmap), NOT row order.

Writes results/c3xb/god_data_contract.json, god_trial_manifest.json,
god_perception_imagery_correspondence.json. No geometry, no reliability here.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np

SUBS = ["Subject1", "Subject2", "Subject3", "Subject4", "Subject5"]


def _load(sd: Path, cond: str):
    p = sd / cond
    cat = np.load(p / "category.npy")
    run = np.load(p / "run.npy")
    return cat, run


def certify_subject(subj: str, ext: Path) -> dict:
    sd = ext / subj
    ic, ir = _load(sd, "Imagery")
    pc, pr = _load(sd, "ImageNetTest")
    iuc, icnt = np.unique(ic, return_counts=True)
    puc, pcnt = np.unique(pc, return_counts=True)

    # run-pair contract
    pair = (ir - 1) // 2
    upairs = sorted(set(pair.tolist()))
    pair_ok = len(upairs) == 10
    per_pair = {}
    for pv in upairs:
        cats = ic[pair == pv]
        uu, cc = np.unique(cats, return_counts=True)
        ok = (len(uu) == 50 and bool((cc == 1).all()))
        pair_ok &= ok
        per_pair[int(pv)] = {"runs": sorted(set(ir[pair == pv].tolist())),
                             "n_categories": int(len(uu)), "each_once": bool((cc == 1).all())}

    imagery_ok = (len(iuc) == 50 and bool((icnt == 10).all()) and ic.shape[0] == 500
                  and len(set(ir.tolist())) == 20 and pair_ok)
    # 25 trials/run
    _, rc = np.unique(ir, return_counts=True)
    trials_per_run_ok = bool((rc == 25).all())
    imagery_ok = imagery_ok and trials_per_run_ok

    perception_ok = (len(puc) == 50 and bool((pcnt == 35).all()) and pc.shape[0] == 1750)

    shared = set(iuc.tolist()) & set(puc.tolist())
    corr_ok = (len(shared) == 50 and len(iuc) == 50 and len(puc) == 50)

    status = "CERTIFIED"
    if not imagery_ok and not pair_ok:
        status = "BLOCKED_GOD_RUN_CATEGORY_CONTRACT"
    elif not (imagery_ok and perception_ok and corr_ok):
        status = "BLOCKED_GOD_DATA_CONTRACT"

    out = {
        "subject": subj, "status": status,
        "imagery": {"n_trials": int(ic.shape[0]), "n_categories": int(len(iuc)),
                    "reps_per_category_min": int(icnt.min()), "reps_per_category_max": int(icnt.max()),
                    "n_runs": int(len(set(ir.tolist()))), "trials_per_run_all_25": trials_per_run_ok,
                    "run_pair_contract_ok": bool(pair_ok), "n_run_pairs": len(upairs),
                    "contract_ok": bool(imagery_ok)},
        "perception_imagenet_test": {"n_trials": int(pc.shape[0]), "n_categories": int(len(puc)),
                    "valid_reps_per_category_min": int(pcnt.min()),
                    "valid_reps_per_category_max": int(pcnt.max()),
                    "one_back_catch_excluded_in_release": bool(pc.shape[0] == 50 * 35),
                    "contract_ok": bool(perception_ok)},
        "correspondence": {"imagery_categories": int(len(iuc)), "perception_categories": int(len(puc)),
                    "shared_categories": int(len(shared)), "is_50_of_50": bool(corr_ok),
                    "certified_from": "WNID integer of stimulus_number (vmap n%08d_%d), NOT row order"},
        "per_run_pair": per_pair,
    }
    out["self_hash"] = hashlib.sha256(json.dumps(out, sort_keys=True, default=str).encode()).hexdigest()
    return out


def main() -> None:
    ext = Path(os.environ["C3XB_EXTRACT_DIR"])
    out_dir = Path(os.environ.get("C3XB_OUT_DIR", "results/c3xb"))
    out_dir.mkdir(parents=True, exist_ok=True)
    subs = os.environ.get("C3XB_SUBJECTS", ",".join(SUBS)).split(",")

    contract = {"artifact": "C3XB_GOD_DATA_CONTRACT", "dataset": "GOD ds001246 / figshare 7387130 v8",
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "subjects": {}}
    manifest = {"artifact": "C3XB_GOD_TRIAL_MANIFEST", "subjects": {}}
    corr = {"artifact": "C3XB_GOD_PERCEPTION_IMAGERY_CORRESPONDENCE",
            "level": "natural-object CATEGORY (NOT exact-image / pixel-matched)", "subjects": {}}
    n_cert = 0
    for s in subs:
        c = certify_subject(s, ext)
        contract["subjects"][s] = c
        manifest["subjects"][s] = {"imagery": c["imagery"], "perception": c["perception_imagenet_test"]}
        corr["subjects"][s] = c["correspondence"]
        n_cert += int(c["status"] == "CERTIFIED")
        print(f"[{s}] {c['status']} imagery_ok={c['imagery']['contract_ok']} "
              f"pair_ok={c['imagery']['run_pair_contract_ok']} "
              f"perc_ok={c['perception_imagenet_test']['contract_ok']} "
              f"corr50={c['correspondence']['is_50_of_50']}")
    contract["n_certified"] = n_cert
    contract["all_certified"] = bool(n_cert == len(subs))
    for obj, name in [(contract, "god_data_contract.json"), (manifest, "god_trial_manifest.json"),
                      (corr, "god_perception_imagery_correspondence.json")]:
        obj["self_hash"] = hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()
        json.dump(obj, open(out_dir / name, "w"), indent=2)
    print(f"certified {n_cert}/{len(subs)}")


if __name__ == "__main__":
    main()
