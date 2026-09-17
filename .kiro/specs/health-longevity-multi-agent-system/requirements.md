# Requirements Document

## Introduction

个人健康长寿多智能体系统是一个全栈应用，作为用户的"长寿与全科健康主治医生"。该系统结合用户长期健康画像，通过多个专业智能体（营养学、运动康复、神经心理调节）提供跨学科的深度洞察和系统化干预方案。系统采用 LangGraph 实现多智能体编排，LlamaIndex 实现知识库检索，前端使用 Next.js 和 Vercel AI SDK 实现 Generative UI 交互和流式输出，并支持 Human-in-the-loop (HITL) 确认机制确保高风险干预的安全性。

## Glossary

- **Health_System**: 个人健康长寿多智能体系统的整体应用
- **User_Profile**: 用户健康画像数据结构，包含基础生理信息、病史、体检指标、用药史和生活方式基线
- **Action_Item**: 单个干预措施的数据结构，包含类别、标题、描述和执行频率
- **Final_Report**: 系统生成的最终报告，包含深度洞察、行动计划、随访安排和确认标志
- **Health_State**: LangGraph 工作流的全局状态对象
- **Controller_Agent**: 主控智能体节点，负责任务拆解和风险检测
- **Nutrition_Agent**: 营养学专家智能体节点
- **Rehabilitation_Agent**: 运动康复专家智能体节点
- **Neuropsychology_Agent**: 神经心理调节专家智能体节点
- **Synthesis_Agent**: 综合反思与安全检查智能体节点
- **Markdown_RAG**: 基于 LlamaIndex MarkdownNodeParser 的知识库检索工具
- **Graph_RAG**: 基于 LlamaIndex KnowledgeGraphIndex 的知识图谱检索工具
- **HITL_Mechanism**: Human-in-the-loop 确认机制，用于高风险干预的用户确认
- **UI_Interrupt_Flag**: 状态标志，指示是否需要暂停工作流等待用户确认
- **SSE_Stream**: Server-Sent Events 流式输出机制
- **Insight_Card**: 前端组件，用于展示深度洞察内容
- **Action_Plan_List**: 前端组件，用于展示行动计划列表

---

## Requirements

### Requirement 1: 用户健康画像数据结构

**User Story:** 作为系统开发者，我需要定义完整的用户健康画像数据结构，以便系统能够存储和处理用户的综合健康信息。

#### Acceptance Criteria

1. THE User_Profile SHALL 包含基础生理信息字段：年龄（int类型，范围0-150）、性别（枚举值"男"/"女"/"其他"）、身高（float类型，范围30-300厘米）、体重（float类型，范围0.5-500千克）
2. THE User_Profile SHALL 包含既往病史字段，类型为病史记录列表（最多100条），每条记录包含：疾病名称（字符串，最大长度200）、诊断日期（date类型）、当前状态（枚举值"已治愈"/"治疗中"/"慢性管理"）
3. THE User_Profile SHALL 包含体检指标字段，包括血脂指标（总胆固醇、甘油三酯、HDL、LDL，均为float类型，单位mmol/L，范围0-50）和血糖指标（空腹血糖float类型单位mmol/L范围0-50，糖化血红蛋白float类型单位%范围0-20）
4. THE User_Profile SHALL 包含用药史字段，类型为用药记录列表（最多50条），每条记录包含：药物名称（字符串，最大长度200）、剂量（字符串，最大长度100）、用药频率（枚举值"每日一次"/"每日两次"/"每日三次"/"按需服用"/"其他"）、起始日期（date类型）、结束日期（date类型，可选）
5. THE User_Profile SHALL 包含生活方式基线字段：睡眠时长（float类型，范围0-24小时）、运动频率（枚举值"从不"/"每周1-2次"/"每周3-5次"/"每天"）、饮食习惯（枚举值"荤素均衡"/"素食为主"/"肉食为主"/"不规律"）、压力水平（int类型，1-10级量表）
6. THE User_Profile SHALL 使用 Pydantic 模型定义，支持数据验证和JSON序列化
7. IF User_Profile 的任意字段值不符合上述验证规则，THEN THE User_Profile SHALL 抛出 Pydantic ValidationError 并包含指示具体违规字段的错误信息

