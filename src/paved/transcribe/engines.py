# SPDX-License-Identifier: AGPL-3.0-only
"""Concrete transcription engines. All run fully offline.

Each engine lazy-imports its heavy dependency inside is_available()/transcribe()
so importing this module never fails just because one optional package is absent.
Priorities order the default selection: faster-whisper preferred, sphinx last.
"""
from __future__ import annotations

import importlib.util

from paved.transcribe.base import Engine, Segment, Transcript, extract_audio


def _have(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


class FasterWhisperEngine(Engine):
    name = "faster-whisper"
    priority = 10
    default_model = "base"

    def is_available(self) -> bool:
        return _have("faster_whisper")

    def transcribe(self, audio_path: str, model: str | None = None) -> Transcript:
        from faster_whisper import WhisperModel

        model_name = model or self.default_model
        # int8 on CPU: best speed/memory tradeoff on the target hardware.
        wm = WhisperModel(model_name, device="cpu", compute_type="int8")
        segments_iter, info = wm.transcribe(audio_path)
        segs, parts = [], []
        for s in segments_iter:
            segs.append(Segment(start=s.start, end=s.end, text=s.text.strip()))
            parts.append(s.text.strip())
        return Transcript(
            engine=self.name, model=model_name,
            language=getattr(info, "language", None),
            text=" ".join(parts).strip(), segments=segs,
        )


class WhisperCppEngine(Engine):
    name = "whisper.cpp"
    priority = 20
    default_model = "base"

    def is_available(self) -> bool:
        return _have("pywhispercpp")

    def transcribe(self, audio_path: str, model: str | None = None) -> Transcript:
        from pywhispercpp.model import Model

        model_name = model or self.default_model
        m = Model(model_name)
        result = m.transcribe(audio_path)
        segs, parts = [], []
        for s in result:
            text = s.text.strip()
            segs.append(Segment(start=s.t0 / 100.0, end=s.t1 / 100.0, text=text))
            parts.append(text)
        return Transcript(
            engine=self.name, model=model_name, language=None,
            text=" ".join(parts).strip(), segments=segs,
        )


class VoskEngine(Engine):
    name = "vosk"
    priority = 30
    default_model = "vosk-model-small-en-us-0.15"

    def is_available(self) -> bool:
        return _have("vosk")

    def transcribe(self, audio_path: str, model: str | None = None) -> Transcript:
        import json
        import wave

        from vosk import KaldiRecognizer, Model

        model_name = model or self.default_model
        m = Model(lang="en-us") if model is None else Model(model_path=model_name)
        parts = []
        with wave.open(audio_path, "rb") as wf:
            rec = KaldiRecognizer(m, wf.getframerate())
            rec.SetWords(True)
            while True:
                data = wf.readframes(4000)
                if not data:
                    break
                if rec.AcceptWaveform(data):
                    parts.append(json.loads(rec.Result()).get("text", ""))
            parts.append(json.loads(rec.FinalResult()).get("text", ""))
        text = " ".join(p for p in parts if p).strip()
        return Transcript(engine=self.name, model=model_name, language="en",
                          text=text, segments=[])


class PocketSphinxEngine(Engine):
    """Legacy engine, kept by request. Accuracy is poor — use Whisper if available."""
    name = "pocketsphinx"
    priority = 90
    default_model = "default"

    def is_available(self) -> bool:
        return _have("pocketsphinx")

    def transcribe(self, audio_path: str, model: str | None = None) -> Transcript:
        from pocketsphinx import AudioFile

        parts = [seg.hypothesis() or "" for seg in AudioFile(audio_file=audio_path)]
        return Transcript(
            engine=self.name, model=model or self.default_model, language="en",
            text=" ".join(p for p in parts if p).strip(), segments=[],
        )


ALL_ENGINES = [
    FasterWhisperEngine(),
    WhisperCppEngine(),
    VoskEngine(),
    PocketSphinxEngine(),
]
