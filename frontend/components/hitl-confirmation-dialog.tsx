"use client";

import { AlertTriangle, Loader2 } from "lucide-react";
import * as React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn, formatCountdown } from "@/lib/utils";
import type { ActionCategory, ActionItem, HITLConfirmationDialogProps } from "@/types";
import { CATEGORY_ICONS } from "@/types";

/**
 * 获取分类颜色配置
 */
const getCategoryColors = (category: ActionCategory) => {
  const colors: Record<
    ActionCategory,
    { bgClass: string; borderClass: string; textClass: string }
  > = {
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
  return colors[category];
};

/**
 * 高风险干预措施项组件
 */
function HighRiskItem({ item }: { item: ActionItem }) {
  const colors = getCategoryColors(item.category);
  const icon = CATEGORY_ICONS[item.category];

  return (
    <Card className={cn("border-l-4", colors.borderClass, colors.bgClass, "transition-colors")}>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <span className="text-xl" aria-hidden="true">
            {icon}
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span
                className={cn(
                  "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                  colors.textClass,
                  colors.bgClass
                )}
              >
                {item.category}
              </span>
              <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">
                {item.risk_level}
              </span>
            </div>
            <h4 className="font-semibold text-gray-900 mb-1">{item.title}</h4>
            <p className="text-sm text-gray-600 line-clamp-2">{item.description}</p>
            <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
              <span>频率: {item.frequency}</span>
              <span>持续: {item.duration}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * HITL 确认弹窗组件 (Requirements 18.1-18.9)
 *
 * 用于显示需要用户确认的高风险干预措施，支持倒计时、键盘交互和加载状态。
 */
export function HITLConfirmationDialog({
  isOpen,
  sessionId: _sessionId,
  highRiskItems,
  timeoutSeconds = 600,
  onConfirm,
  onCancel,
}: HITLConfirmationDialogProps) {
  // 剩余秒数状态
  const [remainingSeconds, setRemainingSeconds] = React.useState(timeoutSeconds);
  // 加载状态
  const [isConfirming, setIsConfirming] = React.useState(false);
  const [isCancelling, setIsCancelling] = React.useState(false);

  // 引用确认按钮以便聚焦
  const confirmButtonRef = React.useRef<HTMLButtonElement>(null);

  // 使用 ref 跟踪 onCancel 回调，避免闭包问题
  const onCancelRef = React.useRef(onCancel);
  React.useEffect(() => {
    onCancelRef.current = onCancel;
  }, [onCancel]);

  // 是否有任何操作正在进行
  const isLoading = isConfirming || isCancelling;

  // 处理确认操作 (Requirements 18.6, 18.7)
  const handleConfirm = React.useCallback(async () => {
    if (isConfirming || isCancelling) return;

    setIsConfirming(true);
    try {
      await onConfirm();
    } finally {
      setIsConfirming(false);
    }
  }, [isConfirming, isCancelling, onConfirm]);

  // 处理取消操作 (Requirements 18.6, 18.7)
  const handleCancel = React.useCallback(async () => {
    if (isConfirming || isCancelling) return;

    setIsCancelling(true);
    try {
      await onCancelRef.current();
    } finally {
      setIsCancelling(false);
    }
  }, [isConfirming, isCancelling]);

  // 当弹窗打开时重置倒计时
  // 这是一个有意的同步状态重置，用于响应 prop 变化重置组件内部状态
  React.useEffect(() => {
    if (isOpen) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional state reset when dialog opens
      setRemainingSeconds(timeoutSeconds);
      setIsConfirming(false);
      setIsCancelling(false);
    }
  }, [isOpen, timeoutSeconds]);

  // 倒计时逻辑 (Requirements 18.3, 18.4)
  React.useEffect(() => {
    if (!isOpen || isLoading) return;

    const timer = setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          // 倒计时归零，自动提交拒绝响应
          clearInterval(timer);
          // 直接调用 onCancel ref 以避免依赖循环
          setIsCancelling(true);
          onCancelRef.current().finally(() => {
            setIsCancelling(false);
          });
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isOpen, isLoading]);

  // 键盘交互处理 (Requirements 18.8)
  React.useEffect(() => {
    if (!isOpen || isLoading) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Enter") {
        event.preventDefault();
        handleConfirm();
      } else if (event.key === "Escape") {
        event.preventDefault();
        handleCancel();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isLoading, handleConfirm, handleCancel]);

  // 弹窗打开时聚焦到确认按钮
  React.useEffect(() => {
    if (isOpen && confirmButtonRef.current) {
      // 延迟聚焦以确保动画完成
      const timer = setTimeout(() => {
        confirmButtonRef.current?.focus();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  // 格式化倒计时显示
  const formattedTime = formatCountdown(remainingSeconds);

  // 计算倒计时警告样式（最后2分钟显示警告色）
  const isUrgent = remainingSeconds <= 120;

  return (
    <Dialog open={isOpen} modal>
      <DialogContent
        className="sm:max-w-[600px] max-h-[90vh] overflow-hidden flex flex-col"
        onPointerDownOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => {
          e.preventDefault();
          if (!isLoading) {
            handleCancel();
          }
        }}
        aria-describedby="hitl-dialog-description"
      >
        {/* 标题区域 (Requirements 18.2) */}
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <AlertTriangle className="h-5 w-5 text-amber-500" aria-hidden="true" />
            高风险干预确认
          </DialogTitle>
          <DialogDescription id="hitl-dialog-description">
            以下干预措施被标记为高风险，请仔细阅读并确认是否执行。
          </DialogDescription>
        </DialogHeader>

        {/* 倒计时提示 (Requirements 18.3) */}
        <div
          className={cn(
            "flex items-center justify-center gap-2 py-2 px-4 rounded-md text-sm font-medium",
            isUrgent ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-800"
          )}
          role="timer"
          aria-live="polite"
          aria-label={`剩余时间 ${formattedTime}`}
        >
          <span>请在</span>
          <span className="font-mono text-lg font-bold">{formattedTime}</span>
          <span>内完成确认，超时将自动取消</span>
        </div>

        {/* 内容区域 - 高风险干预措施列表 (Requirements 18.2) */}
        <div className="flex-1 overflow-y-auto py-4 -mx-6 px-6">
          <ul className="space-y-3" aria-label="高风险干预措施列表">
            {highRiskItems.map((item, index) => (
              <li key={`${item.title}-${index}`}>
                <HighRiskItem item={item} />
              </li>
            ))}
          </ul>
          {highRiskItems.length === 0 && (
            <p className="text-center text-gray-500 py-8">暂无需要确认的高风险干预措施</p>
          )}
        </div>

        {/* 底部区域 - 操作按钮 (Requirements 18.5, 18.6) */}
        <DialogFooter className="flex-shrink-0 gap-2 sm:gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={handleCancel}
            disabled={isLoading}
            className="min-w-[100px]"
          >
            {isCancelling ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                处理中...
              </>
            ) : (
              "取消"
            )}
          </Button>
          <Button
            ref={confirmButtonRef}
            type="button"
            onClick={handleConfirm}
            disabled={isLoading}
            className="min-w-[100px] bg-blue-600 hover:bg-blue-700"
          >
            {isConfirming ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                处理中...
              </>
            ) : (
              "确认执行"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
