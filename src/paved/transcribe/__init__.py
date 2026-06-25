# SPDX-License-Identifier: AGPL-3.0-only
"""Engine registry, default selection, and the transcribe pipeline."""
from __future__ import annotations

import os

from paved.transcribe.base import Transcript, extract_audio
from paved.transcribe.engines import ALL_ENGINES


def registry() -> dict:
    return {e.name: e for e in ALL_ENGINES}


def available_engines() -> list:
    """Engines whose dependency is installed, in priority order."""
    return sorted(
        (e for e in ALL_ENGINES if e.is_available()),
        key=lambda e: e.priority,
    )


def select_engine(name: str | None):
    """Pick an engine by name, or the highest-priority available one.

    Raises RuntimeError with guidance if the request can't be satisfied.
    """
    reg = registry()
    if name:
        if name not in reg:
            raise RuntimeError(
                f"Unknown engine '{name}'. Known: {', '.join(reg)}."
            )
        engine = reg[name]
        if not engine.is_available():
            raise RuntimeError(
                f"Engine '{name}' is selected but its dependency is not installed."
            )
        return engine
    avail = available_engines()
    if not avail:
        raise RuntimeError(
            "No transcription engine is available. Install one of: "
            + ", ".join(registry())
        )
    return avail[0]


def transcribe_file(
    src: str,
    engine_name: str | None = None,
    model: str | None = None,
) -> Transcript:
    """Extract audio and transcribe with the chosen (or best-available) engine."""
    engine = select_engine(engine_name)
    wav = extract_audio(src)
    try:
        return engine.transcribe(wav, model=model)
    finally:
        try:
            os.remove(wav)
        except OSError:
            pass
