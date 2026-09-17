# Implementation Plan: 个人健康长寿多智能体系统

## Overview

本任务列表将设计文档转化为可执行的实现步骤，采用后端先行、前端跟进的开发顺序。后端使用 Python (FastAPI + LangGraph + LlamaIndex + Pydantic)，前端使用 TypeScript (Next.js + Vercel AI SDK + shadcn/ui)。任务按照依赖关系排序，确保增量开发和持续验证。

## Tasks

- [x] 1. 后端项目初始化与基础设施搭建
  - [x] 1.1 创建 Python 后端项目结构
    - 创建 `backend/` 目录，包含 `app/`、`tests/`、`scripts/` 子目录
    - 创建 `app/` 下的模块目录：`models/`、`agents/`、`tools/`、`workflow/`、`api/`、`core/`、`services/`
    - 创建 `pyproject.toml` 配置文件，使用 Poetry 管理依赖
    - 添加核心依赖：fastapi, uvicorn, pydantic, langgraph, llama-index, chromadb, neo4j, pytest, hypothesis
    - 创建 `.env.example` 环境变量模板文件
    - _Requirements: 全局基础设施_
  
  - [x] 1.2 配置 FastAPI 应用入口
    - 创建 `app/main.py`，初始化 FastAPI 应用
    - 配置 CORS 中间件，允许跨域请求
    - 配置全局异常处理器
    - 添加健康检查端点 `/health`
    - _Requirements: 13.1, 14.11_
    - _Design: Components and Interfaces - FastAPI 应用入口_

- [x] 2. Pydantic 数据模型实现
  - [x] 2.1 实现 User_Profile 数据模型
    - 创建 `app/models/user_profile.py`
    - 实现所有枚举类型：Gender, DiseaseStatus, MedicationFrequency, ExerciseFrequency, DietHabit
    - 实现嵌套模型：MedicalHistory, Medication, BloodLipids, BloodGlucose, PhysicalExamination, Lifestyle
    - 实现 UserProfile 主模型，包含所有字段验证和 BMI 计算属性
    - _Requirements: 1.1-1.7_
    - _Design: Data Models - User_Profile 模型_
  
  - [ ]* 2.2 编写 User_Profile 属性测试
    - **Property P1: User_Profile 数值范围验证**
    - **Property P2: User_Profile 列表长度约束**
    - **Property P3: Pydantic 模型 JSON 序列化往返**
    - **Validates: Requirements 1.1-1.7**
  
  - [x] 2.3 实现 Action_Item 数据模型
    - 创建 `app/models/action_item.py`
    - 实现枚举类型：ActionCategory, Priority, RiskLevel
    - 实现 ActionItem 模型，包含 duration 格式验证器
    - _Requirements: 2.1-2.9_
    - _Design: Data Models - Action_Item 模型_
  
  - [ ]* 2.4 编写 Action_Item 属性测试
    - **Property P4: Action_Item 字段验证**
    - **Validates: Requirements 2.1-2.9**
  
  - [x] 2.5 实现 Final_Report 数据模型
    - 创建 `app/models/final_report.py`
    - 实现 ConfirmationStatus 枚举
    - 实现 FinalReport 模型，包含所有字段和验证
    - _Requirements: 3.1-3.8_
    - _Design: Data Models - Final_Report 模型_
  
  - [x] 2.6 实现 Health_State 状态模型
    - 创建 `app/models/state.py`
    - 实现辅助模型：SubTask, ErrorInfo
    - 实现枚举：TargetAgent, NodeExecutionStatus
    - 实现 HealthState TypedDict，兼容 LangGraph 状态模式
    - _Requirements: 4.1-4.10_
    - _Design: Data Models - Health_State 模型_
  
  - [x] 2.7 实现 API 请求/响应模型
    - 创建 `app/models/api.py`
    - 实现 ChatRequest, ChatResponse, ConfirmRequest, ConfirmResponse
    - 实现 SSE 事件数据模型：StatusEventData, PauseEventData, ErrorEventData
    - _Requirements: 13.2, 14.2_
    - _Design: Data Models - API 请求/响应模型_

