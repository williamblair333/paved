# paved — run `just` for this list.
# Each recipe is one line; the commands are the ones the Readme documents.

# list recipes
default:
    @just --list

# build the image (ffmpeg + all transcription engines)
setup:
    docker compose build

# run the tests (no ffmpeg, models or network needed; host needs: pip install -e ".[dev]")
test *args:
    pytest {{args}}

# the paved CLI in the container: just paved probe|repair|transcribe|engines /data/FILE ...
paved *args:
    docker compose run --rm app {{args}}
