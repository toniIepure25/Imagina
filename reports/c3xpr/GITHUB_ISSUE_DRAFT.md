# DRAFT — GitHub Issue (NOT POSTED)

**Do not post automatically.** For review only. Repo: `horikawa-t/MindCaptioning`.
Title: *ROI masks + native BOLD reference for raw-fMRI reproducibility (exact spatial correspondence)*

---

Thanks for releasing the Mind Captioning data and code.

We are running an independent raw-fMRI reproducibility analysis from OpenNeuro **ds005191 v1.0.2** and
the Figshare **25808179** `.mat` release, and want to reuse your **exact** ROI definitions.

From the public artifacts we can read the ROI membership (`metainf.roiind_value` / `roiname`) and the
per-voxel world coordinates (`metainf.xyz`, a regular 2 mm lattice), and `getRoiVoxelIdx.m` selects ROI
voxels from those. What is missing to place the ROIs exactly into an **independently preprocessed
native functional space** is:

- a functional **reference image (BOLDref)** the released voxels are defined on, and/or an
  **affine/parent-grid** for the released voxel indices, and/or the **raw→released transform**; and
- the retinotopy/localizer + manually-corrected FreeSurfer derivatives that defined the ROIs (not in
  ds005191).

**Smallest thing that would unblock us:** per-subject **VC/LVC/HVC (+V1) NIfTI masks + the matching
native-space BOLD reference** for S1–S6. Any of the alternatives above would also work.

We do not need features, captions, decoder outputs, checkpoints, or any performance/ranking info — just
the spatial reference. Happy to cite as you prefer and share our code. Thank you!
