from __future__ import annotations

import asyncio
from typing import Optional

from .config import QUEUE_WORKER_COUNT
from .processor import JobProcessor
from .ws import WebSocketManager


class JobQueue:
    def __init__(self, ws_manager: Optional[WebSocketManager] = None) -> None:
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self._workers: list[asyncio.Task] = []
        self._ws_manager = ws_manager
        self._processor = JobProcessor(ws_manager=ws_manager)

    async def start(self) -> None:
        for _ in range(QUEUE_WORKER_COUNT):
            self._workers.append(asyncio.create_task(self._worker()))

    async def stop(self) -> None:
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers = []

    async def enqueue(self, job_id: str) -> None:
        await self.queue.put(job_id)

    async def _worker(self) -> None:
        while True:
            job_id = await self.queue.get()
            try:
                await self._process(job_id)
            finally:
                self.queue.task_done()

    async def _process(self, job_id: str) -> None:
        await self._processor.run(job_id)
