<div align="center">

# 🎬 PAVED

### Salvage broken videos. Transcribe anything. 100% offline.

**PAVED** is a Dockerized, **offline-first** command-line toolkit that does two hard things well:
it **repairs broken / unplayable video containers** that other tools give up on, and it
**transcribes speech** with four swappable local engines — all without ever touching the cloud.

No API keys. No uploads. No telemetry. Your media never leaves your machine.

<br>

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white)
![ffmpeg](https://img.shields.io/badge/ffmpeg-bundled-007808?logo=ffmpeg&logoColor=white)
![Offline](https://img.shields.io/badge/cloud-not%20required-success)
![Tests](https://img.shields.io/badge/tests-21%2F21%20passing-brightgreen)
![Version](https://img.shields.io/badge/version-1.0.0-orange)

<br>

```bash
docker compose run --rm app repair     /data/broken.mp4
docker compose run --rm app transcribe /data/talk.mp4 --llm summary
```

</div>

---

## ✨ Why PAVED?

Most "video repair" tools are either expensive black-box GUIs or shell one-liners that
re-encode (and degrade) your footage on the first try. Most transcription tools ship your
audio to someone else's servers. PAVED was built to do neither.

It was born from a real disaster: a **Clipchamp export that wrote a valid index but left the
`mdat` box header zeroed and the opening media as an unflushed hole** — a file every player
refused to open. PAVED reconstructs exactly that kind of damage, **losslessly when possible**,
and tells you the truth when it can't.

| | |
|---|---|
| 🛡️ **Never destroys your source** | Every fix runs on a *copy*. The original is read-only, always. |
| 🔬 **Honest about loss** | Lossless fixes are tried first. A lossy salvage reports *exactly* what was lost — it never lies about a clean recovery. |
| ✅ **Verifies before it claims success** | Every repaired file must pass a full ffmpeg decode before PAVED calls it fixed. |
| 🔌 **Four transcription engines, swappable** | faster-whisper, whisper.cpp, Vosk, PocketSphinx — auto-selected or pick your own. |
| 🤖 **Optional local-LLM polish** | Pipe transcripts through Ollama for cleanup or summaries — and it *fail-softs* if Ollama isn't running. |
| 🐳 **One-command Docker** | ffmpeg + every engine baked into the image. Zero host setup. |
| 📴 **Truly offline** | No accounts, no keys, no network calls in the hot path. |
| 🧩 **Scriptable** | `--json` on every command for clean automation and CI pipelines. |

---

## 📑 Table of Contents

- [Quick Start](#-quick-start)
- [Repair](#-repair) · [Transcribe](#-transcribe) · [Local-LLM Polish](#-local-llm-polish)
- [Running Without Docker](#-running-on-the-host-without-docker)
- [CLI Reference](#-cli-reference)
- [Supported Formats](#-supported-formats)
- [How It Works](#-how-it-works)
- [Configuration](#-configuration)
- [Project Layout](#-project-layout)
- [Testing](#-testing)
- [Roadmap](#-roadmap)
- [FAQ](#-faq)
- [Contributing](#-contributing) · [License](#-license)

---

## 🚀 Quick Start

Everything runs in Docker with **ffmpeg bundled** — no host setup beyond Docker itself.

```bash
git clone https://github.com/williamblair333/paved.git
cd paved
docker compose build           # builds the image (ffmpeg + all engines)
mkdir -p data                  # drop your video files here — mounted at /data
```

Then point PAVED at any file or folder under `./data`:

```bash
docker compose run --rm app probe      /data/broken.mp4
docker compose run --rm app repair     /data/broken.mp4
docker compose run --rm app transcribe /data/talk.mp4
docker compose run --rm app engines
```

---

## 🔧 Repair

Diagnose and salvage broken, truncated, or unplayable video containers.

```bash
# Diagnose only — write nothing:
docker compose run --rm app repair /data/broken.mp4 --dry-run

# Repair one file (output written alongside as <name>.repaired.mp4):
docker compose run --rm app repair /data/broken.mp4

# Repair an entire folder (e.g. a mounted USB recovery copy):
docker compose run --rm app repair /data --recursive
```

**The pipeline:** `probe → copy → apply strategies (on the copy) → decode-verify → report`

The source file is **never modified**. Every fix runs on a copy, and the result **must pass a
full ffmpeg decode** before success is claimed. When a salvage is **lossy** (e.g. an
unrecoverable damaged head region), the report says exactly what was lost. It never claims a
lossy salvage is lossless.

Fault strategies, tried **cheapest-first**:

| Strategy | Fixes | Lossy? |
|---|---|---|
| `reconstruct_mdat_header` | missing / zeroed `mdat` box header | ✅ no — lossless |
| `remux_faststart` | index / streaming / faststart quirks | ✅ no — lossless |
| `salvage_playable_span` | damaged / unflushed head region | ⚠️ yes (loss reported) |
| `transcode_rescue` | otherwise-undecodable streams | ⚠️ yes (re-encode) |

> The taxonomy is extensible — add a function to `src/paved/repair/strategies.py` and register
> it in `FAULT_STRATEGIES`.

---

## 🎙️ Transcribe

Offline speech-to-text from **video *or* audio** files, with four swappable engines.

```bash
# Best available engine (defaults to faster-whisper); writes <name>.txt + <name>.json:
docker compose run --rm app transcribe /data/talk.mp4

# Pick an engine and/or model:
docker compose run --rm app transcribe /data/talk.mp4 --engine vosk
docker compose run --rm app transcribe /data/talk.mp4 --engine faster-whisper --model small

# Transcribe a whole folder:
docker compose run --rm app transcribe /data --recursive

# See which engines are installed and which is the default:
docker compose run --rm app engines
```

### Engine line-up

| Engine | Priority | Accuracy | Notes |
|---|---|---|---|
| **faster-whisper** ⭐ | 10 (default) | Excellent | CTranslate2 Whisper, CPU `int8` — fast & accurate on plain CPUs |
| **whisper.cpp** | 20 | Excellent | Pure-C++ Whisper via `pywhispercpp` |
| **Vosk** | 30 | Good | Lightweight Kaldi models, low memory |
| **PocketSphinx** | 90 | Basic | Legacy fallback, kept by request |

PAVED auto-selects the **highest-priority installed engine**, or transcribes with whatever you
pass to `--engine`. Every run emits both a plain-text `.txt` and a structured `.json` (with
per-segment timestamps where the engine provides them).

---

## 🤖 Local-LLM Polish

Optionally pipe a raw transcript through a **local** Ollama model for cleanup or summarization:

```bash
docker compose run --rm app transcribe /data/talk.mp4 --llm clean     # tidy punctuation/casing
docker compose run --rm app transcribe /data/talk.mp4 --llm summary   # condensed summary
```

The LLM step auto-detects Ollama at `host.docker.internal:11434`. If Ollama isn't running,
**transcription still succeeds** and emits the raw transcript with a warning — it *never* fails
the run. Default model is `llama3.2:3b` (override with `PAVED_LLM_MODEL`).

---

## 💻 Running on the Host (without Docker)

```bash
pip install -e ".[all,ffmpeg]"   # or pick specific extras (see below)
paved repair     /path/to/video.mp4
paved transcribe /path/to/video.mp4 --engine faster-whisper
```

Pick only what you need via optional extras:

| Extra | Installs |
|---|---|
| `faster-whisper` | faster-whisper engine |
| `whispercpp` | whisper.cpp engine |
| `vosk` | Vosk engine |
| `sphinx` | PocketSphinx engine |
| `ffmpeg` | a bundled static ffmpeg (via `imageio-ffmpeg`) |
| `all` | every transcription engine |
| `dev` | the test suite (`pytest`) |

> Repair-only? Install the bare package — it has **zero required dependencies** beyond ffmpeg,
> so a lightweight install never fails on an engine build you don't need.

---

## 📖 CLI Reference

```text
paved probe       PATH [--json]
paved repair      PATH [--out DIR] [--dry-run] [--recursive] [--json]
paved transcribe  PATH [--engine E] [--model M] [--llm off|clean|summary] [--out DIR] [--recursive]
paved engines
paved --version
```

`PATH` may be a single file **or a directory** (use `--recursive` to descend).
Exit codes are script-friendly: `0` success, `1` a real failure, `2` nothing found / fault present.

---

## 🗂️ Supported Formats

| | Extensions |
|---|---|
| **Video** (repair + transcribe) | `.mp4` `.mov` `.m4v` `.mkv` `.webm` `.avi` |
| **Audio** (transcribe) | `.mp3` `.wav` `.m4a` `.aac` `.flac` `.ogg` |

---

## 🧠 How It Works

PAVED is a small, dependency-light Python package with a clean separation of concerns:

- **`mp4box`** — a pure-Python ISO-BMFF (MP4/MOV) box walker. No native libs.
- **`probe`** — a fault classifier that names *what's wrong* with a container (and scans for
  `moov` via `mmap`, so it won't OOM on multi-GB files).
- **`repair`** — orchestrates the copy → strategy → decode-verify → report loop.
- **`transcribe`** — an engine registry that lazy-imports each backend, so one missing optional
  package never breaks the others.
- **`llm`** — the fail-soft Ollama post-processor.
- **`ffmpeg`** — a thin, configurable wrapper around the system (or bundled) ffmpeg binary.

Every transcription engine runs **fully offline**, and the repair path makes **no network calls
at all**.

---

## ⚙️ Configuration

| Environment variable | Purpose | Default |
|---|---|---|
| `PAVED_LLM_MODEL` | Ollama model for `--llm clean/summary` | `llama3.2:3b` |
| `OLLAMA_HOST` | Ollama endpoint (set in the image) | `http://host.docker.internal:11434` |
| `PAVED_FFMPEG` | Path to a specific ffmpeg binary | auto-detected / bundled |

The Compose service mounts `./data → /data` and wires `host.docker.internal` so the container
can reach an Ollama instance running on your host.

---

## 📁 Project Layout

```text
paved/
├── src/paved/
│   ├── cli.py              # argparse entry point (probe/repair/transcribe/engines)
│   ├── mp4box.py           # pure-Python ISO-BMFF box walker
│   ├── probe.py            # container fault classifier
│   ├── ffmpeg.py           # ffmpeg wrapper (decode-verify, remux, transcode)
│   ├── report.py           # human + JSON reporting
│   ├── repair/
│   │   └── strategies.py   # fault → fix strategies (FAULT_STRATEGIES registry)
│   ├── transcribe/
│   │   ├── base.py         # Engine ABC, audio extraction, Transcript model
│   │   └── engines.py      # faster-whisper / whisper.cpp / Vosk / PocketSphinx
│   └── llm/ollama.py       # fail-soft local-LLM post-step
├── tests/                  # 21 unit tests — no ffmpeg/models/network needed
├── docs/                   # design spec
├── Dockerfile              # native deps + ffmpeg FIRST, then pip
├── docker-compose.yml
└── pyproject.toml
```

---

## 🧪 Testing

```bash
pip install -e ".[dev]"
pytest
```

The suite (**21/21 passing**) covers the box walker, fault classification, `mdat`
reconstruction, the engine registry/selection logic, and CLI parsing — and needs **no ffmpeg,
no models, and no network**, so it runs anywhere in seconds.

---

## 🛣️ Roadmap

v1.0 is complete and merged. Candidate work for future releases:

- 📥 `yt-dlp` URL download mode
- 🎵 First-class audio extract / convert mode
- 👀 Watch-folder daemon for hands-off batch processing
- 🧪 Dedicated test for the 64-bit extended-size `moov` scan path

---

## ❓ FAQ

**Does anything get uploaded to the cloud?**
No. Every engine runs locally and the repair path makes no network calls. The only optional
network hop is to a **local** Ollama instance you control.

**Will repair re-encode and degrade my video?**
Only as a last resort, and only when nothing lossless works — and the report tells you when that
happens. Lossless strategies are always tried first.

**Can it hurt my original file?**
No. The source is opened read-only and every fix is applied to a copy.

**Do I need a GPU?**
No. The target is CPU-only; faster-whisper uses `int8` quantization and runs comfortably on a
plain CPU.

**What if I only want repair?**
Install the bare package — it pulls in **no** transcription engines and stays light.

---

## 🤝 Contributing

Extending PAVED is intentionally easy:

- **New repair strategy** → add a function to `src/paved/repair/strategies.py` and register it
  in `FAULT_STRATEGIES`.
- **New transcription engine** → subclass `Engine` in `src/paved/transcribe/engines.py` and
  append it to `ALL_ENGINES`.

Run `pytest` before opening a PR. See the full design spec in
[`docs/superpowers/specs/2026-06-18-paved-toolkit-design.md`](docs/superpowers/specs/2026-06-18-paved-toolkit-design.md).

---

## 📜 License

[MIT](LICENSE) © William Blair

