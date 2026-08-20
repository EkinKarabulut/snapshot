# Snapshot

Snapshot is a Kubernetes-native checkpoint and restore system for NVIDIA GPU
workloads. It captures a fully initialized GPU pod — its running process, with
CPU and GPU memory — and restores that state on any compatible node, so a pod
becomes ready in seconds instead of minutes.

Snapshot provides the checkpoint and restore primitives for GPU pods.
Higher-level decisions — which pods to snapshot, when, and how to handle
failures — are left to the systems that integrate it.

> [!WARNING]
> Snapshot is in **alpha** and under active development. APIs and behavior may
> change, and it is not yet ready for production use. See
> [Limitations & known issues](docs/limitations.md).

> [!TIP]
> Want to try it? The **[Quickstart](docs/quickstart.md)** walks through
> capturing a live GPU pod and restoring it into a fresh one.

## The Problem

In inference serving, a replica can't answer a single request until it is fully
initialized — model weights loaded into GPU memory, CUDA and runtime libraries
initialized, execution kernels warmed up, and computation graphs compiled. For
large models, this **cold start** takes minutes.

That cost is paid over and over. Every replica added to meet demand, every
scale-up from zero, every restart or reschedule pays the full cold start again
before it can serve traffic:

- New replicas take minutes to become ready, so autoscaling lags behind demand.
- Teams over-provision idle GPUs just to absorb demand spikes.
- Restarts and reschedules stall serving capacity exactly when it is needed.

## The Solution

Snapshot captures a fully initialized pod once and restores it on demand, so a
new replica comes online in seconds instead of minutes.

- **Capture** — pause a running pod and save its complete execution state (CPU
  and GPU memory) as a portable artifact.
- **Restore** — start a new pod from that artifact on any node with matching GPU
  hardware and driver versions, skipping model loading and warm-up; the process
  resumes from where it was captured.

## When to use it

- **Autoscaling inference** — scale out from an existing snapshot: bring the N+1
  replica and beyond online in seconds to keep pace with demand.
- **Scale-to-zero** — park idle models at zero replicas and restore them quickly
  when capacity is needed again.
- **Faster restarts and reschedules** — recover a pod's initialized state after a
  restart or a move to another node.

Snapshot currently focuses on inference cold-start; further use cases are on the
roadmap.

## Who it's for

Snapshot is a building block for the teams that build inference infrastructure:

- Engineers developing **Kubernetes controllers** that manage the inference
  lifecycle.
- **Platforms that orchestrate inference pipelines** and want fast, repeatable
  GPU startup.

They integrate Snapshot's primitives into their control loop, and the AI
practitioners and MLOps teams running on top get faster scaling without touching
Snapshot directly. Any controller or platform can integrate Snapshot through the
Kubernetes API.

## Prerequisites

Before installing Snapshot, make sure you have:

