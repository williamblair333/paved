"""Transcription engine interface and shared audio extraction."""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field

from paved import ffmpeg


@dataclass
class Segment:
    start: float
    end: float
    text: str


@dataclass
class Transcript:
    engine: str
    model: str
    language: str | None
    text: str
    segments: list[Segment] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "engine": self.engine,
            "model": self.model,
            "language": self.language,
            "text": self.text,
            "segments": [s.__dict__ for s in self.segments],
        }


class Engine:
    """Base class for transcription engines.

    Subclasses set `name` and `priority` (lower = preferred default) and implement
    `is_available()` and `transcribe()`. Engines lazy-import heavy deps inside
    those methods so an absent optional dependency never breaks import of the
    package — it just makes that one engine unavailable.
    """

    name: str = "base"
    priority: int = 100
    default_model: str = "base"

    def is_available(self) -> bool:
        raise NotImplementedError

    def transcribe(self, audio_path: str, model: str | None = None) -> Transcript:
        raise NotImplementedError


def extract_audio(src: str, sample_rate: int = 16000) -> str:
    """Extract mono PCM WAV at the given sample rate to a temp file. Returns path.

    16 kHz mono is what Whisper/Vosk/Sphinx all expect.
    """
    fd, wav = tempfile.mkstemp(suffix=".wav", prefix="paved_")
    os.close(fd)
    proc = ffmpeg.run(
        ["-v", "error", "-y", "-i", src,
         "-vn", "-ac", "1", "-ar", str(sample_rate), "-f", "wav", wav]
    )
    if proc.returncode != 0:
        try:
            os.remove(wav)
        except OSError:
            pass
        raise RuntimeError(f"audio extraction failed: {proc.stderr.strip()[:300]}")
    return wav
