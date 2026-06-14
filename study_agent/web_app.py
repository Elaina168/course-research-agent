from __future__ import annotations

import argparse
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .agent import CourseResearchAgent
from .config import Settings
from .llm import OpenAIChatClient
from .tools import build_default_registry


DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_PROXY_URL = "http://127.0.0.1:7890"
BAD_PROXY_URL = "http://127.0.0.1:9"
PROXY_ENV_NAMES = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)


INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>课程资料学习研究助手</title>
  <style>
    :root {
      --bg: #f5f5f7;
      --panel: rgba(255, 255, 255, 0.78);
      --panel-strong: rgba(255, 255, 255, 0.92);
      --text: #1d1d1f;
      --muted: #6e6e73;
      --border: rgba(0, 0, 0, 0.10);
      --primary: #0071e3;
      --primary-dark: #005bb5;
      --danger: #d70015;
      --ok: #248a3d;
      --code: #111827;
      --shadow: 0 18px 50px rgba(0, 0, 0, 0.10);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at 18% 8%, rgba(0, 113, 227, 0.14), transparent 30%),
        radial-gradient(circle at 82% 0%, rgba(175, 82, 222, 0.12), transparent 28%),
        linear-gradient(180deg, #fbfbfd 0%, var(--bg) 100%);
      color: var(--text);
      -webkit-font-smoothing: antialiased;
    }
    main {
      max-width: 1220px;
      margin: 0 auto;
      padding: 44px 22px 56px;
    }
    header {
      margin-bottom: 24px;
      text-align: center;
    }
    h1 {
      margin: 0 0 10px;
      font-size: clamp(34px, 5vw, 56px);
      line-height: 1.05;
      letter-spacing: -0.055em;
      font-weight: 760;
    }
    h2 {
      font-size: 21px;
      margin: 0 0 12px;
      letter-spacing: -0.02em;
    }
    p { line-height: 1.65; }
    .subtitle {
      margin: 0 auto;
      color: var(--muted);
      max-width: 820px;
      font-size: 17px;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 28px;
      box-shadow: var(--shadow);
      padding: 24px;
      backdrop-filter: blur(24px) saturate(1.8);
      -webkit-backdrop-filter: blur(24px) saturate(1.8);
    }
    .settings-grid {
      display: grid;
      grid-template-columns: minmax(260px, 0.58fr) minmax(320px, 1fr);
      gap: 16px;
      align-items: start;
    }
    .settings-grid .wide { grid-column: auto; }
    .system-note {
      margin-top: 14px;
      padding: 13px 15px;
      border-radius: 18px;
      background: rgba(0, 113, 227, 0.08);
      color: var(--muted);
      font-size: 14px;
    }
    .workspace {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
      align-items: start;
      margin-top: 18px;
    }
    .export-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(180px, 0.42fr);
      gap: 12px;
      align-items: start;
    }
    label {
      display: block;
      font-weight: 650;
      margin: 14px 0 8px;
      letter-spacing: -0.01em;
    }
    input, textarea {
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 13px 14px;
      font: inherit;
      background: var(--panel-strong);
      color: var(--text);
      outline: none;
      transition: border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
    }
    textarea {
      min-height: 132px;
      resize: vertical;
    }
    input:focus, textarea:focus {
      border-color: rgba(0, 113, 227, 0.75);
      background: #fff;
      box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.14);
    }
    .hint {
      margin-top: 7px;
      color: var(--muted);
      font-size: 13px;
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }
    button {
      border: 0;
      border-radius: 999px;
      padding: 11px 18px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      background: var(--primary);
      color: white;
      box-shadow: 0 8px 22px rgba(0, 113, 227, 0.28);
      transition: transform 0.16s ease, background 0.16s ease, box-shadow 0.16s ease;
    }
    button:hover {
      background: var(--primary-dark);
      transform: translateY(-1px);
      box-shadow: 0 10px 26px rgba(0, 113, 227, 0.34);
    }
    button.secondary {
      background: rgba(0, 113, 227, 0.10);
      color: var(--primary-dark);
      box-shadow: none;
    }
    button.secondary:hover { background: rgba(0, 113, 227, 0.15); }
    button:disabled {
      opacity: 0.65;
      cursor: wait;
      transform: none;
    }
    .status {
      min-height: 24px;
      margin-top: 12px;
      color: var(--muted);
      font-size: 14px;
    }
    .status.error { color: var(--danger); }
    .status.ok { color: var(--ok); }
    .output {
      min-height: 360px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: rgba(18, 18, 18, 0.94);
      color: #f5f5f7;
      border-radius: 22px;
      padding: 19px;
      line-height: 1.72;
      font-size: 15px;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
    }
    .section-note {
      color: var(--muted);
      margin-top: -4px;
      margin-bottom: 12px;
    }
    @media (max-width: 980px) {
      .settings-grid, .workspace, .export-grid { grid-template-columns: 1fr; }
      .settings-grid .wide { grid-column: auto; }
      main { padding: 28px 14px 42px; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>课程资料学习研究助手</h1>
      <p class="subtitle">填写 API Key 和本地 PDF 路径；下方“询问”和“测试”两个板块互不影响，方便反复切换。</p>
    </header>

    <section class="card">
      <h2>通用设置</h2>
      <div class="settings-grid">
        <div>
          <label for="apiKey">DeepSeek API Key</label>
          <input id="apiKey" type="password" autocomplete="off" placeholder="sk-..." />
          <div class="hint">只随本次请求发送给本地后端，不会写入文件。</div>
        </div>
        <div>
          <label for="pdfPath">本地 PDF 路径</label>
          <input id="pdfPath" placeholder="例如：C:\\path\\to\\course-reading.pdf" />
          <div class="hint">路径必须是运行 Agent 的这台电脑能访问的 PDF 文件路径。</div>
        </div>
      </div>
      <div class="system-note">系统默认使用 DeepSeek：模型 `deepseek-chat`，Base URL `https://api.deepseek.com`。</div>
    </section>

    <section class="workspace">
      <div class="card">
        <h2>询问</h2>
        <p class="section-note">输入你对 PDF 的问题，生成面向复习的回答。</p>
        <label for="askQuestion">问题</label>
        <textarea id="askQuestion">请总结这份 PDF 的核心观点、重要概念，并指出容易混淆的地方。</textarea>
        <div class="actions">
          <button id="askBtn">生成询问结果</button>
        </div>
        <div id="askStatus" class="status">准备就绪。</div>

        <div class="export-grid">
          <div>
            <label for="askOutputDir">保存目录</label>
            <input id="askOutputDir" value="" placeholder="留空则保存到系统临时目录，例如：C:\\path\\to\\outputs" />
          </div>
          <div>
            <label for="askOutputName">文件名</label>
            <input id="askOutputName" value="study_answer.md" />
          </div>
        </div>
        <div class="actions">
          <button id="saveAskBtn" class="secondary">导出询问结果</button>
        </div>
        <div id="askOutput" class="output">询问结果会显示在这里。</div>
      </div>

      <div class="card">
        <h2>测试</h2>
        <p class="section-note">根据 PDF 自动生成测验题、参考答案和解析。</p>
        <label for="quizCount">测试题数量</label>
        <input id="quizCount" inputmode="numeric" value="8" />
        <label for="quizRequirement">测试要求</label>
        <textarea id="quizRequirement">题型包含选择题、简答题和概念解释题，覆盖核心概念和易错点。</textarea>
        <div class="actions">
          <button id="quizBtn">生成测试题</button>
        </div>
        <div id="quizStatus" class="status">准备就绪。</div>

        <div class="export-grid">
          <div>
            <label for="quizOutputDir">保存目录</label>
            <input id="quizOutputDir" value="" placeholder="留空则保存到系统临时目录，例如：C:\\path\\to\\outputs" />
          </div>
          <div>
            <label for="quizOutputName">文件名</label>
            <input id="quizOutputName" value="study_quiz.md" />
          </div>
        </div>
        <div class="actions">
          <button id="saveQuizBtn" class="secondary">导出测试结果</button>
        </div>
        <div id="quizOutput" class="output">测试题、参考答案和解析会显示在这里。</div>
      </div>
    </section>
  </main>

  <script>
    const $ = (id) => document.getElementById(id);

    function setStatus(targetId, message, kind = "") {
      const statusEl = $(targetId);
      statusEl.className = `status ${kind}`.trim();
      statusEl.textContent = message;
    }

    async function postJson(path, payload) {
      const response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok || data.ok === false) {
        throw new Error(data.error || `请求失败：${response.status}`);
      }
      return data;
    }

    function sharedConfig() {
      return {
        api_key: $("apiKey").value.trim(),
        base_url: "https://api.deepseek.com",
        model: "deepseek-chat",
        pdf_path: $("pdfPath").value.trim()
      };
    }

    function validateSharedConfig(config, statusId) {
      if (!config.api_key) {
        setStatus(statusId, "请先填写 DeepSeek API Key。", "error");
        return false;
      }
      if (!config.pdf_path) {
        setStatus(statusId, "请先填写本地 PDF 路径。", "error");
        return false;
      }
      return true;
    }

    function buildAskPayload(config) {
      const question = $("askQuestion").value.trim();
      return {
        task_type: "course_qa",
        pdf_path: config.pdf_path,
        question: question || "请总结这份 PDF 的核心观点、重要概念，并指出容易混淆的地方。"
      };
    }

    function buildQuizPayload(config) {
      const quizCount = $("quizCount").value.trim() || "8";
      const requirement = $("quizRequirement").value.trim();
      return {
        task_type: "quiz_generation",
        pdf_path: config.pdf_path,
        quiz_count: quizCount,
        quiz_requirement: requirement
      };
    }

    async function runAgent({ buttonId, statusId, outputId, payloadBuilder }) {
      const button = $(buttonId);
      const config = sharedConfig();
      if (!validateSharedConfig(config, statusId)) return;

      try {
        button.disabled = true;
        setStatus(statusId, "正在读取 PDF 并调用大模型...");
        $(outputId).textContent = "";
        const data = await postJson("/api/ask", {
          api_key: config.api_key,
          base_url: config.base_url,
          model: config.model,
          ...payloadBuilder(config)
        });
        $(outputId).textContent = data.answer;
        setStatus(statusId, "完成。", "ok");
      } catch (error) {
        setStatus(statusId, error.message, "error");
        $(outputId).textContent = error.message;
      } finally {
        button.disabled = false;
      }
    }

    function buildOutputPath(dirInputId, nameInputId) {
      const outputDir = $(dirInputId).value.trim();
      const outputName = $(nameInputId).value.trim();
      if (!outputName) return "";
      if (!outputDir) return outputName;
      const separator = outputDir.includes("\\\\") ? "\\\\" : "/";
      return outputDir.replace(/[\\\\/]+$/, "") + separator + outputName;
    }

    async function saveMarkdown({ buttonId, statusId, outputId, dirInputId, nameInputId }) {
      const button = $(buttonId);
      const content = $(outputId).textContent.trim();
      const outputPath = buildOutputPath(dirInputId, nameInputId);
      if (!content || content === "询问结果会显示在这里。" || content === "测试题、参考答案和解析会显示在这里。") {
        setStatus(statusId, "请先生成内容，再导出。", "error");
        return;
      }
      if (!outputPath) {
        setStatus(statusId, "请先填写 Markdown 文件名。", "error");
        return;
      }

      try {
        button.disabled = true;
        setStatus(statusId, "正在导出 Markdown...");
        const data = await postJson("/api/save-markdown", {
          output_path: outputPath,
          content
        });
        setStatus(statusId, `已导出：${data.result.source}`, "ok");
      } catch (error) {
        setStatus(statusId, error.message, "error");
      } finally {
        button.disabled = false;
      }
    }

    $("askBtn").addEventListener("click", () => runAgent({
      buttonId: "askBtn",
      statusId: "askStatus",
      outputId: "askOutput",
      payloadBuilder: buildAskPayload
    }));

    $("quizBtn").addEventListener("click", () => runAgent({
      buttonId: "quizBtn",
      statusId: "quizStatus",
      outputId: "quizOutput",
      payloadBuilder: buildQuizPayload
    }));

    $("saveAskBtn").addEventListener("click", () => saveMarkdown({
      buttonId: "saveAskBtn",
      statusId: "askStatus",
      outputId: "askOutput",
      dirInputId: "askOutputDir",
      nameInputId: "askOutputName"
    }));

    $("saveQuizBtn").addEventListener("click", () => saveMarkdown({
      buttonId: "saveQuizBtn",
      statusId: "quizStatus",
      outputId: "quizOutput",
      dirInputId: "quizOutputDir",
      nameInputId: "quizOutputName"
    }));
  </script>
</body>
</html>
"""


class StudyAgentRequestHandler(BaseHTTPRequestHandler):
    server_version = "StudyAgentWeb/0.3"

    def do_GET(self) -> None:
        if self.path == "/":
            self._send_html(INDEX_HTML)
            return
        if self.path == "/api/tools":
            registry = build_default_registry()
            self._send_json({"ok": True, "tools": registry.describe()})
            return
        self._send_json({"ok": False, "error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
            if self.path == "/api/ask":
                self._handle_ask(payload)
                return
            if self.path == "/api/save-markdown":
                self._handle_save_markdown(payload)
                return
            self._send_json({"ok": False, "error": "Not found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as error:
            self._send_json(
                {"ok": False, "error": str(error)},
                status=HTTPStatus.BAD_REQUEST,
            )

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")

    def _handle_ask(self, payload: dict[str, Any]) -> None:
        api_key = str(payload.get("api_key", "")).strip()
        base_url = str(payload.get("base_url", DEFAULT_BASE_URL)).strip() or DEFAULT_BASE_URL
        model = str(payload.get("model", DEFAULT_MODEL)).strip() or DEFAULT_MODEL
        task_type = str(payload.get("task_type", "")).strip()
        if not api_key:
            self._send_json(
                {"ok": False, "error": "API Key is required."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        env_settings = Settings.from_env()
        settings = Settings(
            api_key=api_key,
            model=model or env_settings.model,
            base_url=base_url or env_settings.base_url,
        )
        llm_client = OpenAIChatClient(settings)
        agent = CourseResearchAgent(
            llm_client=llm_client,
            tool_registry=build_default_registry(),
        )

        if task_type == "course_qa":
            pdf_path = str(payload.get("pdf_path", "")).strip()
            question = str(payload.get("question", "")).strip()
            if not pdf_path:
                self._send_json(
                    {"ok": False, "error": "PDF path is required."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            if not question:
                self._send_json(
                    {"ok": False, "error": "Question is required."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            result = agent.run_course_qa(pdf_path=pdf_path, question=question)
            self._send_json(
                {
                    "ok": True,
                    "answer": result.content,
                    "skill": result.skill,
                    "context_source": result.context_source,
                    "tool_trace": result.tool_trace,
                }
            )
            return

        if task_type == "quiz_generation":
            pdf_path = str(payload.get("pdf_path", "")).strip()
            raw_quiz_count = str(payload.get("quiz_count", "8")).strip() or "8"
            requirement = str(payload.get("quiz_requirement", "")).strip()
            if not pdf_path:
                self._send_json(
                    {"ok": False, "error": "PDF path is required."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            try:
                quiz_count = int(raw_quiz_count)
            except ValueError:
                self._send_json(
                    {"ok": False, "error": "Quiz count must be an integer."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            if quiz_count < 1 or quiz_count > 50:
                self._send_json(
                    {"ok": False, "error": "Quiz count must be between 1 and 50."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            result = agent.run_quiz_generation(
                pdf_path=pdf_path,
                quiz_count=quiz_count,
                requirement=requirement,
            )
            self._send_json(
                {
                    "ok": True,
                    "answer": result.content,
                    "skill": result.skill,
                    "context_source": result.context_source,
                    "tool_trace": result.tool_trace,
                }
            )
            return

        question = str(payload.get("question", "")).strip()
        if not question:
            self._send_json(
                {"ok": False, "error": "Question is required."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        answer = agent.run(question)
        self._send_json({"ok": True, "answer": answer})

    def _handle_save_markdown(self, payload: dict[str, Any]) -> None:
        registry = build_default_registry()
        raw_result = registry.call(
            "save_markdown",
            json.dumps(
                {
                    "output_path": str(payload.get("output_path", "")).strip(),
                    "content": str(payload.get("content", "")),
                    "overwrite": True,
                },
                ensure_ascii=False,
            ),
        )
        result = json.loads(raw_result)
        if result.get("ok") is False:
            self._send_json(result, status=HTTPStatus.BAD_REQUEST)
            return
        self._send_json({"ok": True, "result": result})

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            return {}
        body = self.rfile.read(content_length).decode("utf-8")
        data = json.loads(body)
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object.")
        return data

    def _send_html(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def run_server(host: str, port: int) -> None:
    normalize_proxy_environment()
    server = ThreadingHTTPServer((host, port), StudyAgentRequestHandler)
    print(f"Study Agent Web UI running at http://{host}:{port}")
    print(f"Proxy: {os.environ.get('HTTPS_PROXY') or 'not configured'}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


def normalize_proxy_environment(proxy_url: str = DEFAULT_PROXY_URL) -> None:
    bad_proxy_detected = any(os.environ.get(name) == BAD_PROXY_URL for name in PROXY_ENV_NAMES)
    if not bad_proxy_detected:
        return

    for name in PROXY_ENV_NAMES:
        os.environ[name] = proxy_url


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Course Research Agent Web UI.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind.")
    parser.add_argument(
        "--proxy",
        default=DEFAULT_PROXY_URL,
        help="Proxy URL used when the inherited environment contains the known bad 127.0.0.1:9 proxy.",
    )
    args = parser.parse_args()
    normalize_proxy_environment(args.proxy)
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
