"""Shared fixtures: synthetic MP4 byte structures (no real media, no ffmpeg)."""
import struct

import pytest


def box(box_type: bytes, payload: bytes) -> bytes:
    """Build a well-formed box: size(4) + type(4) + payload."""
    size = 8 + len(payload)
    return struct.pack(">I", size) + box_type + payload


@pytest.fixture
def good_mp4_bytes():
    """ftyp + mdat + moov, all well-formed, parses cleanly to EOF."""
    ftyp = box(b"ftyp", b"isom" + b"\x00" * 8)
    mdat = box(b"mdat", b"\x11" * 200)
    moov = box(b"moov", box(b"mvhd", b"\x00" * 90))
    return ftyp + mdat + moov


@pytest.fixture
def missing_mdat_header_bytes():
    """ftyp + [zeroed 8-byte header + raw media] + moov.

    Mirrors the real Clipchamp fault: the mdat box header is zeroed, so a walker
    sees a size-0 box that swallows the rest of the file, yet a valid moov exists.
    """
    ftyp = box(b"ftyp", b"isom" + b"\x00" * 8)
    media = b"\x00" * 8 + b"\x42" * 300        # zeroed header, then real payload
    moov = box(b"moov", box(b"mvhd", b"\x00" * 90))
    return ftyp + media + moov, len(ftyp), len(ftyp) + len(media)
