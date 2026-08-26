# Checkpoint a replica

Checkpointing saves an initialized replica's state as a snapshot artifact. There
are two ways to do it, with an important trade-off.

| Method | What it does | Best for |
|--------|--------------|----------|
| **`PodSnapshot`** | Checkpoints a replica you are already running | The faster path overall — you initialize the first replica once and keep it serving. The trade-off is more orchestration: you bring the replica up, wait until it is ready, then trigger the checkpoint. |
| **`SnapshotJob`** | Runs a replica from a template, checkpoints it once ready, then deletes it | Self-contained, with less orchestration. Fits pipelines that pre-bake a snapshot and then bring up every replica — including the first — via [restore](restore.md). |

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
      name: vllm-replica-0
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
trade-off is that you own the orchestration of bringing it up and triggering the
checkpoint.

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
          image: <your-registry>/vllm-placeholder:<tag>
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
