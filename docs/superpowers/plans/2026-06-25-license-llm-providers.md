# License + Multi-Provider LLM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the MIT stub + Ollama-only LLM step with AGPL-3.0 licensing and 8-provider LLM support (Ollama, Anthropic API, claude-cli, Google Gemini, OpenAI, DeepSeek, Qwen, generic OpenAI-compat).

**Architecture:** The current `llm/ollama.py` monolith is replaced by three focused modules: `_base.py` (types + prompts), `_providers.py` (all provider classes), `__init__.py` (router). The CLI gains `--llm-provider` and `--llm-model` flags. All HTTP uses stdlib `urllib`; `claude-cli` uses `subprocess`. Zero new runtime deps.

**Tech Stack:** Python 3.10+, stdlib only (`urllib`, `subprocess`, `dataclasses`, `abc`), `unittest.mock` for tests.

## Global Constraints

- Python >= 3.10 (uses `str | None` union syntax)
- Zero new runtime dependencies — all HTTP via `urllib`, subprocess via stdlib
- Fail-soft contract: every provider failure returns `LLMResult(ok=False, text=<original>, warning=<reason>)`
- `PAVED_LLM_PROVIDER` env var is the default; `--llm-provider` CLI flag overrides it
- All new `.py` source files get `# SPDX-License-Identifier: AGPL-3.0-only` as first line
- Tests do NOT get SPDX headers
- `ollama.py` is deleted at end of Task 6 — do not import from it in any new code

---

### Task 1: LICENSE + pyproject.toml

**Files:**
- Create: `LICENSE`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: nothing consumed by code — metadata only

- [ ] **Step 1: Fetch canonical AGPL-3.0 text**

```bash
curl -fsSL https://www.gnu.org/licenses/agpl-3.0.txt -o /opt/proj/paved/LICENSE
```

Verify first line reads `                    GNU AFFERO GENERAL PUBLIC LICENSE`.

- [ ] **Step 2: Update pyproject.toml license fields**

In `pyproject.toml`, replace:
```toml
license = { text = "MIT" }
```
with:
```toml
license = { text = "AGPL-3.0-only" }
license-files = ["LICENSE"]
```

- [ ] **Step 3: Verify pyproject.toml parses**

```bash
cd /opt/proj/paved && python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))" && echo OK
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add LICENSE pyproject.toml
git commit -m "license: switch to AGPL-3.0-only"
```

---

### Task 2: LLM base types

**Files:**
- Create: `src/paved/llm/_base.py`
- Create: `tests/test_llm_base.py`

**Interfaces:**
- Produces:
  - `LLMResult` — `@dataclass(mode: str, ok: bool, text: str, warning: str = "")`
  - `PROMPTS` — `dict[str, str]` with keys `"clean"` and `"summary"`, each a `str` with `{text}` placeholder
  - `LLMProvider` — ABC with `name: str`, `is_available() -> bool`, `process(text, mode, model, timeout) -> LLMResult`, helpers `_ok()` and `_fail()`

- [ ] **Step 1: Write the failing test**

Create `tests/test_llm_base.py`:
```python
from paved.llm._base import LLMResult, PROMPTS, LLMProvider


def test_llm_result_defaults():
    r = LLMResult(mode="clean", ok=True, text="hello")
    assert r.warning == ""


def test_prompts_has_clean_and_summary():
    assert "clean" in PROMPTS
    assert "summary" in PROMPTS
    assert "{text}" in PROMPTS["clean"]
    assert "{text}" in PROMPTS["summary"]


def test_provider_helpers():
    class DummyProvider(LLMProvider):
        name = "dummy"
        def is_available(self): return True
        def process(self, text, mode, model=None, timeout=600.0):
            return self._ok(mode, text)

    p = DummyProvider()
    r = p._ok("clean", "out")
    assert r.ok is True and r.text == "out"
    r2 = p._fail("clean", "orig", "oops")
    assert r2.ok is False and r2.text == "orig" and r2.warning == "oops"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /opt/proj/paved && python -m pytest tests/test_llm_base.py -v 2>&1 | tail -5
```
Expected: `ModuleNotFoundError: No module named 'paved.llm._base'`

