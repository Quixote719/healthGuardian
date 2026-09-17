/**
 * 健康多智能体系统 - TypeScript 类型定义
 * 对应后端 Pydantic 模型和 API 接口
 */

// ============================================
// 枚举类型
// ============================================

/**
 * 干预措施类别 (Requirements 2.1)
 */
export type ActionCategory = "营养" | "康复" | "神经心理";

/**
 * 优先级 (Requirements 2.5)
 */
export type Priority = "高" | "中" | "低";

/**
 * 风险等级 (Requirements 2.6)
 */
export type RiskLevel = "高风险" | "中风险" | "低风险";

/**
 * 确认状态 (Requirements 3.7)
 */
export type ConfirmationStatus = "pending" | "confirmed" | "rejected";

/**
 * 连接状态 (Requirements 17.7)
 */
export type ConnectionStatus = "connected" | "disconnected" | "reconnecting";

/**
 * SSE 事件类型 (Requirements 13.4)
 */
export type SSEEventType =
  | "status"
  | "intermediate"
  | "report"
  | "pause"
  | "error"
  | "heartbeat";

// ============================================
// 数据模型接口
// ============================================

/**
 * 干预措施数据结构 (Requirements 2.1-2.9)
 */
export interface ActionItem {
  /** 干预类别：营养、康复或神经心理 */
  category: ActionCategory;
  /** 干预措施标题 (1-100字符) */
  title: string;
  /** 干预措施详细描述 (1-2000字符) */
  description: string;
  /** 执行频率 (1-200字符) */
  frequency: string;
  /** 优先级：高、中、低 */
  priority: Priority;
  /** 风险等级：高风险、中风险、低风险 */
  risk_level: RiskLevel;
  /** 预期持续时间，格式: 正整数+时间单位(天/周/月) */
  duration: string;
}

/**
 * 最终报告数据结构 (Requirements 3.1-3.8)
 */
export interface FinalReport {
  /** 底层心身一体病理分析文本 */
  deep_insight: string;
  /** 干预措施列表 (0-50项) */
  action_plan: ActionItem[];
  /** 随访计划信息，包含复查时间和关注指标 */
  follow_up: string;
  /** 是否需要用户确认高风险干预 */
  requires_confirmation: boolean;
  /** 报告生成时间 (UTC ISO 8601格式) */
  created_at: string;
  /** LangGraph 工作流会话 ID */
  session_id: string;
  /** 确认状态 */
  confirmation_status: ConfirmationStatus;
}

// ============================================
// 组件 Props 接口
// ============================================

/**
 * Insight_Card 组件 Props (Requirements 15.1-15.8)
 */
export interface InsightCardProps {
  /** 深度洞察内容 (Markdown 格式) */
  deepInsight: string;
  /** 加载状态，默认 false */
  isLoading?: boolean;
  /** 自定义样式类名 */
  className?: string;
}

/**
 * Action_Plan_List 组件 Props (Requirements 16.1-16.9)
 */
export interface ActionPlanListProps {
  /** 行动计划列表 */
  actionPlan: ActionItem[];
  /** 默认展开的分类列表，默认全部展开 */
  defaultExpandedCategories?: ActionCategory[];
  /** 自定义样式类名 */
  className?: string;
}

/**
 * HITL 确认弹窗组件 Props (Requirements 18.1-18.9)
 */
export interface HITLConfirmationDialogProps {
  /** 弹窗是否打开 */
  isOpen: boolean;
  /** 会话 ID */
  sessionId: string;
  /** 需要确认的高风险干预措施列表 */
  highRiskItems: ActionItem[];
  /** 超时秒数，默认 600 (10分钟) */
  timeoutSeconds?: number;
  /** 确认回调函数 */
  onConfirm: () => Promise<void>;
  /** 取消回调函数 */
  onCancel: () => Promise<void>;
}

// ============================================
// SSE 事件数据接口
// ============================================

/**
 * 状态事件数据 (Requirements 13.5)
 */
export interface StatusEventData {
  /** 当前处理的智能体名称 */
  agent_name: string;
  /** 处理进度描述 */
  progress: string;
  /** 进度百分比 (0-100) */
  percentage: number;
}

/**
 * 中间结果事件数据 (Requirements 13.5)
 */
export interface IntermediateEventData {
  /** 智能体名称 */
  agent_name: string;
  /** 部分结果内容 */
  partial_result: string;
}

/**
 * 暂停事件数据 (Requirements 13.8)
 */
export interface PauseEventData {
  /** 会话 ID */
  session_id: string;
  /** 需要确认的高风险干预措施 */
  high_risk_items: ActionItem[];
  /** 超时秒数 */
  timeout_seconds: number;
}

/**
 * 错误事件数据 (Requirements 13.9)
 */