- [x] 3. Checkpoint - 数据模型验证
  - 确保所有数据模型通过单元测试和属性测试
  - 验证 JSON 序列化/反序列化正确性
  - 确保所有测试通过，ask the user if questions arise.

- [x] 4. 异常处理和核心工具
  - [x] 4.1 实现自定义异常类
    - 创建 `app/core/exceptions.py`
    - 实现 HealthSystemError 基类
    - 实现具体异常：AgentTimeoutError, RAGQueryError, SessionNotFoundError, SessionTimeoutError
    - _Design: Error Handling - 错误分类与处理策略_
  
  - [x] 4.2 实现全局异常处理器
    - 创建 `app/core/error_handler.py`
    - 实现 FastAPI 异常处理器注册
    - 在 `app/main.py` 中注册异常处理器
    - _Design: Error Handling - 错误处理代码_

- [x] 5. RAG 工具实现
  - [x] 5.1 定义 RAG 接口基类
    - 创建 `app/tools/rag_interface.py`
    - 定义 RAGResult 数据模型
    - 定义 RAGInterface 抽象基类，包含 query() 和 health_check() 方法
    - _Requirements: 11.3, 12.3_
    - _Design: Components and Interfaces - RAG 工具接口_
  
  - [x] 5.2 实现 Markdown RAG 检索工具
    - 创建 `app/tools/markdown_rag.py`
    - 使用 LlamaIndex MarkdownNodeParser 解析文档（chunk_size=512, overlap=50）
    - 使用 ChromaDB 作为向量存储后端
    - 实现 build_index() 方法构建向量索引
    - 实现 query() 方法，支持 top_k 和 similarity_threshold 参数
    - 实现类别过滤（营养学/运动康复）
    - _Requirements: 11.1-11.6_
    - _Design: RAG 工具设计 - Markdown RAG 实现_
  
  - [ ]* 5.3 编写 Markdown RAG 集成测试
    - 测试索引构建和检索功能
    - 测试相似度阈值过滤
    - 测试类别过滤
    - _Requirements: 11.3-11.6_
  
  - [x] 5.4 实现 Graph RAG 检索工具
    - 创建 `app/tools/graph_rag.py`
    - 使用 LlamaIndex KnowledgeGraphIndex 构建图谱索引
    - 使用 Neo4j 作为图数据库后端
    - 实现 build_index() 方法
    - 实现 query() 方法，支持多跳查询（最大3跳）和10秒超时
    - 实现结构化结果返回（实体列表、关系列表）
    - _Requirements: 12.1-12.7_
    - _Design: RAG 工具设计 - Graph RAG 实现_
  
  - [ ]* 5.5 编写 Graph RAG 集成测试
    - 测试图谱索引构建
    - 测试多跳关系查询
    - 测试超时处理
    - _Requirements: 12.3-12.7_

- [x] 6. Checkpoint - RAG 工具验证
  - 确保 Markdown RAG 和 Graph RAG 工具正常工作
  - 验证与 ChromaDB 和 Neo4j 的连接
  - 确保所有测试通过，ask the user if questions arise.

- [x] 7. 智能体基类和辅助函数
  - [x] 7.1 实现智能体基类
    - 创建 `app/agents/base.py`
    - 定义 BaseAgent 抽象基类
    - 定义 name 属性、process() 方法、get_system_prompt() 方法
    - _Design: Components and Interfaces - 智能体节点接口_
  
  - [x] 7.2 实现高风险/禁止关键词检测函数
    - 创建 `app/agents/risk_detector.py`
    - 实现 detect_high_risk_keywords() 函数
    - 实现 detect_prohibited_keywords() 函数
    - 实现 detect_out_of_scope() 函数
    - _Requirements: 5.3, 5.4, 8.7_
  
  - [ ]* 7.3 编写关键词检测属性测试
    - **Property P5: 高风险/禁止关键词检测**
    - **Validates: Requirements 5.3, 5.4, 8.7**
  
  - [x] 7.4 实现健康指标检测辅助函数
    - 创建 `app/agents/health_analyzer.py`
    - 实现 detect_lipid_abnormality() 血脂异常检测
    - 实现 detect_glucose_abnormality() 血糖异常检测
    - 实现 get_exercise_intensity_by_age() 年龄-运动强度匹配
    - 实现 get_intensity_adjustment_by_bmi() BMI 强度调整
    - 实现 check_medical_contraindications() 禁忌病史检查
    - 实现 get_stress_intervention_level() 压力等级-干预策略匹配
    - 实现 evaluate_sleep_duration() 睡眠时长评估
    - _Requirements: 6.3, 6.4, 7.2, 7.3, 7.6, 8.2, 8.3_
  
  - [ ]* 7.5 编写健康指标检测属性测试
    - **Property P6: 血脂血糖异常检测**
    - **Property P8: 年龄-运动强度匹配**
    - **Property P9: BMI 计算与强度调整**
    - **Property P10: 禁忌病史排除运动**
    - **Property P11: 压力等级-干预策略匹配**
    - **Property P12: 睡眠时长评估**
    - **Validates: Requirements 6.3, 6.4, 7.2, 7.3, 7.6, 8.2, 8.3**

