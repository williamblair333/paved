"""Repair pipeline: probe → copy → apply strategies (on copy) → decode-verify → report.

Safety invariant: the source file is opened read-only and copied before any byte
is written. All strategies operate on the working copy. The original is never
modified.
"""
from __future__ import annotations

import os
import shutil

from paved import ffmpeg, probe as probe_mod
from paved.report import RepairResult
from paved.repair import strategies as S


def repair_file(
    src: str,
    out_dir: str | None = None,
    dry_run: bool = False,
    verify_timeout: int | None = 1800,
) -> RepairResult:
    """Diagnose and attempt to repair a single file. Never mutates src."""
    diag = probe_mod.probe(src)

    # Already playable? Nothing to do.
    if diag.container_ok:
        ok, _ = ffmpeg.decode_verify(src, timeout=verify_timeout)
        if ok:
            return RepairResult(
                path=src, output=None, fault="none", strategy=None,
                success=True, lossy=False, lost="",
                detail="File already plays cleanly; no repair needed.",
                dry_run=dry_run,
            )

    plan = S.FAULT_STRATEGIES.get(diag.fault, S.STRATEGY_ORDER)

    if dry_run:
        names = ", ".join(fn.__name__ for fn in plan) or "(none)"
        return RepairResult(
            path=src, output=None, fault=diag.fault, strategy=None,
            success=False, lossy=False, lost="",
            detail=f"{diag.detail} Planned strategies (in order): {names}.",
            dry_run=True,
        )

    out_dir = out_dir or os.path.dirname(os.path.abspath(src)) or "."
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.basename(src)
    stem, _ = os.path.splitext(base)
    work = os.path.join(out_dir, f"{stem}.repaired.mp4")
    shutil.copy2(src, work)  # work on a copy; source untouched

    last_detail = diag.detail
    for fn in plan:
        outcome = fn(work, diag)
        if not outcome.applied:
            last_detail = outcome.detail or last_detail
            continue
        candidate = outcome.output or work
        ok, verr = ffmpeg.decode_verify(candidate, timeout=verify_timeout)
        if ok:
            final = _finalize(candidate, out_dir, stem, work)
            return RepairResult(
                path=src, output=final, fault=diag.fault,
                strategy=fn.__name__, success=True,
                lossy=outcome.lossy, lost=outcome.lost,
                detail=outcome.detail,
            )
        last_detail = f"{fn.__name__} ran but result still fails decode: {verr[:200]}"
        # If the strategy produced a separate file that didn't verify, drop it.
        if candidate != work:
            S._rm(candidate)

    # Nothing produced a playable file. Clean up the working copy.
    S._rm(work)
    return RepairResult(
        path=src, output=None, fault=diag.fault, strategy=None,
        success=False, lossy=False, lost="",
        detail=f"All strategies exhausted. {last_detail}",
    )


def _finalize(candidate: str, out_dir: str, stem: str, work: str) -> str:
    """Name the verified file <stem>.repaired.mp4 and remove leftovers."""
    final = os.path.join(out_dir, f"{stem}.repaired.mp4")
    if os.path.abspath(candidate) != os.path.abspath(final):
        shutil.move(candidate, final)
        if os.path.exists(work) and os.path.abspath(work) != os.path.abspath(final):
            S._rm(work)
    return final


VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}


def iter_videos(path: str, recursive: bool = False):
    """Yield video file paths from a file or directory."""
    if os.path.isfile(path):
        yield path
        return
    if recursive:
        for root, _dirs, files in os.walk(path):
            for name in sorted(files):
                if os.path.splitext(name)[1].lower() in VIDEO_EXTS:
                    yield os.path.join(root, name)
    else:
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            if os.path.isfile(full) and os.path.splitext(name)[1].lower() in VIDEO_EXTS:
                yield full
