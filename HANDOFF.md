# HANDOFF

## Current State (2026-06-25)

Two sessions today on top of v1.0.0:

**Session 2 (this session)** — license + multi-provider LLM:
- License changed MIT → AGPL-3.0-only. `LICENSE` created, `pyproject.toml` updated, SPDX
  headers on all 13 source files.
- `src/paved/llm/` fully refactored: `ollama.py` deleted, replaced by `_base.py` (types/ABC),
  `_providers.py` (8 providers), `__init__.py` (router). CLI gains `--llm-provider` and
  `--llm-model` flags.
- 46/46 tests passing. All commits on `main`, not yet pushed to origin.
- **Single most important thing**: `from paved.llm import process, PROVIDER_NAMES, LLMResult`
  is the new public API. `from paved.llm import ollama` no longer works — it's gone.

**Session 1** — docs-only README marketing rewrite. GitHub About updated.

## Prior State (2026-06-22)

PAVED was revived from a broken stub into a working, Dockerized video toolkit
(v1.0.0). Two modes ship:

- **repair** — diagnoses and salvages broken MP4/MOV containers
  (`probe → copy → strategies → decode-verify → report`). Source is never
  modified. Lossy salvage reports exactly what was lost.
- **transcribe** — offline speech-to-text with four swappable engines
  (faster-whisper default, whisper.cpp, Vosk, PocketSphinx) and an optional
  Ollama clean/summary post-step that fails soft when Ollama is absent.

Verified this session:
- `docker compose build` succeeds (the old pip-before-compiler bug is fixed).
- All 4 engines report available inside the image.
- End-to-end `repair` on the original broken Clipchamp file (mdat header
  re-zeroed to reproduce the exact fault) produces a decode-clean 13:26 output;
  source confirmed untouched.
- 21/21 unit tests pass (no ffmpeg/models/network needed).
- Code review: 0 HIGH, 2 MEDIUM + 1 LOW — all fixed (mmap moov scan, Vosk
  handle leak, 64-bit moov size).

## Next Session

- **Nothing blocking.** v1 is complete and merged.
- Possible v1.1 work (deferred, not started): yt-dlp URL download mode, a
  first-class audio extract/convert mode, a watch-folder daemon, and a unit
  test for the 64-bit extended-size moov scan path (fix is in, dedicated test
  is not).
- Repair fault taxonomy is extensible: add a function to
  `src/paved/repair/strategies.py` and register it in `FAULT_STRATEGIES`.
  Add a transcription engine by subclassing `Engine` in
  `src/paved/transcribe/engines.py` and appending to `ALL_ENGINES`.

## Notes / Quirks

- Design spec: `docs/superpowers/specs/2026-06-18-paved-toolkit-design.md`.
- Host (non-Docker) runs need ffmpeg; `pip install -e ".[ffmpeg]"` bundles a
  static one via imageio-ffmpeg, or set `PAVED_FFMPEG`.
- Target hardware is CPU-only (no CUDA); faster-whisper uses int8 on CPU.
