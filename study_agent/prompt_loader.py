from __future__ import annotations

from importlib.resources import files


def load_system_prompt() -> str:
    return load_prompt("system_prompt.md")


def load_prompt(filename: str) -> str:
    prompt_file = files("study_agent.prompts").joinpath(filename)
    return prompt_file.read_text(encoding="utf-8")
