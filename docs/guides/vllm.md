# Build a snapshot-ready vLLM image

Snapshot restores a replica by injecting its captured state into a *placeholder*
image: your normal vLLM runtime image wrapped with the restore tooling (CRIU,
`cuda-checkpoint`, `nsrestore`). Build it once and run your vLLM replicas from it.

## Build

From the `agent/` directory, build the `placeholder` target against your vLLM
runtime image and push it to a registry your cluster can pull from:

```bash
docker build \
  --platform linux/amd64 \
  --target placeholder \
  --build-context api=../api \
  --build-arg BASE_IMAGE=<your-vllm-runtime-image> \
  -t <your-registry>/vllm-placeholder:<tag> .

docker push <your-registry>/vllm-placeholder:<tag>
```

Use this image for the replica containers you want to checkpoint and restore.

<!-- TODO(eng): confirm the canonical build invocation (make target vs raw docker build), vLLM base-image guidance, and any vLLM-specific entrypoint/args needed for a checkpointable replica. -->

## Next steps

- [Checkpoint a replica](checkpoint.md)
- [Restore a replica](restore.md)
