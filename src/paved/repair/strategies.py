# SPDX-License-Identifier: AGPL-3.0-only
"""Repair strategies. Each takes a working-copy path + Diagnosis and returns a
StrategyOutcome. Strategies operate ONLY on the working copy, never the source.

A strategy returns applied=False when it does not apply to the given fault; the
pipeline then tries the next one.
"""
from __future__ import annotations

import os
import struct
from dataclasses import dataclass

from paved import ffmpeg
from paved.probe import (
    FAULT_MISSING_MDAT_HEADER,
    FAULT_NO_MOOV,
    FAULT_UNKNOWN_STRUCTURE,
)


@dataclass
class StrategyOutcome:
    applied: bool                 # did this strategy attempt a fix?
    output: str | None            # resulting file path (may equal working copy)
    lossy: bool = False
    lost: str = ""
    detail: str = ""


def reconstruct_mdat_header(work: str, diag) -> StrategyOutcome:
    """Rewrite a missing/zeroed 'mdat' box header in place.

    The media payload sits between the end of 'ftyp' and the start of 'moov';
    we write the 8-byte box header (size + 'mdat') so the payload is wrapped in
    a valid box. Lossless — no bytes move.
    """
    if diag.fault != FAULT_MISSING_MDAT_HEADER:
        return StrategyOutcome(applied=False, output=None)
    start = diag.extra.get("mdat_start")
    end = diag.extra.get("mdat_end")
    if start is None or end is None:
        return StrategyOutcome(applied=False, output=None,
                               detail="missing offsets for mdat reconstruction")
    size = end - start
    if not (0 < size < 2**32):
        # Would need a 64-bit box; not handled in v1.
        return StrategyOutcome(applied=False, output=None,
                               detail=f"mdat size {size} out of 32-bit range")
    header = struct.pack(">I", size) + b"mdat"
    with open(work, "r+b") as f:
        f.seek(start)
        f.write(header)
    return StrategyOutcome(
        applied=True, output=work, lossy=False,
        detail=f"wrote mdat header size={size} at offset {start}",
    )


def remux_faststart(work: str, diag) -> StrategyOutcome:
    """Stream-copy remux with +faststart. Fixes index/streaming quirks losslessly."""
    out = _sibling(work, ".remux.mp4")
    proc = ffmpeg.run(
        ["-v", "error", "-y", "-i", work, "-c", "copy",
         "-movflags", "+faststart", out]
    )
    if proc.returncode == 0 and os.path.exists(out):
        return StrategyOutcome(applied=True, output=out, lossy=False,
                               detail="remuxed with +faststart")
    _rm(out)
    return StrategyOutcome(applied=False, output=None,
                           detail=f"remux failed: {proc.stderr.strip()[:200]}")


def salvage_playable_span(work: str, diag) -> StrategyOutcome:
    """Seek past a damaged/zeroed head region and stream-copy the good remainder.

    Lossy: the skipped span is gone. We probe for the first decodable point by
    trying increasing start offsets, then copy from there.
    """
    for start in (5, 15, 30, 60, 90, 120, 180):
        out = _sibling(work, f".salvage{start}.mp4")
        proc = ffmpeg.run(
            ["-v", "error", "-y", "-ss", str(start),
             "-fflags", "+discardcorrupt", "-i", work,
             "-c", "copy", "-movflags", "+faststart", out]
        )
        if proc.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0:
            ok, _ = ffmpeg.decode_verify(out)
            if ok:
                return StrategyOutcome(
                    applied=True, output=out, lossy=True,
                    lost=f"first ~{start}s of the file (damaged/unflushed; unrecoverable)",
                    detail=f"salvaged playable span from t={start}s",
                )
        _rm(out)
    return StrategyOutcome(applied=False, output=None,
                           detail="no playable span found by seeking")


def transcode_rescue(work: str, diag) -> StrategyOutcome:
    """Last resort: full re-encode with error concealment. May lose quality."""
    out = _sibling(work, ".rescue.mp4")
    proc = ffmpeg.run(
        ["-v", "error", "-y", "-err_detect", "ignore_err",
         "-fflags", "+discardcorrupt", "-i", work,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-c:a", "aac", "-movflags", "+faststart", out]
    )
    if proc.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0:
        return StrategyOutcome(
            applied=True, output=out, lossy=True,
            lost="re-encoded (generation-loss); any undecodable frames dropped",
            detail="transcode rescue with error concealment",
        )
    _rm(out)
    return StrategyOutcome(applied=False, output=None,
                           detail=f"transcode failed: {proc.stderr.strip()[:200]}")


# Ordering: cheapest/lossless first, lossy last. The pipeline stops at the first
# strategy that yields a decode-verifiable file.
STRATEGY_ORDER = [
    reconstruct_mdat_header,
    remux_faststart,
    salvage_playable_span,
    transcode_rescue,
]

# Which strategies are worth trying for each fault (others are skipped fast).
FAULT_STRATEGIES = {
    FAULT_MISSING_MDAT_HEADER: [
        reconstruct_mdat_header, salvage_playable_span, transcode_rescue,
    ],
    FAULT_NO_MOOV: [salvage_playable_span, transcode_rescue],
    FAULT_UNKNOWN_STRUCTURE: [remux_faststart, salvage_playable_span, transcode_rescue],
}


def _sibling(path: str, suffix: str) -> str:
    base, _ = os.path.splitext(path)
    return base + suffix


def _rm(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass
