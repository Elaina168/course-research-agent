from __future__ import annotations

from typing import Any

from .llm import OpenAIChatClient
from .prompt_loader import load_system_prompt
from .tools import ToolRegistry


class CourseResearchAgent:
    def __init__(
        self,
        llm_client: OpenAIChatClient,
        tool_registry: ToolRegistry,
        max_tool_rounds: int = 5,
    ):
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.max_tool_rounds = max_tool_rounds

    def run(self, user_input: str) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": user_input},
        ]

        for _tool_round in range(self.max_tool_rounds):
            completion = self.llm_client.create_completion(
                messages=messages,
                tools=self.tool_registry.schemas(),
            )
            assistant_message = completion.choices[0].message
            messages.append(self._assistant_message_to_dict(assistant_message))

            tool_calls = assistant_message.tool_calls or []
            if not tool_calls:
                return assistant_message.content or ""

            for tool_call in tool_calls:
                tool_output = self.tool_registry.call(
                    name=tool_call.function.name,
                    raw_arguments=tool_call.function.arguments,
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": tool_output,
                    }
                )

        return "Tool-call round limit reached before a final answer was produced. Narrow the question or reduce source size."

    @staticmethod
    def _assistant_message_to_dict(assistant_message: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "role": "assistant",
            "content": assistant_message.content,
        }
        if assistant_message.tool_calls:
            payload["tool_calls"] = [
                tool_call.model_dump(exclude_none=True)
                for tool_call in assistant_message.tool_calls
            ]
        return payload

