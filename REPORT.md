# Experiment 2: Bring Your Own Agent（BYOA）实验报告

## 1. 项目简介

本项目实现了一个“课程资料学习研究助手 Agent”。它面向课程 PDF 学习场景，内置课程学习助手系统 Prompt，并通过两个显式 Skill 完成资料问答和复习测验生成。用户还可以将生成结果导出为 Markdown 文件，方便后续复习和归档。

这个 Agent 不只是直接向大模型提问，而是先由 Agent 编排层选择 Skill，再调用本地 PDF 工具读取外部上下文，最后让模型基于系统 Prompt、Skill Prompt 和 PDF context 输出结果。因此它符合 BYOA 实验中“依赖外部工具和上下文，而不是只依赖 LLM 基础知识”的要求。

## 2. 系统机制与工具

本项目使用 OpenAI-compatible function calling 作为工具桥接方式。后端使用 OpenAI Python SDK，但将 `base_url` 配置为 DeepSeek：

```text
https://api.deepseek.com
```

默认模型：

```text
deepseek-chat
```

Agent 设计了两个主要 Skill：

1. `course_qa_skill`
   - 功能：基于 PDF context 回答用户问题、总结课程重点、解释重要概念。
   - Prompt 文件：`study_agent/prompts/course_qa_skill.md`

2. `quiz_generation_skill`
   - 功能：基于 PDF context 生成测验题、参考答案和解析，用于检测初步复习成果。
   - Prompt 文件：`study_agent/prompts/quiz_generation_skill.md`

Agent 还注册了两个底层工具：

1. `read_pdf`
   - 参数：`pdf_path`、`max_pages`、`max_chars`
   - 功能：读取本地 PDF，提取页级文本，作为大模型回答问题的外部上下文。

2. `save_markdown`
   - 参数：`output_path`、`content`、`overwrite`
   - 功能：将生成的学习总结、测验题、参考答案和解析保存为本地 Markdown 文件。

Agent 的执行流程是：

1. 用户在 Web 前端填写 API Key、PDF 路径和任务。
2. 后端根据任务类型选择 `course_qa_skill` 或 `quiz_generation_skill`。
3. Agent 调用 `read_pdf` 读取本地 PDF，并把提取文本作为 context。
4. Agent 将系统 Prompt、Skill Prompt、PDF context 和用户任务发送给 DeepSeek。
5. 模型基于 PDF 内容生成总结、问答或测验题。
6. 用户需要保存时，后端调用 `save_markdown` 写入本地 `.md` 文件。

## 3. 前端功能

Web 前端分为三部分：

1. 通用设置
   - DeepSeek API Key
   - 本地 PDF 路径
   - API Base URL 和模型由系统默认配置：`https://api.deepseek.com` 与 `deepseek-chat`

2. 询问板块
   - 用户输入对 PDF 的问题
   - Agent 生成基于 PDF 的回答
   - 用户选择保存目录和文件名
   - 导出 Markdown

3. 测试板块
   - 用户输入测试题数量和测试要求
   - Agent 生成测验题、参考答案和解析
   - 用户选择保存目录和文件名
   - 导出 Markdown

## 4. 执行截图说明

建议最终报告中放入以下 3～4 张截图：

1. Web 前端整体页面
   - 展示通用设置、询问板块和测试板块。

2. PDF 询问结果
   - 展示用户输入问题后，Agent 基于 PDF 生成学习总结或解释。

3. PDF 测试结果
   - 展示 Agent 生成的测验题、参考答案和解析。

4. Markdown 导出结果
   - 展示导出成功提示，以及生成的 `.md` 文件内容。

## 5. 使用 AI 辅助开发的反思

这次开发中，AI 辅助编程主要帮助我快速生成了 Python 项目结构、工具注册表、Pydantic 参数模型、Agent 编排循环和 Web 前端样板代码。这样我可以把更多精力放在 Agent 的系统提示词、工具设计和交互流程上。

一个具体技术困难是网页抓取功能不稳定。最初方案包含抓取正在浏览的网页，但实际测试 Bilibili 等动态网页时，遇到了代理错误、JavaScript 动态渲染、反爬限制等问题。简单的 `requests + BeautifulSoup` 对课程静态网页可用，但对视频平台和复杂网页不稳定。为了保证实验可演示性，我删除了网页抓取功能，改为更稳定的本地 PDF 读取和 Markdown 导出。

第二个困难是 API 接入。最初使用 OpenAI API 时遇到 quota、invalid key 和代理配置问题。后来改用 DeepSeek API，并利用它兼容 OpenAI SDK 的特点，只需要配置 `base_url`、`api_key` 和 `model`，不需要重写整个 Agent 调用逻辑。

第三个困难是本地文件权限。Markdown 导出最初总是保存到系统临时目录，是因为当前 Python 进程对部分目录没有写权限。后来我修改了保存逻辑：如果用户填写保存目录，就严格写入该目录；如果没有权限，则直接报错，不再偷偷回退到 Temp。最终的使用方式是让用户选择自己有写入权限的目录，例如个人文档目录或项目下的 `outputs/` 目录。

总体来看，AI 在生成样板代码上效率很高，但它容易一开始设计过大的功能范围，例如网页抓取和自动浏览器读取。真正让项目稳定下来的关键，是把功能收敛到可控的本地工具：读取 PDF 和保存 Markdown。这两个工具足够清晰、稳定，也更容易用截图证明 Agent 真的完成了外部工具调用。

## 6. 当前交付状态

当前项目已经实现：

- DeepSeek 大模型接入
- 内置系统 Prompt
- 课程资料问答 Skill
- 复习测验生成 Skill
- 本地 PDF 读取工具和 PDF context 集成
- Markdown 导出工具
- Web 前端
- 询问模式
- 测试题生成模式
- 本地文件保存

因此项目满足实验要求中的：

- 至少两个明确 Skill
- 标准 OpenAI-compatible API 和本地工具桥接
- 外部上下文集成
- 可运行 Agent 代码仓库
- 可截图展示的 Agent 执行流程
