"""
SSE 事件管理器测试

测试 Requirements 13.3-13.9 的实现
"""

import asyncio
import json
from datetime import UTC, datetime

import pytest

from app.api.sse_manager import SSEEvent, SSEEventType, SSEManager


class TestSSEEventType:
    """测试 SSE 事件类型枚举"""

    def test_event_type_values(self):
        """测试所有事件类型值 (Requirement 13.4)"""
        assert SSEEventType.STATUS.value == "status"
        assert SSEEventType.INTERMEDIATE.value == "intermediate"
        assert SSEEventType.REPORT.value == "report"
        assert SSEEventType.PAUSE.value == "pause"
        assert SSEEventType.ERROR.value == "error"
        assert SSEEventType.HEARTBEAT.value == "heartbeat"

    def test_event_type_is_str_enum(self):
        """测试事件类型是字符串枚举"""
        assert isinstance(SSEEventType.STATUS, str)
        assert SSEEventType.STATUS == "status"


class TestSSEEvent:
    """测试 SSE 事件数据模型"""

    def test_create_event_with_dict_data(self):
        """测试使用字典数据创建事件"""
        event = SSEEvent(
            event_type=SSEEventType.STATUS,
            data={"agent_name": "test", "progress": "processing"}
        )

        assert event.event_type == SSEEventType.STATUS
        assert event.data["agent_name"] == "test"
        assert event.timestamp is not None

    def test_create_event_with_string_data(self):
        """测试使用字符串数据创建事件"""
        event = SSEEvent(
            event_type=SSEEventType.INTERMEDIATE,
            data="中间结果内容"
        )

        assert event.event_type == SSEEventType.INTERMEDIATE
        assert event.data == "中间结果内容"

    def test_event_timestamp_auto_generated(self):
        """测试事件时间戳自动生成"""
        before = datetime.now(UTC)
        event = SSEEvent(event_type=SSEEventType.HEARTBEAT, data={})
        after = datetime.now(UTC)

        event_time = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
        assert before <= event_time <= after

    def test_to_sse_format_basic(self):
        """测试 SSE 格式转换"""
        event = SSEEvent(
            event_type=SSEEventType.STATUS,
            data={"message": "test"}
        )

        sse_str = event.to_sse_format()

        # 验证格式
        assert sse_str.startswith("event: status\n")
        assert "data: " in sse_str
        assert sse_str.endswith("\n\n")

    def test_to_sse_format_contains_data(self):
        """测试 SSE 格式包含正确数据"""
        event = SSEEvent(
            event_type=SSEEventType.INTERMEDIATE,
            data={"key": "value", "number": 42}
        )

        sse_str = event.to_sse_format()

        # 提取 data 部分
        data_line = sse_str.split("\n")[1]
        assert data_line.startswith("data: ")

        # 解析 JSON
        data_json = json.loads(data_line[6:])
        assert data_json["data"]["key"] == "value"
        assert data_json["data"]["number"] == 42
        assert "timestamp" in data_json

    def test_to_sse_format_chinese_content(self):
        """测试 SSE 格式支持中文内容"""
        event = SSEEvent(
            event_type=SSEEventType.STATUS,
            data={"agent_name": "营养智能体", "progress": "正在分析血脂指标"}
        )

        sse_str = event.to_sse_format()

        assert "营养智能体" in sse_str
        assert "正在分析血脂指标" in sse_str


