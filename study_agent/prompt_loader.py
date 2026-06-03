from __future__ import annotations

from importlib.resources import files


def load_system_prompt() -> str:
    prompt_file = files("study_agent.prompts").joinpath("system_prompt.md")
    return prompt_file.read_text(encoding="utf-8")

