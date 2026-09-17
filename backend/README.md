# 个人健康长寿多智能体系统后端

基于 LangGraph 的多智能体编排系统，结合 LlamaIndex 知识检索能力，为用户提供跨学科的健康干预方案。

## 技术栈

- **Web 框架**: FastAPI
- **多智能体编排**: LangGraph
- **知识检索**: LlamaIndex
- **数据验证**: Pydantic v2
- **向量存储**: ChromaDB
- **图数据库**: Neo4j

## 项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── models/              # Pydantic 数据模型
│   │   ├── user_profile.py  # 用户画像模型
│   │   ├── action_item.py   # 干预措施模型
│   │   ├── final_report.py  # 最终报告模型
│   │   ├── state.py         # LangGraph 状态模型
│   │   └── api.py           # API 请求/响应模型
│   ├── agents/              # 智能体实现
│   │   ├── base.py          # 智能体基类
│   │   ├── controller.py    # 主控智能体
│   │   ├── nutrition.py     # 营养学专家
│   │   ├── rehabilitation.py # 运动康复专家
│   │   ├── neuropsychology.py # 神经心理专家
│   │   └── synthesis.py     # 综合反思智能体
│   ├── tools/               # RAG 工具
│   │   ├── rag_interface.py # RAG 接口定义
│   │   ├── markdown_rag.py  # Markdown RAG 实现
│   │   └── graph_rag.py     # Graph RAG 实现
│   ├── workflow/            # LangGraph 工作流
│   │   ├── graph.py         # 工作流图定义
│   │   └── hitl.py          # HITL 中断/恢复机制
│   ├── api/                 # API 端点
│   │   ├── routes/
│   │   │   ├── chat.py      # 流式聊天 API
│   │   │   └── confirm.py   # HITL 确认 API
│   │   └── sse_manager.py   # SSE 事件管理器
│   ├── core/                # 核心功能
│   │   ├── config.py        # 配置管理
│   │   ├── exceptions.py    # 自定义异常
│   │   └── error_handler.py # 异常处理器
│   └── services/            # 业务服务
│       └── user_profile.py  # 用户画像服务
├── tests/                   # 测试目录
│   ├── conftest.py          # 测试配置
│   ├── test_models/         # 模型测试
│   ├── test_agents/         # 智能体测试
│   └── test_api/            # API 测试
├── scripts/                 # 脚本目录
│   └── build_index.py       # 索引构建脚本
├── data/                    # 数据目录 (gitignore)
│   ├── knowledge/           # 知识库文档
│   ├── chroma_db/           # ChromaDB 持久化
│   └── checkpoints/         # LangGraph 检查点
├── pyproject.toml           # Poetry 配置
├── .env.example             # 环境变量模板
└── README.md                # 本文件
```

## 快速开始

### 1. 安装依赖

```bash
# 使用 Poetry 安装
cd backend
poetry install
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入实际配置
```

### 3. 启动开发服务器

```bash
poetry run uvicorn app.main:app --reload --port 8000
```

### 4. 运行测试

```bash
# 运行所有测试
poetry run pytest

# 运行带覆盖率的测试
poetry run pytest --cov=app

# 运行属性测试
poetry run pytest tests/ -k "property"
```

## API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/chat` | POST | 流式聊天 (SSE) |
| `/api/confirm` | POST | HITL 确认/拒绝 |

## 开发指南

### 代码风格

项目使用 Ruff 进行代码检查和格式化：

```bash
# 检查代码
poetry run ruff check .

# 格式化代码
poetry run ruff format .
```

### 类型检查

```bash
poetry run mypy app
```

## License

MIT
