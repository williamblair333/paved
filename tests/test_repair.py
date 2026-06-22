"""Repair-strategy tests that need no ffmpeg: the mdat header reconstruction is
pure byte surgery, so we can verify it directly and re-probe the result.
"""
import struct

from paved import mp4box, probe
from paved.repair import strategies


def test_reconstruct_mdat_header_writes_valid_box(tmp_path, missing_mdat_header_bytes):
    data, start, end = missing_mdat_header_bytes
    p = tmp_path / "broken.mp4"
    p.write_bytes(data)
    diag = probe.probe(str(p))

    outcome = strategies.reconstruct_mdat_header(str(p), diag)
    assert outcome.applied is True
    assert outcome.lossy is False

    # The 8 bytes at `start` are now a valid mdat header spanning to `end`.
    with open(p, "rb") as f:
        f.seek(start)
        size = struct.unpack(">I", f.read(4))[0]
        tag = f.read(4)
    assert tag == b"mdat"
    assert size == end - start

    # And the file now parses cleanly: ftyp, mdat, moov, to EOF.
    boxes = mp4box.top_level(str(p))
    assert [b.type for b in boxes] == ["ftyp", "mdat", "moov"]
    assert boxes[-1].end == len(data)
    assert not any(b.truncated for b in boxes)


def test_strategy_skips_wrong_fault(tmp_path, good_mp4_bytes):
    p = tmp_path / "good.mp4"
    p.write_bytes(good_mp4_bytes)
    diag = probe.probe(str(p))  # fault == none
    outcome = strategies.reconstruct_mdat_header(str(p), diag)
    assert outcome.applied is False


def test_iter_videos_filters_extensions(tmp_path):
    from paved.repair import iter_videos

    (tmp_path / "a.mp4").write_bytes(b"x")
    (tmp_path / "b.txt").write_bytes(b"x")
    (tmp_path / "c.mkv").write_bytes(b"x")
    found = {p.rsplit("/", 1)[-1] for p in iter_videos(str(tmp_path))}
    assert found == {"a.mp4", "c.mkv"}