class TestSSEManager:
    """测试 SSE 管理器"""

    @pytest.fixture
    def manager(self):
        """创建 SSE 管理器实例"""
        return SSEManager()

    @pytest.mark.asyncio
    async def test_create_stream_initializes_session(self, manager):
        """测试创建流初始化会话"""
        session_id = "test-session-1"

        # 启动流生成器
        stream = manager.create_stream(session_id)

        # 消费第一个事件（需要触发流的初始化）
        async def consume_stream():
            async for _ in stream:
                break  # 只获取一个事件后退出

        # 发送一个事件然后关闭
        async def send_and_close():
            await asyncio.sleep(0.1)  # 等待流初始化
            await manager.emit_event(
                session_id,
                SSEEvent(event_type=SSEEventType.STATUS, data={})
            )
            await manager.close_stream(session_id)

        await asyncio.gather(
            consume_stream(),
            send_and_close()
        )

    @pytest.mark.asyncio
    async def test_emit_event_to_session(self, manager):
        """测试向会话发送事件"""
        session_id = "test-session-2"
        received_events = []

        async def consume_stream():
            async for event_str in manager.create_stream(session_id):
                received_events.append(event_str)
                if len(received_events) >= 2:
                    break

        async def send_events():
            await asyncio.sleep(0.1)
            await manager.emit_status(
                session_id,
                agent_name="Test_Agent",
                progress="开始处理",
                percentage=0
            )
            await manager.emit_status(
                session_id,
                agent_name="Test_Agent",
                progress="处理完成",
                percentage=100
            )
            await asyncio.sleep(0.1)
            await manager.close_stream(session_id)

        await asyncio.gather(
            consume_stream(),
            send_events()
        )

        assert len(received_events) == 2
        assert "Test_Agent" in received_events[0]
        assert "开始处理" in received_events[0]

    @pytest.mark.asyncio
    async def test_emit_status_event(self, manager):
        """测试发送状态事件 (Requirement 13.5)"""
        session_id = "test-session-3"
        received = []

        async def consume():
            async for event in manager.create_stream(session_id):
                received.append(event)
                if "status" in event:
                    break

        async def send():
            await asyncio.sleep(0.1)
            await manager.emit_status(
                session_id,
                agent_name="Controller_Agent",
                progress="任务拆解中",
                percentage=25
            )
            await asyncio.sleep(0.1)
            await manager.close_stream(session_id)

        await asyncio.gather(consume(), send())

        assert len(received) >= 1
        assert "event: status" in received[0]
        assert "Controller_Agent" in received[0]
        assert "任务拆解中" in received[0]

    @pytest.mark.asyncio
    async def test_emit_intermediate_event(self, manager):
        """测试发送中间结果事件 (Requirement 13.5)"""
        session_id = "test-session-4"
        received = []

        async def consume():
            async for event in manager.create_stream(session_id):
                received.append(event)
                if "intermediate" in event:
                    break

        async def send():
            await asyncio.sleep(0.1)
            await manager.emit_intermediate(
                session_id,
                data={"partial_result": "血脂分析中间结果"}
            )
            await asyncio.sleep(0.1)
            await manager.close_stream(session_id)

        await asyncio.gather(consume(), send())

        assert len(received) >= 1
        assert "event: intermediate" in received[0]
        assert "血脂分析中间结果" in received[0]

    @pytest.mark.asyncio
    async def test_emit_report_event(self, manager):
        """测试发送报告事件 (Requirement 13.7)"""
        session_id = "test-session-5"
        received = []

        async def consume():
            async for event in manager.create_stream(session_id):
                received.append(event)
                if "report" in event:
                    break

        async def send():
            await asyncio.sleep(0.1)
            await manager.emit_report(
                session_id,
                report={"deep_insight": "健康分析报告内容", "action_plan": []}
            )
            await asyncio.sleep(0.1)
            await manager.close_stream(session_id)

        await asyncio.gather(consume(), send())

        assert len(received) >= 1
        assert "event: report" in received[0]
        assert "健康分析报告内容" in received[0]

    @pytest.mark.asyncio
    async def test_emit_pause_event(self, manager):
        """测试发送暂停事件 (Requirement 13.8)"""
        session_id = "test-session-6"
        received = []

        async def consume():
            async for event in manager.create_stream(session_id):
                received.append(event)
                if "pause" in event:
                    break

        async def send():
            await asyncio.sleep(0.1)
            await manager.emit_pause(
                session_id,
                high_risk_items=[],
                timeout_seconds=600
            )
            await asyncio.sleep(0.1)
            await manager.close_stream(session_id)

        await asyncio.gather(consume(), send())

        assert len(received) >= 1
        assert "event: pause" in received[0]
        assert session_id in received[0]

    @pytest.mark.asyncio
    async def test_emit_error_event(self, manager):
        """测试发送错误事件 (Requirement 13.9)"""
        session_id = "test-session-7"
        received = []

        async def consume():
            async for event in manager.create_stream(session_id):
                received.append(event)
                if "error" in event:
                    break

        async def send():
            await asyncio.sleep(0.1)
            await manager.emit_error(
                session_id,
                error_type="agent_timeout",
                error_message="智能体处理超时"
            )
            await asyncio.sleep(0.1)
            await manager.close_stream(session_id)

        await asyncio.gather(consume(), send())

        assert len(received) >= 1
        assert "event: error" in received[0]
        assert "agent_timeout" in received[0]
        assert "智能体处理超时" in received[0]

    @pytest.mark.asyncio
    async def test_heartbeat_mechanism(self, manager):
        """测试心跳机制 (Requirement 13.6)

        注意：为了加快测试速度，我们修改心跳间隔
        """
        session_id = "test-session-8"
        received = []

        # 临时修改心跳间隔为更短的时间
        original_interval = SSEManager.HEARTBEAT_INTERVAL
        SSEManager.HEARTBEAT_INTERVAL = 0.5  # 0.5秒心跳

        try:
            async def consume():
                count = 0
                async for event in manager.create_stream(session_id):
                    received.append(event)
                    if "heartbeat" in event:
                        count += 1
                        if count >= 2:
                            break

            async def close_later():
                # 等待足够时间让心跳发送
                await asyncio.sleep(1.5)
                await manager.close_stream(session_id)

            # 使用 asyncio.wait 设置超时
            await asyncio.wait_for(
                asyncio.gather(consume(), close_later()),
                timeout=5.0
            )

            # 验证收到心跳事件
            heartbeat_events = [e for e in received if "heartbeat" in e]
            assert len(heartbeat_events) >= 1

        finally:
            # 恢复原始心跳间隔
            SSEManager.HEARTBEAT_INTERVAL = original_interval

    @pytest.mark.asyncio
    async def test_close_stream(self, manager):
        """测试关闭流"""
        session_id = "test-session-9"
        received = []

        async def consume():
            async for event in manager.create_stream(session_id):
                received.append(event)

        async def close():
            await asyncio.sleep(0.1)
            await manager.close_stream(session_id)

        await asyncio.gather(consume(), close())

        # 验证会话已关闭
        assert not manager.is_session_active(session_id)

    @pytest.mark.asyncio
    async def test_emit_to_nonexistent_session_raises_error(self, manager):
        """测试向不存在的会话发送事件抛出错误"""
        with pytest.raises(KeyError):
            await manager.emit_event(
                "nonexistent-session",
                SSEEvent(event_type=SSEEventType.STATUS, data={})
            )

    @pytest.mark.asyncio
    async def test_is_session_active(self, manager):
        """测试会话活跃状态检查"""
        session_id = "test-session-10"

        # 会话不存在时返回 False
        assert not manager.is_session_active(session_id)

        # 创建流后返回 True
        async def consume():
            async for _ in manager.create_stream(session_id):
                break

        async def check_and_close():
            await asyncio.sleep(0.1)
            assert manager.is_session_active(session_id)
            await manager.close_stream(session_id)

        await asyncio.gather(consume(), check_and_close())

    @pytest.mark.asyncio
    async def test_multiple_sessions(self, manager):
        """测试多个并发会话"""
        session_ids = ["session-a", "session-b", "session-c"]
        received = {sid: [] for sid in session_ids}

        async def consume(session_id):
            async for event in manager.create_stream(session_id):
                received[session_id].append(event)
                if "status" in event:
                    break

        async def send_events():
            await asyncio.sleep(0.1)
            for sid in session_ids:
                await manager.emit_status(
                    sid,
                    agent_name=f"Agent_{sid}",
                    progress="处理中",
                    percentage=50
                )
            await asyncio.sleep(0.1)
            for sid in session_ids:
                await manager.close_stream(sid)

        tasks = [consume(sid) for sid in session_ids]
        tasks.append(send_events())

        await asyncio.gather(*tasks)

        # 验证每个会话都收到了自己的事件
        for sid in session_ids:
            assert len(received[sid]) >= 1
            assert f"Agent_{sid}" in received[sid][0]


