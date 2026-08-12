"""LLM configuration read from environment variables.

Set these in a .env file or your shell (never hardcode keys):
    LLM_PROVIDER = groq | openai | ollama   (default: groq)
    LLM_API_KEY  = ...   (or GROQ_API_KEY / OPENAI_API_KEY)
    LLM_MODEL    = ...   (optional; provider default used otherwise)
    LLM_BASE_URL = ...   (optional override for self-hosted / custom)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    """Minimal .env loader (no dependency). Does not override existing env vars."""
    # project root = two levels up from this file (app/config.py -> project/)
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)

_PROVIDER_DEFAULTS = {
    "groq": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile", "GROQ_API_KEY"),
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini", "OPENAI_API_KEY"),
    "ollama": ("http://localhost:11434/v1", "llama3.1", None),
}


@dataclass
class LLMConfig:
    provider: str
    base_url: str
    model: str
    api_key: str
    requires_key: bool

    @property
    def configured(self) -> bool:
        return (not self.requires_key) or bool(self.api_key)


def load_llm_config() -> LLMConfig:
    _load_dotenv()
    provider = os.environ.get("LLM_PROVIDER", "groq").lower()
    base_url, model, key_env = _PROVIDER_DEFAULTS.get(provider, _PROVIDER_DEFAULTS["groq"])
    api_key = os.environ.get("LLM_API_KEY") or (os.environ.get(key_env) if key_env else "") or ""
    return LLMConfig(
        provider=provider,
        base_url=os.environ.get("LLM_BASE_URL", base_url),
        model=os.environ.get("LLM_MODEL", model),
        api_key=api_key,
        requires_key=provider != "ollama",
    )
