# SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request

from paved.llm._base import LLMProvider, LLMResult, PROMPTS


class OllamaProvider(LLMProvider):
    name = "ollama"
    default_model = os.environ.get("PAVED_LLM_MODEL", "llama3.2:3b")

    def __init__(self) -> None:
        self._host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    def is_available(self, timeout: float = 3.0) -> bool:
        try:
            with urllib.request.urlopen(f"{self._host}/api/tags", timeout=timeout) as r:
                return r.status == 200
        except Exception:
            return False

    def process(
        self, text: str, mode: str, model: str | None = None, timeout: float = 600.0
    ) -> LLMResult:
        if mode == "off":
            return LLMResult(mode=mode, ok=True, text=text)
        if mode not in PROMPTS:
            return self._fail(mode, text, f"unknown llm mode '{mode}'")
        if not self.is_available():
            return self._fail(
                mode, text,
                f"Ollama not reachable at {self._host}; returning raw transcript. "
                "Install/start Ollama and pull a model to enable this step.",
            )
        m = model or self.default_model
        prompt = PROMPTS[mode].format(text=text)
        payload = json.dumps({"model": m, "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request(
            f"{self._host}/api/generate", data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode())
            out = (data.get("response") or "").strip()
            if not out:
                return self._fail(mode, text, "Ollama returned an empty response")
            return self._ok(mode, out)
        except urllib.error.HTTPError as e:
            return self._fail(mode, text, f"Ollama HTTP error {e.code} (model '{m}' missing?)")
        except Exception as e:
            return self._fail(mode, text, f"Ollama call failed: {e}")


class AnthropicProvider(LLMProvider):
    name = "anthropic"
    default_model = "claude-sonnet-4-6"
    _endpoint = "https://api.anthropic.com/v1/messages"

    def _api_key(self) -> str | None:
        return os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("PAVED_LLM_API_KEY")

    def is_available(self) -> bool:
        return bool(self._api_key())

    def process(
        self, text: str, mode: str, model: str | None = None, timeout: float = 600.0
    ) -> LLMResult:
        if mode == "off":
            return LLMResult(mode=mode, ok=True, text=text)
        if mode not in PROMPTS:
            return self._fail(mode, text, f"unknown llm mode '{mode}'")
        key = self._api_key()
        if not key:
            return self._fail(mode, text,
                "Anthropic API key not set (ANTHROPIC_API_KEY or PAVED_LLM_API_KEY)")
        m = model or self.default_model
        payload = json.dumps({
            "model": m,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": PROMPTS[mode].format(text=text)}],
        }).encode()
        req = urllib.request.Request(
            self._endpoint, data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode())
            out = (data.get("content", [{}])[0].get("text") or "").strip()
            if not out:
                return self._fail(mode, text, "Anthropic returned an empty response")
            return self._ok(mode, out)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            return self._fail(mode, text, f"Anthropic HTTP error {e.code}: {body[:200]}")
        except Exception as e:
            return self._fail(mode, text, f"Anthropic call failed: {e}")


class ClaudeCLIProvider(LLMProvider):
    name = "claude-cli"

    def is_available(self) -> bool:
        return shutil.which("claude") is not None

    def process(
        self, text: str, mode: str, model: str | None = None, timeout: float = 600.0
    ) -> LLMResult:
        if mode == "off":
            return LLMResult(mode=mode, ok=True, text=text)
        if mode not in PROMPTS:
            return self._fail(mode, text, f"unknown llm mode '{mode}'")
        if not self.is_available():
            return self._fail(mode, text,
                "claude CLI not found on PATH; install Claude Code and authenticate")
        prompt = PROMPTS[mode].format(text=text)
        cmd = ["claude", "-p", prompt]
        if model:
            cmd += ["--model", model]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode != 0:
                return self._fail(mode, text,
                    f"claude CLI exited {result.returncode}: {result.stderr[:200]}")
            out = result.stdout.strip()
            if not out:
                return self._fail(mode, text, "claude CLI returned empty output")
            return self._ok(mode, out)
        except subprocess.TimeoutExpired:
            return self._fail(mode, text, f"claude CLI timed out after {timeout}s")
        except Exception as e:
            return self._fail(mode, text, f"claude CLI call failed: {e}")


class GeminiProvider(LLMProvider):
    name = "google"
    default_model = "gemini-2.0-flash"

    def _api_key(self) -> str | None:
        return os.environ.get("GOOGLE_API_KEY") or os.environ.get("PAVED_LLM_API_KEY")

    def is_available(self) -> bool:
        return bool(self._api_key())

    def process(
        self, text: str, mode: str, model: str | None = None, timeout: float = 600.0
    ) -> LLMResult:
        if mode == "off":
            return LLMResult(mode=mode, ok=True, text=text)
        if mode not in PROMPTS:
            return self._fail(mode, text, f"unknown llm mode '{mode}'")
        key = self._api_key()
        if not key:
            return self._fail(mode, text,
                "Google API key not set (GOOGLE_API_KEY or PAVED_LLM_API_KEY)")
        m = model or self.default_model
        url = (
            f"https://generativelanguage.googleapis.com/v1beta"
            f"/models/{m}:generateContent?key={key}"
        )
        payload = json.dumps({
            "contents": [{"parts": [{"text": PROMPTS[mode].format(text=text)}]}]
        }).encode()
        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode())
            out = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text") or ""
            ).strip()
            if not out:
                return self._fail(mode, text, "Gemini returned an empty response")
            return self._ok(mode, out)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            return self._fail(mode, text, f"Gemini HTTP error {e.code}: {body[:200]}")
        except Exception as e:
            return self._fail(mode, text, f"Gemini call failed: {e}")


