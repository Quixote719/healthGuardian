"use client";

import * as React from "react";
import type {
  UseHealthChatOptions,
  UseHealthChatReturn,
  ChatMessage,
  FinalReport,
  ActionItem,
  ConnectionStatus,
  SSEEventType,
  StatusEventData,
  IntermediateEventData,
  PauseEventData,
  ErrorEventData,
} from "@/types";
import { getExponentialBackoffDelay, delay } from "@/lib/utils";

/**
 * API 基础 URL
 */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * 最大自动重试次数 (Requirements 17.6)
 */
const MAX_RETRIES = 3;

/**
 * 生成简单的唯一 ID
 */
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * useHealthChat Hook (Requirements 17.1-17.8)
 *
 * 处理 SSE 流式数据、状态管理和 HITL 确认机制的 React Hook。
 *
 * @param options - 可选的回调配置
 * @returns 聊天状态和操作方法
 */
export function useHealthChat(options?: UseHealthChatOptions): UseHealthChatReturn {
  const { onStatusUpdate, onIntermediate, onPause, onError } = options || {};

  // 状态管理 (Requirements 17.7)
  const [messages, setMessages] = React.useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const [connectionStatus, setConnectionStatus] = React.useState<ConnectionStatus>("disconnected");
  const [currentPhase, setCurrentPhase] = React.useState<string>("");
  const [finalReport, setFinalReport] = React.useState<FinalReport | null>(null);

  // 内部状态
  const [currentSessionId, setCurrentSessionId] = React.useState<string | null>(null);
  const [retryCount, setRetryCount] = React.useState(0);
  const [lastRequest, setLastRequest] = React.useState<{ content: string; userProfileId: string } | null>(null);

  // HITL 暂停状态
  const [pausedSessionId, setPausedSessionId] = React.useState<string | null>(null);
  const [pausedHighRiskItems, setPausedHighRiskItems] = React.useState<ActionItem[]>([]);

  // AbortController 引用用于取消请求
  const abortControllerRef = React.useRef<AbortController | null>(null);

  // 使用 ref 跟踪回调函数，避免闭包问题
  const onStatusUpdateRef = React.useRef(onStatusUpdate);
  const onIntermediateRef = React.useRef(onIntermediate);
  const onPauseRef = React.useRef(onPause);
  const onErrorRef = React.useRef(onError);

  React.useEffect(() => {
    onStatusUpdateRef.current = onStatusUpdate;
    onIntermediateRef.current = onIntermediate;
    onPauseRef.current = onPause;
    onErrorRef.current = onError;
  }, [onStatusUpdate, onIntermediate, onPause, onError]);

  /**
   * 关闭 SSE 连接
   */
  const closeConnection = React.useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  /**
   * 处理 SSE 事件
   */
  const handleSSEEvent = React.useCallback((eventType: string, data: string) => {
    try {
      const parsedData = JSON.parse(data);
      // 后端发送的数据格式为 {"data": {...}, "timestamp": "..."}
      // 实际数据在 .data 字段中
      const eventData = parsedData.data || parsedData;

      switch (eventType as SSEEventType) {
        case "status": {
          const statusData = eventData as StatusEventData;
          setCurrentPhase(`${statusData.agent_name}: ${statusData.progress}`);
          onStatusUpdateRef.current?.(statusData.progress, statusData.agent_name);
          break;
        }

        case "intermediate": {
          const intermediateData = eventData as IntermediateEventData;
          onIntermediateRef.current?.(intermediateData);
          break;
        }

        case "report": {
          const report = eventData as FinalReport;
          setFinalReport(report);
          setIsLoading(false);
          setCurrentPhase("");
          
          // 添加 assistant 消息
          const assistantMessage: ChatMessage = {
            id: generateId(),
            role: "assistant",
            content: report.deep_insight,
            createdAt: new Date(report.created_at),
            report,
          };
          setMessages((prev) => [...prev, assistantMessage]);
          break;
        }

        case "pause": {
          const pauseData = eventData as PauseEventData;
          setPausedSessionId(pauseData.session_id);
          // 确保 high_risk_items 是数组
          const items = Array.isArray(pauseData.high_risk_items) ? pauseData.high_risk_items : [];
          setPausedHighRiskItems(items);
          setCurrentPhase("等待用户确认高风险干预...");
          onPauseRef.current?.(pauseData.session_id, items);
          break;
        }

        case "error": {
          const errorData = eventData as ErrorEventData;
          const error = new Error(errorData.error_message);
          setIsLoading(false);
          setCurrentPhase("");
          onErrorRef.current?.(error);
          break;
        }

        case "heartbeat":
          // 心跳事件，保持连接活跃
          break;

        default:
          console.warn(`Unknown SSE event type: ${eventType}`);
      }
    } catch (parseError) {
      console.error("Failed to parse SSE data:", parseError);
    }
  }, []);

  /**
   * 发送消息 (Requirements 17.1)
   */
  const sendMessage = React.useCallback(
    async (content: string, userProfileId: string) => {
      // 保存请求以便重试
      setLastRequest({ content, userProfileId });
      setRetryCount(0);

      // 添加用户消息
      const userMessage: ChatMessage = {
        id: generateId(),
        role: "user",
        content,
        createdAt: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // 重置状态
      setIsLoading(true);
      setFinalReport(null);
      setCurrentPhase("正在连接...");
      setPausedSessionId(null);
      setPausedHighRiskItems([]);

      // 关闭旧连接
      closeConnection();

      // 创建新的 AbortController
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      try {
        setConnectionStatus("connected");

        // 使用 fetch + ReadableStream 处理 SSE
        const response = await fetch(`${API_BASE_URL}/api/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify({
            user_query: content,
            user_profile_id: userProfileId,
          }),
          signal: abortController.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        // 从响应头获取 session_id
        const sessionId = response.headers.get("X-Session-ID") || generateId();
        setCurrentSessionId(sessionId);

        // 读取 SSE 流
        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("No response body");
        }

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // 解析 SSE 事件
          const lines = buffer.split("\n");
          buffer = lines.pop() || ""; // 保留未完成的行

          let currentEventType = "";
          let currentData = "";

          for (const line of lines) {
            if (line.startsWith("event:")) {
              currentEventType = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              currentData = line.slice(5).trim();
              if (currentEventType && currentData) {
                handleSSEEvent(currentEventType, currentData);
                currentEventType = "";
                currentData = "";
              }
            } else if (line === "" && currentEventType && currentData) {
              handleSSEEvent(currentEventType, currentData);
              currentEventType = "";
              currentData = "";
            }
          }
        }

        setIsLoading(false);
        setConnectionStatus("disconnected");
      } catch (error) {
        // 忽略中止错误
        if ((error as Error).name === "AbortError") {
          return;
        }

        console.error("SSE connection error:", error);
        setConnectionStatus("disconnected");
        setIsLoading(false);

        const err = error instanceof Error ? error : new Error("Unknown error");
        onErrorRef.current?.(err);
      }
    },
    [closeConnection, handleSSEEvent]
  );

  /**
   * 提交 HITL 确认/拒绝 (Requirements 17.1)
   */
  const confirmHITL = React.useCallback(
    async (sessionId: string, confirmed: boolean) => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/confirm`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            session_id: sessionId,
            confirmed,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
        }

        const result = await response.json();

        // 清除暂停状态
        setPausedSessionId(null);
        setPausedHighRiskItems([]);

        if (result.status === "terminated" && result.partial_report) {
          // 用户拒绝，显示部分报告
          setFinalReport(result.partial_report);
          setIsLoading(false);
          setCurrentPhase("");

          const assistantMessage: ChatMessage = {
            id: generateId(),
            role: "assistant",
            content: result.partial_report.deep_insight,
            createdAt: new Date(result.partial_report.created_at),
            report: result.partial_report,
          };
          setMessages((prev) => [...prev, assistantMessage]);
        } else if (result.status === "resumed") {
          // 用户确认，工作流继续
          setCurrentPhase("工作流已恢复，继续处理中...");
        }
      } catch (error) {
        console.error("HITL confirm error:", error);
        const err = error instanceof Error ? error : new Error("Unknown error");
        onErrorRef.current?.(err);
      }
    },
    []
  );

  /**
   * 手动重试 (Requirements 17.6)
   */
  const retry = React.useCallback(async () => {
    if (!lastRequest) {
      console.warn("No previous request to retry");
      return;
    }

    if (retryCount >= MAX_RETRIES) {
      console.warn("Max retries reached");
      onErrorRef.current?.(new Error("已达到最大重试次数，请稍后再试"));
      return;
    }

    // 指数退避延迟 (Requirements 17.6: 2秒, 4秒, 8秒)
    const backoffDelay = getExponentialBackoffDelay(retryCount);
    setConnectionStatus("reconnecting");
    setCurrentPhase(`正在重试... (${retryCount + 1}/${MAX_RETRIES})`);

    await delay(backoffDelay);

    setRetryCount((prev) => prev + 1);
    await sendMessage(lastRequest.content, lastRequest.userProfileId);
  }, [lastRequest, retryCount, sendMessage]);

  // 清理连接
  React.useEffect(() => {
    return () => {
      closeConnection();
    };
  }, [closeConnection]);

  return {
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
  };
}

export default useHealthChat;
