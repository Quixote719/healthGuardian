# 健康长寿智能助手 - 前端

基于 Next.js 14 (App Router) 的个人健康长寿多智能体系统前端应用。

## 技术栈

- **框架**: Next.js 14 (App Router)
- **UI 组件库**: shadcn/ui + Tailwind CSS
- **流式处理**: Vercel AI SDK (@ai-sdk/react)
- **Markdown 渲染**: react-markdown + remark-gfm
- **类型检查**: TypeScript

## 项目结构

```
frontend/
├── app/                    # Next.js App Router 页面
│   ├── layout.tsx         # 根布局
│   ├── page.tsx           # 首页
│   └── globals.css        # 全局样式
├── components/            # React 组件
│   └── ui/               # shadcn/ui 基础组件
├── hooks/                 # 自定义 React Hooks
├── lib/                   # 工具函数库
│   └── utils.ts          # 通用工具函数
├── types/                 # TypeScript 类型定义
│   └── index.ts          # 核心类型定义
└── public/               # 静态资源
```

## 开始使用

### 安装依赖

```bash
npm install
# 或
pnpm install
# 或
yarn install
```

### 开发服务器

```bash
npm run dev
# 或
pnpm dev
# 或
yarn dev
```

在浏览器中打开 [http://localhost:3000](http://localhost:3000) 查看结果。

### 构建生产版本

```bash
npm run build
npm run start
```

## 核心组件

### Insight_Card (待实现)
展示 AI 生成的深度健康洞察，支持 Markdown 渲染和骨架屏加载状态。

### Action_Plan_List (待实现)
按类别（营养、康复、神经心理）分组展示行动计划，支持折叠展开。

### HITL_Confirmation_Dialog (待实现)
高风险干预确认弹窗，包含10分钟倒计时和键盘交互支持。

## 环境变量

复制 `.env.example` 为 `.env.local` 并配置：

```bash
cp .env.example .env.local
```

| 变量 | 描述 | 默认值 |
|------|------|--------|
| BACKEND_URL | 后端 API 地址 | http://localhost:8000 |

## 与后端集成

前端通过 SSE (Server-Sent Events) 与后端通信，支持以下事件类型：
- `status`: 智能体处理状态更新
- `intermediate`: 中间结果
- `report`: 最终报告
- `pause`: HITL 暂停（等待用户确认）
- `error`: 错误信息
- `heartbeat`: 心跳保活

## 可访问性

本项目遵循 WCAG 2.1 AA 级可访问性标准：
- 使用语义化 HTML 标签
- 确保文本对比度不低于 4.5:1
- 支持键盘导航
- 提供适当的 ARIA 属性
