from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .config import (
    ANALYTICS_DIR,
    INGEST_DIR,
    OUTPUT_DIR,
    UPLOAD_FINAL_DIR,
    UPLOAD_TMP_DIR,
    MAX_PART_SIZE_BYTES,
)


def ensure_storage_dirs() -> None:
    UPLOAD_TMP_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_FINAL_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    INGEST_DIR.mkdir(parents=True, exist_ok=True)


def get_output_dir(job_id: str) -> Path:
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir


def get_analytics_path(job_id: str) -> Path:
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    return ANALYTICS_DIR / f"{job_id}.json"


def get_ingest_path(job_id: str, suffix: str) -> Path:
    INGEST_DIR.mkdir(parents=True, exist_ok=True)
    return INGEST_DIR / f"{job_id}{suffix}"


def get_upload_tmp_dir(upload_id: str) -> Path:
    return UPLOAD_TMP_DIR / upload_id


def get_part_path(upload_id: str, part_number: int) -> Path:
    return get_upload_tmp_dir(upload_id) / f"part_{part_number:06d}"


def save_part(upload_id: str, part_number: int, data_iter: Iterable[bytes]) -> int:
    upload_dir = get_upload_tmp_dir(upload_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    part_path = get_part_path(upload_id, part_number)

    size_bytes = 0
    with part_path.open("wb") as f:
        for chunk in data_iter:
            if not chunk:
                continue
            size_bytes += len(chunk)
            if size_bytes > MAX_PART_SIZE_BYTES:
                raise ValueError("Part size exceeds maximum limit.")
            f.write(chunk)
    return size_bytes


async def save_part_from_uploadfile(upload_id: str, part_number: int, upload_file) -> int:
    upload_dir = get_upload_tmp_dir(upload_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    part_path = get_part_path(upload_id, part_number)

    size_bytes = 0
    with part_path.open("wb") as f:
        while True:
            chunk = await upload_file.read(1024 * 1024)
            if not chunk:
                break
            size_bytes += len(chunk)
            if size_bytes > MAX_PART_SIZE_BYTES:
                raise ValueError("Part size exceeds maximum limit.")
            f.write(chunk)
    return size_bytes


def assemble_upload(upload_id: str, total_parts: int, filename: str) -> Path:
    upload_dir = get_upload_tmp_dir(upload_id)
    final_path = UPLOAD_FINAL_DIR / f"{upload_id}_{filename}"
    with final_path.open("wb") as out:
        for part_number in range(1, total_parts + 1):
            part_path = get_part_path(upload_id, part_number)
            if not part_path.exists():
                raise FileNotFoundError(f"Missing part {part_number}")
            with part_path.open("rb") as part:
                for chunk in iter(lambda: part.read(1024 * 1024), b""):
                    out.write(chunk)

    for part_number in range(1, total_parts + 1):
        get_part_path(upload_id, part_number).unlink(missing_ok=True)
    upload_dir.rmdir()
    return final_path
