# PAVED — video repair + transcription toolkit
FROM python:3.12-slim

# --- system build deps + ffmpeg FIRST ---
# The original paved bug was running pip before the compiler/swig existed, so
# pocketsphinx's wheel build failed. Order matters: native deps, THEN pip.
#   build-essential + swig  -> pocketsphinx
#   cmake                   -> pywhispercpp
#   ffmpeg                  -> audio/video processing + decode-verify
RUN apt-get update && apt-get install --yes --no-install-recommends \
        build-essential \
        swig \
        cmake \
        ffmpeg \
        wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install engine deps (now that the toolchain exists).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install the paved package itself.
COPY pyproject.toml Readme.md ./
COPY src ./src
RUN pip install --no-cache-dir .

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Inside the container, localhost->host Ollama is reachable via this hostname.
ENV OLLAMA_HOST=http://host.docker.internal:11434

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["--help"]
