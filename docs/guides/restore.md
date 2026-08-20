# Restore a replica

Restoring starts a new replica from a snapshot instead of cold-starting it. You add
the `nvidia.com/restore-from` annotation to a new pod, naming the `PodSnapshot` to
restore from; the node agent restores the captured state into the container during
pod startup.

## Prerequisites

- A ready `PodSnapshot` exists (see [Checkpoint a replica](checkpoint.md)).
- The new pod uses the same [snapshot-ready image](README.md) and matching replica
  configuration.

## Example

Add the annotation to the replica pod you want to restore:

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
      image: <your-registry>/vllm-placeholder:<tag>
      # ...the replica configuration you captured
```

```bash
kubectl apply -f vllm-restored.yaml
kubectl get pod vllm-restored -n my-inference -w
```

The restored process resumes from the captured state, skipping model loading and
warm-up. In practice, higher-level systems add this annotation to the pods they
create, rather than applying pods by hand.

<!-- TODO(eng): validate the restore-from annotation semantics, the required pod fields, and how restore interacts with readiness and scheduling. -->
