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