- [ ] **Step 3: Write minimal implementation**

Create `src/paved/llm/_base.py`:
```python
# SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResult:
    mode: str
    ok: bool
    text: str
    warning: str = ""


PROMPTS: dict[str, str] = {
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


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def process(
        self,
        text: str,
        mode: str,
        model: str | None = None,
        timeout: float = 600.0,
    ) -> LLMResult: ...

    def _ok(self, mode: str, text: str) -> LLMResult:
        return LLMResult(mode=mode, ok=True, text=text)

    def _fail(self, mode: str, text: str, warning: str) -> LLMResult:
        return LLMResult(mode=mode, ok=False, text=text, warning=warning)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /opt/proj/paved && python -m pytest tests/test_llm_base.py -v 2>&1 | tail -5
```
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/paved/llm/_base.py tests/test_llm_base.py
git commit -m "feat(llm): add LLMResult, PROMPTS, LLMProvider base"
```

---

### Task 3: Provider implementations

**Files:**
- Create: `src/paved/llm/_providers.py`
- Create: `tests/test_llm_providers.py`

**Interfaces:**
- Consumes: `LLMProvider`, `LLMResult`, `PROMPTS` from `paved.llm._base`
- Produces (all from `paved.llm._providers`):
  - `OllamaProvider` — HTTP to `OLLAMA_HOST`
  - `AnthropicProvider` — HTTPS to `api.anthropic.com`, key from `ANTHROPIC_API_KEY` or `PAVED_LLM_API_KEY`
  - `ClaudeCLIProvider` — subprocess `claude -p`
  - `GeminiProvider` — HTTPS to `generativelanguage.googleapis.com`, key from `GOOGLE_API_KEY` or `PAVED_LLM_API_KEY`
  - `OpenAICompatProvider` — HTTPS, base URL from `_base_url` class attr or `PAVED_LLM_BASE_URL`
  - `OpenAIProvider(OpenAICompatProvider)` — `api.openai.com`, key from `OPENAI_API_KEY`
  - `DeepSeekProvider(OpenAICompatProvider)` — `api.deepseek.com`, key from `DEEPSEEK_API_KEY`
  - `QwenProvider(OpenAICompatProvider)` — `dashscope.aliyuncs.com`, key from `QWEN_API_KEY`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_llm_providers.py`:
