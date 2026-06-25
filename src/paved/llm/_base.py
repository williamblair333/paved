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
