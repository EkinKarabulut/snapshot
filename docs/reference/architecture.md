# Architecture

_Documentation for this page is in progress._

<!-- TODO(eng): write the Architecture page. Suggested coverage:
     - Operator (control plane): reconcilers, PodSnapshot -> PodSnapshotContent binding, lifecycle, cleanup.
     - Node agent: privileged DaemonSet; CRIU + cuda-checkpoint; dump/restore stages; seccomp profile.
     - Custom resources: PodSnapshot, PodSnapshotContent, SnapshotJob, nvidia.com/restore-from.
     - Capture and restore flow (mermaid diagrams).
     - Storage: shared RWX checkpoint PVC; agentMount vs podMount.
     - Design principles: mechanics not policy; everything as Kubernetes resources. -->