- [x] 8. 智能体节点实现
  - [x] 8.1 实现 Controller_Agent 主控智能体
    - 创建 `app/agents/controller.py`
    - 继承 BaseAgent 基类
    - 实现任务拆解逻辑，将请求分解为营养、康复、神经心理三个维度
    - 调用风险检测函数，设置 ui_interrupt_flag
    - 检测超出范围的请求，返回建议寻求专业帮助
    - 实现30秒超时处理
    - _Requirements: 5.1-5.5_
    - _Design: LangGraph 工作流设计_
  
  - [x] 8.2 实现 Nutrition_Agent 营养学专家智能体
    - 创建 `app/agents/nutrition.py`
    - 继承 BaseAgent 基类
    - 调用 Markdown_RAG 检索营养学知识库（10秒超时）
    - 根据血脂血糖阈值生成针对性建议
    - 检测药物-食物交互，附加警告信息
    - 输出 3-5 个 Action_Item，category 设置为"营养"
    - _Requirements: 6.1-6.7_
  
  - [ ]* 8.3 编写 Nutrition_Agent 药物交互属性测试
    - **Property P7: 药物交互警告触发**
    - **Validates: Requirements 6.5**
  
  - [x] 8.4 实现 Rehabilitation_Agent 运动康复专家智能体
    - 创建 `app/agents/rehabilitation.py`
    - 继承 BaseAgent 基类
    - 调用 Markdown_RAG 检索运动康复知识库
    - 根据年龄和 BMI 调整运动强度
    - 根据禁忌病史排除对应运动类型
    - 输出 3-5 个 Action_Item，category 设置为"康复"
    - _Requirements: 7.1-7.6_
  
  - [x] 8.5 实现 Neuropsychology_Agent 神经心理调节专家智能体
    - 创建 `app/agents/neuropsychology.py`
    - 继承 BaseAgent 基类
    - 调用 Graph_RAG 检索心理神经免疫学知识图谱
    - 根据压力等级匹配干预策略
    - 根据睡眠时长生成相应干预
    - 区分硬件层和软件层干预输出
    - 检测禁止关键词，拒绝提供干预并返回建议
    - _Requirements: 8.1-8.8_
  
  - [x] 8.6 实现 Synthesis_Agent 综合反思与安全检查智能体
    - 创建 `app/agents/synthesis.py`
    - 继承 BaseAgent 基类
    - 读取所有 expert_responses 并整合
    - 生成 deep_insight（健康现状、跨学科关联、核心问题归因、干预逻辑）
    - 实现 Action_Item 去重逻辑（title 相同或 description 相似度 > 80%）
    - 检测干预冲突（药物-营养、运动-病史、措施矛盾）
    - 检测高风险干预组合，设置 requires_confirmation
    - 根据风险等级生成随访计划
    - 构建完整 Final_Report
    - _Requirements: 9.1-9.7_
  
  - [ ]* 8.7 编写 Synthesis_Agent 去重和风险检测属性测试
    - **Property P13: Action_Item 去重**
    - **Property P14: 高风险组合检测**
    - **Property P15: 风险等级-随访计划映射**
    - **Validates: Requirements 9.3, 9.5, 9.6**

