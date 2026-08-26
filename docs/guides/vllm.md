# Build a snapshot-ready vLLM image

Snapshot restores a replica by injecting its captured state into a *placeholder*
image: your normal vLLM runtime image prepared with the application and
container layout Snapshot expects. The Snapshot agent injects the restore
tooling at runtime.

## Build

Start with a vLLM image that already contains the model runtime and Python
package. Add one program that prepares vLLM for checkpoint and resumes it after
restore.

### 1. Save the vLLM program

Save the following file as `app.py`:

```python
import asyncio
import os
from pathlib import Path

from vllm import SamplingParams
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.usage.usage_lib import UsageContext
from vllm.v1.engine.async_llm import AsyncLLM

MODEL = "Qwen/Qwen3-0.6B"
CONTROL_DIR = Path(
    os.environ.get("SNAPSHOT_CONTROL_DIR", "/snapshot-control")
)


async def generate_text(
    engine: AsyncLLM,
    prompt: str,
    request_id: str,
) -> str:
    result = None
    async for output in engine.generate(
        prompt,
        SamplingParams(temperature=0.0, max_tokens=8),
        request_id,
    ):
        result = output
    if result is None or not result.outputs:
        raise RuntimeError("vLLM produced no output")
    text = result.outputs[0].text.strip()
    if not text:
        raise RuntimeError("vLLM produced empty output")
    return text


async def main() -> None:
    engine = AsyncLLM.from_engine_args(
        AsyncEngineArgs(
            model=MODEL,
            enable_sleep_mode=True,
        ),
        usage_context=UsageContext.LLM_CLASS,
    )

    text = await generate_text(
        engine,
        "Reply with one word: ready",
        "snapshot-preflight",
    )
    print(f"vLLM pre-checkpoint output={text!r}", flush=True)

    await engine.pause_generation()
    await engine.sleep()
    CONTROL_DIR.joinpath("ready-for-snapshot").write_text(
        "ready\n",
        encoding="utf-8",
    )

    while True:
        if CONTROL_DIR.joinpath("snapshot-complete").exists():
            return
        if CONTROL_DIR.joinpath("restore-complete").exists():
            await engine.wake_up()
            await engine.resume_generation()
            await engine.check_health()
            text = await generate_text(
                engine,
                "Reply with one word: restored",
                "snapshot-restore-check",
            )
            CONTROL_DIR.joinpath("vllm-restore-ready").write_text(
                text + "\n",
                encoding="utf-8",
            )
            print(f"vLLM restored output={text!r}", flush=True)
            while True:
                await asyncio.sleep(3600)
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
    os._exit(0)
```

Set `MODEL` near the top of `app.py` before building the image. The example uses
`Qwen/Qwen3-0.6B`, the public Hugging Face model used by the Snapshot vLLM test.
Other values include `TinyLlama/TinyLlama-1.1B-Chat-v1.0` or a mounted model
path such as `/models/Qwen3-0.6B`. A mounted path must also be available when
restoring the replica.

The program loads the selected model, runs one generation to initialize vLLM,
and then calls `pause_generation()` and `sleep()`. It writes
`ready-for-snapshot` only when the process is safe to checkpoint. After restore,
it calls `wake_up()` and `resume_generation()`, runs another generation, and
writes `vllm-restore-ready`.

### 2. Save the Dockerfile

Save the following file as `Dockerfile.vllm` next to `app.py`:

```dockerfile
ARG VLLM_RUNTIME_IMAGE=vllm/vllm-openai:v0.27.1
FROM ${VLLM_RUNTIME_IMAGE}

ARG VLLM_RUNTIME_IMAGE
ARG TARGETARCH=amd64

ENV ORIGINAL_BASE_IMAGE=${VLLM_RUNTIME_IMAGE}

USER root

RUN set -eux; \
    if [ "${TARGETARCH}" != "amd64" ]; then \
      echo "Snapshot requires x86_64" >&2; \
      exit 1; \
    fi; \
    printf 'deb http://archive.ubuntu.com/ubuntu noble main universe\n' \
      >/etc/apt/sources.list.d/snapshot-noble.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends -t noble libc6 libc-bin; \
    rm -f /etc/apt/sources.list.d/snapshot-noble.list; \
    rm -rf /var/lib/apt/lists/*; \
    mkdir -p /checkpoints

WORKDIR /app
COPY app.py ./
ENTRYPOINT ["python3", "/app/app.py"]
```

This Dockerfile performs the complete build. It starts from the official vLLM
image, installs the glibc version required by the current Snapshot restore
bundle, applies the placeholder container requirements, and adds `app.py`.

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
