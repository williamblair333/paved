from paved import mp4box


def test_walks_clean_structure(tmp_path, good_mp4_bytes):
    p = tmp_path / "good.mp4"
    p.write_bytes(good_mp4_bytes)
    boxes = mp4box.top_level(str(p))
    assert [b.type for b in boxes] == ["ftyp", "mdat", "moov"]
    # Last box ends exactly at EOF; nothing truncated.
    assert boxes[-1].end == len(good_mp4_bytes)
    assert not any(b.truncated for b in boxes)


def test_zeroed_header_flagged_truncated(tmp_path, missing_mdat_header_bytes):
    data, _start, _end = missing_mdat_header_bytes
    p = tmp_path / "broken.mp4"
    p.write_bytes(data)
    boxes = mp4box.top_level(str(p))
    # First box is ftyp; the zeroed-header region is flagged truncated.
    assert boxes[0].type == "ftyp"
    assert any(b.truncated for b in boxes)


def test_recurse_into_moov(tmp_path, good_mp4_bytes):
    p = tmp_path / "good.mp4"
    p.write_bytes(good_mp4_bytes)
    boxes = mp4box.top_level(str(p), recurse=True)
    moov = mp4box.find_first(boxes, "moov")
    assert moov is not None
    assert [c.type for c in moov.children] == ["mvhd"]


def test_find_first_returns_none_when_absent(tmp_path, good_mp4_bytes):
    p = tmp_path / "good.mp4"
    p.write_bytes(good_mp4_bytes)
    boxes = mp4box.top_level(str(p))
    assert mp4box.find_first(boxes, "nope") is None
