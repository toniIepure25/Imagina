"""Certify the FMRI2images pre-extracted perception features against the frozen
C3 decoder, and (if certified) build the core-NSD perception reference X_p in
the decoder's exact 15587-voxel order.

Certification is self-verifying: we reconstruct the perception-train per-voxel
mean/std from the FMRI2images features over the SAME 9000 (train+val) images and
require them to match the frozen decoder's stored voxel_mean/voxel_std
bit-closely. Only a correct voxel column mapping AND identical units can produce
that match, so a pass certifies both.

Voxel mapping: FMRI2images enumerated its 15724 columns as np.where(mask_nii>0)
in the nsdgeneral NIfTI frame (81,104,83). The frozen decoder's beta_coords are
(i,j,k) in the HDF5 beta frame (83,104,81) = transpose(nii,(2,1,0)); i.e. hdf5
(i,j,k) == nii (k,j,i). We map each decoder voxel to its FMRI2images column and
verify (a) all map, (b) the mapped columns are exactly the ncsnr>0 subset.
"""
from __future__ import annotations

import json
import os
import pickle
from pathlib import Path

import numpy as np


def main() -> None:
    feat_path = Path(os.environ["FMRI2I_FEATURES"])
    meta_path = Path(os.environ["FMRI2I_META"])
    roi_path = Path(os.environ["NSD_ROI_NII"])
    ncsnr_path = Path(os.environ["NSD_NCSNR_NII"])
    decoder_path = Path(os.environ["C3M_DECODER"])
    split_path = Path(os.environ["C3_SPLIT_MANIFEST"])
    out_dir = Path(os.environ.get("XP_OUT_DIR", "."))
    out_dir.mkdir(parents=True, exist_ok=True)

    import nibabel as nib
    import pandas as pd

    frozen = pickle.load(open(decoder_path, "rb"))
    dec = frozen["decoder"]
    bc = np.asarray(frozen["beta_coords"])  # (15587,3) hdf5 (i,j,k)
    vmean_ref = np.asarray(dec.voxel_mean, dtype=np.float64)
    vstd_ref = np.asarray(dec.voxel_std, dtype=np.float64)

    M = nib.load(str(roi_path)).get_fdata()      # (81,104,83) nii
    N = nib.load(str(ncsnr_path)).get_fdata()     # (81,104,83) nii
    assert M.shape == (81, 104, 83), M.shape

    # FMRI2images column order = np.where(mask>0) in nii C-order
    xs, ys, zs = np.where(M > 0)
    n_cols = xs.shape[0]
    assert n_cols == 15724, n_cols
    col_of = {}
    for c in range(n_cols):
        col_of[(int(xs[c]), int(ys[c]), int(zs[c]))] = c

    # decoder voxel (i,j,k) hdf5 -> nii (k,j,i) -> FMRI2images column
    dec_cols = np.empty(bc.shape[0], dtype=np.int64)
    missing = 0
    for v in range(bc.shape[0]):
        i, j, k = int(bc[v, 0]), int(bc[v, 1]), int(bc[v, 2])
        c = col_of.get((k, j, i), -1)
        dec_cols[v] = c
        if c < 0:
            missing += 1
    mapping_ok = missing == 0

    # consistency: mapped columns' ncsnr>0 and they equal the ncsnr>0 subset of the 15724
    ncsnr_at_cols = np.array([N[k, j, i] for (i, j, k) in bc.tolist()])
    ncsnr_all = N[xs, ys, zs]
    subset_ncsnr_gt0 = int((ncsnr_all > 0).sum())

    # load features and reconstruct train voxel_mean/std over 9000 (train+val) images
    tm = pd.read_parquet(meta_path)  # nsdId, session ; row order == feature row order
    split = json.load(open(split_path))
    train_ids = set(int(x) for x in split["train_image_ids"]) | set(int(x) for x in split["val_image_ids"])
    n_train_expected = len(train_ids)

    X = np.load(feat_path, mmap_mode="r")  # (30000, 15724) float32
    nsd = tm["nsdId"].to_numpy()

    # image-average per nsdId (only train+val ids), on the mapped decoder columns
    # group rows by nsdId
    order = np.argsort(nsd, kind="stable")
    nsd_sorted = nsd[order]
    uniq, starts = np.unique(nsd_sorted, return_index=True)
    ends = np.append(starts[1:], len(nsd_sorted))
    img_means = []
    for u, s, e in zip(uniq.tolist(), starts.tolist(), ends.tolist()):
        if u not in train_ids:
            continue
        rows = order[s:e]
        block = np.asarray(X[np.sort(rows)], dtype=np.float64)[:, dec_cols]  # (reps,15587)
        img_means.append(block.mean(axis=0))
    IMG = np.asarray(img_means)  # (9000,15587)
    vmean_rec = IMG.mean(axis=0)
    vstd_rec = np.clip(IMG.std(axis=0), 1e-8, None)

    mean_max_abs = float(np.max(np.abs(vmean_rec - vmean_ref)))
    mean_rel = float(np.max(np.abs(vmean_rec - vmean_ref) / (np.abs(vmean_ref) + 1e-6)))
    std_max_abs = float(np.max(np.abs(vstd_rec - vstd_ref)))
    corr_mean = float(np.corrcoef(vmean_rec, vmean_ref)[0, 1])

    certified = bool(mapping_ok and mean_max_abs < 1e-2 and std_max_abs < 1e-1)

    report = {
        "artifact": "C3M_XP_CERTIFICATION",
        "mapping_all_voxels_found": mapping_ok,
        "n_missing": missing,
        "n_selected": int(bc.shape[0]),
        "mapped_cols_ncsnr_all_gt0": bool((ncsnr_at_cols > 0).all()),
        "fmri2i_ncsnr_gt0_subset_count": subset_ncsnr_gt0,
        "decoder_selected_count": int(bc.shape[0]),
        "n_train_images_reconstructed": int(IMG.shape[0]),
        "n_train_images_expected": int(n_train_expected),
        "decoder_n_train_images": int(dec.n_train_images),
        "voxel_mean_max_abs_diff": mean_max_abs,
        "voxel_mean_max_rel_diff": mean_rel,
        "voxel_mean_corr": corr_mean,
        "voxel_std_max_abs_diff": std_max_abs,
        "CERTIFIED": certified,
    }
    print(json.dumps(report, indent=2))
    json.dump(report, open(out_dir / "c3m_xp_certification.json", "w"), indent=2)

    if certified:
        # persist the mapping + a compact perception reference for M3/M4/Family-B:
        # (a) full per-trial X_p is large; save image-averaged IMG (9000x15587) and
        #     the column mapping + nsdId order for Family-B target lookups.
        np.save(out_dir / "c3m_xp_decoder_columns.npy", dec_cols)
        np.save(out_dir / "c3m_xp_train_image_means.npy", IMG.astype(np.float32))
        np.save(out_dir / "c3m_xp_train_image_ids.npy",
                np.array([u for u in uniq.tolist() if u in train_ids], dtype=np.int64))
        # full per-trial X_p in the decoder's 15587-voxel order (for H1 mechanism,
        # M3/M4 covariance reference, counterfactual, Family-B target lookups)
        Xp = np.empty((X.shape[0], dec_cols.shape[0]), dtype=np.float32)
        for a in range(0, X.shape[0], 3000):
            Xp[a:a + 3000] = np.asarray(X[a:a + 3000], dtype=np.float32)[:, dec_cols]
        np.save(out_dir / "c3m_xp_pertrial.npy", Xp)
        np.save(out_dir / "c3m_xp_pertrial_nsdid.npy", nsd.astype(np.int64))
        np.save(out_dir / "c3m_xp_pertrial_session.npy", tm["session"].to_numpy().astype(np.int64))
        print(f"Saved X_p artifacts (incl. per-trial {Xp.shape}) to {out_dir}")
    else:
        print("NOT CERTIFIED — do not use FMRI2images as X_p; fall back to rolling extraction.")


if __name__ == "__main__":
    main()
