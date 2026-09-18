"""
/confirm HITL 确认 API

实现 POST /api/confirm 端点，处理用户对高风险干预的确认或拒绝响应。

Requirements: 14.1-14.11
- 14.1: 提供 /confirm POST 端点接收用户的 HITL 确认响应
- 14.2: 接收包含 session_id 和 confirmed 字段的 JSON 请求体
- 14.3: 验证对应的工作流会话存在且处于暂停状态
- 14.4: session_id 对应的会话不存在时返回 "session_not_found" 错误
- 14.5: session_id 对应的会话未处于暂停状态时返回 "session_not_paused" 错误
- 14.6: 用户确认执行时调用 resume_execution 继续工作流
- 14.7: 用户拒绝执行时终止工作流并返回部分结果
- 14.8: 返回包含 status 和 partial_report 字段的 JSON 响应体
- 14.9: 对暂停状态的会话设置10分钟超时限制
- 14.10: 会话暂停超过10分钟未收到确认时自动终止并释放资源
- 14.11: 使用 FastAPI 框架实现

Design Reference: API 设计 - HITL 确认 API
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.models.api import ConfirmRequest, ConfirmResponse
from app.models.final_report import FinalReport
from app.workflow.hitl import HITLManager, SessionStatus

# Setup logging
logger = logging.getLogger(__name__)


# Create router
router = APIRouter()


# ============================================================================
# Constants
# ============================================================================

# HITL 超时时间（分钟）(Requirement 14.9)
HITL_TIMEOUT_MINUTES = 10


# ============================================================================
# HITL Manager Import
# ============================================================================

# 从 chat 路由获取共享的 HITL 管理器
# 延迟导入以避免循环依赖
_hitl_manager: HITLManager | None = None


def _get_hitl_manager() -> HITLManager:
    """获取 HITL 管理器实例

    使用延迟导入从 chat 路由获取共享的 HITL 管理器。

    Returns:
        HITLManager: HITL 管理器实例
    """
    global _hitl_manager

    if _hitl_manager is None:
        from app.api.routes.chat import get_hitl_manager

        _hitl_manager = get_hitl_manager()

    return _hitl_manager


# ============================================================================
# API Endpoint
# ============================================================================


@router.post("/confirm", response_model=ConfirmResponse)
async def confirm_hitl(request: ConfirmRequest) -> ConfirmResponse:
    """HITL 确认端点

    处理用户对高风险干预的确认或拒绝响应。

    Requirements: 14.1-14.11
    - 14.1: 提供 /confirm POST 端点接收用户的 HITL 确认响应
    - 14.2: 接收包含 session_id 和 confirmed 字段的 JSON 请求体
    - 14.3: 验证对应的工作流会话存在且处于暂停状态

    Args:
        request: ConfirmRequest 包含 session_id 和 confirmed

    Returns:
        ConfirmResponse: 包含 status 和可选的 partial_report

    Raises:
        HTTPException:
            - 404: 会话不存在 (session_not_found)
            - 400: 会话未暂停 (session_not_paused)
            - 400: 会话超时 (session_timeout)

    Example:
        POST /api/confirm
        {
            "session_id": "sess_abc123",
            "confirmed": true
        }

        Response:
        {
            "status": "resumed",
            "partial_report": null
        }
    """
    session_id = request.session_id
    confirmed = request.confirmed

    logger.info(f"HITL confirm request: session_id={session_id}, confirmed={confirmed}")

    # 获取 HITL 管理器
    hitl_manager = _get_hitl_manager()

    # ========== 验证会话存在 (Requirement 14.3, 14.4) ==========
    session = hitl_manager.get_session(session_id)

    if session is None:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_type": "session_not_found",
                "message": "会话不存在",
            },
        )

    # ========== 验证会话处于暂停状态 (Requirement 14.3, 14.5) ==========
    if session.status != SessionStatus.PAUSED:
        logger.warning(f"Session not paused: session_id={session_id}, status={session.status}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_type": "session_not_paused",
                "message": "会话未处于暂停状态",
            },
        )

    # ========== 检查超时 (Requirement 14.9, 14.10) ==========
    is_timeout = await hitl_manager.check_timeout(
        session_id=session_id,
        timeout_minutes=HITL_TIMEOUT_MINUTES,
    )

    if is_timeout:
        logger.warning(f"Session timeout: {session_id}")

        # 自动终止超时会话 (Requirement 14.10)
        await hitl_manager.terminate_session(
            session_id=session_id,
            reason=f"timeout after {HITL_TIMEOUT_MINUTES} minutes",
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_type": "session_timeout",
                "message": f"会话已超时（{HITL_TIMEOUT_MINUTES}分钟）",
            },
        )

    # ========== 处理确认/拒绝 (Requirements 14.6, 14.7, 14.8) ==========
    if confirmed:
        # 用户确认执行 (Requirement 14.6)
        await hitl_manager.resume_workflow(
            session_id=session_id,
            confirmed=True,
        )

        logger.info(f"Workflow resumed: session_id={session_id}")

        return ConfirmResponse(
            status="resumed",
            partial_report=None,
        )
    else:
        # 用户拒绝执行 (Requirement 14.7)
        # 获取部分报告
        paused_state = session.state
        partial_report: FinalReport | None = None

        final_report = paused_state.get("final_report")
        if final_report is not None:
            if isinstance(final_report, FinalReport):
                partial_report = final_report
            elif hasattr(final_report, "model_dump"):
                # Pydantic model
                partial_report = final_report
            elif isinstance(final_report, dict):
                # 尝试转换为 FinalReport
                try:
                    partial_report = FinalReport(**final_report)
                except Exception as e:
                    logger.warning(f"Failed to convert partial report: {e}")
                    partial_report = None

        # 终止工作流
        await hitl_manager.terminate_session(
            session_id=session_id,
            reason="user rejected",
        )

        logger.info(f"Workflow terminated by user: session_id={session_id}")

        return ConfirmResponse(
            status="terminated",
            partial_report=partial_report,
        )


# ============================================================================
# Additional Endpoints
# ============================================================================


@router.get("/confirm/status/{session_id}")
async def get_confirm_status(session_id: str):
    """获取会话确认状态

    用于前端轮询检查会话状态。

    Args:
        session_id: 会话 ID

    Returns:
        dict: 包含会话状态信息
    """
    hitl_manager = _get_hitl_manager()
    session = hitl_manager.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_type": "session_not_found",
                "message": "会话不存在",
            },
        )

    # 检查是否超时
    is_timeout = await hitl_manager.check_timeout(
        session_id=session_id,
        timeout_minutes=HITL_TIMEOUT_MINUTES,
    )

    return {
        "session_id": session_id,
        "status": session.status.value,
        "reason": session.reason,
        "paused_at": session.paused_at.isoformat(),
        "elapsed_seconds": session.elapsed_seconds(),
        "timeout_seconds": HITL_TIMEOUT_MINUTES * 60,
        "remaining_seconds": max(0, HITL_TIMEOUT_MINUTES * 60 - session.elapsed_seconds()),
        "is_timeout": is_timeout,
        "high_risk_items_count": len(session.high_risk_items),
    }


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "router",
    "confirm_hitl",
    "HITL_TIMEOUT_MINUTES",
]
