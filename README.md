# Intern-Hunter / internship-pilot

面向实习投递和面试准备的个人求职 Agent 系统。当前版本已经从纯规则 MVP 升级为：

```text
PDF 简历上传 -> PDF 文本抽取工具 -> DeepSeek 简历解析工具 -> ResumeProfile
JD 粘贴 -> DeepSeek JD 解析工具 -> 规则评分工具 -> DeepSeek 建议生成工具 -> SQLite 入库
Streamlit 前端 -> FastAPI HTTP API -> LangGraph Agent 工作流
```

## 当前能力

- 支持上传 PDF 简历，抽取 PDF 文本后调用 DeepSeek 解析结构化简历画像。
- 支持粘贴岗位 JD，优先调用 DeepSeek 解析结构化岗位信息，失败时规则降级。
- 使用规则评分计算技能、项目、方向、约束和准备成本分数。
- 使用 DeepSeek 基于规则评分补充优势、短板、投递建议、简历修改建议和准备建议。
- 使用 LangGraph 编排岗位匹配 Agent 工作流。
- 使用 FastAPI 提供后端 API，Streamlit 只通过 HTTP 调用后端。
- 使用 SQLite 保存岗位、匹配报告、面试准备和投递状态。

## 工具层设计

```text
app/tools/deepseek_client.py       DeepSeek JSON API 调用工具
app/tools/pdf_resume_tool.py       PDF 文本抽取工具
app/tools/resume_parse_tool.py     简历解析工具：PDF 文本 -> ResumeProfile
app/tools/jd_parse_tool.py         JD 解析工具：JD 文本 -> JobStructured
app/tools/match_advice_tool.py     匹配建议工具：规则报告 -> DeepSeek 中文建议
app/tools/persistence_tool.py      持久化工具：岗位和报告 -> SQLite
```

## Agent 工作流

入口函数：`app.agent.graph_job_match.run_job_match_agent`

```text
jd_parse_node
  -> resume_load_node
  -> match_score_node
  -> llm_advice_node
  -> gap_analysis_node
  -> recommendation_node
  -> save_result_node
```

其中：

- `jd_parse_node` 调用 DeepSeek 解析 JD，失败时规则降级。
- `match_score_node` 始终使用规则评分，保证分数可解释。
- `llm_advice_node` 调用 DeepSeek 基于规则结果生成具体建议。
- `save_result_node` 使用 SQLite 保存岗位和报告。

## 快速开始

```bash
cd internship-pilot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

在 `.env` 中配置 DeepSeek：

```text
DEEPSEEK_API_KEY=你的 DeepSeek API Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
ENABLE_LLM_PARSING=true
```

不要把 `.env` 提交到 GitHub。

启动后端：

```bash
uvicorn app.main:app --reload
```

启动前端：

```bash
streamlit run frontend/streamlit_app.py
```

运行测试：

```bash
pytest
```

## API

```text
GET  /health
GET  /resume/profile
PUT  /resume/profile
POST /resume/parse-pdf
GET  /jobs
GET  /jobs/{job_id}
POST /jobs/parse
POST /match/run
GET  /match/{job_id}
POST /interview/{job_id}/generate
GET  /interview/{job_id}
GET  /applications
PATCH /applications/{job_id}
```

## 安全边界

- 不自动投递岗位。
- 不登录招聘网站。
- 不发送邮件。
- 不把 API Key 写入代码或示例文件。
- `.env` 已被 `.gitignore` 忽略。

## 一键启动

```bash
python start.py
```

运行后会自动启动 FastAPI 后端和 Streamlit 前端，并打开本地页面。按 Ctrl+C 可以同时停止两个服务。
