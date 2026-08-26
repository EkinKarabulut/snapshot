# Build a snapshot-ready vLLM image

Snapshot restores a replica by injecting its captured state into a *placeholder*
image: the normal vLLM runtime image wrapped with the restore tooling (CRIU,
`cuda-checkpoint`, `nsrestore`). Build it once and run vLLM replicas from it.

## Build

From the `agent/` directory, build the `placeholder` target against the vLLM
runtime image and push it to a registry the cluster can pull from:

```bash
docker build \
  --platform linux/amd64 \
  --target placeholder \
  --build-context api=../api \
  --build-arg BASE_IMAGE=<vllm-runtime-image> \
  -t <registry>/vllm-placeholder:<tag> .

docker push <registry>/vllm-placeholder:<tag>
```

Use this image for the replica containers to checkpoint and restore.

<!-- TODO(eng): confirm the canonical build invocation (make target vs raw docker build), vLLM base-image guidance, and any vLLM-specific entrypoint/args needed for a checkpointable replica. -->

## Next steps

- [Checkpoint a replica](checkpoint.md)
- [Restore a replica](restore.md)