class TestSSEEventWithPydanticModels:
    """测试 SSE 事件与 Pydantic 模型的集成"""

    def test_event_with_status_event_data(self):
        """测试使用 StatusEventData 模型"""
        from app.models.api import StatusEventData

        status_data = StatusEventData(
            agent_name="Nutrition_Agent",
            progress="分析血脂指标",
            percentage=30
        )

        event = SSEEvent(
            event_type=SSEEventType.STATUS,
            data=status_data
        )

        sse_str = event.to_sse_format()

        assert "event: status" in sse_str
        assert "Nutrition_Agent" in sse_str
        assert "分析血脂指标" in sse_str

    def test_event_with_pause_event_data(self):
        """测试使用 PauseEventData 模型"""
        from app.models.action_item import ActionCategory, ActionItem, Priority, RiskLevel
        from app.models.api import PauseEventData

        high_risk_item = ActionItem(
            category=ActionCategory.NUTRITION,
            title="断食方案",
            description="24小时断食",
            frequency="每周一次",
            priority=Priority.HIGH,
            risk_level=RiskLevel.HIGH,
            duration="4周"
        )

        pause_data = PauseEventData(
            session_id="test-session",
            high_risk_items=[high_risk_item],
            timeout_seconds=600
        )

        event = SSEEvent(
            event_type=SSEEventType.PAUSE,
            data=pause_data
        )

        sse_str = event.to_sse_format()

        assert "event: pause" in sse_str
        assert "test-session" in sse_str
        assert "断食方案" in sse_str

    def test_event_with_error_event_data(self):
        """测试使用 ErrorEventData 模型"""
        from app.models.api import ErrorEventData

        error_data = ErrorEventData(
            error_type="rag_query_error",
            error_message="知识库检索超时"
        )

        event = SSEEvent(
            event_type=SSEEventType.ERROR,
            data=error_data
        )

        sse_str = event.to_sse_format()

        assert "event: error" in sse_str
        assert "rag_query_error" in sse_str
        assert "知识库检索超时" in sse_str