---

### Requirement 2: 干预措施数据结构

**User Story:** 作为系统开发者，我需要定义标准化的干预措施数据结构，以便各专家智能体能够以统一格式输出建议。

#### Acceptance Criteria

1. THE Action_Item SHALL 包含 category 字段，取值限定为"营养"、"康复"或"神经心理"三个枚举值之一
2. THE Action_Item SHALL 包含 title 字段，长度限制为1至100个字符，用于简要描述干预措施名称
3. THE Action_Item SHALL 包含 description 字段，长度限制为1至2000个字符，用于详细说明干预措施内容
4. THE Action_Item SHALL 包含 frequency 字段，长度限制为1至200个字符，用于指定执行频率
5. THE Action_Item SHALL 包含 priority 字段，取值限定为"高"、"中"或"低"三个枚举值之一
6. THE Action_Item SHALL 包含 risk_level 字段，取值限定为"高风险"、"中风险"或"低风险"三个枚举值之一
7. THE Action_Item SHALL 包含 duration 字段，用于指定干预措施的预期持续时间，格式为正整数加时间单位（天、周、月）
8. IF Action_Item 的任意字段值不符合上述验证规则，THEN THE Action_Item SHALL 抛出 Pydantic ValidationError
9. THE Action_Item SHALL 使用 Pydantic 模型定义，支持数据验证和JSON序列化

---

### Requirement 3: 最终报告数据结构

**User Story:** 作为系统开发者，我需要定义综合报告数据结构，以便系统能够以结构化形式呈现分析结果和干预方案。

#### Acceptance Criteria

1. THE Final_Report SHALL 包含 deep_insight 字段（字符串类型），用于存储底层心身一体病理分析文本
2. THE Final_Report SHALL 包含 action_plan 字段，存储 Action_Item 列表（长度范围0-50项）
3. THE Final_Report SHALL 包含 follow_up 字段（字符串类型），用于存储随访计划信息，包含复查时间和关注指标
4. THE Final_Report SHALL 包含 requires_confirmation 布尔字段，指示是否需要用户确认高风险干预
5. THE Final_Report SHALL 包含 created_at 字段（datetime类型），记录报告生成的UTC时间戳
6. THE Final_Report SHALL 包含 session_id 字段（字符串类型），关联 LangGraph 工作流会话
7. THE Final_Report SHALL 包含 confirmation_status 字段，枚举值为"pending"/"confirmed"/"rejected"
8. THE Final_Report SHALL 使用 Pydantic 模型定义，支持数据验证和JSON序列化

---

### Requirement 4: LangGraph 全局状态定义

**User Story:** 作为系统开发者，我需要定义 LangGraph 工作流的全局状态结构，以便在多智能体节点间共享和传递数据。

#### Acceptance Criteria

1. THE Health_State SHALL 包含 user_query 字段（字符串类型，最大长度5000字符），存储用户的原始查询文本
2. THE Health_State SHALL 包含 user_profile 字段，存储 User_Profile 对象
3. THE Health_State SHALL 包含 task_breakdown 字段，存储子任务列表，每个子任务包含：task_id、target_agent（枚举值"nutrition"/"rehabilitation"/"neuropsychology"）、task_description
4. THE Health_State SHALL 包含 expert_responses 字段（字典类型），键为智能体名称，值为响应内容
5. THE Health_State SHALL 包含 ui_interrupt_flag 布尔字段，指示是否需要暂停等待用户确认
6. THE Health_State SHALL 包含 interrupt_reason 字段（字符串类型），当 ui_interrupt_flag 为 true 时存储中断原因
7. THE Health_State SHALL 包含 node_execution_status 字段（字典类型），追踪5个节点的执行状态（枚举值"pending"/"running"/"completed"/"failed"/"skipped"）
8. THE Health_State SHALL 包含 error_info 字段（列表类型），存储错误信息，每条包含：node_name、error_type、error_message（最大长度1000字符）、timestamp
9. THE Health_State SHALL 包含 final_report 字段，存储 Final_Report 对象（工作流未完成时为None）
10. THE Health_State SHALL 兼容 LangGraph 的 TypedDict 状态模式

