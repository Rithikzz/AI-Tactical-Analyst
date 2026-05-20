from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import DB_PATH, VAR_DIR

_LOCK = threading.Lock()


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db() -> None:
    VAR_DIR.mkdir(parents=True, exist_ok=True)
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS uploads (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                mime_type TEXT NOT NULL,
                total_parts INTEGER NOT NULL,
                received_parts INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                target_path TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS upload_parts (
                upload_id TEXT NOT NULL,
                part_number INTEGER NOT NULL,
                size_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (upload_id, part_number)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_ref TEXT NOT NULL,
                status TEXT NOT NULL,
                stage TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                error TEXT,
                output_video_path TEXT,
                analytics_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        _ensure_column(conn, "jobs", "output_video_path", "TEXT")
        _ensure_column(conn, "jobs", "analytics_path", "TEXT")
        conn.commit()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
    cur = conn.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cur.fetchall()}
    if column in existing:
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def create_upload(
    upload_id: str,
    filename: str,
    size_bytes: int,
    mime_type: str,
    total_parts: int,
) -> None:
    now = datetime.utcnow().isoformat()
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            INSERT INTO uploads (id, filename, size_bytes, mime_type, total_parts, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (upload_id, filename, size_bytes, mime_type, total_parts, "created", now),
        )
        conn.commit()


def get_upload(upload_id: str) -> Optional[Dict]:
    with _LOCK, _connect() as conn:
        cur = conn.execute("SELECT * FROM uploads WHERE id = ?", (upload_id,))
        row = cur.fetchone()
        if not row:
            return None
        columns = [d[0] for d in cur.description]
        return dict(zip(columns, row))


def list_upload_parts(upload_id: str) -> List[int]:
    with _LOCK, _connect() as conn:
        cur = conn.execute(
            "SELECT part_number FROM upload_parts WHERE upload_id = ? ORDER BY part_number",
            (upload_id,),
        )
        return [row[0] for row in cur.fetchall()]


def add_upload_part(upload_id: str, part_number: int, size_bytes: int) -> None:
    now = datetime.utcnow().isoformat()
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO upload_parts (upload_id, part_number, size_bytes, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (upload_id, part_number, size_bytes, now),
        )
        conn.execute(
            """
            UPDATE uploads
            SET received_parts = (
                SELECT COUNT(*) FROM upload_parts WHERE upload_id = ?
            )
            WHERE id = ?
            """,
            (upload_id, upload_id),
        )
        conn.commit()


def mark_upload_complete(upload_id: str, target_path: str) -> None:
    now = datetime.utcnow().isoformat()
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            UPDATE uploads
            SET status = ?, completed_at = ?, target_path = ?
            WHERE id = ?
            """,
            ("completed", now, target_path, upload_id),
        )
        conn.commit()


def update_upload_status(upload_id: str, status: str) -> None:
    with _LOCK, _connect() as conn:
        conn.execute(
            "UPDATE uploads SET status = ? WHERE id = ?",
            (status, upload_id),
        )
        conn.commit()


def create_job(job_id: str, source_type: str, source_ref: str) -> None:
    now = datetime.utcnow().isoformat()
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            INSERT INTO jobs (id, source_type, source_ref, status, stage, progress, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (job_id, source_type, source_ref, "queued", "queued", 0, now, now),
        )
        conn.commit()


def update_job(job_id: str, status: str, stage: str, progress: int, error: Optional[str] = None) -> None:
    now = datetime.utcnow().isoformat()
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET status = ?, stage = ?, progress = ?, error = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, stage, progress, error, now, job_id),
        )
        conn.commit()


def update_job_outputs(job_id: str, output_video_path: Optional[str], analytics_path: Optional[str]) -> None:
    now = datetime.utcnow().isoformat()
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET output_video_path = ?, analytics_path = ?, updated_at = ?
            WHERE id = ?
            """,
            (output_video_path, analytics_path, now, job_id),
        )
        conn.commit()


def get_job(job_id: str) -> Optional[Dict]:
    with _LOCK, _connect() as conn:
        cur = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cur.fetchone()
        if not row:
            return None
        columns = [d[0] for d in cur.description]
        return dict(zip(columns, row))


def list_jobs(limit: int = 50) -> List[Dict]:
    with _LOCK, _connect() as conn:
        cur = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description]
        return [dict(zip(columns, row)) for row in rows]



