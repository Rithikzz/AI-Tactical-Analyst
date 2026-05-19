from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .analysis_pipeline import run_full_pipeline
from .config import ALLOWED_EXTENSIONS
from .db import get_job, update_job, update_job_outputs
from .ingest_download import capture_live_stream, download_youtube
from .storage import get_analytics_path, get_ingest_path, get_output_dir
from .ws import WebSocketManager


class JobProcessor:
    def __init__(self, ws_manager: Optional[WebSocketManager] = None) -> None:
        self._ws_manager = ws_manager

    async def run(self, job_id: str) -> None:
        job = get_job(job_id)
        if not job:
            return

        try:
            await self._update(job_id, status="processing", stage="validating", progress=10)
            self._validate_job(job)

            await self._update(job_id, status="processing", stage="processing", progress=40)
            output_video_path, analytics_path = await self._process_job(job)

            update_job_outputs(job_id, output_video_path, analytics_path)
            await self._update(job_id, status="processing", stage="rendering", progress=80)

            await self._update(job_id, status="completed", stage="completed", progress=100)
        except Exception as exc:
            await self._update(job_id, status="failed", stage="failed", progress=100, error=str(exc))

    def _validate_job(self, job: dict) -> None:
        if job["source_type"] in {"upload", "youtube", "live"}:
            if job["source_type"] == "upload":
                path = Path(job["source_ref"])
                if not path.exists():
                    raise FileNotFoundError("Uploaded file not found.")
                if path.suffix.lower() not in ALLOWED_EXTENSIONS:
                    raise ValueError("Unsupported file extension.")
                if path.stat().st_size == 0:
                    raise ValueError("Empty upload.")

    async def _process_job(self, job: dict) -> tuple[Optional[str], Optional[str]]:
        job_id = job["id"]
        output_dir = get_output_dir(job_id)
        analytics_path = get_analytics_path(job_id)

        output_video_path: Optional[str] = None
        analytics: dict

        input_path: Optional[Path] = None

        if job["source_type"] == "upload":
            input_path = Path(job["source_ref"])
        elif job["source_type"] == "youtube":
            await self._update(job_id, status="processing", stage="downloading", progress=20)
            input_path = download_youtube(job["source_ref"], get_ingest_path(job_id, ".mp4"))
        elif job["source_type"] == "live":
            await self._update(job_id, status="processing", stage="capturing", progress=20)
            input_path = capture_live_stream(job["source_ref"], get_ingest_path(job_id, ".mp4"))

        if input_path is None or not input_path.exists():
            raise FileNotFoundError("Input video is not available.")

        output_video = output_dir / f"{input_path.stem}_processed.avi"
        output_video, analytics = run_full_pipeline(input_path, output_video)
        output_video_path = str(output_video)

        analytics.update(
            {
                "job_id": job_id,
                "source_type": job["source_type"],
                "source_ref": job["source_ref"],
                "generated_at": datetime.utcnow().isoformat(),
            }
        )
        analytics_path.write_text(json.dumps(analytics, indent=2))
        return output_video_path, str(analytics_path)

    async def _update(
        self,
        job_id: str,
        status: str,
        stage: str,
        progress: int,
        error: Optional[str] = None,
    ) -> None:
        update_job(job_id, status=status, stage=stage, progress=progress, error=error)
        await self._broadcast(job_id)

    async def _broadcast(self, job_id: str) -> None:
        if not self._ws_manager:
            return
        job = get_job(job_id)
        if not job:
            return
        await self._ws_manager.broadcast(job_id, {"type": "job", "payload": job})
