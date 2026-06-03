from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE_URL = "https://api.deepseek.com"


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    model: str
    base_url: str | None = DEFAULT_BASE_URL

    @classmethod
    def from_env(cls, model_override: str | None = None) -> "Settings":
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

        return cls(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=model_override or os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
            base_url=os.getenv("OPENAI_BASE_URL") or DEFAULT_BASE_URL,
        )
