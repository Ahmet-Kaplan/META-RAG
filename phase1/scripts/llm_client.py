#!/usr/bin/env python3
"""
llm_client.py — OpenAI-compatible LLM client with provider selection.

Providers are resolved per call so one process can compare models (E3):

  deepseek   (default) DEEPSEEK_API_KEY   api.deepseek.com
  gemini               GEMINI_API_KEY     generativelanguage.googleapis.com/v1beta/openai/
  openai_compatible    LLM_API_KEY        LLM_BASE_URL (local vLLM/Ollama, any
                                          OpenAI-compatible server)

Key resolution order (per provider):
  1. the provider's key environment variable
  2. phase1/.env  (chmod 600; never commit)

Model resolution: explicit `model=` argument > provider's *_MODEL env var >
provider default.

Backward compatibility: existing call sites pass no provider and get the
DeepSeek behaviour they had before.

Usage:
  from llm_client import chat_json, chat_text
  obj = chat_json(prompt, system="...")                       # deepseek
  obj = chat_json(prompt, provider="gemini")                  # Gemini
  obj = chat_json(prompt, provider="openai_compatible",
                  model="Qwen/Qwen2.5-7B-Instruct")           # local server
"""

import json
import os
import sys
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent

# provider -> (key env, base-url env, default base url, model env, default model)
# NOTE: model names drift. Verified 2026-09-05 against the live endpoint:
#   gemini-3.1-pro-preview  exists (was rate-limited: credits depleted)
#   gemini-2.5-pro          RETIRED ("no longer available to new users")
#   gemini-2.5-flash        exists
# Override per call (model=...) or per environment (GEMINI_MODEL=...).
PROVIDERS = {
    "deepseek": ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL",
                 "https://api.deepseek.com", "DEEPSEEK_MODEL", "deepseek-chat"),
    "gemini": ("GEMINI_API_KEY", "GEMINI_BASE_URL",
               "https://generativelanguage.googleapis.com/v1beta/openai/",
               "GEMINI_MODEL", "gemini-3.1-pro-preview"),
    "openai_compatible": ("LLM_API_KEY", "LLM_BASE_URL",
                          "http://localhost:8000/v1", "LLM_MODEL", ""),
}

DEFAULT_PROVIDER = os.environ.get("LLM_PROVIDER", "deepseek")

# Back-compat module-level names (the DeepSeek defaults the shipped scripts use)
DEFAULT_MODEL = os.environ.get(PROVIDERS["deepseek"][3],
                               PROVIDERS["deepseek"][4])
BASE_URL = os.environ.get(PROVIDERS["deepseek"][1], PROVIDERS["deepseek"][2])


def _provider_spec(provider):
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider {provider!r}; "
                         f"choose from {sorted(PROVIDERS)}")
    return PROVIDERS[provider]


def get_key(provider=DEFAULT_PROVIDER):
    if load_dotenv is not None:
        load_dotenv(ROOT / ".env")
    key_env = _provider_spec(provider)[0]
    key = os.environ.get(key_env, "").strip()
    if not key:
        raise RuntimeError(
            f"No {key_env} found for provider {provider!r}. Either:\n"
            f"  export {key_env}=...      (in the environment running the harness)\n"
            f"  or add {key_env}=... to phase1/.env   (chmod 600)"
        )
    return key


def _client(provider=DEFAULT_PROVIDER):
    _, base_env, base_default, _, _ = _provider_spec(provider)
    base = os.environ.get(base_env, base_default)
    return OpenAI(api_key=get_key(provider), base_url=base)


def default_model(provider=DEFAULT_PROVIDER):
    _, _, _, model_env, model_default = _provider_spec(provider)
    return os.environ.get(model_env, model_default)


def chat_text(prompt, system=None, temperature=0.3, max_tokens=2048, model=None,
              provider=None, retries=3, backoff=2.0):
    provider = provider or DEFAULT_PROVIDER
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    client = _client(provider)
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=model or default_model(provider),
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(backoff * (attempt + 1))
    raise RuntimeError("unreachable")


def chat_json(prompt, system=None, temperature=0.0, max_tokens=2048, model=None,
              provider=None):
    """Ask for a single JSON object; robustly extracts it from the reply."""
    text = chat_text(prompt, system=system, temperature=temperature,
                     max_tokens=max_tokens, model=model, provider=provider)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # tolerate fences / trailing text
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise ValueError(f"LLM did not return JSON: {text[:200]!r}")


if __name__ == "__main__":
    # smoke test: python3 llm_client.py "say hi in 3 words" [provider]
    prov = sys.argv[2] if len(sys.argv) > 2 else None
    out = chat_text(sys.argv[1] if len(sys.argv) > 1 else "Reply with exactly: OK",
                    provider=prov)
    print(out)
