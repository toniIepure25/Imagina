# C3XDR-R1 — Remote Execution Environment Provenance

**Execution attempt 2** of the sealed C3XDR question (`c3xdr_execution_seal.json` self_hash
`7afc7946…`). Protocol / Model A / estimator / ROI / storage threshold **UNCHANGED**. No secrets are
recorded; the kubeconfig is never committed.

## Remote cluster (audited via explicit `--kubeconfig`, not default/localhost)
- Kubeconfig `C:/Users/ComputaCenter/Downloads/antoniu_iepure.yaml` (5626 bytes, sha256 `d9380cc3…`) —
  **found** (attempt-1 did not test it). Context `antoniu-iepure@default`, namespace
  `runai-romania-dev`, server `https://10.130.123.31:10443` — **TCP reachable + authenticated** (RBAC
  scoped to the namespace; kube-system forbidden as expected).
- Permissions (namespace): get/create pods, jobs, PVCs; get logs; create pods/exec; delete jobs; get
  nodes/storageclasses → a valid Kubernetes container-execution environment.

## Execution pod (sealed lead confirmed)
- `orchestraiq-jupyter-5d6c688775-fbxj5` — **Running 5d+**, node `k8s-worker-gpu-node-xe8545`.
- Image `quay.io/jupyter/pytorch-notebook:cuda12-latest`, digest
  `sha256:85ab930435b7afc06396e2949a4fe508d027a7980a319bec6a92f827578e5343`.
- Compute: **256 CPU, 1007 GiB RAM, NVIDIA A100-SXM4-40GB**, kernel 6.8, Python 3.13.
- Base image has **no** fMRIPrep/FSL/FreeSurfer/SPM/nibabel (a pinned preprocessing container Job would
  be required — container execution itself is not the blocker).

## Persistent storage — **PASS**
- Two NFS PVCs (nfs-client StorageClass, RWO, Bound 5d+): `orchestraiq-jupyter-pvc` @
  `/home/jovyan/legacy-work` and `orchestraiq-jupyter-extra-pvc` @ `/home/jovyan/work`, both backed by
  `10.130.200.199:/ifs/bcm11/...` (nfs4): **138 T total, 107 T available**. Inodes: 302 billion free.
- Usable persistent free storage ≈ **107 TB ≫ 300 GB** required. Ephemeral volumes (node-local xfs
  `/local-data`, tmpfs `/dev/shm`, emptyDir) are explicitly excluded from the certification.
- Persistence established by the **Kubernetes PVC contract** (Bound nfs-client, NFS network-backed,
  survives pod restart) + multi-day age; a write-probe was intentionally **not** performed to avoid
  mutating the user's active jupyter workspace (sealed: do not disturb production workloads).

## Net infrastructure verdict
`C3XDR_R1_REMOTE_INFRA_PASS` — the storage/compute blocker that stopped C3XDR attempt-1
(`C3XDR_BLOCKED_STORAGE`) is **resolved**. The remaining barrier is scientific provenance (see the final
report and `results/c3xdr_r1/roi_provenance.json`), not infrastructure.
