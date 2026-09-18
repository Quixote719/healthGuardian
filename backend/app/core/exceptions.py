"""
自定义异常类
Custom exception classes for the Health Longevity Multi-Agent System
"""

from typing import Any


class HealthSystemError(Exception):
    """系统基础异常 - Base exception for the health system"""

    def __init__(self, message: str, error_type: str, details: dict[str, Any] | None = None):
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        super().__init__(message)


class AgentTimeoutError(HealthSystemError):
    """智能体超时异常 - Agent execution timeout"""

    def __init__(self, agent_name: str, timeout_seconds: int):
        super().__init__(
            message=f"智能体 {agent_name} 执行超时 ({timeout_seconds}秒)",
            error_type="agent_timeout",
            details={"agent_name": agent_name, "timeout": timeout_seconds},
        )


class RAGQueryError(HealthSystemError):
    """RAG 检索异常 - RAG query failure"""

    def __init__(self, rag_type: str, original_error: str):
        super().__init__(
            message=f"{rag_type} 检索失败: {original_error}",
            error_type="rag_query_error",
            details={"rag_type": rag_type, "original_error": original_error},
        )


class SessionNotFoundError(HealthSystemError):
    """会话不存在异常 - Session not found"""

    def __init__(self, session_id: str):
        super().__init__(
            message=f"会话 {session_id} 不存在",
            error_type="session_not_found",
            details={"session_id": session_id},
        )


class SessionTimeoutError(HealthSystemError):
    """会话超时异常 - Session timeout"""

    def __init__(self, session_id: str, timeout_minutes: int):
        super().__init__(
            message=f"会话 {session_id} 已超时 ({timeout_minutes}分钟)",
            error_type="session_timeout",
            details={"session_id": session_id, "timeout_minutes": timeout_minutes},
        )


class SessionNotPausedError(HealthSystemError):
    """会话未暂停异常 - Session not in paused state"""

    def __init__(self, session_id: str):
        super().__init__(
            message=f"会话 {session_id} 未处于暂停状态",
            error_type="session_not_paused",
            details={"session_id": session_id},
        )


class ValidationError(HealthSystemError):
    """数据验证异常 - Data validation failure"""

    def __init__(self, field: str, message: str):
        super().__init__(
            message=f"验证失败: {field} - {message}",
            error_type="validation_error",
            details={"field": field, "validation_message": message},
        )
