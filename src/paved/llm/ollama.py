"""Optional transcript post-processing via a local Ollama server.

Fully optional and fail-soft: if Ollama is unreachable, post-processing returns
the original text plus a warning. It NEVER raises into the transcribe pipeline,
so a missing/down Ollama can't fail an otherwise-successful transcription.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("PAVED_LLM_MODEL", "llama3.2:3b")

_PROMPTS = {
    "clean": (
        "You are a transcript editor. Fix punctuation, capitalization, and obvious "
        "transcription errors in the text below. Do NOT add, remove, or summarize "
        "content. Return only the corrected transcript.\n\n{text}"
    ),
    "summary": (
        "Summarize the following transcript in a few concise bullet points. "
        "Return only the summary.\n\n{text}"
    ),
}


@dataclass
class LLMResult:
    mode: str
    ok: bool
    text: str          # processed text, or original on failure
    warning: str = ""


def is_available(host: str = DEFAULT_HOST, timeout: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def process(
    text: str,
    mode: str,
    model: str = DEFAULT_MODEL,
    host: str = DEFAULT_HOST,
    timeout: float = 600.0,
) -> LLMResult:
    """Run a clean/summary pass. Returns original text + warning on any failure."""
    if mode == "off":
        return LLMResult(mode=mode, ok=True, text=text)
    if mode not in _PROMPTS:
        return LLMResult(mode=mode, ok=False, text=text,
                         warning=f"unknown llm mode '{mode}'")
    if not is_available(host):
        return LLMResult(
            mode=mode, ok=False, text=text,
            warning=(f"Ollama not reachable at {host}; returning raw transcript. "
                     "Install/start Ollama and pull a model to enable this step."),
        )
    prompt = _PROMPTS[mode].format(text=text)
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        f"{host}/api/generate", data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        out = (data.get("response") or "").strip()
        if not out:
            return LLMResult(mode=mode, ok=False, text=text,
                             warning="Ollama returned an empty response")
        return LLMResult(mode=mode, ok=True, text=out)
    except urllib.error.HTTPError as e:
        return LLMResult(mode=mode, ok=False, text=text,
                         warning=f"Ollama HTTP error {e.code} (model '{model}' missing?)")
    except Exception as e:
        return LLMResult(mode=mode, ok=False, text=text,
                         warning=f"Ollama call failed: {e}")
