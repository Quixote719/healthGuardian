"""
Health_State 状态模型
LangGraph 工作流的全局状态结构，兼容 TypedDict 状态模式

Requirements: 4.1-4.10
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Optional, TypedDict

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.models.final_report import FinalReport
    from app.models.user_profile import UserProfile


def _utc_now() -> datetime:
    """Return current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class TargetAgent(StrEnum):
    """目标智能体枚举

    Requirement 4.3: target_agent 枚举值 "nutrition"/"rehabilitation"/"neuropsychology"
    """

    NUTRITION = "nutrition"
    REHABILITATION = "rehabilitation"
    NEUROPSYCHOLOGY = "neuropsychology"


class NodeExecutionStatus(StrEnum):
    """节点执行状态枚举

    Requirement 4.7: 节点执行状态 "pending"/"running"/"completed"/"failed"/"skipped"
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SubTask(BaseModel):
    """子任务结构

    Requirement 4.3: 每个子任务包含 task_id, target_agent, task_description
    """

    task_id: str = Field(..., description="子任务唯一标识")
    target_agent: TargetAgent = Field(
        ..., description="目标智能体，枚举值 nutrition/rehabilitation/neuropsychology"
    )
    task_description: str = Field(..., description="子任务描述")


class ErrorInfo(BaseModel):
    """错误信息结构

    Requirement 4.8: 每条错误信息包含 node_name, error_type, error_message(最大1000字符), timestamp
    """

    node_name: str = Field(..., description="发生错误的节点名称")
    error_type: str = Field(..., description="错误类型标识")
    error_message: str = Field(..., max_length=1000, description="错误描述信息（最大1000字符）")
    timestamp: datetime = Field(default_factory=_utc_now, description="错误发生时间(UTC)")


class HealthState(TypedDict, total=False):
    """LangGraph 全局状态 (兼容 TypedDict)

    Requirement 4.1-4.10: LangGraph 工作流的全局状态结构
    使用 total=False 使所有字段可选，兼容 LangGraph 的状态更新模式

    Attributes:
        user_query: 用户原始查询文本（最大5000字符）(Requirement 4.1)
        user_profile: 用户健康画像对象 (Requirement 4.2)
        task_breakdown: 子任务列表 (Requirement 4.3)
        expert_responses: 专家响应字典 {agent_name: response} (Requirement 4.4)
        ui_interrupt_flag: 是否需要暂停等待用户确认 (Requirement 4.5)
        interrupt_reason: 中断原因 (Requirement 4.6)
        node_execution_status: 节点执行状态字典 (Requirement 4.7)
        error_info: 错误信息列表 (Requirement 4.8)
        final_report: 最终报告对象 (Requirement 4.9)

    Note:
        Requirement 4.10: 兼容 LangGraph 的 TypedDict 状态模式
        使用 TYPE_CHECKING 导入 UserProfile 和 FinalReport 避免循环导入
    """

    # Requirement 4.1: 用户原始查询（最大5000字符）
    user_query: str

    # Requirement 4.2: 用户健康画像
    user_profile: "UserProfile"

    # Requirement 4.3: 子任务列表
    task_breakdown: list[SubTask]

    # Requirement 4.4: 专家响应 {agent_name: response}
    expert_responses: dict[str, str]

    # Requirement 4.5: 是否需要暂停等待用户确认
    ui_interrupt_flag: bool

    # Requirement 4.6: 中断原因
    interrupt_reason: str

    # Requirement 4.7: 节点执行状态 {node_name: status}
    node_execution_status: dict[str, NodeExecutionStatus]

    # Requirement 4.8: 错误信息列表
    error_info: list[ErrorInfo]

    # Requirement 4.9: 最终报告（工作流未完成时为None）
    final_report: Optional["FinalReport"]
