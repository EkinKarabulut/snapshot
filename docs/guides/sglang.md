# Build and deploy an SGLang replica

_Documentation for this page is in progress._

The flow mirrors the [vLLM example](vllm.md): start from the SGLang runtime image,
add a small program that cooperates with Snapshot's checkpoint/restore lifecycle
(pause and free the GPU before checkpoint, resume after restore), then deploy the
source pod.

<!-- TODO(eng): provide the SGLang app, Dockerfile, and pod manifest; document the base image and SGLang-specific pause/resume; confirm support scope. -->

## Next steps

- [Checkpoint a replica](checkpoint.md)
- [Restore a replica](restore.md)
