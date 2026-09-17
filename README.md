# 个人健康长寿多智能体系统

Health Longevity Multi-Agent System

基于 LangGraph 的多智能体编排系统，结合 LlamaIndex 知识检索能力，为用户提供跨学科的健康干预方案。

## 系统架构

```
healthLab/
├── backend/                 # Python 后端 (FastAPI + LangGraph + LlamaIndex)
│   ├── app/                # 应用代码
│   │   ├── agents/        # 智能体实现
│   │   ├── api/           # API 路由
│   │   ├── core/          # 核心工具
│   │   ├── models/        # Pydantic 数据模型
│   │   ├── services/      # 服务层
│   │   ├── tools/         # RAG 工具
│   │   └── workflow/      # LangGraph 工作流
│   ├── tests/             # 测试文件
│   └── scripts/           # 脚本工具
├── frontend/               # Next.js 前端 (React + Vercel AI SDK)
│   ├── app/               # Next.js App Router
│   ├── components/        # React 组件
│   ├── hooks/             # 自定义 Hooks
│   ├── lib/               # 工具函数
│   └── types/             # TypeScript 类型定义
└── docker-compose.yml      # 容器化开发配置
```

## 技术栈

### 后端
- **框架**: FastAPI
- **智能体编排**: LangGraph
- **知识检索**: LlamaIndex (MarkdownNodeParser, KnowledgeGraphIndex)
- **数据验证**: Pydantic v2
- **向量存储**: ChromaDB
- **图数据库**: Neo4j

### 前端
- **框架**: Next.js 14 (App Router)
- **UI 组件**: shadcn/ui + Tailwind CSS
- **流式处理**: Vercel AI SDK
- **Markdown 渲染**: react-markdown

## 开发环境设置

### 前置要求

- **Python**: 3.11+
- **Node.js**: 18+
- **Poetry**: Python 包管理器
- **Docker**: (可选) 用于运行 ChromaDB 和 Neo4j

### 方式一：本地开发

#### 1. 后端设置

```bash
# 进入后端目录
cd backend

# 安装依赖
poetry install

# 复制环境变量文件
cp .env.example .env

# 编辑 .env 文件，配置以下关键变量:
# - OPENAI_API_KEY: OpenAI API 密钥
# - NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD: Neo4j 连接信息

# 启动后端服务 (开发模式)
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端服务将在 http://localhost:8000 运行

- API 文档: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

#### 2. 前端设置

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 复制环境变量文件 (如果不存在)
cp .env.example .env.local

# .env.local 默认配置:
# NEXT_PUBLIC_API_URL=http://localhost:8000

# 启动前端服务 (开发模式)
npm run dev
```

前端服务将在 http://localhost:3000 运行

### 方式二：Docker 容器化开发

使用 Docker Compose 一键启动所有服务：

```bash
# 在项目根目录运行
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

服务地址：
- 前端: http://localhost:3000
- 后端 API: http://localhost:8000
- ChromaDB: http://localhost:8001
- Neo4j Browser: http://localhost:7474
- Neo4j Bolt: bolt://localhost:7687

## API 端点

### 聊天 API (SSE 流式)

```http
POST /api/chat
Content-Type: application/json

{
  "user_query": "我最近血脂偏高，睡眠质量差，请给我一些建议",
  "user_profile_id": "user_123"
}
```

响应为 Server-Sent Events 流，包含以下事件类型：
- `status`: 处理状态更新
- `intermediate`: 中间结果
- `report`: 最终报告
- `pause`: HITL 暂停等待确认
- `error`: 错误信息
- `heartbeat`: 心跳保持连接

### HITL 确认 API

```http
POST /api/confirm
Content-Type: application/json

{
  "session_id": "sess_abc123",
  "confirmed": true
}
```

## 开发命令

### 后端

```bash
cd backend

# 运行测试
poetry run pytest

# 运行测试并生成覆盖率报告
poetry run pytest --cov=app --cov-report=html

# 代码格式化
poetry run ruff format .

# 代码检查
poetry run ruff check .

# 类型检查
poetry run mypy app
```

### 前端

```bash
cd frontend

# 开发模式
npm run dev

# 构建生产版本
npm run build

# 运行生产版本
npm run start

# 代码检查
npm run lint
```

## 环境变量说明

### 后端 (.env)

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | - |
| `OPENAI_MODEL` | LLM 模型 | gpt-4-turbo-preview |
| `NEO4J_URI` | Neo4j 连接地址 | bolt://localhost:7687 |
| `NEO4J_USER` | Neo4j 用户名 | neo4j |
| `NEO4J_PASSWORD` | Neo4j 密码 | - |
| `CHROMA_PERSIST_DIR` | ChromaDB 存储路径 | ./data/chroma_db |
| `AGENT_TIMEOUT_SECONDS` | 智能体超时时间 | 30 |
| `HITL_TIMEOUT_MINUTES` | HITL 确认超时 | 10 |

### 前端 (.env.local)

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `NEXT_PUBLIC_API_URL` | 后端 API 地址 | http://localhost:8000 |

## 项目结构说明

### 智能体节点

1. **Controller_Agent**: 主控智能体，任务拆解和风险检测
2. **Nutrition_Agent**: 营养学专家，提供饮食和补剂建议
3. **Rehabilitation_Agent**: 运动康复专家，提供运动方案
4. **Neuropsychology_Agent**: 神经心理专家，提供心理干预建议
5. **Synthesis_Agent**: 综合反思，整合建议并安全检查

### 数据模型

- **User_Profile**: 用户健康画像
- **Action_Item**: 干预措施
- **Final_Report**: 最终报告
- **Health_State**: LangGraph 工作流状态

## 常见问题

### Q: 前端连接后端失败？

1. 确认后端服务正在运行 (http://localhost:8000/health)
2. 检查 frontend/.env.local 中的 NEXT_PUBLIC_API_URL 配置
3. 确认 CORS 配置允许前端域名

### Q: RAG 检索返回空结果？

1. 确认已运行索引构建脚本
2. 检查 ChromaDB 服务状态
3. 确认知识库文档已正确放置

### Q: Neo4j 连接失败？

1. 确认 Neo4j 服务正在运行
2. 检查连接凭据是否正确
3. 确认 Bolt 端口 (7687) 可访问

## 许可证

MIT License
