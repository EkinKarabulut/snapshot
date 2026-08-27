# Limitations and known issues

Snapshot currently focuses on inference cold-start; further use cases are on the
roadmap.

## Current limitations

- Single-GPU workloads only.
- x86_64 nodes only.
- vGPU is not supported.
- Runs only on NVIDIA GPUs supported by the required CUDA driver.

Multi-GPU and Arm support are on the roadmap.

<!-- TODO(eng): add a Known issues section with validated issues and workarounds. Candidates from field reports:
     - Reusing a PodSnapshot name does not overwrite prior checkpoint content (a checkpoint can report success while restore fails on incompatible content).
     - Restored-process logs are not surfaced to the user.
     - CRIU checkpoint can fail on some smaller GPUs (for example A10) — document minimum requirements.
     - On EKS the default storage class may not support RWX, leaving the checkpoint PVC unbound; set an RWX storage class (see Storage). -->
