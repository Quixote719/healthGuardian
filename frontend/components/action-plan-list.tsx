"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import {
  type ActionCategory,
  type ActionItem,
  type ActionPlanListProps,
  CATEGORY_COLORS,
  CATEGORY_ICONS,
  CATEGORY_ORDER,
} from "@/types";

/**
 * 按分类分组 Action Items
 */
function groupByCategory(
  actionPlan: ActionItem[] | undefined | null
): Record<ActionCategory, ActionItem[]> {
  const grouped: Record<ActionCategory, ActionItem[]> = {
    营养: [],
    康复: [],
    神经心理: [],
  };

  if (!Array.isArray(actionPlan)) {
    return grouped;
  }

  actionPlan.forEach((item) => {
    if (item && grouped[item.category]) {
      grouped[item.category].push(item);
    }
  });

  return grouped;
}

/**
 * 优先级标签组件
 */
function PriorityBadge({ priority }: { priority: ActionItem["priority"] }) {
  const priorityStyles = {
    高: "bg-red-100 text-red-800 border-red-300",
    中: "bg-yellow-100 text-yellow-800 border-yellow-300",
    低: "bg-gray-100 text-gray-800 border-gray-300",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border",
        priorityStyles[priority]
      )}
    >
      {priority}优先级
    </span>
  );
}

/**
 * 风险等级标签组件
 */
function RiskLevelBadge({ riskLevel }: { riskLevel: ActionItem["risk_level"] }) {
  const riskStyles = {
    高风险: "bg-red-100 text-red-800 border-red-300",
    中风险: "bg-orange-100 text-orange-800 border-orange-300",
    低风险: "bg-green-100 text-green-800 border-green-300",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border",
        riskStyles[riskLevel]
      )}
    >
      {riskLevel}
    </span>
  );
}

/**
 * 单个 Action Item 卡片
 */
function ActionItemCard({
  item,
  categoryColor,
}: {
  item: ActionItem;
  categoryColor: (typeof CATEGORY_COLORS)[ActionCategory];
}) {
  return (
    <div className={cn("p-4 rounded-lg border-l-4 bg-white shadow-sm", categoryColor.borderClass)}>
      {/* 标题 */}
      <h4 className="font-semibold text-gray-900 mb-2">{item.title}</h4>

      {/* 描述 */}
      <p className="text-gray-600 text-sm mb-3 leading-relaxed">{item.description}</p>

      {/* 标签区域 */}
      <div className="flex flex-wrap gap-2 items-center">
        {/* 执行频率 */}
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
          📅 {item.frequency}
        </span>

        {/* 持续时间 */}
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200">
          ⏱️ {item.duration}
        </span>

        {/* 优先级 */}
        <PriorityBadge priority={item.priority} />

        {/* 风险等级 */}
        <RiskLevelBadge riskLevel={item.risk_level} />
      </div>
    </div>
  );
}

/**
 * 分类折叠面板
 */
function CategorySection({
  category,
  items,
  defaultExpanded,
}: {
  category: ActionCategory;
  items: ActionItem[];
  defaultExpanded: boolean;
}) {
  const [isOpen, setIsOpen] = React.useState(defaultExpanded);
  const colorConfig = CATEGORY_COLORS[category];
  const icon = CATEGORY_ICONS[category];

  if (items.length === 0) {
    return null;
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="w-full">
      <CollapsibleTrigger
        className={cn(
          "flex items-center justify-between w-full p-4 rounded-lg transition-colors duration-200",
          "hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2",
          colorConfig.bgClass,
          `focus:ring-${category === "营养" ? "green" : category === "康复" ? "blue" : "purple"}-500`
        )}
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl" role="img" aria-hidden="true">
            {icon}
          </span>
          <span className={cn("font-semibold text-lg", colorConfig.textClass)}>{category}</span>
          <span
            className={cn(
              "inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-medium",
              colorConfig.bgClass,
              colorConfig.textClass,
              "border",
              colorConfig.borderClass
            )}
          >
            {items.length}
          </span>
        </div>
        <div className={cn("transition-transform duration-200", colorConfig.textClass)}>
          {isOpen ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
        </div>
      </CollapsibleTrigger>

      <CollapsibleContent className="overflow-hidden data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
        <div className="pt-3 space-y-3">
          {items.map((item, index) => (
            <ActionItemCard
              key={`${category}-${index}-${item.title}`}
              item={item}
              categoryColor={colorConfig}
            />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

/**
 * 空状态组件 (Requirements 16.7)
 */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
        <span className="text-3xl" role="img" aria-label="没有数据">
          📋
        </span>
      </div>
      <h3 className="text-lg font-medium text-gray-900 mb-2">暂无行动计划</h3>
      <p className="text-sm text-gray-500">系统正在分析中，请稍候</p>
    </div>
  );
}

/**
 * Action_Plan_List 行动计划展示组件
 *
 * 以结构化方式展示所有干预措施建议，按分类（营养、康复、神经心理）分组
 *
 * @param actionPlan - Action_Item 数组，必填
 * @param defaultExpandedCategories - 默认展开的分类列表，默认全部展开
 * @param className - 自定义样式类名
 *
 * Requirements: 16.1-16.9
 * Design: Components and Interfaces - Action_Plan_List 组件接口
 */
export function ActionPlanList({
  actionPlan,
  defaultExpandedCategories,
  className,
}: ActionPlanListProps) {
  // 确保 actionPlan 是数组
  const safeActionPlan = Array.isArray(actionPlan) ? actionPlan : [];

  // 如果没有指定默认展开的分类，则全部展开
  const expandedCategories = defaultExpandedCategories ?? CATEGORY_ORDER;

  // 按分类分组
  const groupedItems = groupByCategory(safeActionPlan);

  // 检查是否有任何项目
  const hasItems = safeActionPlan.length > 0;

  // 检查分类是否应该默认展开
  const isDefaultExpanded = (category: ActionCategory) => expandedCategories.includes(category);

  return (
    <Card className={cn("w-full", className)} role="region" aria-label="行动计划列表">
      <CardHeader className="pb-4">
        <CardTitle className="text-xl font-bold flex items-center gap-2">
          <span role="img" aria-hidden="true">
            📝
          </span>
          行动计划
          {hasItems && (
            <span className="text-sm font-normal text-muted-foreground">
              （共 {safeActionPlan.length} 项）
            </span>
          )}
        </CardTitle>
      </CardHeader>

      <CardContent>
        {!hasItems ? (
          <EmptyState />
        ) : (
          <div
            className={cn(
              // 响应式布局：移动端单列，桌面端双列网格 (Requirements 16.9)
              "grid gap-4",
              "grid-cols-1 sm:grid-cols-1 md:grid-cols-2"
            )}
          >
            {CATEGORY_ORDER.map((category) => (
              <CategorySection
                key={category}
                category={category}
                items={groupedItems[category]}
                defaultExpanded={isDefaultExpanded(category)}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default ActionPlanList;
