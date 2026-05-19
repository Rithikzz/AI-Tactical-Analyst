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
LIVE_CAPTURE_SECONDS = 120

JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret")
JWT_ISSUER = os.getenv("JWT_ISSUER", "football-intel")
JWT_EXP_MINUTES = int(os.getenv("JWT_EXP_MINUTES", "60"))

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@local")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "120"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
