# Restore a replica

Restoring starts a new replica from a snapshot instead of cold-starting it. A new
pod carries the `nvidia.com/restore-from` annotation, naming the `PodSnapshot` to
restore from; the node agent restores the checkpointed state into the container during
pod startup.

## Prerequisites

- A ready `PodSnapshot` exists (see [Checkpoint a replica](checkpoint.md)).
- The new pod uses the same [snapshot-ready image](README.md) and matching replica
  configuration.

## Example

Add the annotation to the replica pod to restore:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: vllm-restored
  namespace: my-inference
  annotations:
    nvidia.com/restore-from: vllm-snapshot
spec:
  containers:
    - name: main
      image: <registry>/vllm-placeholder:<tag>
      # ...the replica configuration that was checkpointed
```

```bash
kubectl apply -f vllm-restored.yaml
kubectl get pod vllm-restored -n my-inference -w
```

The node agent adds a `snapshot/Restored` condition to the pod once the restore
completes — watch it, along with pod readiness, to confirm.

The restored process resumes from the checkpointed state, skipping model loading
and warm-up. In practice, higher-level systems add this annotation to the pods
they create, rather than applying pods by hand.
