from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class UploadCreateRequest(BaseModel):
    filename: str = Field(..., min_length=1)
    size_bytes: int = Field(..., gt=0)
    mime_type: str = Field(..., min_length=3)
    total_parts: int = Field(..., gt=0, le=20000)


class UploadCreateResponse(BaseModel):
    upload_id: str
    chunk_size_bytes: int
    status: str


class UploadStatusResponse(BaseModel):
    upload_id: str
    filename: str
    size_bytes: int
    mime_type: str
    total_parts: int
    received_parts: int
    status: str
    target_path: Optional[str]
    uploaded_parts: List[int]


class UploadPartResponse(BaseModel):
    upload_id: str
    part_number: int
    received_parts: int
    status: str


class JobResponse(BaseModel):
    id: str
    source_type: str
    source_ref: str
    status: str
    stage: str
    progress: int
    error: Optional[str]
    output_video_path: Optional[str] = None
    analytics_path: Optional[str] = None

    @classmethod
    def from_db(cls, job: dict) -> JobResponse:
        return cls(
            id=job["id"],
            source_type=job["source_type"],
            source_ref=job["source_ref"],
            status=job["status"],
            stage=job["stage"],
            progress=job["progress"],
            error=job.get("error"),
            output_video_path=job.get("output_video_path"),
            analytics_path=job.get("analytics_path"),
        )


class JobCreateResponse(BaseModel):
    job: JobResponse


class YouTubeIngestRequest(BaseModel):
    url: HttpUrl


class LiveIngestRequest(BaseModel):
    url: HttpUrl
