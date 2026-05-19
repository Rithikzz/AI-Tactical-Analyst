from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .config import LIVE_CAPTURE_SECONDS, MAX_UPLOAD_SIZE_BYTES


def _ensure_command(cmd: str) -> None:
    if shutil.which(cmd) is None:
        raise FileNotFoundError(f"Required command not found: {cmd}")


def download_youtube(url: str, target_path: Path) -> Path:
    try:
        from yt_dlp import YoutubeDL
    except ImportError as exc:
        raise RuntimeError("yt-dlp is not installed.") from exc

    target_path.parent.mkdir(parents=True, exist_ok=True)
    output_template = str(target_path.with_suffix(".%(ext)s"))

    ydl_opts = {
        "outtmpl": output_template,
        "format": "mp4/best",
        "noplaylist": True,
        "quiet": True,
        "max_filesize": MAX_UPLOAD_SIZE_BYTES,
    }

    with YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=True)

    if "requested_downloads" in result and result["requested_downloads"]:
        filename = result["requested_downloads"][0]["filepath"]
        return Path(filename)

    raise RuntimeError("YouTube download failed.")


def capture_live_stream(url: str, target_path: Path) -> Path:
    _ensure_command("ffmpeg")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        url,
        "-t",
        str(LIVE_CAPTURE_SECONDS),
        "-c",
        "copy",
        str(target_path),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.strip()}")
    return target_path
