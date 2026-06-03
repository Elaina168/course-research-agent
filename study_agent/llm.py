from __future__ import annotations

from typing import Any

from .config import Settings


class OpenAIChatClient:
    def __init__(self, settings: Settings):
        if not settings.api_key:
            raise RuntimeError(
                "Missing OPENAI_API_KEY. Copy .env.example to .env and fill OPENAI_API_KEY."
            )

        try:
            from openai import OpenAI
        except ImportError as import_error:
            raise RuntimeError("Missing openai dependency. Run pip install -r requirements.txt.") from import_error

        self.model = settings.model
        self.client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)

    def create_completion(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Any:
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
