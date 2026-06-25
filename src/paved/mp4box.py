# SPDX-License-Identifier: AGPL-3.0-only
"""Minimal ISO Base Media (MP4/MOV) box walker.

Pure-Python, no decoder. Walks the top-level box list and can recurse into
container boxes. Used by probe/repair to reason about structure without ffmpeg.

A box header is: 4-byte big-endian size, 4-byte type. size==1 means a 64-bit
size follows; size==0 means "extends to end of file".
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

# Box types that contain child boxes (the subset we ever recurse into).
CONTAINER_TYPES = {
    b"moov", b"trak", b"mdia", b"minf", b"stbl", b"edts", b"udta", b"dinf",
}


@dataclass
class Box:
    offset: int          # absolute file offset of the box header
    size: int            # full box size including header (resolved for 0/1 forms)
    type: str            # 4-char type, latin1-decoded
    header_size: int     # 8 or 16
    truncated: bool = False   # declared size runs past EOF
    children: list["Box"] = field(default_factory=list)

    @property
    def end(self) -> int:
        return self.offset + self.size

    @property
    def payload_offset(self) -> int:
        return self.offset + self.header_size


def _read_header(f, offset: int, container_end: int) -> Box | None:
    """Parse one box header at offset. Returns None if no full header fits."""
    f.seek(offset)
    hdr = f.read(8)
    if len(hdr) < 8:
        return None
    size = struct.unpack(">I", hdr[:4])[0]
    btype = hdr[4:8]
    header_size = 8
    truncated = False
    if size == 1:
        ext = f.read(8)
        if len(ext) < 8:
            return None
        size = struct.unpack(">Q", ext)[0]
        header_size = 16
    elif size == 0:
        size = container_end - offset  # extends to end
    if size < header_size:
        # Malformed/zeroed header: treat as "rest of container", flag it.
        size = container_end - offset
        truncated = True
    if offset + size > container_end:
        truncated = True
    # A null-type box (4 zero bytes) is never legitimate — it's a zeroed header.
    if btype == b"\x00\x00\x00\x00":
        truncated = True
    try:
        type_str = btype.decode("latin1")
    except Exception:
        type_str = repr(btype)
    return Box(offset=offset, size=size, type=type_str,
               header_size=header_size, truncated=truncated)


def walk(f, start: int, end: int, recurse: bool = False, _depth: int = 0) -> list[Box]:
    """Walk boxes in [start, end). Optionally recurse into container types."""
    boxes: list[Box] = []
    offset = start
    while offset < end - 8:
        box = _read_header(f, offset, end)
        if box is None:
            break
        if recurse and _depth < 8 and box.type.encode("latin1", "replace") in CONTAINER_TYPES:
            box.children = walk(
                f, box.payload_offset, box.end, recurse=True, _depth=_depth + 1
            )
        boxes.append(box)
        if box.size <= 0:
            break
        offset = box.end
    return boxes


def top_level(path: str, recurse: bool = False) -> list[Box]:
    """Walk the top-level boxes of a file."""
    import os

    total = os.path.getsize(path)
    with open(path, "rb") as f:
        return walk(f, 0, total, recurse=recurse)


def find_first(boxes: list[Box], type_: str) -> Box | None:
    for b in boxes:
        if b.type == type_:
            return b
    return None
