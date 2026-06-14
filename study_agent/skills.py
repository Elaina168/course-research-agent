from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .llm import OpenAIChatClient
from .prompt_loader import load_prompt, load_system_prompt


@dataclass(frozen=True)
class PdfContext:
    source: str
    pages_read: int
    total_pages: int
    text: str
    truncated: bool


@dataclass(frozen=True)
class SkillResult:
    skill: str
    content: str
    context_source: str
    tool_trace: list[dict[str, Any]]


class CourseQASkill:
    name = "course_qa_skill"
    description = "Answer questions, summarize readings, and explain concepts from PDF context."

    def run(self, llm_client: OpenAIChatClient, context: PdfContext, question: str) -> SkillResult:
        messages = [
            {"role": "system", "content": load_system_prompt()},
            {
                "role": "user",
                "content": _build_skill_message(
                    skill_prompt=load_prompt("course_qa_skill.md"),
                    context=context,
                    task_input=f"用户问题：\n{question}",
                ),
            },
        ]
        completion = llm_client.create_completion(messages=messages)
        content = completion.choices[0].message.content or ""
        return SkillResult(
            skill=self.name,
            content=content,
            context_source=context.source,
            tool_trace=[],
        )


class QuizGenerationSkill:
    name = "quiz_generation_skill"
    description = "Generate quiz questions, reference answers, and explanations from PDF context."

    def run(
        self,
        llm_client: OpenAIChatClient,
        context: PdfContext,
        quiz_count: int,
        requirement: str,
    ) -> SkillResult:
        task_input = "\n".join(
            [
                f"测试题数量：{quiz_count}",
                f"测试要求：{requirement or '覆盖核心概念和易错点。'}",
            ]
        )
        messages = [
            {"role": "system", "content": load_system_prompt()},
            {
                "role": "user",
                "content": _build_skill_message(
                    skill_prompt=load_prompt("quiz_generation_skill.md"),
                    context=context,
                    task_input=task_input,
                ),
            },
        ]
        completion = llm_client.create_completion(messages=messages)
        content = completion.choices[0].message.content or ""
        return SkillResult(
            skill=self.name,
            content=content,
            context_source=context.source,
            tool_trace=[],
        )


def _build_skill_message(skill_prompt: str, context: PdfContext, task_input: str) -> str:
    truncated_note = "是" if context.truncated else "否"
    return f"""{skill_prompt}

PDF source: {context.source}
Pages read: {context.pages_read}/{context.total_pages}
Context truncated: {truncated_note}

<pdf_context>
{context.text}
</pdf_context>

<task_input>
{task_input}
</task_input>
"""
