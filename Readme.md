# PAVED — Video Repair & Transcription Toolkit

A Dockerized, **offline-first** command-line toolkit for video files:

- **repair** — diagnose and salvage broken / unplayable video containers
  (the origin: a Clipchamp export that wrote a valid index but left the `mdat`
  box header zeroed and the opening media as an unflushed hole).
- **transcribe** — speech-to-text with **multiple swappable local engines**
  (faster-whisper, whisper.cpp, Vosk, PocketSphinx) plus an optional local-LLM
  (Ollama) clean-up / summary step. Everything runs without a cloud API.

Everything runs in Docker with ffmpeg bundled — no host setup beyond Docker.

## Quick start

```bash
git clone https://github.com/williamblair333/paved.git
cd paved
docker compose build           # builds the image (ffmpeg + all engines)
mkdir -p data                  # put your video files here; mounted at /data
```

### Repair

```bash
# Diagnose only, write nothing:
docker compose run --rm app repair /data/broken.mp4 --dry-run

# Repair one file (output written alongside as <name>.repaired.mp4):
docker compose run --rm app repair /data/broken.mp4

# Repair an entire folder (e.g. a mounted USB copy):
docker compose run --rm app repair /data --recursive
```

The repair pipeline: **probe → copy → apply strategies (on the copy) → decode-verify → report.**
The source file is **never modified** — every fix runs on a copy and the result
must pass a full ffmpeg decode before success is claimed. When a salvage is
**lossy** (e.g. an unrecoverable damaged head region), the report says exactly
what was lost. It never claims a lossy salvage is lossless.

Fault strategies, tried cheapest-first:

| Strategy | Fixes | Lossy? |
|---|---|---|
| `reconstruct_mdat_header` | missing/zeroed `mdat` box header | no |
| `remux_faststart` | index/streaming quirks | no |
| `salvage_playable_span` | damaged/unflushed head region | yes (reported) |
| `transcode_rescue` | otherwise-undecodable streams | yes (re-encode) |

### Transcribe

```bash
# Best available engine (defaults to faster-whisper), writes <name>.txt + .json:
docker compose run --rm app transcribe /data/talk.mp4

# Pick an engine and model:
docker compose run --rm app transcribe /data/talk.mp4 --engine vosk
docker compose run --rm app transcribe /data/talk.mp4 --engine faster-whisper --model small

# Add a local-LLM post-step (needs Ollama running on the host):
docker compose run --rm app transcribe /data/talk.mp4 --llm clean
docker compose run --rm app transcribe /data/talk.mp4 --llm summary

# See engine availability:
docker compose run --rm app engines
```

The LLM step auto-detects Ollama at `host.docker.internal:11434`. If it's not
running, transcription still succeeds and emits the raw transcript with a warning —
it never fails the run. Default model `llama3.2:3b` (set `PAVED_LLM_MODEL`).

## Running on the host (without Docker)

```bash
pip install -e ".[all,ffmpeg]"   # or pick specific extras
paved repair /path/to/video.mp4
paved transcribe /path/to/video.mp4 --engine faster-whisper
```

## CLI reference

```
paved probe       PATH [--json]
paved repair      PATH [--out DIR] [--dry-run] [--recursive] [--json]
paved transcribe  PATH [--engine E] [--model M] [--llm off|clean|summary] [--out DIR] [--recursive]
paved engines
```

`PATH` may be a single file or a directory (use `--recursive` to descend).
Video extensions handled: mp4, mov, m4v, mkv, webm, avi.

## Design

See [`docs/superpowers/specs/2026-06-18-paved-toolkit-design.md`](docs/superpowers/specs/2026-06-18-paved-toolkit-design.md).

## License

MIT
