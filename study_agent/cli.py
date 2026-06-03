from __future__ import annotations

import argparse
import json
import sys

from .agent import CourseResearchAgent
from .config import Settings
from .llm import OpenAIChatClient
from .tools import build_default_registry


def main() -> None:
    _configure_utf8_output()

    parser = argparse.ArgumentParser(
        prog="study-agent",
        description="Course material study agent: read PDFs and summarize with an LLM.",
    )
    parser.add_argument(
        "question",
        nargs="*",
        help="Question to send to the agent. Starts interactive mode if omitted.",
    )
    parser.add_argument("--model", help="Override OPENAI_MODEL.")
    parser.add_argument("--max-tool-rounds", type=int, default=5, help="Maximum tool-call rounds.")
    parser.add_argument("--list-tools", action="store_true", help="List available tools and exit.")
    args = parser.parse_args()

    tool_registry = build_default_registry()
    if args.list_tools:
        print(json.dumps(tool_registry.describe(), ensure_ascii=False, indent=2))
        return

    settings = Settings.from_env(model_override=args.model)
    llm_client = OpenAIChatClient(settings)
    agent = CourseResearchAgent(
        llm_client=llm_client,
        tool_registry=tool_registry,
        max_tool_rounds=args.max_tool_rounds,
    )

    question = " ".join(args.question).strip()
    if question:
        print(agent.run(question))
        return

    _run_repl(agent)


def _configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def _run_repl(agent: CourseResearchAgent) -> None:
    print("Course Research Agent started. Type exit to quit.")
    while True:
        try:
            question = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if question.lower() in {"exit", "quit", "q"}:
            return
        if not question:
            continue

        try:
            print("\nAgent:")
            print(agent.run(question))
        except Exception as error:
            print(f"Run failed: {error}", file=sys.stderr)


if __name__ == "__main__":
    main()
