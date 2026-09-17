"""
Final_Report 最终报告数据模型

Requirements 3.1-3.8: 定义综合报告数据结构
"""

from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel, Field

from app.models.action_item import ActionItem


class ConfirmationStatus(str, Enum):
    """确认状态枚举

    用于 HITL (Human-in-the-Loop) 机制的确认状态追踪
    """

    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class FinalReport(BaseModel):
    """最终报告数据结构

    Requirements:
    - 3.1: deep_insight 字段（字符串类型），存储底层心身一体病理分析文本
    - 3.2: action_plan 字段，存储 Action_Item 列表（长度范围0-50项）
    - 3.3: follow_up 字段（字符串类型），存储随访计划信息
    - 3.4: requires_confirmation 布尔字段，指示是否需要用户确认高风险干预
    - 3.5: created_at 字段（datetime类型），记录报告生成的UTC时间戳
    - 3.6: session_id 字段（字符串类型），关联 LangGraph 工作流会话
    - 3.7: confirmation_status 字段，枚举值为"pending"/"confirmed"/"rejected"
    - 3.8: 使用 Pydantic 模型定义，支持数据验证和JSON序列化
    """

    deep_insight: str = Field(..., description="底层心身一体病理分析")
    action_plan: List[ActionItem] = Field(
        default_factory=list, max_length=50, description="干预措施列表（最多50项）"
    )
    follow_up: str = Field(..., description="随访计划信息，包含复查时间和关注指标")
    requires_confirmation: bool = Field(
        default=False, description="是否需要用户确认高风险干预"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.utcnow(), description="报告生成时间(UTC)"
    )
    session_id: str = Field(..., description="LangGraph 工作流会话 ID")
    confirmation_status: ConfirmationStatus = Field(
        default=ConfirmationStatus.PENDING, description="确认状态"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "deep_insight": "根据您的健康画像分析，您当前存在以下需要关注的问题：\n\n"
                    "## 健康现状总结\n"
                    "血脂指标偏高，LDL 达到3.6mmol/L，超过正常阈值。\n\n"
                    "## 跨学科关联分析\n"
                    "高血脂与睡眠不足、压力水平较高存在关联。\n\n"
                    "## 核心问题归因\n"
                    "主要归因于饮食结构不合理和运动不足。\n\n"
                    "## 干预逻辑说明\n"
                    "建议从营养调整和运动康复两个维度进行干预。",
                    "action_plan": [
                        {
                            "category": "营养",
                            "title": "控制饱和脂肪摄入",
                            "description": "每日饱和脂肪摄入量控制在总热量的7%以下",
                            "frequency": "每日三餐",
                            "priority": "高",
                            "risk_level": "低风险",
                            "duration": "12周",
                        }
                    ],
                    "follow_up": "建议14天后复查血脂指标，重点关注LDL和总胆固醇变化",
                    "requires_confirmation": False,
                    "created_at": "2024-01-15T10:30:00Z",
                    "session_id": "sess_abc123",
                    "confirmation_status": "pending",
                }
            ]
        }
    }
