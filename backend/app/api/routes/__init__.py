"""
API 路由模块

包含所有 API 路由:
- chat: 流式聊天 API (POST /api/chat)
- confirm: HITL 确认 API (POST /api/confirm)
"""

from app.api.routes import chat, confirm

__all__ = ["chat", "confirm"]
