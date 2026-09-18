"""
HITL (Human-in-the-Loop) Interrupt/Resume 机制

实现工作流的暂停和恢复功能，用于高风险干预的用户确认。

Requirements: 10.3-10.6
- 10.3: 当 Controller_Agent 完成执行且 ui_interrupt_flag 为 true 时，使用 LangGraph interrupt 机制暂停工作流
- 10.4: 提供 resume_execution 函数，接收用户确认后继续执行暂停的工作流
- 10.5: 工作流暂停状态下保持 Health_State 不变，最长保持30分钟
- 10.6: 暂停状态超过30分钟未收到确认，自动终止会话并释放资源

Design Reference: HITL Interrupt/Resume 机制
"""

import asyncio
import contextlib
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from app.models.final_report import ConfirmationStatus
from app.models.state import HealthState

# Handle LangGraph import - may not be installed in all environments
try:
    from langgraph.checkpoint.base import BaseCheckpointSaver

    LANGGRAPH_CHECKPOINTER_AVAILABLE = True
except ImportError:
    LANGGRAPH_CHECKPOINTER_AVAILABLE = False

    class BaseCheckpointSaver:
        """Mock BaseCheckpointSaver for environments without LangGraph"""

        pass


# Setup logging
logger = logging.getLogger(__name__)


class SessionStatus(StrEnum):
    """会话状态枚举"""

    ACTIVE = "active"  # 正在执行中
    PAUSED = "paused"  # 暂停等待确认
    RESUMED = "resumed"  # 已恢复执行
    TERMINATED = "terminated"  # 已终止（超时或用户拒绝）
    COMPLETED = "completed"  # 正常完成


class PausedSession:
    """暂停会话的数据结构"""

    def __init__(
        self,
        session_id: str,
        state: HealthState,
        reason: str,
        high_risk_items: list[Any] | None = None,
    ):
        self.session_id = session_id
        self.state = state
        self.reason = reason
        self.high_risk_items = high_risk_items or []
        self.paused_at = datetime.now(UTC)
        self.status = SessionStatus.PAUSED

    def elapsed_seconds(self) -> float:
        """计算暂停已经过的秒数"""
        now = datetime.now(UTC)
        return (now - self.paused_at).total_seconds()

    def elapsed_minutes(self) -> float:
        """计算暂停已经过的分钟数"""
        return self.elapsed_seconds() / 60

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "state": self.state,
            "reason": self.reason,
            "high_risk_items": self.high_risk_items,
            "paused_at": self.paused_at.isoformat(),
            "status": self.status.value,
            "elapsed_seconds": self.elapsed_seconds(),
        }