- A Kubernetes cluster with NVIDIA GPU nodes
- containerd or CRI-O as the container runtime
- [NVIDIA GPU Operator](https://github.com/NVIDIA/gpu-operator) 26.3 or newer, with CUDA driver 580 or newer and MIG disabled
- A `ReadWriteMany` (RWX) storage class
- The [Helm](https://helm.sh/docs/intro/install) CLI

Snapshot's node agent runs as a privileged DaemonSet (`hostPID`, `hostIPC`,
`hostNetwork`) so it can perform CRIU and `cuda-checkpoint`. Your workloads stay
unprivileged — only the agent's namespace needs to permit privileged pods.

<!-- TODO(eng): open items for the team to validate (feed Support matrix / Limitations):
     - minimum Kubernetes version (any non-EOL release, or a specific floor?)
     - minimum GPU Operator version (e2e preflight uses 26.3.0+)
     - Helm floor: Ron confirmed Helm 4 — confirm whether Helm 3 also works
     - CRI-O / OpenShift: whether users must set runtime.type=crio (from Dynamo docs; unconfirmed here)
     - VM support (vGPU is unsupported per Oz 2026-08-20)
     - supported backends: vLLM / SGLang today; TensorRT-LLM experimental single-GPU only (Dynamo v1.3.1; validate for this repo) -->


## Installation

Snapshot installs as a single per-cluster Helm release — a control-plane operator
plus a privileged node agent (DaemonSet) on GPU nodes. Install it in its own
namespace, and run your GPU workloads in separate namespaces.

You can install Snapshot:

- **From a release** (recommended)
- **From source** (build it yourself)

### From a release

Find the latest version on the [releases page](https://github.com/ai-dynamo/snapshot/releases),
then install the published chart, replacing `<VERSION>`:

```bash
helm install snapshot oci://ghcr.io/ai-dynamo/snapshot/snapshot \
  --version <VERSION> \
  --namespace snapshot --create-namespace
```

By default the chart provisions its own RWX checkpoint volume; point it at an
existing claim with `--set storage.pvc.create=false --set storage.pvc.name=<claim>`.
See [Installation](docs/operations/install.md) for storage, RBAC, runtime, and uninstall options.

### From source

Follow the instructions in [Building from source](docs/development/build-from-source.md).

<!-- TODO(eng): confirm the install namespace convention and that oci://ghcr.io/ai-dynamo/snapshot/snapshot at <VERSION> matches the first published alpha release; note whether a from-source install needs image tags before appVersion images are published. -->

## How to use it

You drive Snapshot entirely through Kubernetes resources, with standard tooling.
Create a `PodSnapshot` to capture a running pod, and annotate a new pod with
`nvidia.com/restore-from` to restore it. Higher-level systems wire these
primitives into their own control loop.

| Resource | Scope | Role |
|----------|-------|------|
| `PodSnapshot` | Namespaced | Created by callers to request a capture, or to reference an artifact for restore. |
| `PodSnapshotContent` | Cluster-scoped | System-managed record of the physical artifact, bound to a `PodSnapshot`. Created by the operator, never by the caller. |
| `SnapshotJob` | Namespaced | Runs a pod from a template and captures a `PodSnapshot` from it once ready — a self-contained capture job. |
| `nvidia.com/restore-from` | Namespaced | Pod annotation that triggers a restore from a named `PodSnapshot` in the same namespace. |

Under the hood, a control-plane operator and a per-node agent perform the CRIU
and `cuda-checkpoint` work; see [Architecture](docs/reference/architecture.md) to dive in.
The [API reference](docs/reference/api.md) has full field-level detail and the
capture/restore lifecycle.

Once Snapshot is installed, follow the **[Quickstart](docs/quickstart.md)**
to capture and restore your first pod.

<!-- TODO(eng): validate the SnapshotJob role wording — CRD added recently (#65). -->

## Limitations

Current limitations of the alpha:

- Single GPU only.
- x86_64 nodes only.
- No vGPUs — physical NVIDIA GPUs only.
- Runs only on NVIDIA GPUs supported by the required CUDA driver — see the [Support matrix](docs/reference/support-matrix.md).

Multi-GPU and Arm support are on the roadmap.

## Documentation

**Get started**

- [Quickstart](docs/quickstart.md) — install Snapshot and capture/restore a replica end to end.
- [Usage guides](docs/guides/README.md) — build a snapshot-ready image per server, then checkpoint and restore.

**Reference**

- [API](docs/reference/api.md) — `PodSnapshot`, `PodSnapshotContent`, `SnapshotJob`, and the `restore-from` annotation.
- [Architecture](docs/reference/architecture.md) — operator and node-agent design, and the capture/restore internals.
- [Support matrix](docs/reference/support-matrix.md) — supported backends, GPUs, drivers, and Kubernetes versions.
- [CLI (`snapshotctl`)](docs/reference/cli.md) — lower-level checkpoint/restore from a pod manifest.

**Operations**

- [Installation](docs/operations/install.md) — Helm install, storage (RWX PVC), RBAC, runtime, and uninstall.
- [Troubleshooting](docs/operations/troubleshooting.md) — common failures and where to look.
- [Security](docs/operations/security.md) — the privileged agent, seccomp, and Pod Security.

**Development**

- [Building from source](docs/development/build-from-source.md) — build the images and install locally.
- [Benchmarks](docs/development/benchmarks.md) — how startup performance is measured.

**More**

- [Limitations & known issues](docs/limitations.md) — current limitations and what's on the roadmap.

## Adopters

[NVIDIA Dynamo](https://github.com/ai-dynamo/dynamo), the open-source
inference-serving stack, integrates Snapshot for GPU cold-start. If you run
Dynamo, Snapshot is available through it directly — see
[Snapshotting GPU Workers](https://docs.nvidia.com/dynamo/latest/kubernetes/operations/cold-start-optimizations/dynamo-snapshot)
in the Dynamo docs.

## Contributing

Contributions are welcome under the project's [Apache 2.0 license](LICENSE). See
[CONTRIBUTING.md](CONTRIBUTING.md) — all commits must be signed off (DCO).

## Security

To report a security vulnerability, follow the process in [SECURITY.md](SECURITY.md).

## Status

Snapshot is in early development (pre-1.0). The API types and control-plane
components are in place but not yet feature-complete, and the project is not ready
for production use. Expect breaking changes during alpha. Feedback and issues are
welcome — please [open an issue](https://github.com/ai-dynamo/snapshot/issues).

## License

Snapshot is licensed under the [Apache License 2.0](LICENSE).
