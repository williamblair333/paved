# PAVED Toolkit — Design

**Date:** 2026-06-18
**Status:** Approved (build A, ship)

## Background

`paved` was an early "audio/video → text" stub. It did not build (pip installed
`pocketsphinx` before `build-essential`, so the wheel could not compile), shipped two
byte-identical scripts (`paved.py` / `pavet.py`), referenced a dead dependency
(`youtube-dl`), and used CMU PocketSphinx, whose transcription quality is poor.

This revives `paved` as a real, Dockerized **video toolkit**. v1 ships two modes:

1. **repair** — diagnose and salvage broken/unplayable video containers.
2. **transcribe** — speech-to-text with multiple swappable local engines, plus an
   optional local-LLM (Ollama) post-processing step.

The repair mode is the origin: a Clipchamp export wrote `ftyp` + `moov` but left the
`mdat` box header zeroed and the first ~30 MB of media as an unflushed hole. The proven
recovery (rebuild `mdat` header, then salvage the playable remainder) is the seed of the
repair pipeline.

## Constraints (target hardware)

- CPU-only (AMD Ryzen 5650U, no CUDA GPU), 12 threads, ~14 GB RAM.
- Default transcription engine: **faster-whisper** (CTranslate2, `int8`, CPU), default
  model `base` for sane speed; model configurable.
- Ollama is **not** installed; the LLM step must auto-detect and degrade gracefully.

## Architecture (Approach A)

One Python package, one CLI with subcommands, one Docker image.

```
src/paved/
  cli.py            # argparse subcommands: repair, transcribe, probe, engines
  ffmpeg.py         # locate ffmpeg/ffprobe (env > system > bundled)
  report.py         # structured result + human summary + JSON
  mp4box.py         # MP4/ISO-BMFF top-level atom walker
  probe.py          # structural probe, fault classification, decode-verify
  repair/
    __init__.py     # strategy registry + repair pipeline
    strategies.py   # one function per fault strategy
  transcribe/
    __init__.py     # engine registry + default selection
    base.py         # Engine interface (name, is_available, transcribe)
    engines.py      # faster-whisper, whisper.cpp, vosk, pocketsphinx
  llm/
    ollama.py       # optional transcript clean/summarize via local Ollama
```

Adding a fault strategy = add one function + register it. Adding an engine = add one
class + register it. Each unit is independently testable.

### Safety model (repair)

- **Never modify the source.** Always operate on a copy in the output dir.
- `--dry-run` reports the diagnosis and planned actions without writing.
- Every run emits a report stating what was wrong, what was done, and **what is
  permanently lost** (e.g., unflushed holes). Never claim a lossy salvage is lossless.

## Repair pipeline

`probe → classify → apply strategies (on copy) → decode-verify → report`

Decode-verify ground truth: `ffmpeg -v error -i FILE -map 0 -f null -` (exit 0 + no
errors = playable). A thumbnail frame can be extracted for visual sanity.

### Fault strategies (v1)

| Strategy | Trigger | Action | Lossy? |
|---|---|---|---|
| `reconstruct_mdat_header` | zero/blank box header between `ftyp` and a valid `moov` | rewrite the `mdat` box header to span the gap | no |
| `remux_faststart` | parses but won't stream / index quirk | `ffmpeg -c copy -movflags +faststart` | no |
| `salvage_playable_span` | decode fails at head due to a zero hole / truncation | input-seek past the dead zone, stream-copy the good remainder | yes (lost span reported) |
| `transcode_rescue` | copy paths still fail | full re-encode with error concealment (`-err_detect ignore_err`, `-fflags +discardcorrupt`) | maybe |

Strategies are tried cheapest-first; the pipeline stops at the first that yields a
clean decode-verify.

## Transcribe mode

`extract audio (ffmpeg → 16 kHz mono wav) → engine.transcribe → optional LLM post → write`

- Engines registered: `faster-whisper` (default), `whisper.cpp`, `vosk`, `pocketsphinx`.
- Default = first **available** engine in priority order.
- `--engine` overrides; `paved engines` lists availability.
- `--model` sets the engine model (default `base` for whisper-family).
- Output: `<name>.txt` plus `<name>.json` (segments + metadata) in the output dir.

### LLM post-step (Ollama)

- `--llm clean|summary|off` (default `off`).
- Talks to `OLLAMA_HOST` (default `http://localhost:11434`, or `host.docker.internal`
  inside Docker). Auto-detects; if unreachable, emits the raw transcript and a warning —
  never fails the run.
- Default model `llama3.2:3b` (configurable), suited to CPU + 14 GB RAM.

## CLI

```
paved probe      PATH                              # diagnose only
paved repair     PATH [--out DIR] [--dry-run] [--recursive]
paved transcribe PATH [--engine E] [--model M] [--llm clean|summary|off] [--out DIR]
paved engines                                      # list engines + availability
```

`PATH` may be a file or a directory; directories process every video file found
(recursively with `--recursive`). Video extensions: mp4, mov, m4v, mkv, webm, avi.

## Docker

- Base `python:3.12-slim`. Install **build deps + swig + ffmpeg first**, then
  `pip install`, fixing the original ordering bug. Install all engine deps so every
  engine is wired; code lazy-imports so a partial environment still runs.
- `console_scripts` entry point `paved`. `entrypoint.sh` execs `paved "$@"`.
- compose mounts a work dir for input/output.

## Testing

Unit tests that need no ffmpeg/models/network:

- `mp4box`: walk synthetic atom bytes.
- `probe`: classify a synthetic `ftyp` + zeroed-box + `moov` as missing `mdat` header.
- `repair`: `reconstruct_mdat_header` writes the correct size + `mdat` tag; atoms then
  parse to EOF.
- `transcribe`: registry + default-selection with monkeypatched availability.
- `cli`: argument parsing smoke.

Integration proof (manual, in-session): build the image; run `paved repair` on the real
broken Clipchamp file and confirm a clean decode-verify.

## Out of scope (v1)

URL download (yt-dlp), audio extract/convert as a first-class mode, watch-folder daemon,
GPU acceleration. Architecture leaves room for each.
