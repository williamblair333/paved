# SPDX-License-Identifier: AGPL-3.0-only
"""Locate and invoke ffmpeg/ffprobe.

Resolution order for each binary:
1. Explicit env var (PAVED_FFMPEG / PAVED_FFPROBE).
2. A binary on PATH (the Docker image installs the system ffmpeg).
3. The static binary bundled by imageio-ffmpeg, if that package is installed
   (handy for host runs outside Docker). Only ffmpeg is bundled there, not ffprobe.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from functools import lru_cache


class FFmpegNotFound(RuntimeError):
    pass


@lru_cache(maxsize=None)
def ffmpeg_path() -> str:
    explicit = os.environ.get("PAVED_FFMPEG")
    if explicit and os.path.exists(explicit):
        return explicit
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    raise FFmpegNotFound(
        "ffmpeg not found. Install ffmpeg, set PAVED_FFMPEG, or `pip install imageio-ffmpeg`."
    )


@lru_cache(maxsize=None)
def ffprobe_path() -> str | None:
    explicit = os.environ.get("PAVED_FFPROBE")
    if explicit and os.path.exists(explicit):
        return explicit
    return shutil.which("ffprobe")


def run(args: list[str], timeout: int | None = None) -> subprocess.CompletedProcess:
    """Run ffmpeg with the given args (ffmpeg binary prepended). Capture output.

    Uses an argument list (never shell=True) so a hostile filename cannot inject
    a shell command.
    """
    cmd = [ffmpeg_path(), *args]
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, check=False
    )


def decode_verify(path: str, timeout: int | None = None) -> tuple[bool, str]:
    """Full decode pass to the null muxer. Returns (ok, stderr).

    ok is True when ffmpeg exits 0 with no error-level messages — the ground-truth
    test that a file actually plays start to finish.
    """
    proc = run(
        ["-v", "error", "-xerror", "-i", path, "-map", "0", "-f", "null", "-"],
        timeout=timeout,
    )
    ok = proc.returncode == 0 and not proc.stderr.strip()
    return ok, proc.stderr.strip()


def extract_frame(path: str, out_jpg: str, at_seconds: float = 1.0) -> bool:
    """Extract a single JPEG frame for a visual sanity check. Returns success."""
    proc = run(
        ["-v", "error", "-y", "-ss", str(at_seconds), "-i", path,
         "-frames:v", "1", "-q:v", "3", out_jpg]
    )
    return proc.returncode == 0 and os.path.exists(out_jpg)
