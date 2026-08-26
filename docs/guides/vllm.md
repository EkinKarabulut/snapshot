# Build a snapshot-ready vLLM image

Snapshot restores a replica by injecting its captured state into a *placeholder*
image: your normal vLLM runtime image wrapped with the restore tooling (CRIU,
`cuda-checkpoint`, `nsrestore`). Build it once and run your vLLM replicas from it.

This guide covers a team-owned Python application that creates vLLM through
`AsyncLLM.from_engine_args()`.

## Prepare the Python application

The application must stop generation and put vLLM to sleep before Snapshot
checkpoints the process. After restore, it must wake vLLM before serving
requests.

### Enable sleep mode

In the application entrypoint that creates the engine, enable sleep mode:

```python
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.usage.usage_lib import UsageContext
from vllm.v1.engine.async_llm import AsyncLLM

engine_args = AsyncEngineArgs(
    model=model,
    enable_sleep_mode=True,
)
engine = AsyncLLM.from_engine_args(
    engine_args,
    usage_context=UsageContext.LLM_CLASS,
)
```

Edit your application's source, not the vLLM repository. In particular,
`vllm/entrypoints/cli/serve.py` is not an integration point for this Python
flow.

### Add the checkpoint lifecycle

Create `snapshot_lifecycle.py` next to the application entrypoint:

```python
import asyncio
import os
from pathlib import Path
from typing import Literal

from vllm.v1.engine.async_llm import AsyncLLM

CONTROL_DIR = Path(
    os.environ.get("SNAPSHOT_CONTROL_DIR", "/snapshot-control")
)


async def quiesce_for_snapshot(
    engine: AsyncLLM,
) -> Literal["checkpoint", "restore"]:
    await engine.pause_generation()
    await engine.sleep()
    CONTROL_DIR.joinpath("ready-for-snapshot").write_text(
        "ready\n",
        encoding="utf-8",
    )

    while True:
        if CONTROL_DIR.joinpath("snapshot-complete").exists():
            return "checkpoint"
        if CONTROL_DIR.joinpath("restore-complete").exists():
            return "restore"
        await asyncio.sleep(1)


async def resume_after_checkpoint_or_restore(engine: AsyncLLM) -> None:
    await engine.wake_up()
    await engine.resume_generation()
```

The vLLM-specific calls have the following roles:

- `pause_generation()` stops generation work from changing engine state.
- `sleep()` moves model weights to CPU memory and discards the KV cache,
  releasing most GPU memory before the checkpoint.
- `wake_up()` returns model weights to GPU memory.
- `resume_generation()` allows the scheduler to process requests again.

The files under `/snapshot-control` synchronize the application with Snapshot.
The application writes `ready-for-snapshot` only after vLLM is safe to
checkpoint. Snapshot writes `snapshot-complete` in the source process and
`restore-complete` in the restored process.

### Wire the lifecycle into the entrypoint

Adding `snapshot_lifecycle.py` to the image is not enough. Call it after engine
creation and warm-up, at the point where the application has drained traffic
and is ready to be checkpointed:

```python
import asyncio
import os

from snapshot_lifecycle import (
    quiesce_for_snapshot,
    resume_after_checkpoint_or_restore,
)


async def main(exit_after_checkpoint: bool) -> None:
    engine_args = AsyncEngineArgs(
        model=model,
        enable_sleep_mode=True,
    )
    engine = AsyncLLM.from_engine_args(
        engine_args,
        usage_context=UsageContext.LLM_CLASS,
    )
    await warm_up(engine)

    outcome = await quiesce_for_snapshot(engine)
    if outcome == "checkpoint" and exit_after_checkpoint:
        return

    await resume_after_checkpoint_or_restore(engine)
    await serve_requests(engine)


if __name__ == "__main__":
    exit_after_checkpoint = os.environ.get(
        "SNAPSHOT_EXIT_AFTER_CHECKPOINT",
        "true",
    ).lower() == "true"
    asyncio.run(main(exit_after_checkpoint))
```

`warm_up()` and `serve_requests()` represent the application's existing code;
do not create a second engine if the application structures these steps
differently. Use `exit_after_checkpoint=True` for a `SnapshotJob`, whose source
replica should exit after checkpoint. Use `False` when checkpointing a running
replica with `PodSnapshot` so the source wakes up and continues serving. A
restored process always follows the resume path. The example reads this choice
from `SNAPSHOT_EXIT_AFTER_CHECKPOINT`, which defaults to `true`.

The lifecycle expects the control directory at the path provided by
`SNAPSHOT_CONTROL_DIR`, which defaults to `/snapshot-control`. `SnapshotJob`
adds this volume and environment variable to its pod. A pod checkpointed
directly with `PodSnapshot` must expose the same control directory and use
`ready-for-snapshot` as its readiness signal.

## Build the application image

Package the application entrypoint and lifecycle helper in the normal vLLM
runtime image:

```dockerfile
ARG VLLM_RUNTIME_IMAGE
FROM ${VLLM_RUNTIME_IMAGE}

WORKDIR /app
COPY app.py snapshot_lifecycle.py ./
ENTRYPOINT ["python3", "/app/app.py"]
```

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

## Build the snapshot-ready image

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

The placeholder build preserves the application image's entrypoint and adds
the container contract Snapshot needs for restore. Use
`$VLLM_SNAPSHOT_IMAGE` for both the source and restored replica containers.

Verify that the packaged image contains vLLM and the lifecycle module:

```bash
docker run --rm \
  --entrypoint python3 \
  "$VLLM_SNAPSHOT_IMAGE" \
  -c 'import snapshot_lifecycle; import vllm'
```

## Next steps

- [Checkpoint a replica](checkpoint.md)
- [Restore a replica](restore.md)