---

### Requirement 5: 主控智能体节点

**User Story:** 作为用户，我需要系统能够智能理解我的健康咨询请求并合理分配给专业智能体，以便获得针对性的建议。

#### Acceptance Criteria

1. WHEN 用户提交健康咨询请求时，THE Controller_Agent SHALL 从 Health_State 读取 user_profile 信息
2. WHEN 处理用户请求时，THE Controller_Agent SHALL 将请求拆解为营养、康复、神经心理三个维度的子任务，并将拆解结果写入 Health_State 的 task_breakdown 字段
3. WHEN 检测到用户请求包含以下高风险关键词或模式时，THE Controller_Agent SHALL 将 ui_interrupt_flag 设置为 true：用药调整类（停药、换药、加药、减药）、断食类（断食超过24小时、水断食）、极端饮食类（生酮饮食、极低热量饮食低于800千卡/天）、高强度运动类（针对有心血管病史的用户）、补剂类（大剂量补剂超过RDA推荐量3倍）
4. IF 用户请求涉及以下超出系统能力范围的医疗问题，THEN THE Controller_Agent SHALL 建议用户寻求专业医疗机构帮助并终止任务拆解：急性症状（胸痛、呼吸困难、意识障碍、高热超过39°C）、需处方治疗的疾病（感染性疾病、肿瘤）、精神科范畴（自杀倾向、严重抑郁、精神分裂症状）、诊断请求、儿科问题（12岁以下儿童）
5. IF Controller_Agent 处理请求超过30秒未完成，THEN THE Controller_Agent SHALL 终止当前处理并向 Health_State 写入超时错误状态

---

### Requirement 6: 营养学专家智能体节点

**User Story:** 作为用户，我需要获得基于专业知识库的个性化营养和补剂建议，以便优化我的饮食干预方案。

#### Acceptance Criteria

1. WHEN 接收到营养相关子任务时，THE Nutrition_Agent SHALL 调用 Markdown_RAG 检索营养学知识库，超时时间为10秒
2. IF Markdown_RAG 检索失败或超时，THEN THE Nutrition_Agent SHALL 基于内置基础营养知识生成通用建议
3. THE Nutrition_Agent SHALL 根据血脂阈值生成针对性建议：总胆固醇≥5.2mmol/L、LDL≥3.4mmol/L、HDL<1.0mmol/L、甘油三酯≥1.7mmol/L（满足任一即为异常）
4. THE Nutrition_Agent SHALL 根据血糖阈值生成针对性建议：空腹血糖≥6.1mmol/L、糖化血红蛋白≥5.7%（满足任一即为异常）
5. IF 用户存在以下药物用药史，THEN THE Nutrition_Agent SHALL 附加药物-食物交互警告：华法林等抗凝药、他汀类降脂药、二甲双胍等降糖药、ACEI/ARB类降压药、甲状腺激素类药物
6. THE Nutrition_Agent SHALL 输出3至5个 Action_Item，category 设置为"营养"
7. THE Nutrition_Agent SHALL 将响应结果写入 Health_State 的 expert_responses 字段

---

### Requirement 7: 运动康复专家智能体节点

**User Story:** 作为用户，我需要获得基于专业知识库的个性化运动和体态康复建议，以便改善我的身体机能。

#### Acceptance Criteria

1. WHEN 接收到运动康复相关子任务时，THE Rehabilitation_Agent SHALL 调用 Markdown_RAG 检索运动康复知识库
2. THE Rehabilitation_Agent SHALL 根据年龄匹配运动强度：18-39岁（高强度）、40-59岁（中高强度）、60-74岁（中等强度）、75岁以上（低强度）
3. THE Rehabilitation_Agent SHALL 根据BMI调整运动强度：BMI<18.5（轻度增强）、18.5-23.9（标准强度）、24-27.9（适度降低）、BMI≥28（显著降低，避免高冲击运动）
4. THE Rehabilitation_Agent SHALL 输出3至5个 Action_Item，category 设置为"康复"
5. THE Rehabilitation_Agent SHALL 将响应结果写入 Health_State 的 expert_responses 字段
6. IF 用户存在以下禁忌病史，THEN THE Rehabilitation_Agent SHALL 排除对应运动类型：心血管疾病（禁止高强度有氧和负重训练）、骨关节疾病（禁止高冲击运动和深蹲）、呼吸系统疾病（限制高强度有氧）、代谢性疾病（避免空腹运动）、神经系统疾病（禁止平衡要求高的运动）