- [x] 9. Checkpoint - 智能体验证
  - 确保所有5个智能体节点正确实现
  - 验证智能体与 RAG 工具的集成
  - 验证风险检测和业务逻辑正确性
  - 确保所有测试通过，ask the user if questions arise.

- [x] 10. LangGraph 工作流编排
  - [x] 10.1 实现 LangGraph 工作流图
    - 创建 `app/workflow/graph.py`
    - 使用 StateGraph 创建工作流
    - 添加5个智能体节点
    - 设置入口点为 controller
    - 实现条件路由：controller 后检查 ui_interrupt_flag
    - 配置并行执行：nutrition, rehabilitation, neuropsychology 同时执行
    - 实现 synthesis 后的条件路由：检查 requires_confirmation
    - 配置 checkpointer 持久化（SqliteSaver/PostgresSaver）
    - _Requirements: 10.1-10.3_
    - _Design: LangGraph 工作流设计_
  
  - [x] 10.2 实现 HITL Interrupt/Resume 机制
    - 创建 `app/workflow/hitl.py`
    - 实现 HITLManager 类
    - 实现 pause_workflow() 暂停工作流
    - 实现 resume_workflow() 恢复工作流
    - 实现 check_timeout() 检查会话超时
    - 实现30分钟最长暂停时间限制
    - 实现自动终止超时会话
    - _Requirements: 10.3-10.6_
    - _Design: HITL Interrupt/Resume 机制_
  
  - [x] 10.3 实现工作流超时和异常处理
    - 在工作流中配置单个智能体30秒超时
    - 实现超时智能体的终止和状态记录
    - 实现异常捕获和错误信息记录
    - 确保单个智能体失败不影响其他智能体执行
    - _Requirements: 10.7, 10.8_
  
  - [ ]* 10.4 编写工作流集成测试
    - 测试完整工作流执行
    - 测试并行执行顺序
    - 测试 HITL 中断和恢复
    - 测试超时处理
    - _Requirements: 10.1-10.8_

- [x] 11. Checkpoint - 工作流验证
  - 确保 LangGraph 工作流正确编排
  - 验证 HITL 机制正常工作
  - 验证超时和异常处理
  - 确保所有测试通过，ask the user if questions arise.

- [x] 12. FastAPI API 端点实现
  - [x] 12.1 实现 SSE 事件管理器
    - 创建 `app/api/sse_manager.py`
    - 实现 SSEEventType 枚举
    - 实现 SSEEvent 数据模型
    - 实现 SSEManager 类
    - 实现 create_stream() 创建事件流
    - 实现 emit_event() 发送事件
    - 实现15秒心跳机制
    - _Requirements: 13.3-13.9_
    - _Design: Components and Interfaces - SSE 事件管理器接口_
  
  - [x] 12.2 实现 /chat 流式聊天 API
    - 创建 `app/api/routes/chat.py`
    - 实现 POST /api/chat 端点
    - 接收 ChatRequest（user_query, user_profile_id）
    - 生成 session_id
    - 调用工作流并生成 SSE 事件流
    - 实时推送 status、intermediate、report、pause、error、heartbeat 事件
    - 配置 StreamingResponse 响应头
    - _Requirements: 13.1-13.9_
    - _Design: API 设计 - 流式聊天 API_
  
  - [x] 12.3 实现 /confirm HITL 确认 API
    - 创建 `app/api/routes/confirm.py`
    - 实现 POST /api/confirm 端点
    - 接收 ConfirmRequest（session_id, confirmed）
    - 验证会话存在且处于暂停状态
    - 处理确认/拒绝响应
    - 实现10分钟超时检查
    - 返回 ConfirmResponse
    - _Requirements: 14.1-14.11_
    - _Design: API 设计 - HITL 确认 API_
  
  - [x] 12.4 实现用户画像服务
    - 创建 `app/services/user_profile.py`
    - 实现 get_user_profile() 函数
    - 实现用户画像存储和检索逻辑
    - _Requirements: 1.1-1.7_
  
  - [x] 12.5 注册 API 路由
    - 在 `app/main.py` 中注册 chat 和 confirm 路由
    - 配置路由前缀 /api
    - _Requirements: 13.1, 14.1_
  
  - [ ]* 12.6 编写 API 端点集成测试
    - 测试 /chat 端点 SSE 流
    - 测试 /confirm 端点确认/拒绝流程
    - 测试错误响应
    - _Requirements: 13.1-13.9, 14.1-14.11_

