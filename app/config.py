"""Settings, read from the environment once at startup."""

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    database_url: str
    # the API docs are off by default: the server faces the public internet behind Cloudflare
    docs: bool


@lru_cache
def get_settings() -> Settings:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set (see .env.example)")
    return Settings(database_url=url, docs=os.environ.get("ENABLE_DOCS") == "1")
