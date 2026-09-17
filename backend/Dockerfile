# 个人健康多智能体系统 - 后端 Dockerfile
# Health Multi-Agent System - Backend Dockerfile

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 Poetry
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VERSION=1.7.1
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

# 配置 Poetry 不创建虚拟环境
ENV POETRY_VIRTUALENVS_CREATE=false

# 复制依赖文件
COPY pyproject.toml poetry.lock* ./

# 安装依赖
RUN poetry install --no-interaction --no-ansi --no-root

# 复制应用代码
COPY . .

# 安装应用
RUN poetry install --no-interaction --no-ansi

# 创建数据目录
RUN mkdir -p /app/data/chroma_db /app/data/checkpoints

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