- [x] 13. Checkpoint - 后端 API 验证
  - 确保所有 API 端点正常工作
  - 验证 SSE 流式输出正确性
  - 验证 HITL 确认流程
  - 确保所有测试通过，ask the user if questions arise.

- [x] 14. 前端项目初始化
  - [x] 14.1 创建 Next.js 前端项目
    - 创建 `frontend/` 目录
    - 使用 create-next-app 初始化 Next.js 14 项目（App Router）
    - 安装依赖：tailwindcss, shadcn/ui, @ai-sdk/react, react-markdown
    - 配置 Tailwind CSS
    - 初始化 shadcn/ui 组件库
    - _Requirements: 17.8_
    - _Design: 核心技术栈_
  
  - [x] 14.2 定义 TypeScript 类型
    - 创建 `types/index.ts`
    - 定义 ActionItem 接口
    - 定义 FinalReport 接口
    - 定义 InsightCardProps、ActionPlanListProps、HITLConfirmationDialogProps 接口
    - 定义 SSE 事件类型
    - _Design: Components and Interfaces - 前端组件_

- [x] 15. 前端组件实现
  - [x] 15.1 实现 Insight_Card 深度洞察展示组件
    - 创建 `components/insight-card.tsx`
    - 使用 shadcn/ui Card 组件
    - 实现 Markdown 渲染（支持 h1-h4、列表、粗体斜体、代码块）
    - 实现骨架屏加载状态
    - 实现空状态提示
    - 实现响应式布局（移动端/平板端/桌面端）
    - 满足 WCAG 2.1 AA 可访问性要求
    - _Requirements: 15.1-15.8_
    - _Design: Components and Interfaces - Insight_Card 组件接口_
  
  - [ ]* 15.2 编写 Insight_Card 组件测试
    - 测试 Markdown 渲染
    - 测试加载状态
    - 测试空状态
    - 测试响应式布局
    - _Requirements: 15.1-15.8_
  
  - [x] 15.3 实现 Action_Plan_List 行动计划展示组件
    - 创建 `components/action-plan-list.tsx`
    - 使用 shadcn/ui Collapsible 组件
    - 按 category 分组展示（营养→康复→神经心理）
    - 实现分类颜色编码
    - 实现折叠/展开功能（200ms 过渡动画）
    - 实现空状态界面
    - 实现响应式布局（单列/双列网格）
    - _Requirements: 16.1-16.9_
    - _Design: Components and Interfaces - Action_Plan_List 组件接口_
  
  - [ ]* 15.4 编写 Action_Plan_List 组件测试
    - 测试分组和排序
    - 测试折叠/展开
    - 测试颜色编码
    - 测试空状态
    - _Requirements: 16.1-16.9_
  
  - [x] 15.5 实现 HITL 确认弹窗组件
    - 创建 `components/hitl-confirmation-dialog.tsx`
    - 使用 shadcn/ui Dialog 组件（modal=true）
    - 实现内容结构：标题、干预措施列表、操作按钮
    - 实现10分钟倒计时显示（每秒更新）
    - 实现倒计时归零自动关闭和提交拒绝
    - 实现按钮加载状态
    - 实现键盘交互（Enter/Escape/Tab）
    - _Requirements: 18.1-18.9_
    - _Design: Components and Interfaces - HITL 确认弹窗组件接口_
  
  - [ ]* 15.6 编写 HITL 确认弹窗组件测试
    - 测试弹窗打开/关闭
    - 测试倒计时显示
    - 测试按钮交互
    - 测试键盘导航
    - _Requirements: 18.1-18.9_

