"use client";

import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { InsightCardProps } from "@/types";

/**
 * 深度洞察展示组件 (Requirements 15.1-15.8)
 *
 * 以卡片形式展示系统的深度健康分析内容，支持 Markdown 渲染、
 * 骨架屏加载状态、空状态提示和响应式布局。
 *
 * @example
 * ```tsx
 * <InsightCard
 *   deepInsight="## 健康分析\n\n您的血脂指标偏高..."
 *   isLoading={false}
 * />
 * ```
 */
export function InsightCard({
  deepInsight,
  isLoading = false,
  className,
}: InsightCardProps): React.JSX.Element {
  // Loading state - 骨架屏 (Requirements 15.5)
  if (isLoading) {
    return (
      <Card
        className={cn(
          // 响应式布局 (Requirements 15.7)
          "w-full",
          "max-w-full sm:max-w-[640px] lg:max-w-[800px]",
          "mx-auto",
          className
        )}
        role="article"
        aria-busy="true"
        aria-label="深度洞察加载中"
      >
        <CardHeader>
          {/* 使用 h2 标签满足 WCAG 2.1 AA 可访问性要求 (Requirements 15.8) */}
          <h2 className="text-xl font-semibold leading-none tracking-tight text-foreground">
            深度洞察
          </h2>
        </CardHeader>
        <CardContent>
          {/* 3行文本占位符动画 (Requirements 15.5) */}
          <div className="space-y-3" aria-hidden="true">
            <div className="h-4 w-full rounded bg-muted animate-pulse" />
            <div className="h-4 w-5/6 rounded bg-muted animate-pulse" />
            <div className="h-4 w-4/6 rounded bg-muted animate-pulse" />
          </div>
          <span className="sr-only">正在加载深度洞察内容...</span>
        </CardContent>
      </Card>
    );
  }

  // Empty state (Requirements 15.6)
  if (!deepInsight || deepInsight.trim() === "") {
    return (
      <Card
        className={cn(
          // 响应式布局 (Requirements 15.7)
          "w-full",
          "max-w-full sm:max-w-[640px] lg:max-w-[800px]",
          "mx-auto",
          className
        )}
        role="article"
        aria-label="深度洞察"
      >
        <CardHeader>
          {/* 使用 h2 标签满足 WCAG 2.1 AA 可访问性要求 (Requirements 15.8) */}
          <h2 className="text-xl font-semibold leading-none tracking-tight text-foreground">
            深度洞察
          </h2>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-4">
            暂无分析内容
          </p>
        </CardContent>
      </Card>
    );
  }

  // Normal state with Markdown content (Requirements 15.2, 15.3)
  return (
    <Card
      className={cn(
        // 响应式布局 (Requirements 15.7)
        "w-full",
        "max-w-full sm:max-w-[640px] lg:max-w-[800px]",
        "mx-auto",
        className
      )}
      role="article"
      aria-label="深度洞察"
    >
      <CardHeader>
        {/* 使用 h2 标签满足 WCAG 2.1 AA 可访问性要求 (Requirements 15.8) */}
        <h2 className="text-xl font-semibold leading-none tracking-tight text-foreground">
          深度洞察
        </h2>
      </CardHeader>
      <CardContent>
        {/* Markdown 渲染 (Requirements 15.3) */}
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              // h1-h4 标题样式 (Requirements 15.3)
              h1: ({ children, ...props }) => (
                <h3
                  className="text-lg font-bold mt-6 mb-3 text-foreground"
                  {...props}
                >
                  {children}
                </h3>
              ),
              h2: ({ children, ...props }) => (
                <h4
                  className="text-base font-bold mt-5 mb-2 text-foreground"
                  {...props}
                >
                  {children}
                </h4>
              ),
              h3: ({ children, ...props }) => (
                <h5
                  className="text-sm font-semibold mt-4 mb-2 text-foreground"
                  {...props}
                >
                  {children}
                </h5>
              ),
              h4: ({ children, ...props }) => (
                <h6
                  className="text-sm font-medium mt-3 mb-1 text-foreground"
                  {...props}
                >
                  {children}
                </h6>
              ),
              // 有序和无序列表 (Requirements 15.3)
              ul: ({ children, ...props }) => (
                <ul
                  className="list-disc list-inside my-2 space-y-1 text-foreground"
                  {...props}
                >
                  {children}
                </ul>
              ),
              ol: ({ children, ...props }) => (
                <ol
                  className="list-decimal list-inside my-2 space-y-1 text-foreground"
                  {...props}
                >
                  {children}
                </ol>
              ),
              li: ({ children, ...props }) => (
                <li className="text-sm leading-relaxed" {...props}>
                  {children}
                </li>
              ),
              // 粗体和斜体 (Requirements 15.3)
              strong: ({ children, ...props }) => (
                <strong className="font-semibold text-foreground" {...props}>
                  {children}
                </strong>
              ),
              em: ({ children, ...props }) => (
                <em className="italic" {...props}>
                  {children}
                </em>
              ),
              // 代码块 (Requirements 15.3)
              code: ({ children, className: codeClassName, ...props }) => {
                // Check if it's an inline code or code block
                const isInline = !codeClassName;
                if (isInline) {
                  return (
                    <code
                      className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono text-foreground"
                      {...props}
                    >
                      {children}
                    </code>
                  );
                }
                return (
                  <code
                    className={cn(
                      "block bg-muted p-3 rounded-md text-sm font-mono overflow-x-auto",
                      codeClassName
                    )}
                    {...props}
                  >
                    {children}
                  </code>
                );
              },
              pre: ({ children, ...props }) => (
                <pre
                  className="bg-muted p-3 rounded-md overflow-x-auto my-3"
                  {...props}
                >
                  {children}
                </pre>
              ),
              // 段落样式，确保文本对比度 (Requirements 15.8)
              p: ({ children, ...props }) => (
                <p
                  className="text-sm leading-relaxed my-2 text-foreground"
                  {...props}
                >
                  {children}
                </p>
              ),
              // 引用块
              blockquote: ({ children, ...props }) => (
                <blockquote
                  className="border-l-4 border-muted-foreground/30 pl-4 my-3 italic text-muted-foreground"
                  {...props}
                >
                  {children}
                </blockquote>
              ),
              // 分隔线
              hr: (props) => (
                <hr className="my-4 border-muted" {...props} />
              ),
              // 链接
              a: ({ children, href, ...props }) => (
                <a
                  href={href}
                  className="text-primary underline underline-offset-2 hover:text-primary/80"
                  target="_blank"
                  rel="noopener noreferrer"
                  {...props}
                >
                  {children}
                </a>
              ),
            }}
          >
            {deepInsight}
          </ReactMarkdown>
        </div>
      </CardContent>
    </Card>
  );
}

export default InsightCard;
