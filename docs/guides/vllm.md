# Build a snapshot-ready vLLM image

Snapshot restores a replica by injecting its captured state into a *placeholder*
image: a vLLM runtime image prepared with the application and
container layout Snapshot expects. The Snapshot agent injects the restore
tooling at runtime.

## Build

Start with the official vLLM image, which includes vLLM and its runtime
dependencies. Select the model when building the Snapshot-ready image. Add one
program that prepares vLLM for checkpoint and resumes it after restore.

### 1. Download the example files

Download [`app.py`](vllm/app.py) and
[`Dockerfile.vllm`](vllm/Dockerfile.vllm) from the repository:

```bash
mkdir -p vllm-snapshot-image
cd vllm-snapshot-image

curl --fail --location \
  --output app.py \
  https://raw.githubusercontent.com/ai-dynamo/snapshot/main/docs/guides/vllm/app.py

curl --fail --location \
  --output Dockerfile.vllm \
  https://raw.githubusercontent.com/ai-dynamo/snapshot/main/docs/guides/vllm/Dockerfile.vllm
```

The program loads the model selected when building the image, runs one
generation to initialize vLLM, and then calls `pause_generation()` and
`sleep()`. It writes
`ready-for-snapshot` only when the process is safe to checkpoint. In a restore
container, it waits in standby until Snapshot injects the captured process.
That process calls `wake_up()` and `resume_generation()`, runs another
generation, starts a validation API, and writes `vllm-restore-ready` once the
API is listening.

The Dockerfile starts from the official vLLM 0.27.1 image and installs the
Ubuntu 24.04 glibc required by the current Snapshot restore bundle. It creates
`/snapshot-control` and adds `app.py`.
`HF_HUB_DISABLE_XET=1` prevents the model downloader from leaving an open cache
log that CRIU cannot reopen after restore.

The source and restore pods must mount the Snapshot control volume at
`/snapshot-control`.

### 2. Set the model and build the image

```bash
export VLLM_RUNTIME_IMAGE=vllm/vllm-openai:v0.27.1
export VLLM_SNAPSHOT_IMAGE=<registry>/vllm-snapshot:<tag>
export VLLM_MODEL=Qwen/Qwen3-0.6B

docker build \
  --platform linux/amd64 \
  --build-arg VLLM_RUNTIME_IMAGE="$VLLM_RUNTIME_IMAGE" \
  --build-arg VLLM_MODEL="$VLLM_MODEL" \
  -f Dockerfile.vllm \
  -t "$VLLM_SNAPSHOT_IMAGE" .

docker push "$VLLM_SNAPSHOT_IMAGE"
```

The `docker push` command uploads the newly built image to the registry named
in `$VLLM_SNAPSHOT_IMAGE`. In both next-step guides, use that full image name
and tag as `spec.containers[].image` for the source and restore pods.

Other model values include `TinyLlama/TinyLlama-1.1B-Chat-v1.0` or a mounted
model path such as `/models/Qwen3-0.6B`. A mounted path must be available to
both the source and restored containers.

Verify that the packaged image contains vLLM and `app.py`:

```bash
docker run --rm \
  --platform linux/amd64 \
  --entrypoint python3 \
  "$VLLM_SNAPSHOT_IMAGE" \
  -c 'import pathlib; import vllm; assert pathlib.Path("/app/app.py").is_file()'
```

### 3. Validate the restored vLLM

This section exposes the restored vLLM only to validate that it accepts new
inference requests. The example endpoint is not intended as a production
serving API.

Add the validation port and readiness probe to the restored container:

```yaml
ports:
  - name: validation
    containerPort: 8000
readinessProbe:
  httpGet:
    path: /health
    port: validation
  periodSeconds: 1
  failureThreshold: 1200
```

The probe keeps the restored pod unready until the vLLM engine wakes and its
validation API is available.

After restoring a pod, forward its validation port:

```bash
kubectl port-forward \
  --namespace <namespace> \
  pod/<restored-pod> \
  8000:8000
```

In another terminal, send a prompt:

```bash
curl --fail --silent --show-error \
  --request POST \
  --header 'Content-Type: application/json' \
  --data '{"prompt":"Reply with one word: working"}' \
  http://127.0.0.1:8000/generate |
  jq .
```

The response must contain non-empty generated text.

## Next steps

- [Checkpoint a replica](checkpoint.md)
- [Restore a replica](restore.md)
