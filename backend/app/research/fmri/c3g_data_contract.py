"""C3G Phase 1 — state-geometry data contract for subj01.

Builds the canonical analysis dataset that all C3G geometry analyses consume,
with an explicit machine-readable manifest (row identities, state, content,
ROI, source hashes, transforms, exclusions) and strict determinism.

States (NSD-Imagery session, same 6 Set-B stimuli, session-controlled):
  P = Set-B VISION  (visB rows 192:240, 48 trials, 6 content x 8 reps)
  I = Set-B IMAGERY (imgB rows 336:384 + 624:672, 96 trials, 6 content x 16 reps)
Set-A (simple bars) VISION/IMAGERY are built as OOD secondary.
Anchor perception distribution: core-NSD X_p (rolling-extracted betas_fithrf).

All voxel arrays are in the frozen decoder's exact 15587-voxel order (beta_coords).
ROI labels (prf-visualrois, streams) are mapped to that order via the certified
hdf5<->nii axis transpose (2,1,0).

Outputs (under C3G_DATA_DIR): states/*.npy, roi/*.npy, and c3g_data_manifest.json.
No imagery content label is used to transform any array here.
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import time
from pathlib import Path

import numpy as np


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def _sha256_arr(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def _roi_labels_at(coords: np.ndarray, nii_path: Path) -> np.ndarray:
    """Integer ROI label per voxel (in beta_coords order). nii frame (81,104,83)
    -> hdf5 frame via transpose(2,1,0); decoder (i,j,k) == nii (k,j,i)."""
    import nibabel as nib
    A = nib.load(str(nii_path)).get_fdata()
    assert A.shape == (81, 104, 83), A.shape
    return np.array([int(round(A[k, j, i])) for (i, j, k) in coords.tolist()], dtype=np.int64)


def main() -> None:
    manifest_path = Path(os.environ["C3M_EVENT_MANIFEST"])
    decoder_path = Path(os.environ["C3M_DECODER"])
    imagery_betas = Path(os.environ["NSD_IMAGERY_BETAS"])
    xp_dir = Path(os.environ["XP_DIR"])
    roi_dir = Path(os.environ["NSD_ROI_DIR"])
    out_dir = Path(os.environ["C3G_DATA_DIR"])
    (out_dir / "states").mkdir(parents=True, exist_ok=True)
    (out_dir / "roi").mkdir(parents=True, exist_ok=True)

    from app.research.fmri.nsdimagery_transfer import extract_imagery_rows

    frozen = pickle.load(open(decoder_path, "rb"))
    coords = np.asarray(frozen["beta_coords"])
    rows = json.load(open(manifest_path))["rows"]

    def block(event_type, stim_set):
        rr = [r for r in rows if r["event_type"] == event_type and r["stimulus_set"] == stim_set]
        rr = sorted(rr, key=lambda r: r["beta_row_index"])
        return rr

    def build(name, event_type, stim_set):
        rr = block(event_type, stim_set)
        idx = [r["beta_row_index"] for r in rr]
        X = extract_imagery_rows(imagery_betas, coords, idx).astype(np.float32)
        np.save(out_dir / "states" / f"{name}.npy", X)
        meta = [{"beta_row_index": r["beta_row_index"], "run": r["run_name"],
                 "content_pool_index": r["candidate_pool_index"],
                 "content_identity": r["target_identity"], "cue": r.get("cue")}
                for r in rr]
        json.dump(meta, open(out_dir / "states" / f"{name}_meta.json", "w"), indent=1)
        return {"rows": len(rr), "shape": [int(X.shape[0]), int(X.shape[1])],
                "row_indices": idx, "content_pool_indices": [r["candidate_pool_index"] for r in rr],
                "array_sha256": _sha256_arr(X), "meta_file": f"states/{name}_meta.json"}

    states = {
        "setB_vision": build("setB_vision", "vision", "B"),
        "setB_imagery": build("setB_imagery", "imagery", "B"),
        "setA_vision": build("setA_vision", "vision", "A"),
        "setA_imagery": build("setA_imagery", "imagery", "A"),
    }

    # anchor perception X_p (concat rolling-extracted sessions, deterministic order)
    sess_files = sorted(f for f in xp_dir.glob("xp_*_session*.npy") if "nsdid" not in f.name)
    nsd_files = sorted(xp_dir.glob("xp_*_session*_nsdid.npy"))
    Xp = np.concatenate([np.load(f).astype(np.float32) for f in sess_files], axis=0)
    nsd = np.concatenate([np.load(f).astype(np.int64) for f in nsd_files], axis=0)
    sess = np.concatenate([np.full(np.load(f).shape[0], int(f.name.split("session")[1][:2]))
                           for f in sess_files], axis=0)
    np.save(out_dir / "states" / "xp_core.npy", Xp)
    np.save(out_dir / "states" / "xp_core_nsdid.npy", nsd)
    np.save(out_dir / "states" / "xp_core_session.npy", sess)

    # Set-B target nsdIds (5 resolvable in core NSD; nsd00000 absent)
    setB_target_nsdids = {6: 28752, 7: 30857, 8: 53882, 9: 61178, 10: 65873, 11: 0}
    core_matches = {pi: sorted(np.where(nsd == nid)[0].tolist())
                    for pi, nid in setB_target_nsdids.items() if nid != 0 and (nsd == nid).any()}

    # ROI labels in beta_coords order
    prf = _roi_labels_at(coords, roi_dir / "prf-visualrois.nii.gz")
    streams = _roi_labels_at(coords, roi_dir / "streams.nii.gz")
    np.save(out_dir / "roi" / "prf_visualrois_labels.npy", prf)
    np.save(out_dir / "roi" / "streams_labels.npy", streams)

    # prf label map (NSD): 1 V1v,2 V1d,3 V2v,4 V2d,5 V3v,6 V3d,7 hV4
    roi_families = {
        "prf": {"V1": [1, 2], "V2": [3, 4], "V3": [5, 6], "hV4": [7]},
        # streams (NSD): 1 early,2 midventral,3 midlateral,4 midparietal,5 ventral,6 lateral,7 parietal
        "streams": {"early": [1], "ventral": [2, 5], "lateral": [3, 6], "parietal": [4, 7]},
    }
    roi_counts = {
        "prf": {k: int(np.isin(prf, v).sum()) for k, v in roi_families["prf"].items()},
        "streams": {k: int(np.isin(streams, v).sum()) for k, v in roi_families["streams"].items()},
        "nsdgeneral_total": int(coords.shape[0]),
    }

    manifest = {
        "artifact": "C3G_DATA_CONTRACT_MANIFEST",
        "subject": "subj01",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source_c3m_sha": "11445aa90486865ae1fcb33b4e3699e6e501f419",
        "voxel_space": "nsdgeneral AND ncsnr>0, frozen decoder beta_coords order, V=15587",
        "states": states,
        "anchor_perception_xp": {
            "shape": [int(Xp.shape[0]), int(Xp.shape[1])], "sessions": sorted(set(sess.tolist())),
            "array_sha256": _sha256_arr(Xp), "nsdid_sha256": _sha256_arr(nsd),
            "beta_version": "betas_fithrf",
        },
        "setB_content": {"pool_indices": [6, 7, 8, 9, 10, 11],
                         "nsdids": setB_target_nsdids,
                         "core_nsd_perception_matches": {str(k): v for k, v in core_matches.items()},
                         "note": "nsd00000 (pool 11) absent in subj01 core NSD; excluded from "
                                 "core-perception content match"},
        "roi": {"families": roi_families, "counts": roi_counts,
                "prf_labels_sha256": _sha256_arr(prf), "streams_labels_sha256": _sha256_arr(streams),
                "prf_nii_sha256": _sha256_file(roi_dir / "prf-visualrois.nii.gz"),
                "streams_nii_sha256": _sha256_file(roi_dir / "streams.nii.gz")},
        "frozen_input_hashes": {
            "decoder_weights_hash": frozen["weights_hash"],
            "roi_selection_hash": frozen["roi_provenance"]["selection_hash"],
            "imagery_betas_sha256": _sha256_file(imagery_betas),
            "event_manifest_hash": json.load(open(manifest_path)).get("manifest_hash"),
        },
        "exclusions": ["Set C conceptual imagery (no ground-truth image)", "attention runs",
                       "nsd00000 from core-perception content match"],
        "transforms_applied": "NONE (raw int16->float32, no scaling); C3M alignment applied only in "
                              "analysis stages that explicitly require it",
        "seed": 20260826,
    }
    manifest["self_hash"] = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(manifest, open(out_dir / "c3g_data_manifest.json", "w"), indent=2)
    print(f"Wrote {out_dir}/c3g_data_manifest.json")
    print(json.dumps({"states": {k: v["shape"] for k, v in states.items()},
                      "xp_core": manifest["anchor_perception_xp"]["shape"],
                      "roi_counts": roi_counts,
                      "core_perception_matches": {k: len(v) for k, v in core_matches.items()},
                      "self_hash": manifest["self_hash"][:16]}, indent=2))


if __name__ == "__main__":
    main()
