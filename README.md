# 吃神马（what2eat）

“吃神马”是一个有来源、会保存对话的中文菜谱 Agent。用户既可以与 Agent 对话，让它查询菜谱、推荐餐食和制定膳食计划，也可以按分类浏览菜谱、阅读完整做法、上传自己的资料并管理菜谱库。

项目内置 HowToCook 中文 Markdown 菜谱作为初始语料，使用 PostgreSQL 保存会话和文档状态，使用 Milvus Lite 与 BM25 完成混合检索，并通过 LangChain 调用大模型和工具。前端由 Vue 3 构建，聊天结果通过 SSE 实时返回。

## 功能特性

- 创建、切换、重命名和删除对话，会话内容持久化保存。
- 查询全部菜谱、按分类找菜、随机推荐以及生成 7 天膳食计划。
- 分页浏览菜谱，在详情页阅读 Markdown 原文并查看原始来源。
- 从菜谱详情底部删除菜谱，同时清理源文件、数据库记录和检索索引。
- 上传 `.md`、`.txt`、`.pdf`、`.docx` 文件并自动建立索引，单文件最大 10 MiB。
- 使用 DeepSeek 大模型、阿里云百炼 Embedding、Milvus Lite 和 BM25 混合检索。
- PostgreSQL 保存会话、消息、运行状态、来源快照和长期偏好。

## 技术栈

- 后端：Python 3.13、FastAPI、Pydantic、LangChain、Psycopg
- 数据：PostgreSQL 17、Milvus Lite、BM25
- 模型：DeepSeek `deepseek-flash`、阿里云百炼 `text-embedding-v4`
- 前端：Vue 3、TypeScript、Vite
- 通信：REST API、Server-Sent Events（SSE）

项目只使用 LangChain，不使用 LlamaIndex。

## 系统架构

```mermaid
flowchart LR
    U[用户浏览器] -->|Vue 3 / REST| F[前端应用]
    F -->|HTTP API| A[FastAPI]
    A -->|SSE 流式响应| F

    subgraph Backend[后端服务]
        A --> C[会话与消息服务]
        A --> R[菜谱目录]
        A --> G[LangChain Agent]
        A --> I[文档索引服务]
        G --> T[菜谱查询 / 推荐 / 规划工具]
        T --> R
        T --> H[混合检索器]
        I --> H
    end

    C --> P[(PostgreSQL)]
    R --> P
    I --> P
    G --> L[DeepSeek LLM]
    I --> E[百炼 Embedding]
    H --> M[(Milvus Lite)]
    H --> B[BM25 内存索引]
    D[内置语料 / 用户上传] --> I
```

典型请求流程如下：

1. 前端创建会话并将用户问题发送到聊天接口。
2. Agent 根据问题调用菜谱目录、检索或膳食规划工具。
3. 检索器组合 Milvus 向量结果与 BM25 关键词结果，并校验文档状态。
4. 大模型生成带来源的答案，后端通过 SSE 持续推送给前端。

## 安装与运行

### 1. 环境要求

- Python 3.13
- Node.js 20+ 与 npm
- Docker Desktop 或兼容的 Docker Compose 环境
- DeepSeek API Key
- 阿里云百炼 Embedding API Key 与对应地域的 OpenAI 兼容端点

### 2. 获取代码

```bash
git clone https://github.com/stillfantasy0321/what2eat.git
cd what2eat
```

### 3. 安装后端依赖

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

macOS / Linux：

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### 4. 安装前端依赖

```bash
cd frontend
npm ci
cd ..
```

### 5. 配置环境变量

复制示例配置：

```powershell
Copy-Item .env.example .env
```

macOS / Linux 使用：

```bash
cp .env.example .env
```

编辑 `.env`，至少填写以下内容：

```dotenv
POSTGRES_PASSWORD=请设置本地数据库密码
DATABASE_URL=postgresql://what2eat:请设置本地数据库密码@127.0.0.1:55432/what2eat

LLM_API_KEY=你的_DeepSeek_API_Key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-flash

EMBEDDING_API_KEY=你的百炼_API_Key
EMBEDDING_BASE_URL=与你的百炼地域对应的兼容端点
EMBEDDING_REGION_CONFIRMED=true
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSIONS=1024

# 留空时使用项目目录下的 var/milvus.db
MILVUS_URI=
```

请勿提交包含真实密钥的 `.env`。如果数据库密码包含 `@`、`:` 等特殊字符，需要在 `DATABASE_URL` 中进行 URL 编码。

### 6. 启动 PostgreSQL 并初始化数据库

```bash
docker compose up -d postgres
python -m what2eat.db.migrate
```

数据库迁移需要在首次运行时执行；后续新增迁移后也应重新执行该命令。

### 7. 启动开发环境

在项目根目录启动后端：

```bash
python -m what2eat --reload
```

后端默认监听 `http://127.0.0.1:8000`，交互式 API 文档位于 `http://127.0.0.1:8000/docs`。

另开一个终端启动前端：

```bash
cd frontend
npm run dev
```

浏览器访问 Vite 输出的地址，默认是 `http://127.0.0.1:5173`。开发服务器会把 `/api` 请求代理到后端的 `8000` 端口。

### 8. 导入内置菜谱

所有服务就绪后执行一次：

```bash
curl -X POST http://127.0.0.1:8000/api/knowledge/import
```

