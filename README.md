# Intern-Hunter / internship-pilot

面向实习投递和面试准备的个人求职 Agent 系统。当前版本已经从纯规则 MVP 升级为：

```text
PDF 简历上传 -> PDF 文本抽取工具 -> 仅保存当前简历文本与历史文本快照
岗位 JD 粘贴 -> Redis/SQLite 去重 -> DeepSeek JD 解析工具 -> 保存结构化岗位
匹配度报告 -> 当前简历文本临时解析 -> 选择已保存 JD -> 规则评分 + DeepSeek LLM Judge 对比
Streamlit 前端 -> FastAPI HTTP API -> LangGraph Agent 工作流
```

## 当前能力

- 支持上传 PDF 简历，抽取 PDF 文本后只保存文本内容；结构化简历画像只在预览或匹配时临时生成。
- 支持粘贴岗位 JD，优先检查 Redis/SQLite 去重，未命中时调用 DeepSeek 解析结构化岗位并保存。
- 匹配度报告固定使用当前上传的简历文本，选择不同已保存 JD 生成报告。
- 报告左右对比展示规则评分和 DeepSeek LLM Judge 独立判断。
- 使用 LangGraph 编排岗位匹配 Agent 工作流。
- 使用 FastAPI 提供后端 API，Streamlit 只通过 HTTP 调用后端。
- 使用 SQLite 保存岗位、匹配报告、面试准备和投递状态。

## 工具层设计

```text
app/tools/deepseek_client.py       DeepSeek JSON API 调用工具
app/tools/pdf_resume_tool.py       PDF 文本抽取工具
app/tools/resume_parse_tool.py     简历解析工具：PDF 文本 -> 临时 ResumeProfile
app/tools/jd_parse_tool.py         JD 解析工具：JD 文本 -> JobStructured
app/tools/resume_text_store.py     简历文本存储工具：保存当前文本和历史快照
app/tools/llm_judge_tool.py         LLM Judge 工具：简历文本画像 + JD -> 独立匹配判断
app/tools/persistence_tool.py      持久化工具：岗位和报告 -> SQLite
```

## Agent 工作流

入口函数：`app.agent.graph_job_match.run_job_match_agent`

```text
jd_parse_node
  -> resume_load_node
  -> match_score_node
  -> llm_judge_node
  -> gap_analysis_node
  -> recommendation_node
  -> save_result_node
```

其中：

- `jd_parse_node` 调用 DeepSeek 解析 JD，失败时规则降级。
- `match_score_node` 始终使用规则评分，保证分数可解释。
- `llm_judge_node` 调用 DeepSeek LLM Judge 直接判断简历与岗位的适配程度。
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
GET  /resume/text/current
GET  /resume/texts
POST /resume/parse-pdf
GET  /jobs
POST /jobs/analyze
POST /jobs/parse
GET  /jobs/{job_id}
POST /match/run
POST /match/jobs/{job_id}/run
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

## Redis 缓存与 JD 去重

项目支持可选 Redis 缓存，用来避免同一个 JD 反复分析时重复入库，并减少重复查询成本：

```text
REDIS_URL=redis://localhost:6379/0
ENABLE_REDIS_CACHE=true
JOB_CACHE_TTL_SECONDS=604800
```

保存岗位时会先计算 `jd_hash`：

```text
用户 JD -> 规范化文本 -> SHA-256 jd_hash
```

然后按以下顺序处理：

```text
查 Redis: jd_hash -> job_id
  -> 命中：直接返回已有报告，不新增 jobs
  -> 未命中：查 SQLite jobs.jd_hash
      -> 命中：回填 Redis，返回已有报告
      -> 未命中：保存新岗位、新报告和默认投递状态
```

Redis 没启动时系统不会报错，会自动回退到 SQLite 去重。
