# `snapshotctl` CLI

`snapshotctl` is a lower-level utility for checkpointing and restoring a pod
directly from a pod manifest. It is not the primary path — most users drive
Snapshot through the [Kubernetes resources](../guides/README.md) — but it is handy
for validation and debugging, and it is a quick way to try checkpoint/restore by
hand.

## Requirements

- The Snapshot Helm chart is installed in the target namespace, with the
  `snapshot-agent` DaemonSet running and the checkpoint PVC mounted.
- `checkpoint` requires the operator (it resolves the `PodSnapshot` into a
  capture). `restore` is handled by the agent directly from pod annotations.

## Checkpoint

`snapshotctl checkpoint` creates a `PodSnapshot` from a pod manifest and waits for
the agent to capture it:

```bash
snapshotctl checkpoint \
  --manifest ./vllm-replica-pod.yaml \
  --container main \
  --namespace my-inference
```

The manifest must be a `Pod` (not a Deployment or Job) using a
[snapshot-ready image](../guides/README.md).

## Restore

`snapshotctl restore` starts a new pod from a checkpoint, or patches restore
metadata onto an existing, snapshot-compatible pod:

```bash
# from a manifest
snapshotctl restore \
  --manifest ./vllm-replica-pod.yaml \
  --checkpoint-id <checkpoint-id> \
  --containers main \
  --namespace my-inference

# or restore an existing pod in place
snapshotctl restore \
  --pod vllm-restore-target \
  --checkpoint-id <checkpoint-id> \
  --containers main \
  --namespace my-inference
```

The source README for the tool lives at
[`operator/cmd/snapshotctl/README.md`](../../operator/cmd/snapshotctl/README.md).

<!-- TODO(eng): confirm the full flag set, the output format, and the checkpoint-id lifecycle. -->