class OpenAICompatProvider(LLMProvider):
    name = "openai-compat"
    default_model: str = ""
    _base_url: str = ""
    _key_env: str = "PAVED_LLM_API_KEY"

    def _api_key(self) -> str | None:
        return os.environ.get(self._key_env) or os.environ.get("PAVED_LLM_API_KEY")

    def _endpoint(self) -> str:
        base = self._base_url or os.environ.get("PAVED_LLM_BASE_URL", "")
        return (base.rstrip("/") + "/chat/completions") if base else ""

    def is_available(self) -> bool:
        return bool(self._api_key() and self._endpoint())

    def process(
        self, text: str, mode: str, model: str | None = None, timeout: float = 600.0
    ) -> LLMResult:
        if mode == "off":
            return LLMResult(mode=mode, ok=True, text=text)
        if mode not in PROMPTS:
            return self._fail(mode, text, f"unknown llm mode '{mode}'")
        key = self._api_key()
        endpoint = self._endpoint()
        if not key:
            return self._fail(mode, text,
                f"{self._key_env} or PAVED_LLM_API_KEY not set")
        if not endpoint:
            return self._fail(mode, text, "PAVED_LLM_BASE_URL not set")
        m = model or self.default_model or os.environ.get("PAVED_LLM_MODEL", "")
        if not m:
            return self._fail(mode, text,
                "PAVED_LLM_MODEL not set (required for openai-compat provider)")
        payload = json.dumps({
            "model": m,
            "messages": [{"role": "user", "content": PROMPTS[mode].format(text=text)}],
        }).encode()
        req = urllib.request.Request(
            endpoint, data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode())
            out = (
                data.get("choices", [{}])[0].get("message", {}).get("content") or ""
            ).strip()
            if not out:
                return self._fail(mode, text, f"{self.name} returned an empty response")
            return self._ok(mode, out)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            return self._fail(mode, text, f"{self.name} HTTP error {e.code}: {body[:200]}")
        except Exception as e:
            return self._fail(mode, text, f"{self.name} call failed: {e}")


class OpenAIProvider(OpenAICompatProvider):
    name = "openai"
    default_model = "gpt-4o-mini"
    _base_url = "https://api.openai.com/v1"
    _key_env = "OPENAI_API_KEY"


class DeepSeekProvider(OpenAICompatProvider):
    name = "deepseek"
    default_model = "deepseek-chat"
    _base_url = "https://api.deepseek.com/v1"
    _key_env = "DEEPSEEK_API_KEY"


class QwenProvider(OpenAICompatProvider):
    name = "qwen"
    default_model = "qwen-plus"
    _base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    _key_env = "QWEN_API_KEY"
