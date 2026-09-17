"""
核心模块
包含异常处理、配置管理、日志等核心功能

Core module containing exception handling, configuration management, and logging
"""

from app.core.exceptions import (
    HealthSystemError,
    AgentTimeoutError,
    RAGQueryError,
    SessionNotFoundError,
    SessionTimeoutError,
    SessionNotPausedError,
    ValidationError,
)

from app.core.error_handler import (
    health_system_exception_handler,
    pydantic_validation_exception_handler,
    generic_exception_handler,
)

__all__ = [
    # Exceptions
    "HealthSystemError",
    "AgentTimeoutError",
    "RAGQueryError",
    "SessionNotFoundError",
    "SessionTimeoutError",
    "SessionNotPausedError",
    "ValidationError",
    # Error handlers
    "health_system_exception_handler",
    "pydantic_validation_exception_handler",
    "generic_exception_handler",
]