---

### Requirement 8: 神经心理调节专家智能体节点

**User Story:** 作为用户，我需要获得基于知识图谱的心理神经免疫学干预建议，以便改善我的心理健康状态。

#### Acceptance Criteria

1. WHEN 接收到神经心理相关子任务时，THE Neuropsychology_Agent SHALL 调用 Graph_RAG 检索心理神经免疫学知识图谱
2. THE Neuropsychology_Agent SHALL 根据压力等级匹配干预策略：1-3级（轻度）匹配日常调节类、4-6级（中度）匹配结构化训练类、7-10级（重度）匹配专业支持类并标记需关注
3. THE Neuropsychology_Agent SHALL 根据睡眠时长评估：少于6小时（睡眠不足）、6-9小时（正常）、超过9小时（睡眠过多）；睡眠异常时优先生成睡眠相关干预
4. THE Neuropsychology_Agent SHALL 按类型分类输出：硬件层干预（呼吸训练、HRV生物反馈、渐进式肌肉放松、光照疗法）和软件层干预（认知重构、正念冥想、情绪日记、行为激活）
5. THE Neuropsychology_Agent SHALL 以 Action_Item 格式输出，category 设置为"神经心理"，在 description 中标注干预类型
6. THE Neuropsychology_Agent SHALL 将响应结果写入 Health_State 的 expert_responses 字段
7. IF 用户描述包含以下关键词之一：自杀、自残、幻觉、幻听、妄想、躁狂发作、重度抑郁、精神分裂、双相情感障碍急性发作，THEN THE Neuropsychology_Agent SHALL 拒绝提供干预并返回"建议立即寻求专业精神科医生帮助"
8. IF Graph_RAG 检索返回空结果或失败，THEN THE Neuropsychology_Agent SHALL 基于内置基础知识生成通用建议并标注"未检索到专业知识库内容"

---

### Requirement 9: 综合反思与安全检查智能体节点

**User Story:** 作为用户，我需要系统能够整合各专家意见并进行安全性检查，以便获得协调一致且安全的综合健康方案。

#### Acceptance Criteria

1. WHEN 所有专家智能体完成响应后，THE Synthesis_Agent SHALL 从 Health_State 读取所有 expert_responses
2. THE Synthesis_Agent SHALL 生成 deep_insight，包含四部分：健康现状总结、跨学科关联分析、核心问题归因、干预逻辑说明
3. THE Synthesis_Agent SHALL 汇总 Action_Item 时执行去重：title相同或description语义相似度超过80%时去重，按营养>康复>神经心理优先级保留
4. THE Synthesis_Agent SHALL 检测以下干预冲突并处理：药物-营养交互冲突、运动-病史禁忌冲突、干预措施矛盾冲突（检测到冲突时移除冲突项并添加替代建议）
5. IF 检测到以下高风险干预组合，THEN THE Synthesis_Agent SHALL 将 requires_confirmation 设置为 true：涉及停药或调整处方药、超过24小时断食方案、心血管病患者高强度运动、超过3种补剂的方案
6. THE Synthesis_Agent SHALL 根据风险等级生成随访计划：高风险（7天后随访）、中风险（14天后随访）、低风险（30天后随访），随访计划包含复查时间和关注指标
7. THE Synthesis_Agent SHALL 将完整的 Final_Report 写入 Health_State

---

### Requirement 10: 多智能体工作流编排

**User Story:** 作为系统开发者，我需要实现多智能体的协调执行流程，以便系统能够高效并行处理专家分析任务。

#### Acceptance Criteria

