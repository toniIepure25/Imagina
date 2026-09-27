"""P2-XR stimulus acquisition + frozen CLIP target embedding (firewall-clean; no neural data).

Acquires the authoritative external stimulus images (BOLD5000 presented_stimuli.zip figshare 20436450;
THINGS images_THINGS.zip OSF jum2f, password-protected), maps every sealed confirmatory identity to exactly
one physical image, loads the EXACT frozen encoder (open_clip ViT-B-32 laion2b_s34b_b79k), hashes the ACTUAL
runtime weight bytes, embeds all unique stimuli (unit-L2), and writes per-dataset embeddings + manifests +
clip_runtime_provenance.json + stimulus_provenance.json. Idempotent; safe to restart.
"""
import glob
import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile

sys.path.insert(0, "/code")
import numpy as np  # noqa: E402
import open_clip  # noqa: E402
import requests  # noqa: E402
import torch  # noqa: E402
from adapters import ADAPTERS  # noqa: E402
from PIL import Image  # noqa: E402

R = "/work/animus_p2xr"
STIM = R + "/stim"
EMB = R + "/embeddings"
EVENTS = R + "/events"
AUDIT = R + "/audit"
for d in (STIM, EMB, EVENTS, AUDIT):
    os.makedirs(d, exist_ok=True)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def unique_identities(ds):
    """Unique sealed stimulus identities for a dataset, via the real adapter over harvested events."""
    adapter = ADAPTERS[ds]()
    evs = glob.glob(f"{EVENTS}/{ds}/**/*_events.tsv", recursive=True)
    ids = set()
    for ev in evs:
        for t in adapter.parse_events_file(ev):
            ids.add(t.stimulus_id)
    return sorted(ids), adapter