- [x] 16. 流式数据处理实现
  - [x] 16.1 实现 useHealthChat Hook
    - 创建 `hooks/use-health-chat.ts`
    - 使用 Vercel AI SDK 的 useChat hook 处理 SSE 流
    - 实现状态管理：connectionStatus、currentPhase、partialData、finalReport
    - 实现事件回调：onStatusUpdate、onIntermediate、onPause、onError
    - 实现 sendMessage() 发送消息
    - 实现 confirmHITL() 提交确认/拒绝
    - 实现自动重试机制（指数退避：2秒、4秒、8秒，最多3次）
    - 实现 retry() 手动重试
    - _Requirements: 17.1-17.8_
    - _Design: Components and Interfaces - 流式数据 Hook 接口_
  
  - [x] 16.2 实现主聊天页面
    - 创建 `app/page.tsx` 或 `app/chat/page.tsx`
    - 集成 useHealthChat Hook
    - 实现加载指示器显示
    - 实现实时状态更新 UI
    - 集成 Insight_Card 和 Action_Plan_List 组件
    - 集成 HITL 确认弹窗
    - 实现连接断开提示和重新连接按钮
    - 实现错误信息显示和重试按钮
    - _Requirements: 17.1-17.7_
  
  - [ ]* 16.3 编写流式处理集成测试
    - 测试 SSE 连接建立
    - 测试事件处理
    - 测试断线重连
    - 测试错误处理
    - _Requirements: 17.1-17.7_

- [x] 17. Checkpoint - 前端验证
  - 确保所有前端组件正常渲染
  - 验证流式数据处理正确性
  - 验证 HITL 弹窗交互
  - 确保所有测试通过，ask the user if questions arise.

- [x] 18. 端到端集成和最终验证
  - [x] 18.1 配置前后端联调环境
    - 配置后端 CORS 允许前端域名
    - 配置环境变量
    - 编写 docker-compose.yml 启动所有服务（后端、ChromaDB、Neo4j）
    - _Requirements: 全局集成_
  
  - [x] 18.2 创建知识库测试数据
    - 创建营养学 Markdown 知识库测试文档
    - 创建运动康复 Markdown 知识库测试文档
    - 创建心理神经免疫学知识图谱测试数据
    - 运行索引构建脚本
    - _Requirements: 11.1, 12.1_
  
  - [ ]* 18.3 编写端到端测试
    - 测试完整健康咨询流程
    - 测试高风险干预 HITL 流程
    - 测试超时和错误处理
    - _Requirements: 全局验证_

- [x] 19. Final Checkpoint - 系统验证
  - 确保所有功能正常工作
  - 验证端到端流程
  - 确保所有测试通过，ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from design document
- Unit tests validate specific examples and edge cases
- The implementation follows a backend-first approach, then frontend integration
- RAG tools require external services (ChromaDB, Neo4j) to be running

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["2.1", "2.3", "2.5", "2.6", "2.7", "4.1"] },
    { "id": 3, "tasks": ["2.2", "2.4", "4.2"] },
    { "id": 4, "tasks": ["5.1", "7.1", "7.2", "7.4"] },
    { "id": 5, "tasks": ["5.2", "5.4", "7.3", "7.5"] },
    { "id": 6, "tasks": ["5.3", "5.5"] },
    { "id": 7, "tasks": ["8.1", "8.2", "8.4", "8.5"] },
    { "id": 8, "tasks": ["8.3", "8.6"] },
    { "id": 9, "tasks": ["8.7"] },
    { "id": 10, "tasks": ["10.1"] },
    { "id": 11, "tasks": ["10.2", "10.3"] },
    { "id": 12, "tasks": ["10.4"] },
    { "id": 13, "tasks": ["12.1", "12.4"] },
    { "id": 14, "tasks": ["12.2", "12.3"] },
    { "id": 15, "tasks": ["12.5", "12.6"] },
    { "id": 16, "tasks": ["14.1"] },
    { "id": 17, "tasks": ["14.2"] },
    { "id": 18, "tasks": ["15.1", "15.3", "15.5"] },
    { "id": 19, "tasks": ["15.2", "15.4", "15.6"] },
    { "id": 20, "tasks": ["16.1"] },
    { "id": 21, "tasks": ["16.2"] },
    { "id": 22, "tasks": ["16.3"] },
    { "id": 23, "tasks": ["18.1", "18.2"] },
    { "id": 24, "tasks": ["18.3"] }
  ]
}
```