class HITLManager:
    """Human-in-the-Loop 管理器

    管理工作流的暂停、恢复和超时逻辑。

    Requirements:
    - 10.3: 支持暂停工作流等待用户确认
    - 10.4: 支持恢复工作流执行
    - 10.5: 暂停状态下保持状态不变，最长30分钟
    - 10.6: 超时后自动终止会话

    Attributes:
        checkpointer: LangGraph 检查点保存器（可选）
        max_pause_minutes: 最长暂停时间（分钟），默认30分钟
        _paused_sessions: 暂停会话的存储字典
        _cleanup_task: 后台清理任务
        _on_timeout_callback: 超时回调函数

    Example:
        >>> from app.workflow.hitl import HITLManager
        >>>
        >>> # 创建 HITL 管理器
        >>> manager = HITLManager()
        >>>
        >>> # 暂停工作流
        >>> await manager.pause_workflow(
        ...     session_id="sess_123",
        ...     state=current_state,
        ...     reason="检测到高风险干预"
        ... )
        >>>
        >>> # 检查超时
        >>> is_timeout = await manager.check_timeout("sess_123")
        >>>
        >>> # 用户确认后恢复
        >>> resumed_state = await manager.resume_workflow("sess_123", confirmed=True)
    """

    # 默认最大暂停时间：30分钟 (Requirement 10.5)
    DEFAULT_MAX_PAUSE_MINUTES = 30

    def __init__(
        self,
        checkpointer: BaseCheckpointSaver | None = None,
        max_pause_minutes: int = DEFAULT_MAX_PAUSE_MINUTES,
    ):
        """初始化 HITL 管理器

        Args:
            checkpointer: LangGraph 检查点保存器，用于持久化状态
            max_pause_minutes: 最长暂停时间（分钟），默认30分钟
        """
        self.checkpointer = checkpointer
        self.max_pause_minutes = max_pause_minutes
        self._paused_sessions: dict[str, PausedSession] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._on_timeout_callback: Callable | None = None
        self._running = False

    # ========================================================================
    # Core HITL Operations
    # ========================================================================

    async def pause_workflow(
        self,
        session_id: str,
        state: HealthState,
        reason: str,
        high_risk_items: list[Any] | None = None,
    ) -> None:
        """暂停工作流等待用户确认

        将工作流状态保存到暂停会话存储中，等待用户确认。

        Requirements:
        - 10.3: 暂停工作流等待用户确认
        - 10.5: 保持 Health_State 状态不变

        Args:
            session_id: 会话 ID
            state: 当前的 HealthState 状态
            reason: 暂停原因
            high_risk_items: 需要确认的高风险干预列表

        Raises:
            ValueError: 如果 session_id 为空

        Example:
            >>> await manager.pause_workflow(
            ...     session_id="sess_123",
            ...     state=current_state,
            ...     reason="检测到高风险干预：停药建议",
            ...     high_risk_items=[action_item_1, action_item_2]
            ... )
        """
        if not session_id:
            raise ValueError("session_id cannot be empty")

        # 创建暂停会话记录
        paused_session = PausedSession(
            session_id=session_id,
            state=state,
            reason=reason,
            high_risk_items=high_risk_items,
        )

        # 存储暂停会话
        self._paused_sessions[session_id] = paused_session

        logger.info(
            f"Workflow paused: session_id={session_id}, reason={reason}, "
            f"high_risk_items_count={len(high_risk_items or [])}"
        )

    async def resume_workflow(
        self,
        session_id: str,
        confirmed: bool,
    ) -> HealthState | None:
        """恢复工作流执行

        根据用户确认结果恢复或终止工作流。

        Requirements:
        - 10.4: 接收用户确认后继续执行暂停的工作流

        Args:
            session_id: 会话 ID
            confirmed: 用户是否确认执行
                - True: 用户确认，清除 ui_interrupt_flag，设置 confirmation_status 为 CONFIRMED
                - False: 用户拒绝，设置 confirmation_status 为 REJECTED

        Returns:
            Optional[HealthState]: 更新后的状态，如果会话不存在则返回 None

        Example:
            >>> # 用户确认
            >>> state = await manager.resume_workflow("sess_123", confirmed=True)
            >>> assert state["ui_interrupt_flag"] == False
            >>>
            >>> # 用户拒绝
            >>> state = await manager.resume_workflow("sess_456", confirmed=False)
            >>> assert state["final_report"].confirmation_status == ConfirmationStatus.REJECTED
        """
        if session_id not in self._paused_sessions:
            logger.warning(f"Session not found for resume: {session_id}")
            return None

        # 获取并移除暂停会话
        paused_session = self._paused_sessions.pop(session_id)
        state = paused_session.state

        if confirmed:
            # 用户确认：清除中断标志，设置确认状态
            state["ui_interrupt_flag"] = False

            # 更新 final_report 的确认状态
            final_report = state.get("final_report")
            if final_report is not None:
                if hasattr(final_report, "confirmation_status"):
                    final_report.confirmation_status = ConfirmationStatus.CONFIRMED
                elif isinstance(final_report, dict):
                    final_report["confirmation_status"] = ConfirmationStatus.CONFIRMED.value

            paused_session.status = SessionStatus.RESUMED
            logger.info(f"Workflow resumed with confirmation: session_id={session_id}")
        else:
            # 用户拒绝：设置拒绝状态
            final_report = state.get("final_report")
            if final_report is not None:
                if hasattr(final_report, "confirmation_status"):
                    final_report.confirmation_status = ConfirmationStatus.REJECTED
                elif isinstance(final_report, dict):
                    final_report["confirmation_status"] = ConfirmationStatus.REJECTED.value

            paused_session.status = SessionStatus.TERMINATED
            logger.info(f"Workflow terminated by user rejection: session_id={session_id}")

        return state

    async def check_timeout(
        self,
        session_id: str,
        timeout_minutes: int | None = None,
    ) -> bool:
        """检查会话是否超时

        检查指定会话的暂停时间是否超过超时限制。

        Requirements:
        - 10.5: 最长保持30分钟
        - 10.6: 超时检查

        Args:
            session_id: 会话 ID
            timeout_minutes: 超时时间（分钟），默认使用 max_pause_minutes（30分钟）

        Returns:
            bool: True 表示已超时，False 表示未超时或会话不存在

        Example:
            >>> # 检查是否超时（使用默认30分钟）
            >>> is_timeout = await manager.check_timeout("sess_123")
            >>>
            >>> # 使用自定义超时时间
            >>> is_timeout = await manager.check_timeout("sess_123", timeout_minutes=10)
        """
        if session_id not in self._paused_sessions:
            return False

        paused_session = self._paused_sessions[session_id]

        # 使用指定的超时时间或默认的最大暂停时间
        effective_timeout = (
            timeout_minutes if timeout_minutes is not None else self.max_pause_minutes
        )

        elapsed = paused_session.elapsed_minutes()
        is_timeout = elapsed > effective_timeout

        if is_timeout:
            logger.warning(
                f"Session timeout detected: session_id={session_id}, "
                f"elapsed_minutes={elapsed:.2f}, timeout_minutes={effective_timeout}"
            )

        return is_timeout

    # ========================================================================
    # Session Management
    # ========================================================================

    def get_session_status(self, session_id: str) -> SessionStatus | None:
        """获取会话状态

        Args:
            session_id: 会话 ID

        Returns:
            Optional[SessionStatus]: 会话状态，不存在时返回 None
        """
        if session_id not in self._paused_sessions:
            return None
        return self._paused_sessions[session_id].status

    def get_session(self, session_id: str) -> PausedSession | None:
        """获取暂停会话信息

        Args:
            session_id: 会话 ID

        Returns:
            Optional[PausedSession]: 暂停会话对象，不存在时返回 None
        """
        return self._paused_sessions.get(session_id)

    def is_session_paused(self, session_id: str) -> bool:
        """检查会话是否处于暂停状态

        Args:
            session_id: 会话 ID

        Returns:
            bool: True 表示会话处于暂停状态
        """
        session = self._paused_sessions.get(session_id)
        return session is not None and session.status == SessionStatus.PAUSED

    def get_paused_session_ids(self) -> list[str]:
        """获取所有暂停会话的 ID 列表

        Returns:
            List[str]: 暂停会话 ID 列表
        """
        return list(self._paused_sessions.keys())

    def get_session_count(self) -> int:
        """获取暂停会话数量

        Returns:
            int: 当前暂停会话数量
        """
        return len(self._paused_sessions)

    async def terminate_session(
        self, session_id: str, reason: str = "manual termination"
    ) -> HealthState | None:
        """终止会话

        强制终止一个暂停的会话并释放资源。

        Args:
            session_id: 会话 ID
            reason: 终止原因

        Returns:
            Optional[HealthState]: 终止时的状态，不存在时返回 None
        """
        if session_id not in self._paused_sessions:
            return None

        paused_session = self._paused_sessions.pop(session_id)
        paused_session.status = SessionStatus.TERMINATED

        state = paused_session.state

        # 设置拒绝状态
        final_report = state.get("final_report")
        if final_report is not None:
            if hasattr(final_report, "confirmation_status"):
                final_report.confirmation_status = ConfirmationStatus.REJECTED
            elif isinstance(final_report, dict):
                final_report["confirmation_status"] = ConfirmationStatus.REJECTED.value

        logger.info(f"Session terminated: session_id={session_id}, reason={reason}")
        return state

    # ========================================================================
    # Timeout Auto-Termination
    # ========================================================================

    async def cleanup_timeout_sessions(self) -> list[str]:
        """清理超时会话

        检查所有暂停会话，自动终止超时的会话。

        Requirement 10.6: 暂停状态超过30分钟未收到用户确认，自动终止会话并释放资源

        Returns:
            List[str]: 被终止的会话 ID 列表
        """
        terminated_sessions = []

        # 获取所有会话 ID 的副本（因为会在循环中修改字典）
        session_ids = list(self._paused_sessions.keys())

        for session_id in session_ids:
            if await self.check_timeout(session_id):
                # 终止超时会话
                await self.terminate_session(
                    session_id, reason=f"timeout after {self.max_pause_minutes} minutes"
                )
                terminated_sessions.append(session_id)

                # 触发超时回调
                if self._on_timeout_callback:
                    try:
                        await self._on_timeout_callback(session_id)
                    except Exception as e:
                        logger.error(f"Error in timeout callback for session {session_id}: {e}")

        if terminated_sessions:
            logger.info(
                f"Cleaned up {len(terminated_sessions)} timeout sessions: {terminated_sessions}"
            )

        return terminated_sessions

    async def start_cleanup_loop(self, interval_seconds: int = 60) -> None:
        """启动后台清理循环

        定期检查并清理超时会话。

        Args:
            interval_seconds: 检查间隔（秒），默认60秒
        """
        if self._running:
            logger.warning("Cleanup loop is already running")
            return

        self._running = True
        logger.info(f"Starting HITL cleanup loop with interval={interval_seconds}s")

        while self._running:
            try:
                await self.cleanup_timeout_sessions()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

            await asyncio.sleep(interval_seconds)

    async def stop_cleanup_loop(self) -> None:
        """停止后台清理循环"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None
        logger.info("HITL cleanup loop stopped")

    def set_timeout_callback(self, callback: Callable) -> None:
        """设置超时回调函数

        当会话超时被自动终止时调用此回调。

        Args:
            callback: 异步回调函数，接收 session_id 作为参数
        """
        self._on_timeout_callback = callback

    # ========================================================================
    # Context Manager Support
    # ========================================================================

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出，清理资源"""
        await self.stop_cleanup_loop()
        # 终止所有暂停会话
        for session_id in list(self._paused_sessions.keys()):
            await self.terminate_session(session_id, reason="manager shutdown")


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "HITLManager",
    "PausedSession",
    "SessionStatus",
    "LANGGRAPH_CHECKPOINTER_AVAILABLE",
]