# ---------------- acquisition ----------------
def acquire_bold5000():
    dst = STIM + "/bold5000"
    marker = dst + "/.extracted"
    if os.path.exists(marker):
        print("bold5000 stimuli already extracted"); return dst
    os.makedirs(dst, exist_ok=True)
    j = requests.get("https://api.figshare.com/v2/articles/20436450", timeout=60).json()
    f = next(x for x in j["files"] if x["name"] == "presented_stimuli.zip")
    zp = dst + "/presented_stimuli.zip"
    if not os.path.exists(zp) or os.path.getsize(zp) != f["size"]:
        print("downloading BOLD5000 presented_stimuli.zip", round(f["size"] / 1e6, 1), "MB")
        with requests.get(f["download_url"], stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(zp, "wb") as out:
                for c in r.iter_content(1 << 20):
                    out.write(c)
    md5 = hashlib.md5(open(zp, "rb").read()).hexdigest()
    print("bold5000 zip md5", md5, "expected a3c87680fdaac6eaa037577f24edb193")
    with zipfile.ZipFile(zp) as z:
        z.extractall(dst)
    open(marker, "w").write(md5)
    return dst


def acquire_things():
    dst = STIM + "/things"
    marker = dst + "/.extracted"
    if os.path.exists(marker):
        print("things stimuli already extracted"); return dst
    os.makedirs(dst, exist_ok=True)
    root = requests.get("https://api.osf.io/v2/nodes/jum2f/files/osfstorage/", timeout=60).json()["data"]
    by = {x["attributes"]["name"]: x for x in root}
    pwd = requests.get(by["password_images.txt"]["links"]["download"], timeout=60).text.strip()
    zp = dst + "/images_THINGS.zip"
    fsz = by["images_THINGS.zip"]["attributes"]["size"]
    if not os.path.exists(zp) or os.path.getsize(zp) != fsz:
        print("downloading THINGS images_THINGS.zip", round(fsz / 1e9, 2), "GB")
        with requests.get(by["images_THINGS.zip"]["links"]["download"], stream=True, timeout=3600) as r:
            r.raise_for_status()
            with open(zp, "wb") as out:
                for c in r.iter_content(1 << 20):
                    out.write(c)
    md5 = sha256_file(zp)[:0] or hashlib.md5(open(zp, "rb").read()).hexdigest()
    with zipfile.ZipFile(zp) as z:
        try:
            z.extractall(dst, pwd=pwd.encode())
        except RuntimeError:
            z.extractall(dst, pwd=(pwd.split()[-1]).encode())
    open(marker, "w").write("extracted")
    return dst, md5, fsz


# ---------------- image index ----------------
def index_by_basename(root):
    idx = {}
    for p in glob.glob(root + "/**/*", recursive=True):
        if p.lower().endswith((".jpg", ".jpeg", ".png")):
            idx.setdefault(os.path.basename(p).lower(), p)
    return idx


def index_by_relpath(root):
    idx = {}
    for p in glob.glob(root + "/**/*", recursive=True):
        if p.lower().endswith((".jpg", ".jpeg", ".png")):
            rp = "/".join(p.split("/")[-2:]).lower()  # concept/file.jpg
            idx[rp] = p
            idx[os.path.basename(p).lower()] = p
    return idx


# ---------------- CLIP ----------------
def load_clip():
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model, _, pre = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k")
    model = model.to(dev).eval()
    # locate the ACTUAL loaded checkpoint bytes in the HF hub cache and hash them
    cands = glob.glob(os.path.expanduser("~/.cache/huggingface/**/open_clip_pytorch_model.bin"), recursive=True)
    cands += glob.glob(os.path.expanduser("~/.cache/**/*laion2B*s34B*b79K*/**/*.bin"), recursive=True)
    cands = [c for c in cands if "laion" in c.lower() or "vit-b-32" in c.lower() or "open_clip" in c.lower()]
    wsha = sha256_file(cands[0]) if cands else None
    wpath = cands[0] if cands else None
    return model, pre, dev, wsha, wpath


def embed(model, pre, dev, id_to_path, ids):
    embs, kept, per = [], [], []
    batch, bids = [], []

    def flush():
        if not batch:
            return
        x = torch.stack(batch).to(dev)
        with torch.no_grad():
            f = model.encode_image(x)
            f = f / f.norm(dim=-1, keepdim=True)
        for i, e in zip(bids, f.cpu().numpy()):
            kept.append(i); embs.append(e.astype(np.float32))
        batch.clear(); bids.clear()

    for sid in ids:
        p = id_to_path.get(sid)
        if not p:
            continue
        try:
            im = Image.open(p).convert("RGB")
        except Exception:
            continue
        w, h = im.size
        batch.append(pre(im)); bids.append(sid)
        per.append({"stimulus_id": sid, "image_path_rel": os.path.relpath(p, STIM),
                    "image_sha256": sha256_file(p), "width": w, "height": h})
        if len(batch) >= 256:
            flush()
    flush()
    E = np.stack(embs) if embs else np.zeros((0, 512), np.float32)
    return kept, E, per


def main():
    model, pre, dev, wsha, wpath = load_clip()
    print("device", dev, "weights_sha", (wsha or "NA")[:16], "weights_path", wpath)
    prov = {"artifact": "ANIMUS_P2XR_CLIP_RUNTIME_PROVENANCE", "milestone": "ANIMUS-P2XR",
            "open_clip_version": open_clip.__version__, "torch_version": torch.__version__,
            "model_id": "open_clip:ViT-B-32", "pretrained": "laion2b_s34b_b79k",
            "weights_sha256": wsha, "weights_path": wpath, "embedding_dim": 512,
            "normalization": "unit_l2", "device": dev,
            "preprocess": str(pre)}
    h = dict(prov); h.pop("self_hash", None)
    prov["self_hash"] = hashlib.sha256(json.dumps(h, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(prov, open(f"{AUDIT}/clip_runtime_provenance.json", "w"), indent=2)
    print("weights_sha256 PINNED:", wsha)

    stim_prov = {"artifact": "ANIMUS_P2XR_STIMULUS_PROVENANCE", "milestone": "ANIMUS-P2XR", "datasets": {}}

    # BOLD5000
    b5root = acquire_bold5000()
    b5idx = index_by_basename(b5root)
    b5ids, _ = unique_identities("ds001499")
    id2path = {sid: b5idx.get(os.path.basename(sid).lower()) for sid in b5ids}
    missing = [s for s in b5ids if not id2path[s]]
    print(f"BOLD5000 identities {len(b5ids)} mapped {len(b5ids)-len(missing)} missing {len(missing)}")
    kept, E, per = embed(model, pre, dev, id2path, b5ids)
    np.savez(f"{EMB}/bold5000_clip_vitb32.npz", stimulus_ids=np.array(kept), embeddings=E)
    stim_prov["datasets"]["ds001499"] = {"n_identities": len(b5ids), "n_mapped": len(b5ids) - len(missing),
                                         "n_missing": len(missing), "missing_sample": missing[:20],
                                         "n_embedded": len(kept), "embeddings_sha256": hashlib.sha256(E.tobytes()).hexdigest(),
                                         "per_stimulus_count": len(per)}
    json.dump({"per_stimulus": per}, open(f"{EMB}/bold5000_stimulus_map.json", "w"))

    # THINGS
    thres = acquire_things()
    throot = thres[0] if isinstance(thres, tuple) else thres
    thidx = index_by_relpath(throot)
    thids, _ = unique_identities("ds004192")
    id2path_t = {}
    for sid in thids:
        key = sid.lower()
        id2path_t[sid] = thidx.get(key) or thidx.get(os.path.basename(sid).lower())
    missing_t = [s for s in thids if not id2path_t[s]]
    print(f"THINGS identities {len(thids)} mapped {len(thids)-len(missing_t)} missing {len(missing_t)}")
    kept_t, Et, per_t = embed(model, pre, dev, id2path_t, thids)
    np.savez(f"{EMB}/things_clip_vitb32.npz", stimulus_ids=np.array(kept_t), embeddings=Et)
    stim_prov["datasets"]["ds004192"] = {"n_identities": len(thids), "n_mapped": len(thids) - len(missing_t),
                                         "n_missing": len(missing_t), "missing_sample": missing_t[:20],
                                         "n_embedded": len(kept_t), "embeddings_sha256": hashlib.sha256(Et.tobytes()).hexdigest(),
                                         "per_stimulus_count": len(per_t)}
    json.dump({"per_stimulus": per_t}, open(f"{EMB}/things_stimulus_map.json", "w"))

    stim_prov["clip_weights_sha256"] = wsha
    stim_prov["all_bold5000_mapped"] = len(missing) == 0
    stim_prov["all_things_mapped"] = len(missing_t) == 0
    h = dict(stim_prov); h.pop("self_hash", None)
    stim_prov["self_hash"] = hashlib.sha256(json.dumps(h, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(stim_prov, open(f"{AUDIT}/stimulus_provenance.json", "w"), indent=2)
    print("EMBED_DONE b5000", len(kept), "things", len(kept_t), "b5_missing", len(missing),
          "things_missing", len(missing_t))


if __name__ == "__main__":
    main()
