"""Versioned prompt templates for the LLM agents (Week 9: prompt versioning).

Each agent's system prompt lives in a `<agent>_v<N>.txt` file so prompts can be
iterated and A/B-tested without touching code. Bump the version (e.g. add
`router_v2.txt`) and pass `version="v2"` to compare.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=None)
def _read(agent: str, version: str) -> str:
    return (_DIR / f"{agent}_{version}.txt").read_text(encoding="utf-8").strip()


def load(agent: str, version: str = "v1", **fields: str) -> str:
    """Return the prompt for `agent`/`version`, formatting in any `fields`.

    Template placeholders use `{name}`; literal braces are written `{{` `}}`.
    """
    template = _read(agent, version)
    return template.format(**fields) if fields else template
