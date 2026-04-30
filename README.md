# 浙商大信电学院「智能体增强」门户（毕业设计示例）

目标：做一个风格参考北理工信息与电子学院门户（`sie.bit.edu.cn`）的学院门户站，但内容为**浙江工商大学信息与电子工程学院**公开信息，并在门户中加入多个**智能体（Agent）**用于咨询与信息处理，方便毕业论文撰写与展示。

本项目包含：

- `backend/`：FastAPI + SQLite，负责爬取/入库/提供文章 API、提供智能体对话 API（支持离线检索模式；可配置大模型升级为 RAG）
- `frontend/`：Vite + React + Tailwind，门户 UI（首页/栏目列表/文章详情/智能体中心）

## 运行方式

### 0)（可选）启动 MySQL（推荐）

如果你希望通知/新闻/聊天记录都持久化到 MySQL，可以在项目根目录使用 Docker 启动：

```bash
docker compose up -d
```

然后在 `backend/.env` 配置：

```bash
DATABASE_URL=mysql+aiomysql://root:root@127.0.0.1:3306/iee_portal?charset=utf8mb4
ADMIN_TOKEN=你自己设置一个口令
```

> 不使用 MySQL 时，保持默认 SQLite 也能运行。

### 1) 启动后端（端口 8002）

在 `d:\Graduation Project\backend`：

```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --port 8002
```

健康检查：

```bash
curl http://127.0.0.1:8002/api/health
```

### 2) 抓取内容入库

抓取通知公告（公示公告）：

```bash
curl -X POST http://127.0.0.1:8002/api/scrape -H "Content-Type: application/json" -d "{\"categories\":[\"notices\"],\"max_pages\":1}"
```

抓取学院新闻（从首页新闻流抓取）：

```bash
curl -X POST http://127.0.0.1:8002/api/scrape -H "Content-Type: application/json" -d "{\"categories\":[\"news\"],\"max_pages\":1}"
```

### 3) 启动前端（端口 5173）

在 `d:\Graduation Project\frontend`：

```bash
npm install
npm run dev
```

打开 `http://localhost:5173/`。

说明：前端开发时已在 `vite.config.ts` 配置了代理，`/api/*` 会转发到 `http://127.0.0.1:8002`。

## 智能体（Agents）

前端「智能体中心」对应后端：

- 列表：`GET /api/agents`
- 对话：`POST /api/agents/chat`

聊天消息会持久化到数据库（SQLite 或 MySQL），表：`chat_sessions`、`chat_messages`。

## 管理员更新（可选）

前端支持“更新内容”按钮，对应后端接口：

- `POST /api/admin/scrape`（需要请求头 `X-Admin-Token: <ADMIN_TOKEN>`）

默认是**离线检索模式**：基于已抓取的门户内容做 TF-IDF 检索，返回引用来源与建议。

### 配置大模型（可选）

后端支持 OpenAI-Compatible 接口（例如本地 Ollama 的 OpenAI 兼容模式或其他兼容服务）。

复制 `backend/.env.example` 为 `backend/.env` 并填入：

- `LLM_BASE_URL`
- `LLM_MODEL`
- `LLM_API_KEY`（如果需要）

然后重启后端。智能体会变为“检索增强生成（RAG）”。

## LangChain 与 MCP（论文展示向）

本项目后端已集成：

- **LangChain**：用于 OpenAI-compatible（含 DashScope compatible-mode）的大模型调用与提示编排（便于在论文中描述 LCEL/PromptTemplate/Chain 结构）。
- **MCP（Model Context Protocol）**：提供一个可运行的 MCP Server，把门户能力暴露为工具（tools），便于演示“外部智能体统一调用门户服务”。

### 启动 MCP Server（stdio）

在 `d:\Graduation Project\backend`：

```bash
python -m pip install -r requirements.txt
python -m app.mcp_server
```

MCP Server 提供的工具包括（名称可能随版本调整）：

- `search_articles`：按关键词检索文章
- `get_article`：按 ID 获取文章详情
- `assistant_chat`：调用学院智能助手（多智能体协作 + 可选 LLM）
- `purge_all_chats`：清空全部会话（演示用）
- `create_manual_article`：通过 MCP 发布手动文章（需要 `ADMIN_TOKEN`）

## 内容来源

当前爬取源站为浙江工商大学信息与电子工程学院官网（示例：`https://iee.zjgsu.edu.cn/`）。

