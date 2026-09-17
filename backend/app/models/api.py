"""
API 请求/响应模型

Requirements 13.2, 14.2: 定义 API 请求和响应数据结构
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.action_item import ActionItem
from app.models.final_report import FinalReport


# Chat API Models
class ChatRequest(BaseModel):
    """聊天请求

    Requirement 13.2: user_query(字符串，最大长度2000字符) 和 user_profile_id(字符串)
    """

    user_query: str = Field(..., max_length=2000, description="用户健康咨询请求文本")
    user_profile_id: str = Field(..., description="用户画像ID")


class ChatResponse(BaseModel):
    """聊天响应 (非流式)"""

    session_id: str = Field(..., description="会话ID")
    status: str = Field(..., description="响应状态")


# Confirm API Models
class ConfirmRequest(BaseModel):
    """HITL 确认请求

    Requirement 14.2: session_id(字符串) 和 confirmed(布尔值)
    """

    session_id: str = Field(..., description="会话ID")
    confirmed: bool = Field(..., description="用户是否确认执行高风险干预")


class ConfirmResponse(BaseModel):
    """HITL 确认响应

    Requirement 14.8: status("resumed"或"terminated") 和 partial_report(仅在拒绝时包含)
    """

    status: str = Field(..., description="响应状态: 'resumed' | 'terminated'")
    partial_report: Optional[FinalReport] = Field(
        default=None, description="部分报告（仅在用户拒绝时包含）"
    )


# SSE Event Data Models
class StatusEventData(BaseModel):
    """状态事件数据

    Requirement 13.5: 包含当前处理的智能体名称和处理进度
    """

    agent_name: str = Field(..., description="当前处理的智能体名称")
    progress: str = Field(..., description="处理进度描述")
    percentage: int = Field(..., ge=0, le=100, description="进度百分比(0-100)")


class PauseEventData(BaseModel):
    """暂停事件数据

    Requirement 13.8: 包含 session_id 和需要确认的高风险干预内容
    """

    session_id: str = Field(..., description="会话ID")
    high_risk_items: List[ActionItem] = Field(
        ..., description="需要确认的高风险干预措施列表"
    )
    timeout_seconds: int = Field(default=600, description="超时时间（秒），默认10分钟")


class ErrorEventData(BaseModel):
    """错误事件数据

    Requirement 13.9: 包含错误类型标识和错误描述信息
    """

    error_type: str = Field(..., description="错误类型标识")
    error_message: str = Field(..., description="错误描述信息")
