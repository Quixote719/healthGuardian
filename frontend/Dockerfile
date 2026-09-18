# 个人健康多智能体系统 - 前端 Dockerfile
# Health Multi-Agent System - Frontend Dockerfile

FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 安装 pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# 复制依赖文件
COPY package.json pnpm-lock.yaml* ./

# 安装依赖
RUN pnpm install --frozen-lockfile

# 复制应用代码
COPY . .

# 构建参数 (用于生产构建)
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# 暴露端口
EXPOSE 3000

# 开发模式启动命令
CMD ["pnpm", "dev"]

# 生产模式使用以下命令 (需要先构建)
# RUN pnpm build
# CMD ["pnpm", "start"]
