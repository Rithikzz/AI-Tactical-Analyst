from __future__ import annotations

import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from ..config import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_PREFIXES,
    MAX_PART_SIZE_BYTES,
    MAX_UPLOAD_SIZE_BYTES,
)
from ..db import (
    add_upload_part,
    create_job,
    create_upload,
    get_upload,
    list_upload_parts,
    mark_upload_complete,
    update_upload_status,
)
from ..deps import get_queue
from ..deps_auth import get_current_user
from ..queue import JobQueue
from ..schemas import (
    JobCreateResponse,
    JobResponse,
    UploadCreateRequest,
    UploadCreateResponse,
    UploadPartResponse,
    UploadStatusResponse,
)
from ..storage import assemble_upload, save_part_from_uploadfile


router = APIRouter(prefix="/uploads", tags=["uploads"])


def _validate_upload_request(req: UploadCreateRequest) -> None:
    ext = Path(req.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file extension.")
    if req.size_bytes > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large.")
    if not any(req.mime_type.startswith(p) for p in ALLOWED_MIME_PREFIXES):
        raise HTTPException(status_code=400, detail="Unsupported MIME type.")


@router.post("", response_model=UploadCreateResponse)
async def create_upload_session(
    req: UploadCreateRequest,
    _user: dict = Depends(get_current_user),
) -> UploadCreateResponse:
    _validate_upload_request(req)
    upload_id = uuid.uuid4().hex
    create_upload(
        upload_id=upload_id,
        filename=req.filename,
        size_bytes=req.size_bytes,
        mime_type=req.mime_type,
        total_parts=req.total_parts,
    )
    return UploadCreateResponse(
        upload_id=upload_id,
        chunk_size_bytes=MAX_PART_SIZE_BYTES,
        status="created",
    )


@router.get("/{upload_id}", response_model=UploadStatusResponse)
async def get_upload_status(
    upload_id: str,
    _user: dict = Depends(get_current_user),
) -> UploadStatusResponse:
    upload = get_upload(upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found.")

    parts = list_upload_parts(upload_id)
    return UploadStatusResponse(
        upload_id=upload["id"],
        filename=upload["filename"],
        size_bytes=upload["size_bytes"],
        mime_type=upload["mime_type"],
        total_parts=upload["total_parts"],
        received_parts=upload["received_parts"],
        status=upload["status"],
        target_path=upload["target_path"],
        uploaded_parts=parts,
    )


@router.post("/{upload_id}/parts", response_model=UploadPartResponse)
async def upload_part(
    upload_id: str,
    part_number: int = Query(..., ge=1),
    file: UploadFile = File(...),
    _user: dict = Depends(get_current_user),
) -> UploadPartResponse:
    upload = get_upload(upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found.")
    if upload["status"] not in {"created", "uploading"}:
        raise HTTPException(status_code=400, detail="Upload is not accepting parts.")
    if part_number > upload["total_parts"]:
        raise HTTPException(status_code=400, detail="Part number out of range.")

    update_upload_status(upload_id, "uploading")

    try:
        size_bytes = await save_part_from_uploadfile(upload_id, part_number, file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    add_upload_part(upload_id, part_number, size_bytes)

    upload = get_upload(upload_id)
    return UploadPartResponse(
        upload_id=upload_id,
        part_number=part_number,
        received_parts=upload["received_parts"],
        status=upload["status"],
    )


@router.post("/{upload_id}/complete", response_model=JobCreateResponse)
async def complete_upload(
    upload_id: str,
    queue: JobQueue = Depends(get_queue),
    _user: dict = Depends(get_current_user),
) -> JobCreateResponse:
    upload = get_upload(upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found.")

    parts = list_upload_parts(upload_id)
    if len(parts) != upload["total_parts"]:
        raise HTTPException(status_code=400, detail="Upload parts incomplete.")

    try:
        final_path = assemble_upload(upload_id, upload["total_parts"], upload["filename"])
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if final_path.stat().st_size != upload["size_bytes"]:
        update_upload_status(upload_id, "failed")
        raise HTTPException(status_code=400, detail="Uploaded size mismatch.")

    mark_upload_complete(upload_id, str(final_path))

    job_id = uuid.uuid4().hex
    create_job(job_id, source_type="upload", source_ref=str(final_path))
    await queue.enqueue(job_id)

    job = get_job_response(job_id)
    return JobCreateResponse(job=job)


def get_job_response(job_id: str) -> JobResponse:
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
