"""Engine registry + default-selection logic, with availability monkeypatched so
the tests need no ML packages installed.
"""
import pytest

from paved import transcribe
from paved.transcribe.base import Transcript


def _force(monkeypatch, available_names):
    """Make exactly the named engines report available."""
    for e in transcribe.ALL_ENGINES:
        monkeypatch.setattr(e, "is_available",
                            lambda n=e.name: n in available_names)


def test_registry_has_all_four():
    assert set(transcribe.registry()) == {
        "faster-whisper", "whisper.cpp", "vosk", "pocketsphinx",
    }


def test_default_prefers_highest_priority(monkeypatch):
    _force(monkeypatch, {"faster-whisper", "vosk", "pocketsphinx"})
    assert transcribe.select_engine(None).name == "faster-whisper"


def test_default_falls_back_when_whisper_absent(monkeypatch):
    _force(monkeypatch, {"vosk", "pocketsphinx"})
    assert transcribe.select_engine(None).name == "vosk"


def test_explicit_unavailable_engine_raises(monkeypatch):
    _force(monkeypatch, {"vosk"})
    with pytest.raises(RuntimeError, match="not installed"):
        transcribe.select_engine("faster-whisper")


def test_unknown_engine_raises(monkeypatch):
    _force(monkeypatch, {"vosk"})
    with pytest.raises(RuntimeError, match="Unknown engine"):
        transcribe.select_engine("does-not-exist")


def test_no_engine_available_raises(monkeypatch):
    _force(monkeypatch, set())
    with pytest.raises(RuntimeError, match="No transcription engine"):
        transcribe.select_engine(None)


def test_transcript_to_dict_roundtrip():
    t = Transcript(engine="x", model="m", language="en", text="hi")
    d = t.to_dict()
    assert d["engine"] == "x" and d["text"] == "hi" and d["segments"] == []
