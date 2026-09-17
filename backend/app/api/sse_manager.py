"""
SSE 事件管理器

Requirements 13.3-13.9: 实现 Server-Sent Events 流式响应机制
- 13.3: 使用 SSE 协议实现流式响应
- 13.4: 定义事件类型 (status, intermediate, report, pause, error, heartbeat)
- 13.5: 实时推送 status 和 intermediate 事件
- 13.6: 每15秒推送 heartbeat 事件
- 13.7: 推送 report 事件 (完整的 Final_Report)
- 13.8: 推送 pause 事件 (session_id 和高风险干预内容)
- 13.9: 推送 error 事件 (错误类型和描述)
"""

import asyncio
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Dict, Optional

from pydantic import BaseModel, Field


class SSEEventType(str, Enum):
    """SSE 事件类型枚举
    
    Requirement 13.4: 定义事件类型
    """
    STATUS = "status"           # 智能体处理状态
    INTERMEDIATE = "intermediate"  # 中间结果
    REPORT = "report"           # 最终报告
    PAUSE = "pause"             # HITL 暂停
    ERROR = "error"             # 错误信息
    HEARTBEAT = "heartbeat"     # 心跳


class SSEEvent(BaseModel):
    """SSE 事件数据结构
    
    Requirement 13.4: SSE 事件数据模型
    """
    event_type: SSEEventType = Field(..., description="事件类型")
    data: Any = Field(..., description="事件数据")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="事件时间戳 (ISO 8601格式)"
    )
    
    def to_sse_format(self) -> str:
        """将事件转换为 SSE 格式字符串
        
        Returns:
            SSE 格式的事件字符串，包含 event 和 data 字段
        """
        # 序列化 data 字段
        if isinstance(self.data, BaseModel):
            data_json = self.data.model_dump_json()
        else:
            data_json = json.dumps(self.data, ensure_ascii=False, default=str)
        
        # 构建完整的事件数据（包含 timestamp）
        event_data = {
            "data": json.loads(data_json) if isinstance(data_json, str) else data_json,
            "timestamp": self.timestamp
        }
        
        return f"event: {self.event_type.value}\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"


