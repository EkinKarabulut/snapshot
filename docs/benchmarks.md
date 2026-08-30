# Performance Benchmarks

Snapshot captures a fully initialized GPU workload and restores it later on the same node or a different one. These benchmarks show how long that restore takes across several model configurations ranging from 1.5 GB to 145.4 GB of model weights and break the time down into the stages that produce it. We cover the restore path only and we show that the time a restore takes is governed almost entirely by how many bytes have to move, that Snapshot's own coordination cost stays flat at around 10 milliseconds regardless of workload size.

## Introduction

### The Cold Start Problem

A GPU inference workload is slow to start and slow to scale up. Before it can serve a single request, it loads tens or hundreds of gigabytes of weights from storage into GPU memory, initializes the inference engine, CUDA and its runtime libraries, warms up execution kernels and compiles or optimizes computation graphs. For large models this takes minutes, and every new replica pays the full cost again.

When traffic spikes, a platform needs additional replicas immediately, but each one is minutes away from being useful. The usual workaround is to keep idle replicas running, which means paying for GPUs that serve nothing.

### How Snapshot Addresses It

Snapshot addresses this by starting one workload the slow way, which can be combined with [Run:ai Model Streamer](https://github.com/run-ai/runai-model-streamer) to speed up weight loading for that first replica, then freezing it once it is warm and thawing copies of that frozen state whenever a new replica is needed. The restored process resumes at the exact instruction where it stopped, with initialization already done. The question this document answers is a practical one: how long does that thaw actually take and what governs it.

## Benchmarking Setup

The runs used single GPU LLM serving workloads, with the KV cache discarded before capture so that it is not part of the artifact.

| Property | Value |
|---|---|
| Workload type | Single GPU LLM inference server |
| Models | 1.5 GB to 145.4 GB of weights |
| KV cache handling | Discarded before capture |
| Inference engine | vLLM 0.20 |
| GPU | NVIDIA B200 |
| NVIDIA driver | 595 |
| Storage backend | VAST PVC |
| Restore locality | Not pinned. Placement was left to the scheduler, so restores were neither forced onto the capture node nor forced away from it. |

The Weights column is the size of each model's safetensors files on the Hugging Face Hub at the checkpoint's native precision. Weight size is not the same thing as artifact size, since a snapshot artifact also contains the CUDA context, compiled kernels, and workspace buffers.

### Snapshot Measurements

The clock starts when Snapshot is instructed to restore and stops when the workload is running again.

The measurements deliberately exclude container image pull and container startup. Those happen before Snapshot is involved and vary widely between clusters. This matches how restore time was reported in the [Dynamo Snapshot blog post](https://developer.nvidia.com/blog/nvidia-dynamo-snapshot-fast-startup-for-inference-workloads-on-kubernetes/).

A GPU workload restore includes four stages. We report each one separately, along with two totals:

| Stage | What happens | What it means in inference setup |
|---|---|---|
| **agent setup** | The node agent locates the snapshot artifact, identifies the target container, works out which physical GPU on this machine to use, and prepares the filesystem mappings. Preparation only, no data is moved yet. | Nothing yet. This is the moment before the inference engine would begin loading the model. No weights are read and no CUDA work has started. |
| **CRIU restore** | CRIU reads the saved process image from storage and rebuilds everything on the CPU side: the program's memory, its threads, its open files and sockets. This is a large read from storage into host RAM, so its speed is set by the storage backend. | Reading safetensors from disk into host RAM. It also brings back everything a cold start would have to construct from scratch: compiled kernels, captured CUDA graphs, the tokenizer, the scheduler, and the engine's own objects. None of that is rebuilt. |
| **CUDA restore** | cuda-checkpoint copies the GPU side state out of host memory and back onto the GPU: CUDA contexts, streams, and device allocations. Its speed is set by the PCIe link between CPU and GPU. | Creating the CUDA context, moving weights onto the device, autotuning kernels, sizing the KV cache pool, and capturing CUDA graphs. For large models, this causes most of the wait time. The process is just a bulk copy of the final state, bypassing any need to compile, autotune, or profile. |
| **nsrestore total** | Wall clock time for the whole restore operation. It is CRIU restore plus CUDA restore plus the sequencing Snapshot performs between them. | The point a cold start reaches once the engine is constructed and the weights are resident, with warm up already complete. |
| **wake / remap** | The revived process still holds the network address and GPU identifier of the machine it was frozen on. This stage rewrites the pod IP through the inet-remap CRIU plugin, maps the saved GPU UUID onto the device present on this node, and signals the workload that it is awake. | The engine's resume hook: the KV cache pool is mapped back, weight buffers return to the device, and the workload announces itself so the router can send traffic to it. This is the last readiness step before a server accepts requests. |
| **end to end** | agent setup plus nsrestore total plus wake / remap. This is the figure a user experiences. | Engine initialization, weight load, and warm up combined. Add your container start time to get the full pod readiness figure. |

### Cold Start Measurements (Scale from Zero)

**Cold start** is the same workload starting from scratch on the same hardware and the same stack, measured in the scale from zero experiment.

That experiment measured container startup as its own stage, between 4.8 and 5.7 seconds depending
on the model, and we have subtracted it from the Cold start column in the results below. The restore
measurements begin once the container is already running, because CRIU injects the restored process
into a container that has already started, so container startup never appears in them. It is a cost
both paths pay, so removing it from both keeps the comparison fair. With it included, the full cold
start totals ranged from 58.0 to 106.9 seconds.

## Results

All timings are in seconds. Rows are ordered by weight size.

| Model | Weights | agent setup | CRIU restore | CUDA restore | nsrestore total | wake / remap | **end to end** | Cold start |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3 0.6B | 1.5 GB | 0.075 | 2.359 | 0.894 | 3.266 | 0.165 | **3.506** | 52.4 |
| Qwen3 8B | 16.4 GB | 0.080 | 4.733 | 2.795 | 7.541 | 0.450 | **8.071** | 58.3 |
| Qwen3 14B | 29.5 GB | 0.076 | 6.834 | 5.145 | 11.992 | 0.722 | **12.790** | 61.7 |
| GPT-OSS 120B | 65.3 GB | 0.072 | 15.465 | 14.054 | 29.533 | 1.530 | **31.135** | 85.3 |
| Qwen3 32B | 65.5 GB | 0.078 | 9.854 | 8.059 | 17.925 | 1.376 | **19.379** | 79.3 |
| Llama 3.3 70B FP8 | 72.7 GB | 0.069 | 11.033 | 9.809 | 20.854 | 1.516 | **22.439** | 102.1 |
| Qwen2.5 72B | 145.4 GB | 0.084 | 20.039 | 17.898 | 37.951 | 2.832 | **40.867** | 97.8 |


<picture>
  <source media="(prefers-color-scheme: dark)" srcset="img/scale-vs-snapshot-plain-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="img/scale-vs-snapshot-plain-light.svg">
  <img alt="Paired column chart comparing scale from zero against Snapshot for each model. Scale from zero ranges from 52 to 102 seconds, Snapshot from 3.5 to 40.9 seconds." src="img/scale-vs-snapshot-plain-light.svg">
</picture>

**Figure 1: Scale from zero compared with Snapshot** One pair per model configuration, ordered by weight size.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="img/restore-stages-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="img/restore-stages-light.svg">
  <img alt="Stacked column chart of restore time by stage for seven models, ordered by weight size. Totals rise from 3.5 seconds at 1.5 GB to 40.9 seconds at 145.4 GB." src="img/restore-stages-light.svg">
</picture>

**Figure 2: Restore time by stage.** The same Snapshot totals, split into the stages that produce them. The number above each column is the end to end time in seconds.

## Discussion & Learnings

### Checkpoint size is what predicts restore time

Llama 3.3 70B FP8 and Qwen2.5 72B have effectively the same parameter count. FP8 halves the bytes, and the restore time roughly halves with it: 22.4 seconds against 40.9 seconds. GPT-OSS 120B is nominally the largest model in the sweep, but MXFP4 quantization and MoE sparsity put its weights at 65.3 GB, less than half those of Qwen2.5 72B, and it restores faster, at 31.1 seconds.

Quantization, parameter count, and other factors combine to determine the size of the checkpoint, and checkpoint size is what ultimately predicts restore time. When estimating for your own workload, start from how many gigabytes it holds on the GPU rather than from its parameter count.

### Storage throughput sets the floor

CRIU restore is a bulk read of the checkpoint from shared storage into host RAM, and it is the single largest stage in every configuration measured here, between 49 and 67 percent of end to end time. The storage backend therefore largely determines how fast a restore can be.

Every number in this document was measured with the checkpoint on a VAST PVC. A slower backend moves every row up, and a faster one moves every row down, so these results should be read as specific to that setup rather than as a property of Snapshot itself.