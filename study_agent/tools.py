from __future__ import annotations

import json
import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ReadPdfArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pdf_path: str = Field(description="Local PDF file path.")
    max_pages: int | None = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum pages to read; defaults to the first 20 pages.",
    )
    max_chars: int = Field(
        default=18000,
        ge=1000,
        le=60000,
        description="Maximum characters to return.",
    )


class SaveMarkdownArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output_path: str = Field(description="Local Markdown output path. It must end with .md.")
    content: str = Field(description="Markdown content to save.")
    overwrite: bool = Field(default=True, description="Whether to overwrite an existing file.")


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    args_model: type[BaseModel]
    handler: Callable[[BaseModel], dict[str, Any]]

    def openai_schema(self) -> dict[str, Any]:
        parameters = self.args_model.model_json_schema()
        parameters["additionalProperties"] = False
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
            },
        }


class ToolRegistry:
    def __init__(self, definitions: list[ToolDefinition]):
        self.definitions = {definition.name: definition for definition in definitions}

    def schemas(self) -> list[dict[str, Any]]:
        return [definition.openai_schema() for definition in self.definitions.values()]

    def describe(self) -> list[dict[str, str]]:
        return [
            {"name": definition.name, "description": definition.description}
            for definition in self.definitions.values()
        ]

    def call(self, name: str, raw_arguments: str) -> str:
        definition = self.definitions.get(name)
        if definition is None:
            return json.dumps(
                {"ok": False, "error": f"Unknown tool: {name}"},
                ensure_ascii=False,
            )

        try:
            arguments = definition.args_model.model_validate_json(raw_arguments or "{}")
            payload = definition.handler(arguments)
            return json.dumps({"ok": True, **payload}, ensure_ascii=False)
        except Exception as error:
            return json.dumps(
                {"ok": False, "tool": name, "error": str(error)},
                ensure_ascii=False,
            )


def build_default_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            ToolDefinition(
                name="read_pdf",
                description="Read a local PDF file and extract text for course-material analysis.",
                args_model=ReadPdfArgs,
                handler=read_pdf,
            ),
            ToolDefinition(
                name="save_markdown",
                description="Save generated study notes, summaries, quizzes, or answers as a local Markdown file.",
                args_model=SaveMarkdownArgs,
                handler=save_markdown,
            ),
        ]
    )


def read_pdf(arguments: BaseModel) -> dict[str, Any]:
    if not isinstance(arguments, ReadPdfArgs):
        raise TypeError("read_pdf received the wrong argument type.")

    pdf_path = Path(arguments.pdf_path).expanduser()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file does not exist: {pdf_path}")
    if not pdf_path.is_file():
        raise ValueError(f"PDF path is not a file: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"File is not a PDF: {pdf_path}")

    try:
        from pypdf import PdfReader
    except ImportError as import_error:
        raise RuntimeError("Missing pypdf dependency. Run pip install -r requirements.txt.") from import_error

    reader = PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    page_limit = min(arguments.max_pages or total_pages, total_pages)

    page_texts: list[str] = []
    for page_index in range(page_limit):
        text = reader.pages[page_index].extract_text() or ""
        clean_page_text = _normalize_text(text)
        if clean_page_text:
            page_texts.append(f"[Page {page_index + 1}]\n{clean_page_text}")

    combined_text = "\n\n".join(page_texts)
    truncated_text = _truncate(combined_text, arguments.max_chars)

    return {
        "tool": "read_pdf",
        "source": str(pdf_path.resolve()),
        "pages_read": page_limit,
        "total_pages": total_pages,
        "text": truncated_text,
        "truncated": len(combined_text) > len(truncated_text),
    }


def save_markdown(arguments: BaseModel) -> dict[str, Any]:
    if not isinstance(arguments, SaveMarkdownArgs):
        raise TypeError("save_markdown received the wrong argument type.")

    requested_path = Path(arguments.output_path).expanduser()
    output_path = _resolve_markdown_output_path(requested_path)
    if output_path.suffix.lower() != ".md":
        raise ValueError(f"Markdown output path must end with .md: {output_path}")
    if output_path.exists() and not arguments.overwrite:
        raise FileExistsError(f"Markdown file already exists: {output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(arguments.content, encoding="utf-8")

    return {
        "tool": "save_markdown",
        "source": str(output_path.resolve()),
        "requested_path": str(requested_path),
        "used_temp_dir": not requested_path.is_absolute(),
        "bytes_written": len(arguments.content.encode("utf-8")),
    }


def _resolve_markdown_output_path(requested_path: Path) -> Path:
    if requested_path.is_absolute():
        return requested_path
    return Path(tempfile.gettempdir()) / requested_path


def _normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    non_empty_lines = [line for line in lines if line]
    compact_text = "\n".join(non_empty_lines)
    compact_text = re.sub(r"\n{3,}", "\n\n", compact_text)
    return compact_text.strip()


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n\n[TRUNCATED]"
