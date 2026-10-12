"""Fetch the public datasets used by the Phase-2 real-data validation into a data root.

Sources are public and openly licensed (PhysioNet ODC-BY / open access, MNE datasets, OpenNeuro CC0).
Writes ``<root>/FETCH_MANIFEST.json`` with source, version, file counts and per-file SHA-256.

    python scripts/phase2_fetch_datasets.py --root /data/phase2 [--only mitdb bidmc ...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

PHYSIONET = {
    "mitdb": {"version": "1.0.0", "title": "MIT-BIH Arrhythmia Database", "modality": "ECG",
              "annotations": "beat-by-beat cardiologist annotations"},
    "bidmc": {"version": "1.0.0", "title": "BIDMC PPG and Respiration Dataset", "modality": "respiration",
              "annotations": "manual breath annotations by two independent annotators"},
    "noneeg": {"version": "1.0.0", "title": "Non-EEG Dataset for Assessment of Neurological Status",
               "modality": "EDA(+HR, SpO2, temperature, accelerometry)",
               "annotations": "protocol stage markers (relax / physical / cognitive / emotional stress)"},
    "eegmat": {"version": "1.0.0", "title": "EEG During Mental Arithmetic Tasks", "modality": "EEG+ECG",
               "annotations": "segment labels: background (rest) vs mental arithmetic"},
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fetch_physionet(name: str, root: Path) -> dict:
    """Download every file listed in the dataset's published SHA256SUMS.txt and verify each hash."""
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor

    out = root / name
    out.mkdir(parents=True, exist_ok=True)
    meta = PHYSIONET[name]
    base = f"https://physionet.org/files/{name}/{meta['version']}/"
    sums = urllib.request.urlopen(base + "SHA256SUMS.txt", timeout=60).read().decode()
    (out / "SHA256SUMS.txt").write_text(sums)
    expected = dict(reversed(line.split(maxsplit=1)) for line in sums.splitlines() if line.strip())
    expected = {k.strip(): v for k, v in expected.items()}

    def get(rel: str) -> tuple[str, str]:
        dst = out / rel
        if dst.exists() and sha256(dst) == expected[rel]:
            return rel, "verified_existing"
        dst.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(3):
            try:
                urllib.request.urlretrieve(base + rel, dst)
                if sha256(dst) == expected[rel]:
                    return rel, "downloaded_verified"
            except Exception:  # noqa: BLE001
                time.sleep(2)
        return rel, "FAILED"

    with ThreadPoolExecutor(8) as ex:
        status = dict(ex.map(get, sorted(expected)))
    failed = [k for k, v in status.items() if v == "FAILED"]
    return {**meta, "source": f"https://physionet.org/content/{name}/{meta['version']}/", "path": str(out),
            "n_listed": len(expected), "hash_verified": len(expected) - len(failed), "failed": failed}


def fetch_mne(name: str, root: Path) -> dict:
    import mne

    if name == "fnirs_motor":
        p = mne.datasets.fnirs_motor.data_path(path=str(root / "mne"), verbose="error")
        meta = {"title": "MNE fNIRS motor (finger tapping), NIRx", "modality": "fNIRS",
                "annotations": "tapping left/right and control events"}
    else:
        p = mne.datasets.sample.data_path(path=str(root / "mne"), verbose="error")
        meta = {"title": "MNE sample (MEG/EEG, auditory and visual stimuli)", "modality": "MEG+EEG",
                "annotations": "stimulus trigger channel STI 014"}
    return {**meta, "source": f"mne.datasets.{name} (MNE {mne.__version__})", "path": str(p)}


def fetch_ds005815(root: Path, subjects: list[str]) -> dict:
    import urllib.request

    base = "https://s3.amazonaws.com/openneuro.org/ds005815"
    out = root / "ds005815"
    out.mkdir(parents=True, exist_ok=True)
    files = ["dataset_description.json", "participants.tsv", "ancillary/Trigger_Vividness_Data.csv"]
    for s in subjects:
        for ses in ("ses-1", "ses-2"):
            stem = f"{s}/{ses}/eeg/{s}_{ses}_task-task"
            files += [f"{stem}_eeg.vhdr", f"{stem}_eeg.vmrk", f"{stem}_eeg.eeg", f"{stem}_events.tsv",
                      f"{stem}_eeg.json"]
    missing = []
    for f in files:
        dst = out / f
        if dst.exists() and dst.stat().st_size > 0:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            urllib.request.urlretrieve(f"{base}/{f}", dst)
        except Exception as e:  # noqa: BLE001
            missing.append({"file": f, "error": type(e).__name__})
            if dst.exists():
                dst.unlink()
    return {"title": "YOTO visual/auditory imagery EEG (OpenNeuro ds005815)", "modality": "EEG",
            "annotations": "trigger codes (authors' codebook) + trial vividness ratings", "source": base,
            "path": str(out), "missing": missing}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--ds005815-subjects", nargs="*",
                    default=[f"sub-{i:02d}" for i in range(1, 27)])
    args = ap.parse_args()
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    wanted = args.only or [*PHYSIONET, "fnirs_motor", "sample", "ds005815"]
    manifest_path = root / "FETCH_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"datasets": {}}
    for name in wanted:
        t0 = time.time()
        try:
            if name in PHYSIONET:
                info = fetch_physionet(name, root)
            elif name in ("fnirs_motor", "sample"):
                info = fetch_mne(name, root)
            elif name == "ds005815":
                info = fetch_ds005815(root, args.ds005815_subjects)
            else:
                raise ValueError(name)
            files = [p for p in Path(info["path"]).rglob("*") if p.is_file()]
            info.update({"status": "ok", "n_files": len(files),
                         "bytes": sum(p.stat().st_size for p in files),
                         "sha256": {str(p.relative_to(info["path"])): sha256(p) for p in files
                                    if p.stat().st_size < 2_000_000_000},
                         "fetched_at": datetime.now(timezone.utc).isoformat(),
                         "seconds": round(time.time() - t0, 1)})
        except Exception as e:  # noqa: BLE001
            info = {"status": "failed", "error": f"{type(e).__name__}: {e}"}
        manifest["datasets"][name] = info
        manifest_path.write_text(json.dumps(manifest, indent=2))
        print(name, info["status"], info.get("n_files"), info.get("bytes"), flush=True)


if __name__ == "__main__":
    main()
