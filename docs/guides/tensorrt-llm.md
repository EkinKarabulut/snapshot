# Build and deploy a TensorRT-LLM replica

_Documentation for this page is in progress._

> TensorRT-LLM support is experimental and currently limited.

The flow mirrors the [vLLM example](vllm.md): start from the TensorRT-LLM runtime
image, add a small program that cooperates with Snapshot's checkpoint/restore
lifecycle, then deploy the source pod.

<!-- TODO(eng): provide the TensorRT-LLM app, Dockerfile, and pod manifest; confirm the support scope and any TRT-LLM-specific requirements. -->

## Next steps

- [Checkpoint a replica](checkpoint.md)
- [Restore a replica](restore.md)