```python
import json
import os
from unittest.mock import MagicMock, patch

import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def _mock_urlopen(response_body: bytes, status: int = 200):
    """Return a context-manager mock for urllib.request.urlopen."""
    cm = MagicMock()
    cm.__enter__ = lambda s: s
    cm.__exit__ = MagicMock(return_value=False)
    cm.status = status
    cm.read.return_value = response_body
    return cm


# ── OllamaProvider ────────────────────────────────────────────────────────────

def test_ollama_fail_soft_when_unreachable():
    from paved.llm._providers import OllamaProvider
    p = OllamaProvider()
    with patch("urllib.request.urlopen", side_effect=OSError("refused")):
        r = p.process("hello", "clean")
    assert r.ok is False
    assert r.text == "hello"
    assert "Ollama" in r.warning


def test_ollama_process_success():
    from paved.llm._providers import OllamaProvider
    p = OllamaProvider()
    tags_cm = _mock_urlopen(b"{}")
    gen_cm = _mock_urlopen(json.dumps({"response": "cleaned"}).encode())

    call_count = 0
    def fake_urlopen(req, timeout=None):
        nonlocal call_count
        call_count += 1
        url = req.full_url if hasattr(req, "full_url") else str(req)
        return tags_cm if "tags" in url else gen_cm

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        r = p.process("raw", "clean")
    assert r.ok is True
    assert r.text == "cleaned"


def test_ollama_off_mode():
    from paved.llm._providers import OllamaProvider
    p = OllamaProvider()
    r = p.process("hello", "off")
    assert r.ok is True and r.text == "hello"


# ── AnthropicProvider ─────────────────────────────────────────────────────────

def test_anthropic_no_key_fail_soft():
    from paved.llm._providers import AnthropicProvider
    p = AnthropicProvider()
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        os.environ.pop("PAVED_LLM_API_KEY", None)
        r = p.process("hello", "clean")
    assert r.ok is False
    assert "API key" in r.warning


def test_anthropic_process_success():
    from paved.llm._providers import AnthropicProvider
    p = AnthropicProvider()
    body = json.dumps({"content": [{"text": "cleaned"}]}).encode()
    cm = _mock_urlopen(body)
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
        with patch("urllib.request.urlopen", return_value=cm):
            r = p.process("raw", "clean")
    assert r.ok is True
    assert r.text == "cleaned"


# ── ClaudeCLIProvider ─────────────────────────────────────────────────────────

def test_claude_cli_not_on_path_fail_soft():
    from paved.llm._providers import ClaudeCLIProvider
    p = ClaudeCLIProvider()
    with patch("shutil.which", return_value=None):
        r = p.process("hello", "clean")
    assert r.ok is False
    assert "claude CLI" in r.warning


def test_claude_cli_success():
    from paved.llm._providers import ClaudeCLIProvider
    import subprocess
    p = ClaudeCLIProvider()
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "cleaned output\n"
    with patch("shutil.which", return_value="/usr/bin/claude"):
        with patch("subprocess.run", return_value=mock_result):
            r = p.process("raw text", "clean")
    assert r.ok is True
    assert r.text == "cleaned output"


def test_claude_cli_nonzero_exit_fail_soft():
    from paved.llm._providers import ClaudeCLIProvider
    p = ClaudeCLIProvider()
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "auth error"
    with patch("shutil.which", return_value="/usr/bin/claude"):
        with patch("subprocess.run", return_value=mock_result):
            r = p.process("raw text", "clean")
    assert r.ok is False
    assert "1" in r.warning


# ── GeminiProvider ────────────────────────────────────────────────────────────

def test_gemini_no_key_fail_soft():
    from paved.llm._providers import GeminiProvider
    p = GeminiProvider()
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("GOOGLE_API_KEY", None)
        os.environ.pop("PAVED_LLM_API_KEY", None)
        r = p.process("hello", "clean")
    assert r.ok is False
    assert "API key" in r.warning


def test_gemini_process_success():
    from paved.llm._providers import GeminiProvider
    p = GeminiProvider()
    body = json.dumps({
        "candidates": [{"content": {"parts": [{"text": "cleaned"}]}}]
    }).encode()
    cm = _mock_urlopen(body)
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "gkey"}):
        with patch("urllib.request.urlopen", return_value=cm):
            r = p.process("raw", "clean")
    assert r.ok is True
    assert r.text == "cleaned"


# ── OpenAICompatProvider + presets ────────────────────────────────────────────

def test_openai_compat_no_base_url_fail_soft():
    from paved.llm._providers import OpenAICompatProvider
    p = OpenAICompatProvider()
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("PAVED_LLM_BASE_URL", None)
        os.environ.pop("PAVED_LLM_API_KEY", None)
        r = p.process("hello", "clean")
    assert r.ok is False


def test_deepseek_uses_correct_base_url():
    from paved.llm._providers import DeepSeekProvider
    p = DeepSeekProvider()
    assert "deepseek.com" in p._base_url


def test_qwen_uses_correct_base_url():
    from paved.llm._providers import QwenProvider
    p = QwenProvider()
    assert "dashscope" in p._base_url


def test_openai_process_success():
    from paved.llm._providers import OpenAIProvider
    p = OpenAIProvider()
    body = json.dumps({
        "choices": [{"message": {"content": "cleaned"}}]
    }).encode()
    cm = _mock_urlopen(body)
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        with patch("urllib.request.urlopen", return_value=cm):
            r = p.process("raw", "clean")
    assert r.ok is True
    assert r.text == "cleaned"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /opt/proj/paved && python -m pytest tests/test_llm_providers.py -v 2>&1 | tail -5
```
Expected: `ModuleNotFoundError: No module named 'paved.llm._providers'`

