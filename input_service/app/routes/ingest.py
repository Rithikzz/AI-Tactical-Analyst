from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException

from ..db import create_job
from ..deps import get_queue
from ..deps_auth import get_current_user
from ..queue import JobQueue
from ..schemas import JobCreateResponse, JobResponse, LiveIngestRequest, YouTubeIngestRequest


router = APIRouter(prefix="/ingest", tags=["ingest"])

YOUTUBE_PATTERN = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$", re.IGNORECASE
)


@router.post("/youtube", response_model=JobCreateResponse)
async def ingest_youtube(
    payload: YouTubeIngestRequest,
    queue: JobQueue = Depends(get_queue),
    _user: dict = Depends(get_current_user),
) -> JobCreateResponse:
    if not YOUTUBE_PATTERN.match(str(payload.url)):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL.")
    job_id = uuid.uuid4().hex
    create_job(job_id, source_type="youtube", source_ref=str(payload.url))
    await queue.enqueue(job_id)
    return JobCreateResponse(job=_job_response(job_id))


@router.post("/live", response_model=JobCreateResponse)
async def ingest_live(
    payload: LiveIngestRequest,
    queue: JobQueue = Depends(get_queue),
    _user: dict = Depends(get_current_user),
) -> JobCreateResponse:
    url_str = str(payload.url)
    if not url_str.startswith(("rtmp://", "srt://", "http://", "https://")):
        raise HTTPException(status_code=400, detail="Unsupported stream URL.")
    job_id = uuid.uuid4().hex
    create_job(job_id, source_type="live", source_ref=url_str)
    await queue.enqueue(job_id)
    return JobCreateResponse(job=_job_response(job_id))


def _job_response(job_id: str) -> JobResponse:
    from ..db import get_job

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobResponse(
        id=job["id"],
        source_type=job["source_type"],
        source_ref=job["source_ref"],
        status=job["status"],
        stage=job["stage"],
        progress=job["progress"],
        error=job["error"],
        output_video_path=job.get("output_video_path"),
        analytics_path=job.get("analytics_path"),
    )
