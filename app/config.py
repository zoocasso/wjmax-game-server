"""Settings, read from the environment once at startup."""

import json
import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    database_url: str
    # the API docs are off by default: a deployed server is public (WJMAX's sat behind Cloudflare)
    docs: bool
    # titles the game client spells differently from music_tb, e.g. {"title as sent": "title in music_tb"}
    title_aliases: dict[str, str]


@lru_cache
def get_settings() -> Settings:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set (see .env.example)")
    return Settings(
        database_url=url,
        docs=os.environ.get("ENABLE_DOCS") == "1",
        title_aliases=_title_aliases(os.environ.get("TITLE_ALIASES", "")),
    )


def _title_aliases(raw: str) -> dict[str, str]:
    """TITLE_ALIASES is a JSON object of strings; empty means no aliases."""
    if not raw.strip():
        return {}
    aliases = json.loads(raw)
    if not isinstance(aliases, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in aliases.items()
    ):
        raise RuntimeError("TITLE_ALIASES must be a JSON object of strings (see .env.example)")
    return aliases
