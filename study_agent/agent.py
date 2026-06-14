from __future__ import annotations

import json
from typing import Any

from .llm import OpenAIChatClient
from .prompt_loader import load_system_prompt
from .skills import CourseQASkill, PdfContext, QuizGenerationSkill, SkillResult
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

    def run_course_qa(self, pdf_path: str, question: str) -> SkillResult:
        context, tool_trace = self._read_pdf_context(pdf_path)
        result = CourseQASkill().run(
            llm_client=self.llm_client,
            context=context,
            question=question,
        )
        return SkillResult(
            skill=result.skill,
            content=result.content,
            context_source=result.context_source,
            tool_trace=tool_trace,
        )

    def run_quiz_generation(
        self,
        pdf_path: str,
        quiz_count: int,
        requirement: str,
    ) -> SkillResult:
        context, tool_trace = self._read_pdf_context(pdf_path)
        result = QuizGenerationSkill().run(
            llm_client=self.llm_client,
            context=context,
            quiz_count=quiz_count,
            requirement=requirement,
        )
        return SkillResult(
            skill=result.skill,
            content=result.content,
            context_source=result.context_source,
            tool_trace=tool_trace,
        )

    def _read_pdf_context(self, pdf_path: str) -> tuple[PdfContext, list[dict[str, Any]]]:
        raw_result = self.tool_registry.call(
            name="read_pdf",
            raw_arguments=json.dumps(
                {
                    "pdf_path": pdf_path,
                    "max_pages": 30,
                    "max_chars": 45000,
                },
                ensure_ascii=False,
            ),
        )
        result = json.loads(raw_result)
        tool_trace = [
            {
                "tool": "read_pdf",
                "ok": result.get("ok"),
                "source": result.get("source"),
                "pages_read": result.get("pages_read"),
                "total_pages": result.get("total_pages"),
                "truncated": result.get("truncated"),
            }
        ]
        if result.get("ok") is False:
            raise RuntimeError(str(result.get("error", "read_pdf failed.")))
        return (
            PdfContext(
                source=str(result.get("source", "")),
                pages_read=int(result.get("pages_read", 0)),
                total_pages=int(result.get("total_pages", 0)),
                text=str(result.get("text", "")),
                truncated=bool(result.get("truncated", False)),
            ),
            tool_trace,
        )

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
