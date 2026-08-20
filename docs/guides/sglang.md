# Build a snapshot-ready SGLang image

_Documentation for this page is in progress._

The build follows the same flow as [vLLM](vllm.md): build the `placeholder` target
with `BASE_IMAGE` set to your SGLang runtime image, then push it to a registry your
cluster can pull from.

<!-- TODO(eng): document the SGLang base image, any server-specific replica settings, and confirm SGLang support scope. -->

## Next steps

- [Checkpoint a replica](checkpoint.md)
- [Restore a replica](restore.md)
