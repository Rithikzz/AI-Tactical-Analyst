from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from ..db import get_job, list_jobs
from ..deps_auth import get_current_user
from ..schemas import JobResponse


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    _user: dict = Depends(get_current_user),
) -> JobResponse:
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


@router.get("", response_model=list[JobResponse])
async def get_jobs(
    limit: int = Query(50, ge=1, le=200),
    _user: dict = Depends(get_current_user),
) -> list[JobResponse]:
    jobs = list_jobs(limit=limit)
    return [
        JobResponse(
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
        for job in jobs
    ]


@router.get("/{job_id}/analytics")
async def get_job_analytics(
    job_id: str,
    _user: dict = Depends(get_current_user),
) -> FileResponse:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    path = job.get("analytics_path")
    if not path or not Path(path).exists():
        raise HTTPException(status_code=404, detail="Analytics not available.")
    return FileResponse(path, media_type="application/json")


@router.get("/{job_id}/output")
async def get_job_output(
    job_id: str,
    _user: dict = Depends(get_current_user),
) -> FileResponse:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    path = job.get("output_video_path")
    if not path or not Path(path).exists():
        raise HTTPException(status_code=404, detail="Output video not available.")
    suffix = Path(path).suffix.lower()
    media_type = "video/mp4"
    if suffix == ".avi":
        media_type = "video/x-msvideo"
    elif suffix == ".mov":
        media_type = "video/quicktime"
    elif suffix == ".mkv":
        media_type = "video/x-matroska"
    return FileResponse(path, media_type=media_type)