export interface ErrorEventData {
  /** 错误类型标识 */
  error_type: string;
  /** 错误描述信息 */
  error_message: string;
}

/**
 * 心跳事件数据 (Requirements 13.6)
 */
export interface HeartbeatEventData {
  /** 时间戳 (ISO 8601格式) */
  timestamp: string;
}

/**
 * SSE 事件联合类型
 */
export type SSEEventData =
  | { type: "status"; data: StatusEventData }
  | { type: "intermediate"; data: IntermediateEventData }
  | { type: "report"; data: FinalReport }
  | { type: "pause"; data: PauseEventData }
  | { type: "error"; data: ErrorEventData }
  | { type: "heartbeat"; data: HeartbeatEventData };

// ============================================
// API 请求/响应接口
// ============================================

/**
 * 聊天请求 (Requirements 13.2)
 */
export interface ChatRequest {
  /** 用户查询文本 (最大2000字符) */
  user_query: string;
  /** 用户画像 ID */
  user_profile_id: string;
}

/**
 * HITL 确认请求 (Requirements 14.2)
 */
export interface ConfirmRequest {
  /** 会话 ID */
  session_id: string;
  /** 是否确认执行 */
  confirmed: boolean;
}

/**
 * HITL 确认响应 (Requirements 14.8)
 */
export interface ConfirmResponse {
  /** 状态: "resumed" 或 "terminated" */
  status: "resumed" | "terminated";
  /** 部分报告 (仅在拒绝时包含) */
  partial_report?: FinalReport;
}

/**
 * API 错误响应
 */
export interface APIErrorResponse {
  /** 错误类型 */
  error_type: "session_not_found" | "session_not_paused" | "session_timeout" | "validation_error" | "internal_error";
  /** 错误消息 */
  message: string;
}

// ============================================
// Hook 相关类型
// ============================================

/**
 * useHealthChat Hook 配置选项 (Requirements 17.1-17.7)
 */
export interface UseHealthChatOptions {
  /** 状态更新回调 */
  onStatusUpdate?: (status: string, agent: string) => void;
  /** 中间结果回调 */
  onIntermediate?: (data: IntermediateEventData) => void;
  /** 暂停回调 */
  onPause?: (sessionId: string, items: ActionItem[]) => void;
  /** 错误回调 */
  onError?: (error: Error) => void;
}

/**
 * useHealthChat Hook 返回值 (Requirements 17.1-17.7)
 */
export interface UseHealthChatReturn {
  /** 消息历史 */
  messages: ChatMessage[];
  /** 是否正在加载 */
  isLoading: boolean;
  /** 连接状态 */
  connectionStatus: ConnectionStatus;
  /** 当前处理阶段 */
  currentPhase: string;
  /** 最终报告 */
  finalReport: FinalReport | null;
  /** 发送消息 */
  sendMessage: (content: string, userProfileId: string) => Promise<void>;
  /** 提交 HITL 确认/拒绝 */
  confirmHITL: (sessionId: string, confirmed: boolean) => Promise<void>;
  /** 手动重试 */
  retry: () => Promise<void>;
  /** 暂停的会话 ID (HITL 机制) */
  pausedSessionId: string | null;
  /** 暂停时的高风险干预列表 */
  pausedHighRiskItems: ActionItem[];
}

/**
 * 聊天消息
 */
export interface ChatMessage {
  /** 消息 ID */
  id: string;
  /** 角色: user 或 assistant */
  role: "user" | "assistant";
  /** 消息内容 */
  content: string;
  /** 创建时间 */
  createdAt: Date;
  /** 关联的最终报告 (仅 assistant 消息) */
  report?: FinalReport;
}

// ============================================
// 工具类型
// ============================================

/**
 * 分类颜色配置
 */
export interface CategoryColorConfig {
  /** 背景色 CSS 类 */
  bgClass: string;
  /** 边框色 CSS 类 */
  borderClass: string;
  /** 文字色 CSS 类 */
  textClass: string;
}

/**
 * 获取分类颜色配置的映射表
 */
export const CATEGORY_COLORS: Record<ActionCategory, CategoryColorConfig> = {
  营养: {
    bgClass: "bg-green-100",
    borderClass: "border-green-500",
    textClass: "text-green-800",
  },
  康复: {
    bgClass: "bg-blue-100",
    borderClass: "border-blue-500",
    textClass: "text-blue-800",
  },
  神经心理: {
    bgClass: "bg-purple-100",
    borderClass: "border-purple-500",
    textClass: "text-purple-800",
  },
};

/**
 * 分类显示顺序 (Requirements 16.3)
 */
export const CATEGORY_ORDER: ActionCategory[] = ["营养", "康复", "神经心理"];

/**
 * 分类图标映射
 */
export const CATEGORY_ICONS: Record<ActionCategory, string> = {
  营养: "🥗",
  康复: "🏃",
  神经心理: "🧠",
};
