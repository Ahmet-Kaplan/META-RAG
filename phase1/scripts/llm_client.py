#!/usr/bin/env python3
"""
llm_client.py — OpenAI-compatible LLM client (default: DeepSeek).

Key resolution order:
  1. DEEPSEEK_API_KEY environment variable
  2. phase1/.env  (DEEPSEEK_API_KEY=sk-...)   <- recommended: works regardless
     of how the command shells are spawned. Keep it chmod 600, never commit.

Usage:
  from llm_client import chat_json, chat_text
  txt = chat_text("hello", temperature=0.3)
  obj = chat_json({"instruction": "..."})
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
DEFAULT_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


def get_key():
    if load_dotenv is not None:
        load_dotenv(ROOT / ".env")
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "No DEEPSEEK_API_KEY found. Either:\n"
            "  export DEEPSEEK_API_KEY=sk-...   (in the environment running the harness)\n"
            "  or create phase1/.env with:      DEEPSEEK_API_KEY=sk-...  (chmod 600)"
        )
    return key


def _client():
    return OpenAI(api_key=get_key(), base_url=BASE_URL)


def chat_text(prompt, system=None, temperature=0.3, max_tokens=2048, model=None, retries=3, backoff=2.0):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    client = _client()
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=model or DEFAULT_MODEL,
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


def chat_json(prompt, system=None, temperature=0.0, max_tokens=2048, model=None):
    """Ask for a single JSON object; robustly extracts it from the reply."""
    text = chat_text(prompt, system=system, temperature=temperature,
                     max_tokens=max_tokens, model=model)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # tolerate fences / trailing text
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise ValueError(f"LLM did not return JSON: {text[:200]!r}")


if __name__ == "__main__":
    # smoke test: python3 llm_client.py "say hi in 3 words"
    out = chat_text(sys.argv[1] if len(sys.argv) > 1 else "Reply with exactly: OK")
    print(out)
