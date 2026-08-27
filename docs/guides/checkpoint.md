# Checkpoint a replica

Checkpointing saves an initialized replica's state as a snapshot artifact. There
are two ways to do it, depending on the use case:

| Method | Choose it when… | Implication |
|--------|-----------------|-------------|
| **`PodSnapshot`** | The running replica can be controlled and tracked — for example, by a controller or platform that manages inference pods | It checkpoints an existing replica directly. Capture terminates the source process, so orchestration must replace it from the snapshot. |
| **`SnapshotJob`** | The running pod cannot be tracked directly — for example, in a pipeline that submits the work | Snapshot runs the whole flow: it creates the replica, checkpoints it, and tears it down. Self-contained, but the source is discarded, so every replica (including the first) comes up via [restore](restore.md). |

These examples use `kubectl` to show the flow. In production, an integrating
controller or platform creates and watches these resources through the Kubernetes
API as part of its control loop.

## Prerequisites

- Snapshot is [installed](../operations/install.md) in the cluster.
- The replica runs a [snapshot-ready image](README.md) and is fully initialized
  (weights loaded, kernels warmed up).

## Option 1 — `PodSnapshot` (checkpoint a running replica)

Point at a replica that is already up and serving. Its pod must expose the
control volume and become ready only after the application writes
`ready-for-snapshot`:

```yaml
spec:
  containers:
    - name: main
      env:
        - name: SNAPSHOT_CONTROL_DIR
          value: /snapshot-control
      readinessProbe:
        exec:
          command: ["cat", "/snapshot-control/ready-for-snapshot"]
      volumeMounts:
        - name: snapshot-control
          mountPath: /snapshot-control
          subPath: main
  volumes:
    - name: snapshot-control
      emptyDir: {}
```

Create a `PodSnapshot` naming that pod and container:

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

The operator binds a cluster-scoped `PodSnapshotContent` and records the
artifact. The CRIU dump terminates the source process after capture.

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
          image: <registry>/vllm-placeholder:<tag>
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
