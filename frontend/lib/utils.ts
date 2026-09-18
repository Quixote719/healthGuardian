import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * 合并 Tailwind CSS 类名，处理冲突
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * 格式化倒计时时间 (Requirements 18.3)
 * @param seconds 剩余秒数
 * @returns 格式化的时间字符串 MM:SS
 */
export function formatCountdown(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes.toString().padStart(2, "0")}:${remainingSeconds.toString().padStart(2, "0")}`;
}

/**
 * 计算指数退避延迟时间 (Requirements 17.6)
 * @param attempt 当前重试次数（从0开始）
 * @param baseDelay 基础延迟时间（毫秒），默认 2000ms
 * @returns 延迟时间（毫秒）
 */
export function getExponentialBackoffDelay(attempt: number, baseDelay: number = 2000): number {
  return baseDelay * 2 ** attempt;
}

/**
 * 延迟执行
 * @param ms 延迟毫秒数
 */
export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
