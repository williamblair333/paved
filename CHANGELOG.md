# Changelog

## 1.0.0 — 2026-06-18

Complete rewrite. PAVED is now a video **repair + transcription** toolkit.

### Added
- **repair** mode: diagnose and salvage broken video containers.
  - Pure-Python ISO-BMFF box walker (`mp4box`) and fault classifier (`probe`).
  - Strategies: `reconstruct_mdat_header` (lossless), `remux_faststart` (lossless),
    `salvage_playable_span` (lossy, reports loss), `transcode_rescue` (last resort).
  - Safety: source never modified; works on a copy; every result must pass an
    ffmpeg decode-verify; lossy salvage reports exactly what was lost.
  - Single-file and recursive folder/batch processing.
- **transcribe** mode: pluggable offline engines — faster-whisper (default),
  whisper.cpp, Vosk, PocketSphinx — selected by priority or `--engine`.
- Optional local-LLM (Ollama) `--llm clean|summary` post-step; fail-soft when
  Ollama is absent.
- `probe` and `engines` subcommands; `--json` output for scripting.
- Test suite covering the box walker, fault classification, mdat reconstruction,
  engine registry/selection, and CLI parsing.

### Fixed
- **Docker build now succeeds.** The previous Dockerfile ran `pip install` before
  installing the compiler/swig, so `pocketsphinx` failed to build. Native build
  deps (build-essential, swig, cmake) + ffmpeg are now installed first.
- Removed the duplicate `pavet.py` (was byte-identical to `paved.py`).
- Dropped dead dependencies (`youtube-dl`, unused `moviepy`/`pydub`).

### Replaced
- PocketSphinx is no longer the only engine; it's kept as a low-priority option.
  Default transcription is faster-whisper (far higher accuracy, runs CPU-only).

### Hardening (post-review)
- `probe._scan_for_moov` now scans via `mmap` instead of reading the whole file
  into RAM (avoids OOM on multi-GB videos) and handles 64-bit extended-size moov.
- `VoskEngine` wraps the wave reader in a context manager (no file-handle leak on
  batch runs).
