# PAVED: AGPL-3 License + Multi-Provider LLM Design

**Date:** 2026-06-25  
**Status:** Approved  
**Scope:** License correction + LLM post-processing provider expansion

---

## 1. License

### Changes

- Create `LICENSE` with full AGPL-3.0-only text
- Update `pyproject.toml`: `license = { text = "AGPL-3.0-only" }` + `license-files = ["LICENSE"]`
- Add `# SPDX-License-Identifier: AGPL-3.0-only` as first line of every `.py` source file (excluding `__init__.py` stubs and test files)

### Dependency Audit

| Dependency | License | AGPL-3 Compatible |
|---|---|---|
| faster-whisper | MIT | ✓ |
| pywhispercpp | MIT | ✓ |
| vosk | Apache-2.0 | ✓ |
| pocketsphinx | BSD-2-Clause | ✓ |
| imageio-ffmpeg | BSD-2-Clause (bundles GPL-2+ FFmpeg binary) | ✓ |
| pytest (dev) | MIT | ✓ |

No conflicts. AGPL-3 is the strongest copyleft present and absorbs all dependencies cleanly.

---

## 2. LLM Multi-Provider

### Motivation

The current LLM post-processing step is hardcoded to Ollama. Users should be able
to substitute any capable LLM — local (Ollama) or remote (Anthropic, Google, OpenAI,
Chinese providers) — without code changes.

### File Structure

Current:
```
src/paved/llm/
    __init__.py    (empty)
    ollama.py      (LLMResult, process(), is_available())
```

After:
```
src/paved/llm/
    __init__.py    (exports: process(), LLMResult)
    _base.py       (LLMResult dataclass, PROMPTS dict, LLMProvider ABC)
    _providers.py  (all provider implementations)
```

`ollama.py` is deleted — logic migrates to `_providers.py`.

### Providers

| Provider name | Transport | Auth | Default model |
|---|---|---|---|
| `ollama` | HTTP (stdlib) | none — `OLLAMA_HOST` | `llama3.2:3b` |
| `anthropic` | HTTPS (stdlib) | `ANTHROPIC_API_KEY` or `PAVED_LLM_API_KEY` | `claude-sonnet-4-6` |
| `claude-cli` | subprocess | OAuth session (no key needed) | CLI default |
| `google` | HTTPS (stdlib) | `GOOGLE_API_KEY` or `PAVED_LLM_API_KEY` | `gemini-2.0-flash` |
| `openai` | HTTPS (stdlib) | `OPENAI_API_KEY` or `PAVED_LLM_API_KEY` | `gpt-4o-mini` |
| `deepseek` | HTTPS (stdlib) | `DEEPSEEK_API_KEY` or `PAVED_LLM_API_KEY` | `deepseek-chat` |
| `qwen` | HTTPS (stdlib) | `QWEN_API_KEY` or `PAVED_LLM_API_KEY` | `qwen-plus` |
| `openai-compat` | HTTPS (stdlib) | `PAVED_LLM_API_KEY` + `PAVED_LLM_BASE_URL` | (user must set `PAVED_LLM_MODEL`) |

`deepseek` and `qwen` are preset subclasses of the OpenAI-compat provider with hardcoded
base URLs (`api.deepseek.com` and `dashscope.aliyuncs.com/compatible-mode/v1` respectively).
`openai-compat` is the escape hatch for any other provider.

### Provider Selection

```
--llm-provider <name>      CLI flag — highest priority
PAVED_LLM_PROVIDER=<name>  env var — fallback
(neither)                  default: ollama
```

### Model Override

```
--llm-model <name>    CLI flag
PAVED_LLM_MODEL=<name>  env var (already exists for Ollama, extended to all providers)
```

### API Key Resolution

For all non-Ollama, non-claude-cli providers, key lookup order:
1. Provider-specific env var (`ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `QWEN_API_KEY`)
2. `PAVED_LLM_API_KEY` (generic fallback)

### `claude-cli` Provider

Calls `claude -p "<prompt>"` as a subprocess. Requires Claude Code to be installed and
authenticated on the host. Fails soft if `claude` is not on PATH. Not suitable for Docker
deployments unless Claude Code is installed in the image.

### Fail-Soft Contract

Unchanged from v1.0.0: any provider failure (network error, bad key, subprocess missing,
empty response) returns the original transcript text plus a human-readable warning string.
The pipeline never crashes due to an LLM step failure.

### CLI Changes

`paved transcribe` gains two new optional flags:
- `--llm-provider` / `-P` — provider name (default: `ollama`)
- `--llm-model` — model override (already exists, no change to semantics)

### No New Runtime Dependencies

All HTTP calls use `urllib` (stdlib). `claude-cli` uses `subprocess` (stdlib).
Zero new entries in `pyproject.toml` `dependencies` or optional extras.

### Testing

- Existing `test_transcribe_llm_choices` extended to cover new provider names
- Each provider's `is_available()` tested with mocked env/subprocess
- Fail-soft path tested for at least one provider (network error → original text returned)
