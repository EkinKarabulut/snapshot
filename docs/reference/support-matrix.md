# Support matrix

_This page is in progress; the values below track what Snapshot supports today._

## Inference frameworks

| Framework | Support |
|-----------|---------|
| vLLM | Supported |
| SGLang | Supported |
| TensorRT-LLM | Experimental, single-GPU only |

## Platform

| Requirement | Support |
|-------------|---------|
| GPUs per workload | Single-GPU only |
| CPU architecture | x86_64 (amd64) |
| GPU | NVIDIA GPUs supported by the required CUDA driver |
| CUDA driver | 580 or newer |
| NVIDIA GPU Operator | 26.3 or newer |
| MIG | Must be disabled |
| vGPU | Not supported |
| Container runtime | containerd or CRI-O |
| Storage | A `ReadWriteMany` (RWX) storage class |

Multi-GPU and Arm support are on the roadmap.

<!-- TODO(eng): confirm the minimum Kubernetes version, the exact GPU families validated, the Helm version floor, and any CRI-O/OpenShift specifics. Keep this table to validated values only. -->