class SSEManager:
    """SSE 事件流管理器
    
    负责管理多个会话的 SSE 事件流，支持：
    - 创建和管理会话事件队列
    - 发送各类型事件
    - 15秒心跳机制 (Requirement 13.6)
    """
    
    # 心跳间隔（秒）
    HEARTBEAT_INTERVAL = 15
    
    def __init__(self):
        """初始化 SSE 管理器"""
        # 存储每个会话的事件队列
        self._event_queues: Dict[str, asyncio.Queue] = {}
        # 存储每个会话的心跳任务
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}
        # 存储每个会话的活跃状态
        self._active_sessions: Dict[str, bool] = {}
    
    async def create_stream(
        self, 
        session_id: str
    ) -> AsyncGenerator[str, None]:
        """创建 SSE 事件流
        
        Requirement 13.3: 使用 SSE 协议实现流式响应
        Requirement 13.6: 每15秒推送 heartbeat 事件
        
        Args:
            session_id: 会话 ID
            
        Yields:
            SSE 格式的事件字符串
        """
        # 初始化会话事件队列
        self._event_queues[session_id] = asyncio.Queue()
        self._active_sessions[session_id] = True
        
        # 启动心跳任务
        self._heartbeat_tasks[session_id] = asyncio.create_task(
            self._heartbeat_loop(session_id)
        )
        
        try:
            while self._active_sessions.get(session_id, False):
                try:
                    # 等待事件，设置超时以便能够检查会话状态
                    event = await asyncio.wait_for(
                        self._event_queues[session_id].get(),
                        timeout=1.0
                    )
                    
                    # 检查是否是终止信号
                    if event is None:
                        break
                    
                    # 将事件转换为 SSE 格式并 yield
                    yield event.to_sse_format()
                    
                except asyncio.TimeoutError:
                    # 超时后继续循环，检查会话是否仍然活跃
                    continue
                    
        finally:
            # 清理会话资源
            await self._cleanup_session(session_id)
    
    async def emit_event(
        self, 
        session_id: str, 
        event: SSEEvent
    ) -> None:
        """发送 SSE 事件
        
        Args:
            session_id: 会话 ID
            event: 要发送的 SSE 事件
            
        Raises:
            KeyError: 会话不存在时抛出
        """
        if session_id not in self._event_queues:
            raise KeyError(f"Session {session_id} not found")
        
        await self._event_queues[session_id].put(event)
    
    async def emit_status(
        self,
        session_id: str,
        agent_name: str,
        progress: str,
        percentage: int
    ) -> None:
        """发送状态事件的便捷方法
        
        Requirement 13.5: 实时推送 status 事件
        
        Args:
            session_id: 会话 ID
            agent_name: 智能体名称
            progress: 进度描述
            percentage: 进度百分比 (0-100)
        """
        from app.models.api import StatusEventData
        
        event = SSEEvent(
            event_type=SSEEventType.STATUS,
            data=StatusEventData(
                agent_name=agent_name,
                progress=progress,
                percentage=percentage
            )
        )
        await self.emit_event(session_id, event)
    
    async def emit_intermediate(
        self,
        session_id: str,
        data: Any
    ) -> None:
        """发送中间结果事件的便捷方法
        
        Requirement 13.5: 实时推送 intermediate 事件
        
        Args:
            session_id: 会话 ID
            data: 中间结果数据
        """
        event = SSEEvent(
            event_type=SSEEventType.INTERMEDIATE,
            data=data
        )
        await self.emit_event(session_id, event)
    
    async def emit_report(
        self,
        session_id: str,
        report: Any
    ) -> None:
        """发送最终报告事件的便捷方法
        
        Requirement 13.7: 推送 report 事件
        
        Args:
            session_id: 会话 ID
            report: Final_Report 对象
        """
        event = SSEEvent(
            event_type=SSEEventType.REPORT,
            data=report
        )
        await self.emit_event(session_id, event)
    
    async def emit_pause(
        self,
        session_id: str,
        high_risk_items: list,
        timeout_seconds: int = 600
    ) -> None:
        """发送暂停事件的便捷方法
        
        Requirement 13.8: 推送 pause 事件
        
        Args:
            session_id: 会话 ID
            high_risk_items: 高风险干预措施列表
            timeout_seconds: 超时时间（秒）
        """
        from app.models.api import PauseEventData
        
        event = SSEEvent(
            event_type=SSEEventType.PAUSE,
            data=PauseEventData(
                session_id=session_id,
                high_risk_items=high_risk_items,
                timeout_seconds=timeout_seconds
            )
        )
        await self.emit_event(session_id, event)
    
    async def emit_error(
        self,
        session_id: str,
        error_type: str,
        error_message: str
    ) -> None:
        """发送错误事件的便捷方法
        
        Requirement 13.9: 推送 error 事件
        
        Args:
            session_id: 会话 ID
            error_type: 错误类型标识
            error_message: 错误描述信息
        """
        from app.models.api import ErrorEventData
        
        event = SSEEvent(
            event_type=SSEEventType.ERROR,
            data=ErrorEventData(
                error_type=error_type,
                error_message=error_message
            )
        )
        await self.emit_event(session_id, event)
    
    async def close_stream(self, session_id: str) -> None:
        """关闭指定会话的事件流
        
        Args:
            session_id: 会话 ID
        """
        if session_id in self._active_sessions:
            self._active_sessions[session_id] = False
            
            # 发送终止信号
            if session_id in self._event_queues:
                await self._event_queues[session_id].put(None)
    
    def is_session_active(self, session_id: str) -> bool:
        """检查会话是否活跃
        
        Args:
            session_id: 会话 ID
            
        Returns:
            会话是否活跃
        """
        return self._active_sessions.get(session_id, False)
    
    async def _heartbeat_loop(self, session_id: str) -> None:
        """心跳循环
        
        Requirement 13.6: 每15秒推送 heartbeat 事件
        
        Args:
            session_id: 会话 ID
        """
        while self._active_sessions.get(session_id, False):
            try:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                
                # 检查会话是否仍然活跃
                if not self._active_sessions.get(session_id, False):
                    break
                
                # 发送心跳事件
                heartbeat_event = SSEEvent(
                    event_type=SSEEventType.HEARTBEAT,
                    data={"message": "keepalive"}
                )
                
                if session_id in self._event_queues:
                    await self._event_queues[session_id].put(heartbeat_event)
                    
            except asyncio.CancelledError:
                break
            except Exception:
                # 忽略心跳发送过程中的错误，继续尝试
                continue
    
    async def _cleanup_session(self, session_id: str) -> None:
        """清理会话资源
        
        Args:
            session_id: 会话 ID
        """
        # 标记会话为非活跃
        self._active_sessions[session_id] = False
        
        # 取消心跳任务
        if session_id in self._heartbeat_tasks:
            task = self._heartbeat_tasks.pop(session_id)
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # 清理事件队列
        if session_id in self._event_queues:
            del self._event_queues[session_id]
        
        # 清理活跃状态
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]


# 全局 SSE 管理器实例
sse_manager = SSEManager()