- [ ] **Step 3: Write implementation**

Create `src/paved/llm/_providers.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /opt/proj/paved && python -m pytest tests/test_llm_providers.py -v 2>&1 | tail -10
```
Expected: `15 passed`

- [ ] **Step 5: Commit**

```bash
git add src/paved/llm/_providers.py tests/test_llm_providers.py
git commit -m "feat(llm): add 8-provider implementation (Ollama, Anthropic, claude-cli, Gemini, OpenAI, DeepSeek, Qwen, openai-compat)"
```

---

### Task 4: Router (`__init__.py`)

**Files:**
- Modify: `src/paved/llm/__init__.py`
- Create: `tests/test_llm_router.py`

**Interfaces:**
- Consumes: all provider classes from `paved.llm._providers`; `LLMResult` from `paved.llm._base`
- Produces:
  - `process(text: str, mode: str, provider: str | None = None, model: str | None = None, timeout: float = 600.0) -> LLMResult`
  - `PROVIDER_NAMES: list[str]` — `["ollama", "anthropic", "claude-cli", "google", "openai", "deepseek", "qwen", "openai-compat"]`
  - `LLMResult` — re-exported for CLI import convenience

- [ ] **Step 1: Write the failing tests**

Create `tests/test_llm_router.py`:
```python
import os
from unittest.mock import patch, MagicMock


def test_provider_names_list():
    from paved.llm import PROVIDER_NAMES
    assert "ollama" in PROVIDER_NAMES
    assert "anthropic" in PROVIDER_NAMES
    assert "claude-cli" in PROVIDER_NAMES
    assert "google" in PROVIDER_NAMES
    assert "openai" in PROVIDER_NAMES
    assert "deepseek" in PROVIDER_NAMES
    assert "qwen" in PROVIDER_NAMES
    assert "openai-compat" in PROVIDER_NAMES


def test_unknown_provider_fail_soft():
    from paved.llm import process
    r = process("hello", "clean", provider="nonexistent")
    assert r.ok is False
    assert "unknown provider" in r.warning


def test_off_mode_returns_original_without_calling_provider():
    from paved.llm import process
    r = process("hello", "off", provider="ollama")
    assert r.ok is True
    assert r.text == "hello"


def test_env_var_selects_provider():
    from paved.llm import process
    with patch.dict(os.environ, {"PAVED_LLM_PROVIDER": "anthropic"}):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            os.environ.pop("PAVED_LLM_API_KEY", None)
            r = process("hello", "clean")
    assert r.ok is False
    assert "API key" in r.warning  # anthropic provider was selected


def test_cli_flag_overrides_env_var():
    from paved.llm import process
    with patch.dict(os.environ, {"PAVED_LLM_PROVIDER": "google"}):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            os.environ.pop("PAVED_LLM_API_KEY", None)
            # passing provider="anthropic" explicitly overrides env
            r = process("hello", "clean", provider="anthropic")
    assert "API key" in r.warning  # anthropic, not google
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /opt/proj/paved && python -m pytest tests/test_llm_router.py -v 2>&1 | tail -5
```
Expected: `ImportError` or `cannot import name 'PROVIDER_NAMES'`

- [ ] **Step 3: Write implementation**

