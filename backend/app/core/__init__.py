"""
核心模块
包含异常处理、配置管理、日志等核心功能

Core module containing exception handling, configuration management, and logging
"""

from app.core.error_handler import (
    generic_exception_handler,
    health_system_exception_handler,
    pydantic_validation_exception_handler,
)
from app.core.exceptions import (
    AgentTimeoutError,
    HealthSystemError,
    RAGQueryError,
    SessionNotFoundError,
    SessionNotPausedError,
    SessionTimeoutError,
    ValidationError,
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
