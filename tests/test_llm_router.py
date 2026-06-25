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
