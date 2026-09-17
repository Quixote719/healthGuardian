"""
个人健康多智能体系统 - FastAPI 应用入口
Health Multi-Agent System - FastAPI Application Entry Point

Requirements: 13.1, 14.11
Design: Components and Interfaces - FastAPI 应用入口
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError as PydanticValidationError

from app import __version__
from app.core.exceptions import HealthSystemError
from app.core.error_handler import (
    health_system_exception_handler,
    pydantic_validation_exception_handler,
    generic_exception_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    Application lifespan management for startup and shutdown events
    """
    # Startup: 初始化资源
    # 这里可以添加数据库连接、RAG 工具初始化等
    print("🚀 Health Longevity Multi-Agent System starting up...")
    
    yield
    
    # Shutdown: 清理资源
    print("👋 Health Longevity Multi-Agent System shutting down...")


# 创建 FastAPI 应用实例
app = FastAPI(
    title="Health Longevity Multi-Agent System",
    description="个人健康多智能体系统 - 基于 LangGraph 的多智能体编排系统，结合 LlamaIndex 知识检索能力",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Session-ID"],  # 暴露自定义响应头
)


# 注册全局异常处理器
app.add_exception_handler(HealthSystemError, health_system_exception_handler)
app.add_exception_handler(PydanticValidationError, pydantic_validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


# 健康检查端点
@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    健康检查端点
    Health check endpoint for monitoring and load balancers
    
    Returns:
        dict: 包含服务状态、版本和时间戳的健康状态信息
    """
    return {
        "status": "healthy",
        "version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "health-longevity-multi-agent-system"
    }


# 根路径端点
@app.get("/", tags=["Root"])
async def root() -> Dict[str, str]:
    """
    根路径端点
    Root endpoint with welcome message
    """
    return {
        "message": "Welcome to Health Longevity Multi-Agent System",
        "version": __version__,
        "docs": "/docs"
    }


# 注册 API 路由 (Requirements: 13.1, 14.1)
from app.api.routes import chat, confirm

app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(confirm.router, prefix="/api", tags=["Confirm"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
