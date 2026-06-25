# Changelog

## Unreleased — 2026-06-25 (session 2 — license + multi-provider LLM)

### Changed
- **License**: MIT → AGPL-3.0-only. `LICENSE` file created (canonical FSF text). `pyproject.toml`
  updated with `license = { text = "AGPL-3.0-only" }` and `license-files = ["LICENSE"]`.
- **`src/paved/llm/`**: Replaced single-provider `ollama.py` with a three-module design —
  `_base.py` (LLMResult, PROMPTS, LLMProvider ABC), `_providers.py` (8 providers), `__init__.py`
  (router with `process()` and `PROVIDER_NAMES`). Zero new runtime dependencies — stdlib HTTP only.

### Added
- **8 LLM providers**: `ollama` (default), `anthropic`, `claude-cli` (subscription, no API key),
  `google`, `openai`, `deepseek`, `qwen`, `openai-compat` (generic escape hatch).
- **`--llm-provider`** CLI flag on `paved transcribe` (also `PAVED_LLM_PROVIDER` env var).
- **`--llm-model`** CLI flag on `paved transcribe` (also `PAVED_LLM_MODEL` env var, pre-existing).
- **SPDX headers** (`# SPDX-License-Identifier: AGPL-3.0-only`) on all 13 non-stub source files.
- 25 new tests (46 total, all passing). New: `tests/test_llm_base.py`,
  `tests/test_llm_providers.py`, `tests/test_llm_router.py`.

### Removed
- `src/paved/llm/ollama.py` — fully migrated to `_providers.py::OllamaProvider`.

## Unreleased — 2026-06-25 (session 1 — docs)

### Changed
- **Readme.md**: full marketing-oriented rewrite — centered hero, badges, "Why PAVED?"
  benefit table, engine comparison table, and new sections (Supported Formats incl. audio
  extensions, How It Works, Configuration env-var table, Project Layout, Testing, Roadmap,
  FAQ, Contributing). All claims grounded in the actual code; no behavior changed.
- **GitHub About**: refreshed the repo description (was the stale "Python Audio Video
  Extractor in Docker") and added 20 discovery topics (video-repair, transcription,
  faster-whisper, offline-first, docker, ollama, iso-bmff, …).

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
