# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import asyncio
import os
from pathlib import Path

from vllm import SamplingParams
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.usage.usage_lib import UsageContext
from vllm.v1.engine.async_llm import AsyncLLM

CONTROL_DIR = Path(os.environ.get("SNAPSHOT_CONTROL_DIR", "/snapshot-control"))
MODEL = os.environ["VLLM_MODEL"]


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
    if os.environ.get("DYN_SNAPSHOT_RESTORE_STANDBY") == "1":
        await asyncio.Event().wait()

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
