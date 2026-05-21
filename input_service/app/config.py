from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BASE_DIR.parents[0]
VAR_DIR = BASE_DIR / "var"
UPLOAD_TMP_DIR = VAR_DIR / "uploads_tmp"
UPLOAD_FINAL_DIR = VAR_DIR / "uploads"
OUTPUT_DIR = VAR_DIR / "outputs"
ANALYTICS_DIR = VAR_DIR / "analytics"
INGEST_DIR = VAR_DIR / "ingest"

DB_PATH = VAR_DIR / "input.db"

MAX_UPLOAD_SIZE_BYTES = 2 * 1024 * 1024 * 1024  # 2GB
MAX_PART_SIZE_BYTES = 8 * 1024 * 1024  # 8MB
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi"}
ALLOWED_MIME_PREFIXES = {"video/"}

QUEUE_WORKER_COUNT = 2

MODEL_PATH = REPO_ROOT / "football_analysis" / "models" / "best.pt"
LIVE_CAPTURE_SECONDS = int(os.getenv("LIVE_CAPTURE_SECONDS", "120"))

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
