# Build a snapshot-ready vLLM image

Snapshot restores a replica by injecting its captured state into a *placeholder*
image: your normal vLLM runtime image prepared with the application and
container layout Snapshot expects. The Snapshot agent injects the restore
tooling at runtime.

## Build

Start with a vLLM image that already contains the model runtime and Python
package. Add one program that prepares vLLM for checkpoint and resumes it after
restore.

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

The program loads the model passed to the container, runs one generation to
initialize vLLM,
and then calls `pause_generation()` and `sleep()`. It writes
`ready-for-snapshot` only when the process is safe to checkpoint. After restore,
it calls `wake_up()` and `resume_generation()`, runs another generation, and
writes `vllm-restore-ready`.

The Dockerfile starts from the official vLLM 0.27.1 image and installs the
Ubuntu 24.04 glibc required by the current Snapshot restore bundle. It applies
the placeholder container requirements and adds `app.py`.

### 2. Build the snapshot-ready image

```bash
export VLLM_RUNTIME_IMAGE=vllm/vllm-openai:v0.27.1
export VLLM_SNAPSHOT_IMAGE=<your-registry>/vllm-snapshot:<tag>

docker build \
  --platform linux/amd64 \
  --build-arg VLLM_RUNTIME_IMAGE="$VLLM_RUNTIME_IMAGE" \
  -f Dockerfile.vllm \
  -t "$VLLM_SNAPSHOT_IMAGE" .

docker push "$VLLM_SNAPSHOT_IMAGE"
```

Verify that the packaged image contains vLLM and `app.py`:

```bash
docker run --rm \
  --entrypoint python3 \
  "$VLLM_SNAPSHOT_IMAGE" \
  -c 'import pathlib; import vllm; assert pathlib.Path("/app/app.py").is_file()'
```

### 3. Pass the model when starting the container

The model is the first argument after the image:

```bash
docker run <runtime-options> \
  "$VLLM_SNAPSHOT_IMAGE" \
  Qwen/Qwen3-0.6B
```

Other values include `TinyLlama/TinyLlama-1.1B-Chat-v1.0` or a mounted model
path such as `/models/Qwen3-0.6B`. A mounted path must be available to both the
source and restored containers.

In Kubernetes, set the same argument on both containers:

```yaml
containers:
  - name: main
    image: <your-registry>/vllm-snapshot:<tag>
    args:
      - Qwen/Qwen3-0.6B
```

## Next steps

Use `$VLLM_SNAPSHOT_IMAGE` and the same model argument for the source and
restored containers.

- [Checkpoint a replica](checkpoint.md)
- [Restore a replica](restore.md)
