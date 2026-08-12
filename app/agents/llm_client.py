"""Provider-agnostic LLM client (stdlib only, no extra deps).

Calls any OpenAI-compatible /chat/completions endpoint and returns parsed JSON.
Used by the LLM agents. Raises LLMUnavailable when no key is configured so the
pipeline can fall back to rules.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from ..config import LLMConfig, load_llm_config


class LLMUnavailable(RuntimeError):
    """Raised when the LLM cannot be used (e.g. no API key)."""


def call_llm_json(
    system: str,
    user: str,
    *,
    temperature: float = 0.0,
    max_retries: int = 1,
    config: LLMConfig | None = None,
    timeout: float = 30.0,
) -> dict:
    """Send a chat completion and return the parsed JSON object."""
    cfg = config or load_llm_config()
    if cfg.requires_key and not cfg.api_key:
        raise LLMUnavailable(f'No API key for provider "{cfg.provider}".')

    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"

    user_msg = user
    last_err: Exception | None = None
    for _ in range(max_retries + 1):
        body = json.dumps(
            {
                "model": cfg.model,
                "temperature": temperature,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                ],
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            f"{cfg.base_url}/chat/completions", data=body, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:300]
            raise RuntimeError(f"LLM HTTP {e.code}: {detail}") from e

        content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            last_err = e
            user_msg = f"{user}\n\nYour previous reply was not valid JSON. Reply with ONLY a valid JSON object."

    raise RuntimeError(f"LLM returned invalid JSON after retries: {last_err}")