1. THE Health_System SHALL 使用 LangGraph 实现工作流编排，并使用 LangGraph 内置持久化机制（SqliteSaver/PostgresSaver）保存会话状态
2. THE Health_System SHALL 按照 Controller_Agent -> [Nutrition_Agent, Rehabilitation_Agent, Neuropsychology_Agent 并行] -> Synthesis_Agent 的顺序执行，单个智能体超时时间为30秒
3. WHEN Controller_Agent 完成执行且 ui_interrupt_flag 为 true 时，THE Health_System SHALL 使用 LangGraph interrupt 机制暂停工作流
4. THE Health_System SHALL 提供 resume_execution 函数，接收用户确认后继续执行暂停的工作流
5. WHILE 工作流处于暂停状态时，THE Health_System SHALL 保持 Health_State 状态不变，最长保持30分钟
6. IF 暂停状态超过30分钟未收到用户确认，THEN THE Health_System SHALL 自动终止会话并释放资源
7. IF 并行执行的智能体超时（超过30秒），THEN THE Health_System SHALL 终止该智能体执行、记录超时状态、继续执行后续流程
8. IF 智能体执行过程中发生异常，THEN THE Health_System SHALL 捕获错误、记录错误信息、继续执行其他智能体

---

### Requirement 11: Markdown 知识库检索工具

**User Story:** 作为系统开发者，我需要实现基于 Markdown 文档的知识库检索工具，以便营养和康复智能体能够查询专业知识。

#### Acceptance Criteria

1. THE Markdown_RAG SHALL 使用 LlamaIndex MarkdownNodeParser 解析 Markdown 文档，分块大小512字符，块间重叠50字符
2. THE Markdown_RAG SHALL 使用 LlamaIndex VectorStoreIndex 构建向量索引，使用 ChromaDB 持久化存储
3. WHEN 智能体调用 query_markdown_rag 函数时，THE Markdown_RAG SHALL 返回最多5个结果，每个结果相似度分数不低于0.7
4. THE Markdown_RAG SHALL 支持指定知识库类别（营养学或运动康复）进行定向检索
5. THE Markdown_RAG SHALL 支持通过可选参数 top_k（范围1-20，默认5）和 similarity_threshold（范围0.0-1.0，默认0.7）自定义返回结果
6. IF 检索结果为空或所有结果相似度低于阈值，THEN THE Markdown_RAG SHALL 返回空结果列表并包含未找到相关内容的状态信息

---

### Requirement 12: 知识图谱检索工具

**User Story:** 作为系统开发者，我需要实现基于知识图谱的检索工具，以便神经心理智能体能够查询复杂的心理神经免疫学关系。

#### Acceptance Criteria

1. THE Graph_RAG SHALL 使用 LlamaIndex KnowledgeGraphIndex 构建知识图谱索引
2. THE Graph_RAG SHALL 使用 Neo4j 图数据库作为持久化存储后端
3. WHEN 智能体调用 query_graph_rag 函数时，THE Graph_RAG SHALL 返回与查询相关的实体和关系信息
4. THE Graph_RAG SHALL 支持多跳关系查询，最大跳数限制为3跳
5. THE Graph_RAG SHALL 以结构化格式返回查询结果，包含实体列表（名称、类型、属性）和关系列表（源实体、目标实体、关系类型）
6. THE Graph_RAG SHALL 对单次查询设置10秒超时限制
7. IF 查询执行超时，THEN THE Graph_RAG SHALL 返回错误响应，包含错误类型标识和错误描述信息

---

### Requirement 13: 流式聊天 API

**User Story:** 作为用户，我需要实时看到系统的分析过程和结果输出，以便获得更好的交互体验。

#### Acceptance Criteria

