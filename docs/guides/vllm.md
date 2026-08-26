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

### 2. Set the model

Open `app.py` and set `MODEL` before building the image:

```python
MODEL = "Qwen/Qwen3-0.6B"
```

`Qwen/Qwen3-0.6B` is the public Hugging Face model used by the Snapshot vLLM
test. Other values include `TinyLlama/TinyLlama-1.1B-Chat-v1.0` or a mounted
model path such as `/models/Qwen3-0.6B`. A mounted path must also be available
when restoring the replica.

The program loads the selected model, runs one generation to initialize vLLM,
and then calls `pause_generation()` and `sleep()`. It writes
`ready-for-snapshot` only when the process is safe to checkpoint. After restore,
it calls `wake_up()` and `resume_generation()`, runs another generation, and
writes `vllm-restore-ready`.

The Dockerfile starts from the official vLLM image, installs the glibc version
required by the current Snapshot restore bundle, applies the placeholder
container requirements, and adds `app.py`.

### 3. Build the snapshot-ready image

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

## Next steps

Use `$VLLM_SNAPSHOT_IMAGE` for the source and restored containers.

- [Checkpoint a replica](checkpoint.md)
- [Restore a replica](restore.md)
