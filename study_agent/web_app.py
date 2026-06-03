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
      --bg: #f5f7fb;
      --panel: #ffffff;
      --text: #172033;
      --muted: #667085;
      --border: #d7ddea;
      --primary: #2563eb;
      --primary-dark: #1e40af;
      --danger: #b42318;
      --ok: #047857;
      --code: #101828;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: linear-gradient(135deg, #eef4ff 0%, var(--bg) 42%, #f8fafc 100%);
      color: var(--text);
    }
    main {
      max-width: 1280px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }
    header { margin-bottom: 24px; }
    h1 {
      margin: 0 0 8px;
      font-size: 32px;
      letter-spacing: -0.03em;
    }
    h2 {
      font-size: 20px;
      margin: 0 0 14px;
    }
    p { line-height: 1.7; }
    .subtitle {
      margin: 0;
      color: var(--muted);
      max-width: 880px;
    }
    .card {
      background: rgba(255, 255, 255, 0.94);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: 0 18px 55px rgba(16, 24, 40, 0.08);
      padding: 20px;
    }
    .settings-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }
    .settings-grid .wide { grid-column: 1 / -1; }
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
    }
    input, textarea {
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 12px 13px;
      font: inherit;
      background: #fff;
      color: var(--text);
      outline: none;
    }
    textarea {
      min-height: 132px;
      resize: vertical;
    }
    input:focus, textarea:focus {
      border-color: var(--primary);
      box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.12);
    }
    .hint {
      margin-top: 6px;
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
      padding: 11px 16px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      background: var(--primary);
      color: white;
    }
    button.secondary {
      background: #eef2ff;
      color: var(--primary-dark);
    }
    button:disabled {
      opacity: 0.65;
      cursor: wait;
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
      background: #0b1220;
      color: #e6edf7;
      border-radius: 16px;
      padding: 18px;
      line-height: 1.72;
      font-size: 15px;
    }
    .section-note {
      color: var(--muted);
      margin-top: -6px;
      margin-bottom: 12px;
    }
    @media (max-width: 980px) {
      .settings-grid, .workspace, .export-grid { grid-template-columns: 1fr; }
      .settings-grid .wide { grid-column: auto; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>课程资料学习研究助手</h1>
      <p class="subtitle">顶部填写通用 API 和 PDF 设置；下方“询问”和“测试”两个板块互不影响，方便反复切换。</p>
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
          <label for="model">模型</label>
          <input id="model" value="deepseek-chat" />
          <div class="hint">DeepSeek 常用模型是 `deepseek-chat`。</div>
        </div>
        <div class="wide">
          <label for="baseUrl">API Base URL</label>
          <input id="baseUrl" value="https://api.deepseek.com" />
          <div class="hint">DeepSeek 默认使用 `https://api.deepseek.com`。</div>
        </div>
        <div class="wide">
          <label for="pdfPath">本地 PDF 路径</label>
          <input id="pdfPath" placeholder="例如：D:\\course\\week1.pdf" />
          <div class="hint">路径必须是运行 Agent 的这台电脑能访问的 PDF 文件路径。</div>
        </div>
      </div>
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
            <input id="askOutputDir" value="" placeholder="留空则保存到系统临时目录，例如：D:\\course\\outputs" />
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
            <input id="quizOutputDir" value="" placeholder="留空则保存到系统临时目录，例如：D:\\course\\outputs" />
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
        base_url: $("baseUrl").value.trim(),
        model: $("model").value.trim(),
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

    function buildAskQuestion(config) {
      const question = $("askQuestion").value.trim();
      return [
        `请读取这个 PDF：${config.pdf_path}`,
        "任务：请回答用户对 PDF 的询问。回答应基于 PDF 内容，结构清晰，适合复习使用。",
        `用户问题：${question || "请总结这份 PDF 的核心观点、重要概念，并指出容易混淆的地方。"}`
      ].join("\\n\\n");
    }

    function buildQuizQuestion(config) {
      const quizCount = $("quizCount").value.trim() || "8";
      const requirement = $("quizRequirement").value.trim();
      return [
        `请读取这个 PDF：${config.pdf_path}`,
        `任务：请根据 PDF 内容生成 ${quizCount} 道测验题，用来检测初步复习成果。`,
        "每道题必须包含：题目、参考答案、简短解析。",
        requirement ? `用户测试要求：${requirement}` : ""
      ].filter(Boolean).join("\\n\\n");
    }

    async function runAgent({ buttonId, statusId, outputId, questionBuilder }) {
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
          question: questionBuilder(config)
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
      questionBuilder: buildAskQuestion
    }));

    $("quizBtn").addEventListener("click", () => runAgent({
      buttonId: "quizBtn",
      statusId: "quizStatus",
      outputId: "quizOutput",
      questionBuilder: buildQuizQuestion
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
        question = str(payload.get("question", "")).strip()
        if not api_key:
            self._send_json(
                {"ok": False, "error": "API Key is required."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        if not question:
            self._send_json(
                {"ok": False, "error": "Question is required."},
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
