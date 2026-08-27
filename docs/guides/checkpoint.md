# Checkpoint a replica

Checkpointing saves an initialized replica's state as a checkpoint artifact. There
are two ways to do it, depending on the use case:

| Method | Choose it when… | Implication |
|--------|-----------------|-------------|
| **`PodSnapshot`** | The running replica can be controlled and tracked — for example, by a controller or platform that manages inference pods | The most efficient path — it checkpoints a replica that stays serving. It needs orchestration: bringing the replica up, waiting until it is ready, then triggering the checkpoint. |
| **`SnapshotJob`** | The running pod cannot be tracked directly — for example, in a pipeline that submits the work | Snapshot runs the whole flow: it creates the replica, checkpoints it, and tears it down. Self-contained, but the source is discarded, so every replica (including the first) comes up via [restore](restore.md). |

These examples use `kubectl` to show the flow. In production, an integrating
controller or platform creates and watches these resources through the Kubernetes
API as part of its control loop.

## Prerequisites

- Snapshot is [installed](../operations/install.md) in the cluster.
- The replica runs a [snapshot-ready image](README.md) and is fully initialized
  (weights loaded, kernels warmed up).

## Option 1 — `PodSnapshot` (checkpoint a running replica)

Point at a replica that is already up and serving. Create a `PodSnapshot` naming its
pod and the container to checkpoint:

```yaml
apiVersion: nvidia.com/v1alpha1
kind: PodSnapshot
metadata:
  name: vllm-snapshot
  namespace: my-inference
spec:
  source:
    podRef:
      name: vllm-source-<pod-id>
      containers:
        - main
```

```bash
kubectl apply -f vllm-snapshot.yaml
kubectl wait --for=condition=Ready podsnapshot/vllm-snapshot \
  -n my-inference --timeout=30m
```

The operator binds a cluster-scoped `PodSnapshotContent` and records the artifact.
Because the replica keeps running and serving, this is the faster path — the
trade-off is the orchestration it requires: bringing the replica up, waiting for
readiness, then triggering the checkpoint.

## Option 2 — `SnapshotJob` (checkpoint a throwaway replica)

`SnapshotJob` runs a replica from a pod template, checkpoints it once ready, and
completes from the resulting `PodSnapshot` — removing the source replica. There is
no long-running replica to manage, which fits pipeline use cases.

```yaml
apiVersion: nvidia.com/v1alpha1
kind: SnapshotJob
metadata:
  name: vllm-snapshot-job
  namespace: my-inference
spec:
  podSnapshotTemplate:
    targetContainers:
      - main
  podTemplate:
    spec:
      containers:
        - name: main
          image: <registry>/vllm-snapshot:<tag>
          # ...the replica configuration to checkpoint
```

```bash
kubectl apply -f vllm-snapshot-job.yaml
kubectl wait --for=condition=Completed snapshotjob/vllm-snapshot-job \
  -n my-inference --timeout=30m

# the resulting PodSnapshot to restore from:
kubectl get snapshotjob vllm-snapshot-job -n my-inference \
  -o jsonpath='{.status.podSnapshotName}'
```

Because the source replica is deleted, every serving replica — including the
first — is brought up via [restore](restore.md).
