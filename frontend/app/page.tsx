"use client";

import { AlertCircle, Heart, Loader2, RefreshCw, Send, WifiOff } from "lucide-react";
import * as React from "react";
import { ActionPlanList } from "@/components/action-plan-list";
import { HITLConfirmationDialog } from "@/components/hitl-confirmation-dialog";
import { InsightCard } from "@/components/insight-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useHealthChat } from "@/hooks/use-health-chat";
import { cn } from "@/lib/utils";
import type { ConnectionStatus } from "@/types";

/**
 * 测试用户画像 ID
 */
const TEST_USER_PROFILE_ID = "user-001";

/**
 * 连接状态指示器组件 (Requirements 17.5)
 */
function ConnectionStatusIndicator({
  status,
  onReconnect,
}: {
  status: ConnectionStatus;
  onReconnect: () => void;
}) {
  const statusConfig = {
    connected: {
      color: "text-green-600",
      bgColor: "bg-green-100",
      text: "已连接",
      icon: null,
    },
    disconnected: {
      color: "text-gray-500",
      bgColor: "bg-gray-100",
      text: "未连接",
      icon: <WifiOff className="h-4 w-4" />,
    },
    reconnecting: {
      color: "text-amber-600",
      bgColor: "bg-amber-100",
      text: "重连中...",
      icon: <Loader2 className="h-4 w-4 animate-spin" />,
    },
  };

  const config = statusConfig[status];

  return (
    <div className={cn("flex items-center gap-2 px-3 py-1.5 rounded-full text-sm", config.bgColor)}>
      {config.icon && <span aria-hidden="true">{config.icon}</span>}
      <span className={cn("font-medium", config.color)}>{config.text}</span>
      {status === "disconnected" && (
        <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={onReconnect}>
          <RefreshCw className="h-3 w-3 mr-1" />
          重连
        </Button>
      )}
    </div>
  );
}

/**
 * 加载指示器组件 (Requirements 17.2)
 */
function LoadingIndicator({ phase }: { phase: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-6">
      <Loader2 className="h-6 w-6 animate-spin text-primary" aria-hidden="true" />
      <span className="text-muted-foreground">{phase || "处理中..."}</span>
    </div>
  );
}

/**
 * 错误提示组件 (Requirements 17.6)
 */
function ErrorDisplay({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Card className="border-red-200 bg-red-50">
      <CardContent className="flex items-center justify-between p-4">
        <div className="flex items-center gap-3 text-red-700">
          <AlertCircle className="h-5 w-5" aria-hidden="true" />
          <span>{message}</span>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={onRetry}
          className="border-red-300 text-red-700 hover:bg-red-100"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          重试
        </Button>
      </CardContent>
    </Card>
  );
}

/**
 * 聊天输入区域组件
 */
function ChatInput({
  onSend,
  isLoading,
  disabled,
}: {
  onSend: (message: string) => void;
  isLoading: boolean;
  disabled?: boolean;
}) {
  const [input, setInput] = React.useState("");
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading && !disabled) {
      onSend(input.trim());
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // 自动调整 textarea 高度
  React.useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <Card className="shadow-lg">
        <CardContent className="p-4">
          <div className="flex gap-3 items-end">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="请描述您的健康问题或咨询需求..."
              className={cn(
                "flex-1 resize-none rounded-lg border border-input bg-background px-4 py-3",
                "placeholder:text-muted-foreground",
                "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1",
                "min-h-[52px] max-h-[200px]",
                "disabled:cursor-not-allowed disabled:opacity-50"
              )}
              disabled={isLoading || disabled}
              rows={1}
              aria-label="健康咨询输入框"
            />
            <Button
              type="submit"
              size="lg"
              disabled={!input.trim() || isLoading || disabled}
              className="h-[52px] px-6"
            >
              {isLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <>
                  <Send className="h-5 w-5 mr-2" />
                  发送
                </>
              )}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2">按 Enter 发送，Shift + Enter 换行</p>
        </CardContent>
      </Card>
    </form>
  );
}

/**
 * 功能介绍卡片组
 */
function FeatureCards() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-4xl">
      <Card className="bg-green-50 border-green-200">
        <CardHeader className="pb-2">
          <CardTitle className="text-green-800 text-lg flex items-center gap-2">
            <span role="img" aria-hidden="true">
              🥗
            </span>
            营养专家
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-green-700">
            基于您的血脂、血糖指标和用药史，提供个性化的饮食和补剂建议。
          </p>
        </CardContent>
      </Card>

      <Card className="bg-blue-50 border-blue-200">
        <CardHeader className="pb-2">
          <CardTitle className="text-blue-800 text-lg flex items-center gap-2">
            <span role="img" aria-hidden="true">
              🏃
            </span>
            康复专家
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-blue-700">根据年龄、BMI和病史，制定安全有效的运动康复方案。</p>
        </CardContent>
      </Card>

      <Card className="bg-purple-50 border-purple-200">
        <CardHeader className="pb-2">
          <CardTitle className="text-purple-800 text-lg flex items-center gap-2">
            <span role="img" aria-hidden="true">
              🧠
            </span>
            心理专家
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-purple-700">
            评估压力水平和睡眠质量，提供心理神经免疫学干预建议。
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * 主聊天页面 (Requirements 17.1-17.7)
 *
 * 集成 useHealthChat Hook，实现流式数据处理、状态管理、
 * HITL 确认弹窗、错误处理和连接状态显示。
 */
