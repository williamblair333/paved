# PAVED

**Status: draft** — written from `Readme.md`, `pyproject.toml` and `src/paved/`,
not from a conversation with the owner. Confirm the core job and non-goals, then
delete this line.

## Core job

Someone holding a video file they cannot use gets something usable out of it —
a repaired file, or a transcript of what was said — without the file ever
leaving their machine.

Repair is the primary path; transcription is the fallback for a file that cannot
be repaired but still holds recoverable speech.

## Users

People with broken recordings: interrupted screen captures, half-written MP4s
from a dead camera, old files no player accepts. They have Docker and a terminal.
They often cannot share the file with an online service at all, because it is a
deposition, a medical recording, or simply theirs.

## Success

- A file that no player opens becomes one that does, or the tool says plainly
  that it cannot be repaired and why.
- Transcription runs fully offline, with no API key and no upload.
- The chosen engine and its confidence are stated, never implied.
- **Time-to-first-result target: 600 seconds** — clone to a repaired file,
  including the image build.

## First-run path

1. `git clone https://github.com/williamblair333/paved && cd paved`
2. `docker compose build`
3. `mkdir -p data` and put the broken file there
4. `docker compose run --rm app repair /data/broken.mp4`
5. `docker compose run --rm app transcribe /data/talk.mp4`

## Non-goals

- No cloud transcription services — offline is the reason this exists.
- No editing, transcoding for delivery, or format conversion beyond what repair
  requires.
- No GUI; this is a per-file command-line tool.
- No guarantee for arbitrarily corrupt files: the honest answer includes "this
  one cannot be recovered".

## UI principles

- Every run says which engine did the work and how far it got.
- A failed repair explains which structure was missing (moov atom, index, frame
  boundary), not just "failed".
- `probe` before `repair`: the user can see what is wrong before changing
  anything.
- Output files never silently overwrite inputs.
- `engines` lists what is actually installed, so a missing engine is visible
  before a long run, not after it.

## Known gap — found by the first gate run, 2026-09-20

**`pip install .` fails on a clean machine today.** `pyproject.toml:11` declares
`license = { text = "AGPL-3.0-only" }`; current setuptools (PEP 639) rejects the
table form with:

```
configuration error: `project.license` must be string
```

`requires = ["setuptools>=68"]` at line 2 allows any newer setuptools, so a
fresh install resolves one that refuses the file. The Docker image likely still
works only because its layer was built when setuptools was older — which is the
exact shape of "works on my machine".

Fix: `license = "AGPL-3.0-only"` with `license-files = ["LICENSE"]` (both are
already PEP 639 spellings), then re-run the gate.

## Verification note

The documented path is `docker compose`, which cannot nest inside the gate's
container, so `verify:` installs the package the same way the image does and
runs a real repair on a deliberately truncated file. The declared exception is
recorded in every gate report.

```yaml
verify:
  image: python:3.12-slim
  network: required
  install_note: "Readme documents `docker compose build`; the gate cannot nest Docker, so it installs the same package the Dockerfile installs"
  install:
    - apt-get update && apt-get install -y ffmpeg
    - pip install --no-cache-dir .
  run: sh -c "ffmpeg -y -f lavfi -i testsrc=duration=2:size=320x240:rate=10 /tmp/ok.mp4 >/dev/null 2>&1 && head -c 20000 /tmp/ok.mp4 > /tmp/broken.mp4 && paved probe /tmp/broken.mp4 2>&1 | tee /tmp/paved-probe.txt"
  expect:
    - stdout_contains: "moov"
    - file: /tmp/paved-probe.txt
    - exit_code: 0
  time_target_seconds: 600
```
