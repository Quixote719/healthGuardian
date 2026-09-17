"""
Action_Item 干预措施数据模型

Requirements 2.1-2.9: 定义标准化的干预措施数据结构
"""

import re
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ActionCategory(str, Enum):
    """干预措施类别枚举"""

    NUTRITION = "营养"
    REHABILITATION = "康复"
    NEUROPSYCHOLOGY = "神经心理"


class Priority(str, Enum):
    """优先级枚举"""

    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


class RiskLevel(str, Enum):
    """风险等级枚举"""

    HIGH = "高风险"
    MEDIUM = "中风险"
    LOW = "低风险"


class ActionItem(BaseModel):
    """干预措施数据结构

    Requirements:
    - 2.1: category 字段，取值限定为"营养"、"康复"或"神经心理"
    - 2.2: title 字段，长度1-100字符
    - 2.3: description 字段，长度1-2000字符
    - 2.4: frequency 字段，长度1-200字符
    - 2.5: priority 字段，取值限定为"高"、"中"或"低"
    - 2.6: risk_level 字段，取值限定为"高风险"、"中风险"或"低风险"
    - 2.7: duration 字段，格式为正整数+时间单位(天/周/月)
    - 2.8: 字段值不符合验证规则时抛出 ValidationError
    - 2.9: 使用 Pydantic 模型定义，支持数据验证和JSON序列化
    """

    category: ActionCategory = Field(..., description="干预措施类别")
    title: str = Field(..., min_length=1, max_length=100, description="干预措施名称")
    description: str = Field(
        ..., min_length=1, max_length=2000, description="干预措施详细说明"
    )
    frequency: str = Field(..., min_length=1, max_length=200, description="执行频率")
    priority: Priority = Field(..., description="优先级")
    risk_level: RiskLevel = Field(..., description="风险等级")
    duration: str = Field(..., description="预期持续时间，格式: 正整数+时间单位(天/周/月)")

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v: str) -> str:
        """验证 duration 格式必须为: 正整数+时间单位(天/周/月)
        
        正整数定义: 大于0的整数，不允许前导零
        有效示例: "7天", "2周", "3月", "14 天"
        无效示例: "0天", "01天", "-1周"
        """
        # [1-9]: 第一位必须是1-9（排除0和前导零）
        # \d*: 后续可以是0个或多个数字（允许10, 100等）
        pattern = r"^[1-9]\d*\s*(天|周|月)$"
        if not re.match(pattern, v):
            raise ValueError("duration 格式必须为: 正整数+时间单位(天/周/月)，例如: '12周'、'30天'、'3月'")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "category": "营养",
                    "title": "控制饱和脂肪摄入",
                    "description": "每日饱和脂肪摄入量控制在总热量的7%以下，避免油炸食品和动物内脏。",
                    "frequency": "每日三餐",
                    "priority": "高",
                    "risk_level": "低风险",
                    "duration": "12周",
                }
            ]
        }
    }
