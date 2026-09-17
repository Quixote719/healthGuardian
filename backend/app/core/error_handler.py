"""
全局异常处理器
Global exception handlers for FastAPI application
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import HealthSystemError


async def health_system_exception_handler(
    request: Request, 
    exc: HealthSystemError
) -> JSONResponse:
    """
    处理 HealthSystemError 及其子类异常
    Handle HealthSystemError and its subclasses
    """
    # 根据异常类型确定 HTTP 状态码
    status_code_map = {
        "session_not_found": 404,
        "session_timeout": 408,
        "session_not_paused": 400,
        "agent_timeout": 504,
        "rag_query_error": 503,
        "validation_error": 422,
    }
    
    status_code = status_code_map.get(exc.error_type, 400)
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error_type": exc.error_type,
            "message": exc.message,
            "details": exc.details
        }
    )


async def pydantic_validation_exception_handler(
    request: Request,
    exc: PydanticValidationError
) -> JSONResponse:
    """
    处理 Pydantic 验证异常
    Handle Pydantic validation errors
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "error_type": "validation_error",
            "message": "请求数据验证失败",
            "details": {"errors": errors}
        }
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    处理未捕获的通用异常
    Handle uncaught generic exceptions
    """
    return JSONResponse(
        status_code=500,
        content={
            "error_type": "internal_error",
            "message": "服务器内部错误",
            "details": {"error": str(exc)}
        }
    )
