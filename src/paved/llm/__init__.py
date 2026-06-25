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
    """Route LLM processing to the specified provider.

    Args:
        text: Input text to process
        mode: Processing mode (e.g., "clean", "summary", "off")
        provider: Provider name (defaults to PAVED_LLM_PROVIDER env var, then "ollama")
        model: Model override (provider-specific)
        timeout: Request timeout in seconds

    Returns:
        LLMResult with processed text or original text on error
    """
    p_name = provider or os.environ.get("PAVED_LLM_PROVIDER", "ollama")
    if p_name not in _PROVIDERS:
        return LLMResult(
            mode=mode, ok=False, text=text,
            warning=f"unknown provider '{p_name}'",
        )
    return _PROVIDERS[p_name]().process(text, mode=mode, model=model, timeout=timeout)