1. THE Health_System SHALL 提供 /chat POST 端点接收用户健康咨询请求
2. THE /chat 端点 SHALL 接收包含 user_query（字符串，最大长度2000字符）和 user_profile_id（字符串）字段的 JSON 请求体
3. THE Health_System SHALL 使用 Server-Sent Events (SSE) 协议实现流式响应
4. THE Health_System SHALL 定义以下 SSE 事件类型：status（智能体处理状态）、intermediate（中间结果）、report（最终报告）、pause（HITL暂停）、error（错误信息）、heartbeat（心跳）
5. WHILE 工作流执行过程中，THE Health_System SHALL 实时推送 status 和 intermediate 事件，包含当前处理的智能体名称和处理进度
6. WHILE SSE 连接保持期间，THE Health_System SHALL 每15秒推送一次 heartbeat 事件
7. WHEN 工作流完成时，THE Health_System SHALL 推送 report 事件，包含完整的 Final_Report 数据
8. IF 工作流因 HITL 机制暂停，THEN THE Health_System SHALL 推送 pause 事件，包含 session_id 和需要确认的高风险干预内容
9. IF 工作流执行过程中发生错误，THEN THE Health_System SHALL 推送 error 事件，包含错误类型标识和错误描述信息

---

### Requirement 14: HITL 确认 API

**User Story:** 作为用户，我需要能够确认或拒绝高风险干预建议，以便保持对自己健康决策的控制权。

#### Acceptance Criteria

1. THE Health_System SHALL 提供 /confirm POST 端点接收用户的 HITL 确认响应
2. THE /confirm 端点 SHALL 接收包含 session_id（字符串）和 confirmed（布尔值）字段的 JSON 请求体
3. WHEN 用户提交确认响应时，THE Health_System SHALL 验证对应的工作流会话存在且处于暂停状态
4. IF session_id 对应的会话不存在，THEN THE Health_System SHALL 返回错误响应，错误类型为"session_not_found"
5. IF session_id 对应的会话未处于暂停状态，THEN THE Health_System SHALL 返回错误响应，错误类型为"session_not_paused"
6. IF 用户确认执行，THEN THE Health_System SHALL 调用 resume_execution 继续工作流
7. IF 用户拒绝执行，THEN THE Health_System SHALL 终止工作流并返回部分结果
8. THE /confirm 端点 SHALL 返回包含 status（"resumed"或"terminated"）和 partial_report（仅在拒绝时包含）字段的 JSON 响应体
9. THE Health_System SHALL 对暂停状态的会话设置10分钟超时限制
10. IF 会话暂停超过10分钟未收到用户确认，THEN THE Health_System SHALL 自动终止工作流并释放会话资源
11. THE Health_System SHALL 使用 FastAPI 框架实现所有 API 端点

---

### Requirement 15: 深度洞察展示组件

**User Story:** 作为用户，我需要以清晰易读的方式查看系统的深度健康分析，以便理解自己的健康状况。

#### Acceptance Criteria

1. THE Insight_Card SHALL 接收 InsightCardProps 类型的 props：deepInsight（string，必填）、isLoading（boolean，可选，默认false）、className（string，可选）
2. THE Insight_Card SHALL 以卡片形式展示 Final_Report 的 deep_insight 内容
3. THE Insight_Card SHALL 支持 Markdown 格式渲染：h1-h4标题、有序和无序列表、粗体和斜体、代码块
4. THE Insight_Card SHALL 使用 shadcn/ui Card 组件和 Tailwind CSS 实现样式
5. WHEN isLoading 为 true 时，THE Insight_Card SHALL 显示骨架屏加载状态（3行文本占位符动画）
6. IF deepInsight 为空字符串，THEN THE Insight_Card SHALL 显示"暂无分析内容"的空状态提示
7. THE Insight_Card SHALL 采用响应式布局：移动端（<640px）单列全宽、平板端（640-1024px）最大宽度640px居中、桌面端（>1024px）最大宽度800px居中
8. THE Insight_Card SHALL 满足 WCAG 2.1 AA 级可访问性要求：使用 article 语义标签、卡片标题使用 h2 标签、文本对比度不低于4.5:1

---

### Requirement 16: 行动计划展示组件

**User Story:** 作为用户，我需要以结构化方式查看所有干预措施建议，以便制定执行计划。

#### Acceptance Criteria

