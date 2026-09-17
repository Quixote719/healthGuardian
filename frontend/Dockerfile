# 个人健康长寿多智能体系统 - 前端 Dockerfile
# Health Longevity Multi-Agent System - Frontend Dockerfile

FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 安装 pnpm (可选，如果项目使用 pnpm)
# RUN npm install -g pnpm

# 复制依赖文件
COPY package.json package-lock.json* ./

# 安装依赖
RUN npm ci

# 复制应用代码
COPY . .

# 构建参数 (用于生产构建)
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# 暴露端口
EXPOSE 3000

# 开发模式启动命令
CMD ["npm", "run", "dev"]

# 生产模式使用以下命令 (需要先构建)
# RUN npm run build
# CMD ["npm", "run", "start"]
