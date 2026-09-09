"""C3XD Stage A — raw BIDS event-timing audit (events.tsv only; NO BOLD).

Downloads every testImagery/testPerception events.tsv for S1-S6 from the public
OpenNeuro S3 mirror (ds005191), parses the canonical trial structure, and certifies
the temporal contract needed to judge cue<->imagery identifiability. No neural data.

Imagery trial_type codes (verified from sidecar-free events):
  -2 cue (cueID) | 2 imagery (imageryID) | 3 post-imagery video (stimID) | -5 eval
  (-1/-3/-4/-6/-7 = rest/gap/fixation). Each imagery trial's cue/imagery/video share one video id.
Writes results/c3xd/c3xd_event_timing_manifest.json and raw_acquisition_plan.json.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path

S3 = "https://s3.amazonaws.com/openneuro.org/"
DS = "ds005191"
SUBS = [f"sub-0{i}" for i in range(1, 7)]


def _get(key: str) -> str:
    return urllib.request.urlopen(urllib.request.Request(S3 + key, headers={"User-Agent": "curl/8"}),
                                  timeout=60).read().decode()


def _s3list(prefix: str):
    out, token = [], None
    import urllib.parse
    while True:
        url = f"https://s3.amazonaws.com/openneuro.org?list-type=2&prefix={prefix}"
        if token:
            url += f"&continuation-token={urllib.parse.quote(token)}"
        x = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8"}), timeout=60).read().decode()  # noqa: E501
        keys = re.findall(r"<Key>(.*?)</Key>", x)
        sizes = re.findall(r"<Size>(.*?)</Size>", x)
        out += list(zip(keys, [int(s) for s in sizes]))
        m = re.search(r"<NextContinuationToken>(.*?)</NextContinuationToken>", x)
        token = m.group(1) if m else None
        if not token:
            break
    return out


def parse_events(text: str):
    """Return list of imagery trials with cue/imagery/video/eval timing, and raw rows."""
    lines = [ln.split("\t") for ln in text.strip().splitlines()]
    hdr = lines[0]
    idx = {h: i for i, h in enumerate(hdr)}
    rows = []
    for r in lines[1:]:
        rows.append({"onset": float(r[idx["onset"]]), "duration": float(r[idx["duration"]]),
                     "tt": int(float(r[idx["trial_type"]])),
                     "cueID": int(float(r[idx.get("cueID", -1)])) if "cueID" in idx else 0,
                     "imageryID": int(float(r[idx["imageryID"]])) if "imageryID" in idx else 0,
                     "stimID": int(float(r[idx["stimID"]])) if "stimID" in idx else 0,
                     "accuracy": int(float(r[idx["accuracy"]])) if "accuracy" in idx else 0,
                     "vividness": int(float(r[idx["vividness"]])) if "vividness" in idx else 0})
    # imagery: assemble each type==2 with its preceding cue (-2) and following video (3) + eval (-5)
    trials = []
    for i, row in enumerate(rows):
        if row["tt"] == 2:
            cue = next((rows[j] for j in range(i - 1, -1, -1) if rows[j]["tt"] == -2), None)
            vid = next((rows[j] for j in range(i + 1, len(rows)) if rows[j]["tt"] == 3), None)
            ev = next((rows[j] for j in range(i + 1, len(rows)) if rows[j]["tt"] == -5), None)
            trials.append({"video_id": row["imageryID"],
                           "cue_onset": cue["onset"] if cue else None, "cue_duration": cue["duration"] if cue else None,
                           "cue_id": cue["cueID"] if cue else None,
                           "imagery_onset": row["onset"], "imagery_duration": row["duration"],
                           "video_onset": vid["onset"] if vid else None, "video_duration": vid["duration"] if vid else None,  # noqa: E501
                           "video_stimID": vid["stimID"] if vid else None,
                           "eval_onset": ev["onset"] if ev else None, "eval_duration": ev["duration"] if ev else None,
                           "vividness": ev["vividness"] if ev else None, "accuracy": ev["accuracy"] if ev else None})
    return trials, rows


def parse_perception(text: str):
    lines = [ln.split("\t") for ln in text.strip().splitlines()]
    idx = {h: i for i, h in enumerate(lines[0])}
    vids = []
    for r in lines[1:]:
        tt = int(float(r[idx["trial_type"]]))
        if "stimID" in idx and tt == 2:  # video-presentation trials
            sid = int(float(r[idx["stimID"]]))
            if sid > 0:
                vids.append(sid)
    return vids


def _fetch(key, ev_dir):
    """Read cached events.tsv from ev_dir if present, else download and cache."""
    local = ev_dir / Path(key).name
    if local.exists():
        return local.read_text()
    txt = _get(key)
    local.write_text(txt)
    return txt


def main() -> None:
    ev_dir = Path(os.environ.get("C3XD_EVENT_DIR", "D:/mc_raw_events_c3xd"))
    ev_dir.mkdir(parents=True, exist_ok=True)
    out_dir = Path(os.environ.get("C3XD_OUT_DIR", "results/c3xd"))
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {"artifact": "C3XD_EVENT_TIMING_MANIFEST", "dataset": "ds005191 v1.0.2 (raw BIDS)",
                "tr_seconds": 1.0, "subjects": {}}
    plan = {"artifact": "C3XD_RAW_ACQUISITION_PLAN", "dataset": "ds005191 v1.0.2",
            "exclude": ["trainPerception"], "tasks": {}, "bold_bytes": {}, "storage_preflight": {}}
    imagery_trial_rows = []  # flat, for identifiability audit (timings only)

    for task, ses_pat in [("testImagery", "ses-testImagery"), ("testPerception", "ses-testPerception")]:
        plan["tasks"][task] = {}
        tot_bold = 0
        for sub in SUBS:
            files = _s3list(f"{DS}/{sub}/")
            func = [(k, s) for k, s in files if ses_pat in k and "/func/" in k]
            bolds = [(k, s) for k, s in func if k.endswith("_bold.nii.gz")]
            evs = sorted(k for k, _ in func if k.endswith("_events.tsv"))
            tot_bold += sum(s for _, s in bolds)
            plan["tasks"][task][sub] = {"n_bold_runs": len(bolds), "bold_bytes": sum(s for _, s in bolds),
                                        "n_events_files": len(evs)}
            sub_key = sub.replace("sub-0", "S")
            manifest["subjects"].setdefault(sub_key, {})
            if task == "testImagery":
                all_trials, per_run = [], {}
                for k in evs:
                    txt = _fetch(k, ev_dir)
                    m = re.search(r"ses-(testImagery\d+)_task.*run-(\d+)", k)
                    ses, run = m.group(1), int(m.group(2))
                    trials, _ = parse_events(txt)
                    per_run[f"{ses}_run{run}"] = len(trials)
                    for t in trials:
                        t2 = dict(t, session=ses, run=run)
                        all_trials.append(t2)
                # prev/next video within run order (flat by session/run/onset)
                all_trials.sort(key=lambda t: (t["session"], t["run"], t["imagery_onset"]))
                for i, t in enumerate(all_trials):
                    t["prev_video_id"] = all_trials[i - 1]["video_id"] if i > 0 else None
                    t["next_video_id"] = all_trials[i + 1]["video_id"] if i < len(all_trials) - 1 else None
                vids = [t["video_id"] for t in all_trials]
                sess = sorted(set(t["session"] for t in all_trials))
                uv = sorted(set(vids))
                # per-session video composition
                sess_ok = all(sorted(set(t["video_id"] for t in all_trials if t["session"] == s)) == uv
                              and all(sum(1 for t in all_trials if t["session"] == s and t["video_id"] == v) == 1 for v in uv)  # noqa: E501
                              for s in sess)
                manifest["subjects"][sub_key]["imagery"] = {
                    "n_trials": len(all_trials), "n_videos": len(uv), "n_sessions": len(sess),
                    "reps_per_video_min": min(vids.count(v) for v in uv),
                    "reps_per_video_max": max(vids.count(v) for v in uv),
                    "trials_per_run": per_run,
                    "session_balance_ok": bool(sess_ok),
                    "cue_durations_unique": sorted(set(t["cue_duration"] for t in all_trials)),
                    "imagery_duration_unique": sorted(set(t["imagery_duration"] for t in all_trials)),
                    "video_duration_unique": sorted(set(t["video_duration"] for t in all_trials if t["video_duration"])),  # noqa: E501
                    "cue_to_imagery_gap_unique": sorted(set(round(t["imagery_onset"] - (t["cue_onset"] + t["cue_duration"]), 3)  # noqa: E501
                                                            for t in all_trials if t["cue_onset"] is not None)),
                    "imagery_to_video_gap_unique": sorted(set(round(t["video_onset"] - (t["imagery_onset"] + t["imagery_duration"]), 3)  # noqa: E501
                                                              for t in all_trials if t["video_onset"] is not None))}
                if sub_key == "S1":
                    imagery_trial_rows = all_trials  # representative timing for identifiability audit
            else:
                allv = []
                for k in evs:
                    allv += parse_perception(_fetch(k, ev_dir))
                uv = sorted(set(allv))
                manifest["subjects"][sub_key]["perception"] = {
                    "n_video_trials": len(allv), "n_videos": len(uv),
                    "reps_per_video_min": min(allv.count(v) for v in uv) if uv else 0,
                    "reps_per_video_max": max(allv.count(v) for v in uv) if uv else 0}
        plan["bold_bytes"][task] = tot_bold
    # storage preflight
    import shutil
    free = shutil.disk_usage("D:/").free
    total_bold = sum(plan["bold_bytes"].values())
    plan["storage_preflight"] = {"free_bytes": free, "free_GB": round(free / 1e9, 1),
                                 "selected_bold_bytes": total_bold, "selected_bold_GB": round(total_bold / 1e9, 1),
                                 "peak_estimate_GB_with_preproc": round(total_bold / 1e9 * 1.6, 1),
                                 "sufficient": bool(free > total_bold * 1.6)}
    # save flat imagery timing rows for the identifiability audit (S1 representative)
    json.dump({"tr_seconds": 1.0, "trials": imagery_trial_rows},
              open(out_dir / "c3xd_s1_imagery_timing.json", "w"), indent=1)
    import hashlib
    for obj, name in [(manifest, "c3xd_event_timing_manifest.json"), (plan, "raw_acquisition_plan.json")]:
        obj["self_hash"] = hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()
        json.dump(obj, open(out_dir / name, "w"), indent=2)
    print("storage:", plan["storage_preflight"])
    for s, v in manifest["subjects"].items():
        im = v.get("imagery", {})
        print(f"{s}: imagery {im.get('n_trials')}tr {im.get('n_videos')}vid {im.get('n_sessions')}ses "
              f"reps[{im.get('reps_per_video_min')},{im.get('reps_per_video_max')}] balance={im.get('session_balance_ok')} "  # noqa: E501
              f"| perc {v.get('perception',{}).get('n_videos')}vid")


if __name__ == "__main__":
    main()