Replace `src/paved/llm/__init__.py` entirely:
```python
# SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations
import os

from paved.llm._base import LLMResult, PROMPTS  # noqa: F401 — re-exported
from paved.llm._providers import (
    AnthropicProvider,
    ClaudeCLIProvider,
    DeepSeekProvider,
    GeminiProvider,
    OllamaProvider,
    OpenAICompatProvider,
    OpenAIProvider,
    QwenProvider,
)

_PROVIDERS = {
    "ollama": OllamaProvider,
    "anthropic": AnthropicProvider,
    "claude-cli": ClaudeCLIProvider,
    "google": GeminiProvider,
    "openai": OpenAIProvider,
    "deepseek": DeepSeekProvider,
    "qwen": QwenProvider,
    "openai-compat": OpenAICompatProvider,
}

PROVIDER_NAMES: list[str] = list(_PROVIDERS.keys())


def process(
    text: str,
    mode: str,
    provider: str | None = None,
    model: str | None = None,
    timeout: float = 600.0,
) -> LLMResult:
    p_name = provider or os.environ.get("PAVED_LLM_PROVIDER", "ollama")
    if p_name not in _PROVIDERS:
        return LLMResult(mode=mode, ok=False, text=text,
                         warning=f"unknown provider '{p_name}'")
    return _PROVIDERS[p_name]().process(text, mode=mode, model=model, timeout=timeout)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /opt/proj/paved && python -m pytest tests/test_llm_router.py -v 2>&1 | tail -5
```
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add src/paved/llm/__init__.py tests/test_llm_router.py
git commit -m "feat(llm): router in __init__ — PROVIDER_NAMES + process() dispatch"
```

---

### Task 5: CLI integration

**Files:**
- Modify: `src/paved/cli.py`
- Modify: `tests/test_cli.py`

**Interfaces:**
- Consumes: `process`, `PROVIDER_NAMES`, `LLMResult` from `paved.llm`
- Produces: `--llm-provider` and `--llm-model` flags on `paved transcribe`

- [ ] **Step 1: Write the failing tests**

In `tests/test_cli.py`, add after the existing `test_transcribe_llm_choices`:
```python
def test_transcribe_llm_provider_choices():
    from paved.cli import build_parser
    from paved.llm import PROVIDER_NAMES
    p = build_parser()
    # verify all provider names are valid choices
    for name in PROVIDER_NAMES:
        args = p.parse_args(["transcribe", "foo.mp4", "--llm-provider", name])
        assert args.llm_provider == name


def test_transcribe_llm_provider_default_is_none():
    from paved.cli import build_parser
    p = build_parser()
    args = p.parse_args(["transcribe", "foo.mp4"])
    assert args.llm_provider is None  # router falls back to env/ollama


def test_transcribe_llm_model_flag():
    from paved.cli import build_parser
    p = build_parser()
    args = p.parse_args(["transcribe", "foo.mp4", "--llm-model", "gpt-4o"])
    assert args.llm_model == "gpt-4o"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /opt/proj/paved && python -m pytest tests/test_cli.py -v 2>&1 | tail -8
```
Expected: failures on the three new tests (attribute error on `llm_provider`/`llm_model`)

- [ ] **Step 3: Update `build_parser` in `src/paved/cli.py`**

In `build_parser`, find the `pt` (transcribe subparser) block and add two arguments after the existing `--llm` line:

```python
    # existing:
    pt.add_argument("--llm", choices=["off", "clean", "summary"], default="off",
                    help="optional LLM post-step (default: off)")
    # add these two:
    pt.add_argument("--llm-provider", dest="llm_provider",
                    choices=PROVIDER_NAMES, default=None,
                    help="LLM provider (default: PAVED_LLM_PROVIDER env var, or 'ollama')")
    pt.add_argument("--llm-model", dest="llm_model", default=None,
                    help="model override for chosen LLM provider")
