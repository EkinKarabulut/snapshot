# Build a snapshot-ready TensorRT-LLM image

_Documentation for this page is in progress._

> TensorRT-LLM support is experimental and currently limited.

The build follows the same flow as [vLLM](vllm.md): build the `placeholder` target
with `BASE_IMAGE` set to your TensorRT-LLM runtime image, then push it to a registry
your cluster can pull from.

<!-- TODO(eng): confirm the TensorRT-LLM support scope and any TRT-LLM-specific build or replica requirements. -->

## Next steps

- [Checkpoint a replica](checkpoint.md)
- [Restore a replica](restore.md)
