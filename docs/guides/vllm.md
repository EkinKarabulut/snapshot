# Build a snapshot-ready vLLM image

Snapshot restores a replica by injecting its captured state into a *placeholder*
image: your normal vLLM runtime image wrapped with the restore tooling (CRIU,
`cuda-checkpoint`, `nsrestore`). Build it once and run your vLLM replicas from it.

Start with a vLLM image that already contains the model runtime and Python
package. Add one program that prepares vLLM for checkpoint and resumes it after
restore.

## 1. Save the vLLM program

Save the following file as `app.py`:

```python
import asyncio
import os
from pathlib import Path

from vllm import SamplingParams
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.usage.usage_lib import UsageContext
from vllm.v1.engine.async_llm import AsyncLLM

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
            model=os.environ["MODEL"],
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

This program loads the model named by `MODEL`, runs one generation to initialize
vLLM, and then calls `pause_generation()` and `sleep()`. It writes
`ready-for-snapshot` only when the process is safe to checkpoint. After restore,
it calls `wake_up()` and `resume_generation()`, runs another generation, and
writes `vllm-restore-ready`.

## 2. Save the Dockerfile

Save the following file as `Dockerfile.vllm` next to `app.py`:

```dockerfile
ARG VLLM_RUNTIME_IMAGE
FROM ${VLLM_RUNTIME_IMAGE}

WORKDIR /app
COPY app.py ./
ENTRYPOINT ["python3", "/app/app.py"]
```

## 3. Build the application image

```bash
export VLLM_RUNTIME_IMAGE=<your-vllm-runtime-image>
export VLLM_APP_IMAGE=<your-registry>/vllm-app:<tag>

docker build \
  --build-arg VLLM_RUNTIME_IMAGE="$VLLM_RUNTIME_IMAGE" \
  -f Dockerfile.vllm \
  -t "$VLLM_APP_IMAGE" .

docker push "$VLLM_APP_IMAGE"
```

The current Snapshot restore bundle is built on Ubuntu 24.04 with glibc 2.39.
Use an x86_64 vLLM runtime image with a compatible glibc version; an older
glibc image may build successfully but fail during restore.

## 4. Build the snapshot-ready image

From the `agent/` directory, build the `placeholder` target against your vLLM
application image and push it to a registry your cluster can pull from:

```bash
export SNAPSHOT_REPO=<path-to-snapshot-repository>
export VLLM_SNAPSHOT_IMAGE=<your-registry>/vllm-placeholder:<tag>

cd "$SNAPSHOT_REPO/agent"

docker build \
  --platform linux/amd64 \
  --target placeholder \
  --build-context api=../api \
  --build-arg BASE_IMAGE="$VLLM_APP_IMAGE" \
  -t "$VLLM_SNAPSHOT_IMAGE" .

docker push "$VLLM_SNAPSHOT_IMAGE"
```

The placeholder build preserves the `app.py` entrypoint and adds the container
contract Snapshot needs for restore.

Verify that the packaged image contains vLLM and `app.py`:

```bash
docker run --rm \
  --entrypoint python3 \
  "$VLLM_SNAPSHOT_IMAGE" \
  -c 'import pathlib; import vllm; assert pathlib.Path("/app/app.py").is_file()'
```

## 5. Use the image

Set `MODEL` to the model name or path in the workload and use
`$VLLM_SNAPSHOT_IMAGE` for the source and restored containers. Then
[create a checkpoint with `SnapshotJob`](checkpoint.md) and
[restore the replica](restore.md).