```

Also add the import at the top of the `build_parser` function (lazy import pattern already used in the file) or at module level. Since `cli.py` uses lazy imports inside functions, add at top of `build_parser`:

```python
def build_parser() -> argparse.ArgumentParser:
    from paved.llm import PROVIDER_NAMES
    ...
```

- [ ] **Step 4: Update `cmd_transcribe` in `src/paved/cli.py`**

Replace:
```python
def cmd_transcribe(args) -> int:
    from paved import transcribe as tr
    from paved.llm import ollama
    ...
        if args.llm != "off":
            r = ollama.process(text, mode=args.llm)
```

With:
```python
def cmd_transcribe(args) -> int:
    from paved import transcribe as tr
    from paved.llm import process as llm_process
    ...
        if args.llm != "off":
            r = llm_process(
                text,
                mode=args.llm,
                provider=args.llm_provider,
                model=args.llm_model,
            )
```

Keep everything else in `cmd_transcribe` identical.

- [ ] **Step 5: Run all tests**

```bash
cd /opt/proj/paved && python -m pytest tests/ -v 2>&1 | tail -15
```
Expected: all tests pass (21 original + new tests)

- [ ] **Step 6: Commit**

```bash
git add src/paved/cli.py tests/test_cli.py
git commit -m "feat(cli): add --llm-provider and --llm-model flags to transcribe"
```

---

### Task 6: Cleanup + SPDX headers

**Files:**
- Delete: `src/paved/llm/ollama.py`
- Modify: all non-stub, non-test `.py` source files (add SPDX header)

**Interfaces:**
- Consumes: nothing new
- Produces: clean repo with no dead code and consistent licensing

- [ ] **Step 1: Delete `ollama.py`**

```bash
git rm src/paved/llm/ollama.py
```

- [ ] **Step 2: Verify no remaining imports of `paved.llm.ollama`**

```bash
cd /opt/proj/paved && grep -r "from paved.llm import ollama\|paved\.llm\.ollama" src/ tests/ && echo "FOUND — fix before continuing" || echo "clean"
```
Expected: `clean`

- [ ] **Step 3: Add SPDX header to source files**

For each file listed below, insert `# SPDX-License-Identifier: AGPL-3.0-only` as the **first line** (before any existing content including `from __future__` imports):

Files to update:
- `src/paved/cli.py`
- `src/paved/ffmpeg.py`
- `src/paved/mp4box.py`
- `src/paved/probe.py`
- `src/paved/report.py`
- `src/paved/repair/__init__.py`
- `src/paved/repair/strategies.py`
- `src/paved/transcribe/__init__.py`
- `src/paved/transcribe/base.py`
- `src/paved/transcribe/engines.py`
- `src/paved/llm/ollama.py` — SKIP (deleted in Step 1)

New files already have the header from their creation tasks:
- `src/paved/llm/_base.py` ✓
- `src/paved/llm/_providers.py` ✓
- `src/paved/llm/__init__.py` ✓

Do NOT add headers to:
- `src/paved/__init__.py` (empty stub)
- `src/paved/__main__.py` (empty stub)
- `src/paved/llm/__init__.py` was already updated in Task 4
- Any file under `tests/`

- [ ] **Step 4: Run full test suite**

```bash
cd /opt/proj/paved && python -m pytest tests/ -v 2>&1 | tail -10
```
Expected: all tests pass

- [ ] **Step 5: Smoke-test the CLI help**

```bash
cd /opt/proj/paved && python -m paved transcribe --help | grep -E "llm-provider|llm-model"
```
Expected: both flags appear in help output

- [ ] **Step 6: Reindex jcodemunch**

```bash
cd /opt/proj/Uncle-J-s-Refinery && bash scripts/jcodemunch-reindex.sh 2>&1 | tail -3
```

- [ ] **Step 7: Final commit**

```bash
git add -u
git commit -m "chore: delete ollama.py (migrated), add SPDX headers to all source files"
```
