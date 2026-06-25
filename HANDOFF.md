# HANDOFF

## Current State (2026-06-25)

Docs-only session on top of v1.0.0: `Readme.md` was rewritten into a heavier
"advertising" README (badges, benefit tables, engine comparison, formats, config,
roadmap, FAQ) — no code or behavior changed, every claim is grounded in the source.
The GitHub **About** description and **topics** were also refreshed for discoverability.
Shipped via PR → merge to `main`. Code state is unchanged from the v1.0.0 baseline below.

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
