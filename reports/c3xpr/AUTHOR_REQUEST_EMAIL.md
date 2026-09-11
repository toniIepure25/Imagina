# DRAFT — Author Request (NOT SENT)

**Do not send automatically.** Prepared for review only. To: Dr. Tomoyasu Horikawa (corresponding
author, Mind Captioning). Subject: *Request for ROI masks + native BOLD reference for an independent
raw-fMRI reproducibility analysis (ds005191 / Mind Captioning)*

---

Dear Dr. Horikawa,

We are performing an independent, prospectively-preregistered **raw-fMRI reproducibility** analysis of
the Mind Captioning imagery data, working from the public releases:

- Raw BIDS: OpenNeuro **ds005191 v1.0.2**
- Preprocessed release: Figshare **25808179** (the per-subject `.mat` files)

We already have and follow the **published functional-preprocessing methodology**; our goal is only to
re-estimate imagery-period responses from the raw BOLD in a way that reuses your **exact** ROI
definitions.

The one piece we cannot reconstruct from the public artifacts is the **exact spatial correspondence
between the released ROI voxel indices and a raw-derived native functional space.** The released `.mat`
provides ROI membership (`metainf.roiind_value`, `roiname`) and per-voxel world coordinates
(`metainf.xyz`, a regular 2 mm lattice), but it does not include an affine/header, a functional
reference image, or a raw→released transform, and the dataset does not include the retinotopy/localizer
runs (or the manually-corrected FreeSurfer surfaces) that defined the ROIs. So we can rebuild the ROI
point set in the released frame but cannot place it exactly into an independently preprocessed native
functional space.

Would it be possible to share, for subjects **S1–S6**, the **smallest** artifact that resolves this:

- **per-subject VC / LVC / HVC (and V1 if available) NIfTI ROI masks, together with the matching
  native-space BOLD reference image** they are defined on?

If that is inconvenient, any one of the following would also suffice: the ROI voxel coordinates with
parent-grid dimensions and affine; the released BOLD reference plus the raw→released transform chain; or
the FreeSurfer/registration derivative used for functional↔anatomical alignment.

We do **not** need any semantic features, captions, decoder outputs, model checkpoints, or any
performance/ranking information — only the spatial reference above. We are glad to cite the masks/
reference as you prefer and to share our reproducibility code.

Thank you very much for the openly released data and for considering this request.

Best regards,
[name] — [affiliation] — iepuretoni@yahoo.com
