#!/usr/bin/env bash
# ANIMUS-P2-XR deterministic resume contract (§27). Read-only inspection + restart-only-incomplete.
# NEVER launches any decoding/confirmatory before the implementation freeze is committed + remote CI-green.
#
# Usage: KUBECONFIG=<kubeconfig> bash resume_p2xr.sh [--relaunch-cohort]
set -uo pipefail
NS=runai-romania-dev
SD="$(cd "$(dirname "$0")" && pwd)"

echo "==================== P2-XR RESUME: jobs ===================="
kubectl -n "$NS" get jobs -l gate=animus-p2xr 2>/dev/null

echo "==================== fMRIPrep per-subject status (PVC markers) ===================="
kubectl -n "$NS" get configmap >/dev/null 2>&1 || { echo "cluster unreachable"; exit 1; }
# spawn a tiny reader to print PVC state (idempotent, ephemeral)
kubectl -n "$NS" delete job p2xr-state-reader --ignore-not-found >/dev/null 2>&1
cat <<'YAML' | kubectl -n "$NS" apply -f - >/dev/null
apiVersion: batch/v1
kind: Job
metadata: {name: p2xr-state-reader, namespace: runai-romania-dev, labels: {gate: animus-p2xr, stage: state-reader}}
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 3600
  template:
    metadata: {labels: {runai/node-pool: cpu-worker, gate: animus-p2xr, stage: state-reader}}
    spec:
      schedulerName: runai-scheduler
      nodeSelector: {runai/node-pool: cpu-worker}
      restartPolicy: Never
      containers:
        - name: r
          image: busybox
          command: ["/bin/sh","-lc"]
          args:
            - |
              echo "-- fmriprep done markers --"; ls -1 /work/animus_p2xr/*/derivatives/*.fmriprep_done 2>/dev/null
              echo "-- status files --"; for f in /work/animus_p2xr/status/*.status; do echo "$f: $(cat $f 2>/dev/null)"; done
              echo "-- feature bundles --"; ls -1 /work/animus_p2xr/features/*.npz 2>/dev/null
              echo "-- embeddings --"; ls -1 /work/animus_p2xr/embeddings/*.npz 2>/dev/null
              echo "-- clip provenance weights_sha --"; grep -o '"weights_sha256": *"[^"]*"' /work/animus_p2xr/audit/clip_runtime_provenance.json 2>/dev/null
          resources: {requests: {cpu: "100m", memory: 256Mi}, limits: {cpu: "500m", memory: 1Gi}}
      volumes: []
YAML
sleep 12
kubectl -n "$NS" logs -l stage=state-reader --tail=60 2>/dev/null

echo "==================== restart rule ===================="
echo "Decision firewall: DO NOT run confirmatory decoding until"
echo "  results/animus_p2xr/P2XR_CONFIRMATORY_IMPLEMENTATION_FREEZE.json is committed + remote CI green."
if [ "${1:-}" = "--relaunch-cohort" ]; then
  echo "Re-applying idempotent fMRIPrep cohort (skips subjects with valid done-markers)..."
  kubectl -n "$NS" apply -f "$SD/fmriprep_cohort.yaml"
else
  echo "Pass --relaunch-cohort to (re)apply the idempotent cohort; it skips already-complete subjects."
fi
