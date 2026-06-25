# SPDX-License-Identifier: AGPL-3.0-only
"""Structural probe + fault classification for video containers.

Classifies a file into one of a known set of faults using only byte-level
structure (no decoder). The repair pipeline maps each fault to strategies.
"""
from __future__ import annotations

import struct

from paved import mp4box
from paved.report import Diagnosis

# Fault codes
FAULT_NONE = "none"
FAULT_MISSING_MDAT_HEADER = "missing_mdat_header"
FAULT_NO_MOOV = "no_moov"
FAULT_NOT_ISOBMFF = "not_isobmff"
FAULT_UNKNOWN_STRUCTURE = "unknown_structure"

_FTYP = "ftyp"
_MOOV = "moov"
_MDAT = "mdat"


def _scan_for_moov(path: str, total: int) -> int | None:
    """Locate a 'moov' box by raw byte scan when the walk can't reach it.

    A zeroed 'mdat' header (size 0) makes the walker swallow everything to EOF,
    hiding 'moov'. We find the last 'moov' tag whose preceding size field makes
    the box end exactly at EOF — the same signal that identified the real moov
    in the original recovery.

    Uses mmap so a multi-GB file is not read into RAM. Handles both 32-bit and
    64-bit (extended-size) box headers.
    """
    import mmap

    if total < 8:
        return None
    with open(path, "rb") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            idx = mm.rfind(b"moov")
            while idx != -1:
                if idx >= 4:
                    box_start = idx - 4
                    size = struct.unpack(">I", mm[box_start:idx])[0]
                    if size == 1 and idx >= 12:
                        # 64-bit extended size follows the type field.
                        size = struct.unpack(">Q", mm[idx + 4:idx + 12])[0]
                        box_start = idx - 4
                    if size >= 8 and box_start + size == total:
                        return box_start
                idx = mm.rfind(b"moov", 0, idx)
    return None


def probe(path: str) -> Diagnosis:
    """Diagnose a file's container structure."""
    import os

    total = os.path.getsize(path)
    boxes = mp4box.top_level(path)
    types = [b.type for b in boxes]

    # Is this even ISO-BMFF? First box should be ftyp (or a known leading box).
    if not boxes or boxes[0].type != _FTYP:
        return Diagnosis(
            path=path, container_ok=False, fault=FAULT_NOT_ISOBMFF,
            detail="File does not begin with an 'ftyp' box; not a recognizable MP4/MOV.",
            boxes=types,
        )

    has_moov_walk = any(b.type == _MOOV for b in boxes)
    has_mdat_walk = any(b.type == _MDAT for b in boxes)
    parses_clean = (
        boxes[-1].end == total
        and not any(b.truncated for b in boxes)
    )

    if parses_clean and has_moov_walk:
        return Diagnosis(
            path=path, container_ok=True, fault=FAULT_NONE,
            detail="Container structure parses cleanly to EOF.",
            boxes=types,
        )

    ftyp = boxes[0]
    second = boxes[1] if len(boxes) > 1 else None
    # The box right after ftyp is blank/zeroed when its header is corrupt:
    # either flagged truncated or its type is all-null.
    blank_after_ftyp = second is not None and (
        second.truncated or second.type.strip("\x00") == ""
    )
    moov_off = _scan_for_moov(path, total)

    # Signature: ftyp + zeroed mdat header + a valid moov found by scan.
    if moov_off is not None and not has_mdat_walk and blank_after_ftyp:
        return Diagnosis(
            path=path, container_ok=False, fault=FAULT_MISSING_MDAT_HEADER,
            detail=(
                "Valid 'ftyp' and 'moov' present, but the 'mdat' box header is "
                "missing/zeroed. The media payload exists but is not wrapped in a "
                "box, so players see an invalid box and stop. The header can be "
                "rebuilt in place."
            ),
            boxes=types,
            extra={"mdat_start": ftyp.end, "mdat_end": moov_off,
                   "moov_offset": moov_off},
        )

    if moov_off is None and not has_moov_walk:
        return Diagnosis(
            path=path, container_ok=False, fault=FAULT_NO_MOOV,
            detail=(
                "No 'moov' index found. File is likely truncated or never "
                "finalized; recovery needs a reference file or transcode rescue."
            ),
            boxes=types,
        )

    if parses_clean:
        return Diagnosis(
            path=path, container_ok=True, fault=FAULT_NONE,
            detail="Container structure parses cleanly to EOF.",
            boxes=types,
        )

    return Diagnosis(
        path=path, container_ok=False, fault=FAULT_UNKNOWN_STRUCTURE,
        detail="Container has structural anomalies not matched to a known fault.",
        boxes=types,
    )