1. THE Action_Plan_List SHALL 接收 ActionPlanListProps 类型的 props：actionPlan（Action_Item数组，必填）、defaultExpandedCategories（string数组，可选，默认全部展开）、className（string，可选）
2. THE Action_Plan_List SHALL 以列表形式展示 Final_Report 的 action_plan 中所有 Action_Item
3. THE Action_Plan_List SHALL 按 category 分组展示，顺序为：营养、康复、神经心理
4. THE Action_Plan_List SHALL 为每个分类使用不同颜色编码："营养"使用绿色系（bg-green-100 border-green-500）、"康复"使用蓝色系（bg-blue-100 border-blue-500）、"神经心理"使用紫色系（bg-purple-100 border-purple-500）
5. THE Action_Plan_List SHALL 为每个 Action_Item 展示 title（粗体）、description（常规文本）和 frequency（标签样式）
6. THE Action_Plan_List SHALL 支持分类折叠和展开：点击分类标题切换状态、使用 shadcn/ui Collapsible 组件、200ms过渡动画
7. IF actionPlan 为空数组，THEN THE Action_Plan_List SHALL 显示空状态界面："暂无行动计划"和"系统正在分析中，请稍候"
8. THE Action_Plan_List SHALL 使用 shadcn/ui 组件库和 Tailwind CSS 实现样式
9. THE Action_Plan_List SHALL 采用响应式布局：移动端（<640px）单列布局、桌面端（≥640px）双列网格布局

---

### Requirement 17: 流式数据处理

**User Story:** 作为用户，我需要前端能够实时显示系统的流式输出，以便获得即时反馈体验。

#### Acceptance Criteria

1. THE Health_System 前端 SHALL 使用 Vercel AI SDK 的 useChat hook 处理 SSE 流式数据
2. WHILE 接收流式数据时，THE Health_System 前端 SHALL 显示加载指示器（旋转动画图标和当前处理阶段文本）
3. WHILE 接收流式数据时，THE Health_System 前端 SHALL 实时更新 UI 显示当前处理状态
4. WHEN 接收到最终报告数据时，THE Health_System 前端 SHALL 渲染 Insight_Card 和 Action_Plan_List 组件
5. IF SSE 连接断开，THEN THE Health_System 前端 SHALL 显示连接断开提示并提供"重新连接"按钮
6. IF 流式请求失败，THEN THE Health_System 前端 SHALL 显示错误信息并提供"重试"按钮，最多支持3次自动重试（指数退避：2秒、4秒、8秒）
7. THE Health_System 前端 SHALL 使用 React useState 和 useReducer 管理状态：connectionStatus、currentPhase、partialData、finalReport
8. THE Health_System 前端 SHALL 使用 Next.js 和 React 框架实现

---

### Requirement 18: HITL 确认弹窗

**User Story:** 作为用户，我需要在系统建议高风险干预时收到明确提示并进行确认，以便做出知情决策。

#### Acceptance Criteria

1. WHEN 接收到 requires_confirmation 为 true 的暂停状态时，THE Health_System 前端 SHALL 显示确认弹窗
2. THE 确认弹窗 SHALL 使用以下内容结构：标题区域显示"高风险干预确认"、内容区域显示需要确认的具体干预措施列表、底部区域显示操作按钮和倒计时提示
3. THE 确认弹窗 SHALL 显示10分钟倒计时提示，格式为"请在 MM:SS 内完成确认，超时将自动取消"，每秒更新
4. WHEN 倒计时归零时，THE 确认弹窗 SHALL 自动关闭并向 /confirm API 提交拒绝响应
5. THE 确认弹窗 SHALL 提供"确认执行"（主要按钮，蓝色）和"取消"（次要按钮，灰色）两个操作按钮
6. WHILE 等待 /confirm API 响应时，THE 操作按钮 SHALL 显示加载状态：禁用按钮、显示旋转加载图标、按钮文本变为"处理中..."
7. WHEN 用户点击操作按钮时，THE Health_System 前端 SHALL 调用 /confirm API 提交用户响应
8. THE 确认弹窗 SHALL 支持键盘交互：Enter键触发确认、Escape键触发取消、Tab键切换焦点
9. THE 确认弹窗 SHALL 使用 shadcn/ui Dialog 组件实现，设置 modal 为 true