export default function ChatPage() {
  // 使用 useHealthChat Hook (Requirements 17.1)
  const {
    messages,
    isLoading,
    connectionStatus,
    currentPhase,
    finalReport,
    sendMessage,
    confirmHITL,
    retry,
    pausedSessionId,
    pausedHighRiskItems,
  } = useHealthChat({
    onStatusUpdate: (status, agent) => {
      console.log(`[${agent}] ${status}`);
    },
    onIntermediate: (data) => {
      console.log("Intermediate:", data);
    },
    onPause: (sessionId, items) => {
      console.log("Paused for HITL:", sessionId, items);
    },
    onError: (error) => {
      console.error("Error:", error);
      setErrorMessage(error.message);
    },
  });

  // 错误消息状态
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  // HITL 弹窗状态 - 添加防御性检查确保 pausedHighRiskItems 是数组
  const isHITLDialogOpen =
    pausedSessionId !== null &&
    Array.isArray(pausedHighRiskItems) &&
    pausedHighRiskItems.length > 0;

  // 处理发送消息
  const handleSendMessage = async (content: string) => {
    setErrorMessage(null);
    await sendMessage(content, TEST_USER_PROFILE_ID);
  };

  // 处理 HITL 确认
  const handleHITLConfirm = async () => {
    if (pausedSessionId) {
      await confirmHITL(pausedSessionId, true);
    }
  };

  // 处理 HITL 取消
  const handleHITLCancel = async () => {
    if (pausedSessionId) {
      await confirmHITL(pausedSessionId, false);
    }
  };

  // 处理重试
  const handleRetry = async () => {
    setErrorMessage(null);
    await retry();
  };

  // 是否显示欢迎界面
  const showWelcome = messages.length === 0 && !isLoading && !finalReport;

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/30">
      {/* 页面头部 */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <Heart className="h-6 w-6 text-primary" />
            <h1 className="text-xl font-bold tracking-tight">健康顾问</h1>
          </div>
          <ConnectionStatusIndicator status={connectionStatus} onReconnect={handleRetry} />
        </div>
      </header>

      {/* 主内容区域 */}
      <main className="container mx-auto px-4 py-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* 欢迎界面 */}
          {showWelcome && (
            <div className="flex flex-col items-center justify-center space-y-8 py-12">
              <div className="text-center space-y-4">
                <h2 className="text-3xl font-bold tracking-tight">欢迎使用健康顾问</h2>
                <p className="text-lg text-muted-foreground max-w-2xl">
                  智能健康管理系统，为您提供营养学、运动康复、神经心理调节等跨学科的专业建议。
                </p>
              </div>
              <FeatureCards />
            </div>
          )}

          {/* 消息历史 */}
          {messages.length > 0 && (
            <div className="space-y-4">
              {messages.map((message) => (
                <Card
                  key={message.id}
                  className={cn(
                    "transition-all",
                    message.role === "user"
                      ? "bg-primary/5 border-primary/20 ml-8"
                      : "bg-background mr-8"
                  )}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <div
                        className={cn(
                          "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium",
                          message.role === "user"
                            ? "bg-primary text-primary-foreground"
                            : "bg-green-100 text-green-700"
                        )}
                      >
                        {message.role === "user" ? "我" : "AI"}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-muted-foreground mb-1">
                          {message.role === "user" ? "您" : "健康助手"} ·{" "}
                          {message.createdAt.toLocaleTimeString("zh-CN", {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </p>
                        <p className="whitespace-pre-wrap">{message.content}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* 加载指示器 (Requirements 17.2) */}
          {isLoading && <LoadingIndicator phase={currentPhase} />}

          {/* 错误提示 (Requirements 17.6) */}
          {errorMessage && <ErrorDisplay message={errorMessage} onRetry={handleRetry} />}

          {/* 最终报告展示 (Requirements 17.4) */}
          {finalReport && (
            <div className="space-y-6 animate-in fade-in-50 duration-500">
              {/* 深度洞察卡片 */}
              <InsightCard deepInsight={finalReport.deep_insight} isLoading={false} />

              {/* 行动计划列表 */}
              <ActionPlanList actionPlan={finalReport.action_plan} />

              {/* 随访计划 */}
              {finalReport.follow_up && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <span role="img" aria-hidden="true">
                        📅
                      </span>
                      随访计划
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground whitespace-pre-wrap">
                      {finalReport.follow_up}
                    </p>
                  </CardContent>
                </Card>
              )}

              {/* 确认状态提示 */}
              {finalReport.confirmation_status === "confirmed" && (
                <Card className="bg-green-50 border-green-200">
                  <CardContent className="flex items-center gap-3 p-4">
                    <span className="text-green-600 text-xl">✓</span>
                    <span className="text-green-700">高风险干预已确认执行</span>
                  </CardContent>
                </Card>
              )}
              {finalReport.confirmation_status === "rejected" && (
                <Card className="bg-amber-50 border-amber-200">
                  <CardContent className="flex items-center gap-3 p-4">
                    <span className="text-amber-600 text-xl">⚠</span>
                    <span className="text-amber-700">高风险干预已被取消，仅显示部分建议</span>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* 聊天输入区域 */}
          <div className="sticky bottom-4 pt-4">
            <ChatInput
              onSend={handleSendMessage}
              isLoading={isLoading}
              disabled={isHITLDialogOpen}
            />
            <p className="text-xs text-muted-foreground text-center mt-3">
              本系统仅提供健康参考建议，不构成医疗诊断。如有严重健康问题，请及时就医。
            </p>
          </div>
        </div>
      </main>

      {/* HITL 确认弹窗 (Requirements 18.1-18.9) */}
      <HITLConfirmationDialog
        isOpen={isHITLDialogOpen}
        sessionId={pausedSessionId || ""}
        highRiskItems={pausedHighRiskItems || []}
        timeoutSeconds={600}
        onConfirm={handleHITLConfirm}
        onCancel={handleHITLCancel}
      />
    </div>
  );
}