Windows PowerShell 可使用 `curl.exe`：

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/knowledge/import
```

接口返回 `202 Accepted` 后会在后台建立索引。可通过 `GET /api/documents` 查看每份文档的 `state`；状态变为 `ready` 后，菜谱会出现在列表中。

### 9. 生产方式运行

先构建前端，再启动后端：

```bash
cd frontend
npm run build
cd ..
python -m what2eat --host 0.0.0.0 --port 8000
```

当 `frontend/dist` 存在时，FastAPI 会直接提供前端静态文件。访问 `http://127.0.0.1:8000` 即可使用完整应用。

## API 接口说明

所有业务错误均使用统一结构：

```json
{
  "error": {
    "code": "document_not_found",
    "message": "文档不存在。",
    "request_id": "请求追踪 ID"
  }
}
```

### 服务状态与诊断

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/status` | 查看数据库、LLM、Embedding 和向量索引的就绪状态 |
| `POST` | `/api/diagnostics/models` | 调用一次模型进行连通性诊断，可能产生模型费用 |

### 会话

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/sessions?limit=30` | 获取会话列表，`limit` 范围为 1–100 |
| `POST` | `/api/sessions` | 创建会话，返回 `201 Created` |
| `GET` | `/api/sessions/{session_id}` | 获取单个会话 |
| `PATCH` | `/api/sessions/{session_id}` | 修改会话标题 |
| `DELETE` | `/api/sessions/{session_id}` | 删除会话及其消息，返回 `204 No Content` |
| `GET` | `/api/sessions/{session_id}/messages` | 分页读取消息，支持 `before_seq` 和 `limit` |

### 聊天

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/chat` | 启动一次 Agent 对话，以 `text/event-stream` 返回 SSE 事件 |

请求体字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `session_id` | UUID | 已存在的会话 ID |
| `request_id` | UUID | 本次请求的唯一 ID，重试同一请求时保持不变 |
| `message` | string | 用户问题，长度为 1–4000 字符 |

### 菜谱

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/recipes` | 分页获取菜谱；支持 `category`、`page`、`page_size` |
| `GET` | `/api/recipes/categories` | 获取当前可用分类 |
| `GET` | `/api/recipes/{recipe_id}` | 获取菜谱详情 |
| `DELETE` | `/api/recipes/{recipe_id}` | 删除菜谱，返回 `202 Accepted` 并在后台清理索引和源文件 |

`page` 从 1 开始，`page_size` 范围为 1–50。只有索引状态为 `ready` 的文档会作为菜谱返回。

### 文档与知识库

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/documents` | 分页获取文档及索引状态 |
| `POST` | `/api/documents` | 上传文档，使用 `multipart/form-data` 的 `file` 字段 |
| `GET` | `/api/documents/{document_id}` | 获取文档元数据及可直接读取的文本内容 |
| `GET` | `/api/documents/{document_id}/content` | 获取统一提取后的文档正文 |
| `POST` | `/api/documents/{document_id}/retry` | 重试失败的索引或删除任务 |
| `DELETE` | `/api/documents/{document_id}` | 删除文档并异步清理索引，返回 `202 Accepted` |
| `POST` | `/api/knowledge/import` | 导入项目内置菜谱并异步建立索引 |

文档状态包括 `pending`、`indexing`、`ready`、`failed` 和 `deleting`。

## API 使用示例

以下示例假设后端运行在 `http://127.0.0.1:8000`。PowerShell 用户可将 `curl` 替换为 `curl.exe`。

### 检查服务状态

```bash
curl http://127.0.0.1:8000/api/status
```

### 创建会话

```bash
curl -X POST http://127.0.0.1:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"title":"今晚吃什么"}'
```

响应中的 `id` 是后续聊天所需的 `session_id`。

### 发起 SSE 对话

先生成一个新的 `request_id`，再调用聊天接口：

```bash
curl -N -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id":"替换为会话 UUID",
    "request_id":"替换为新的 UUID",
    "message":"推荐三道适合工作日晚餐的菜"
  }'
```

`-N` 用于关闭 curl 输出缓冲，以便实时看到 SSE 事件。

### 查询菜谱

```bash
curl "http://127.0.0.1:8000/api/recipes?category=荤菜&page=1&page_size=12"
```

如果分类名包含空格或特殊字符，请进行 URL 编码。

### 删除菜谱

```bash
curl -X DELETE http://127.0.0.1:8000/api/recipes/替换为菜谱UUID
```

成功响应示例：

```json
{
  "queued": true,
  "recipe_id": "菜谱 UUID"
}
```

### 上传自定义资料

```bash
curl -X POST http://127.0.0.1:8000/api/documents \
  -F "file=@./我的菜谱.md"
```

上传成功后接口返回 `202 Accepted`。使用文档列表接口检查索引结果：

```bash
curl "http://127.0.0.1:8000/api/documents?page=1&page_size=12"
```

## 测试与构建

运行后端测试：

```bash
python -m pytest
```

检查并构建前端：

```bash
cd frontend
npm run build
```

## 许可证与语料来源

项目内置菜谱语料来自 HowToCook，具体来源和许可证信息见 `data/corpus/manifest.json` 与 `data/corpus/LICENSE`。使用第三方模型和云服务时，还需遵守对应服务商的使用条款与计费规则。
