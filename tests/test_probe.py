from paved import probe


def test_clean_file_is_none_fault(tmp_path, good_mp4_bytes):
    p = tmp_path / "good.mp4"
    p.write_bytes(good_mp4_bytes)
    diag = probe.probe(str(p))
    assert diag.fault == probe.FAULT_NONE
    assert diag.container_ok is True


def test_missing_mdat_header_classified(tmp_path, missing_mdat_header_bytes):
    data, start, end = missing_mdat_header_bytes
    p = tmp_path / "broken.mp4"
    p.write_bytes(data)
    diag = probe.probe(str(p))
    assert diag.fault == probe.FAULT_MISSING_MDAT_HEADER
    assert diag.container_ok is False
    # Offsets the repair will use to rebuild the header.
    assert diag.extra["mdat_start"] == start
    assert diag.extra["mdat_end"] == end


def test_not_isobmff(tmp_path):
    p = tmp_path / "junk.mp4"
    p.write_bytes(b"\x00\x00\x00\x10not_a_box_at_all_here")
    diag = probe.probe(str(p))
    assert diag.fault == probe.FAULT_NOT_ISOBMFF
    assert diag.container_ok is False
