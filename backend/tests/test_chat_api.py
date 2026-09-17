"""
/chat API 端点测试

测试 app.api.routes.chat 模块的功能
Requirements: 13.1-13.9
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def valid_chat_request():
    """创建有效的聊天请求"""
    return {
        "user_query": "我最近血脂偏高，睡眠质量差，请给我一些建议",
        "user_profile_id": "test_user_123",
    }


# ============================================================================
# Tests: POST /api/chat
# ============================================================================


class TestChatEndpoint:
    """测试 /chat 端点"""

    def test_chat_returns_streaming_response(self, client, valid_chat_request):
        """测试 /chat 返回流式响应
        
        Requirement 13.1: 提供 /chat POST 端点接收用户健康咨询请求
        Requirement 13.3: 使用 SSE 协议实现流式响应
        """
        response = client.post("/api/chat", json=valid_chat_request)
        
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    def test_chat_response_has_session_id_header(self, client, valid_chat_request):
        """测试 /chat 响应包含 X-Session-ID 头
        
        Requirement 13.1: 生成 session_id
        """
        response = client.post("/api/chat", json=valid_chat_request)
        
        assert "X-Session-ID" in response.headers
        assert len(response.headers["X-Session-ID"]) > 0

    def test_chat_response_has_correct_headers(self, client, valid_chat_request):
        """测试 /chat 响应包含正确的头部"""
        response = client.post("/api/chat", json=valid_chat_request)
        
        assert response.headers.get("Cache-Control") == "no-cache"
        assert response.headers.get("Connection") == "keep-alive"

    def test_chat_request_validation_missing_query(self, client):
        """测试缺少 user_query 时返回验证错误
        
        Requirement 13.2: 接收包含 user_query 和 user_profile_id 的 JSON 请求体
        """
        response = client.post("/api/chat", json={
            "user_profile_id": "test_user",
        })
        
        assert response.status_code == 422  # Validation Error

    def test_chat_request_validation_missing_profile_id(self, client):
        """测试缺少 user_profile_id 时返回验证错误
        
        Requirement 13.2: 接收包含 user_query 和 user_profile_id 的 JSON 请求体
        """
        response = client.post("/api/chat", json={
            "user_query": "测试查询",
        })
        
        assert response.status_code == 422  # Validation Error

    def test_chat_request_validation_query_max_length(self, client):
        """测试 user_query 超过最大长度时返回验证错误
        
        Requirement 13.2: user_query 最大长度 2000 字符
        """
        response = client.post("/api/chat", json={
            "user_query": "x" * 2001,  # 超过 2000 字符
            "user_profile_id": "test_user",
        })
        
        assert response.status_code == 422  # Validation Error

    def test_chat_returns_sse_events(self, client, valid_chat_request):
        """测试 /chat 返回 SSE 事件
        
        Requirement 13.4: 定义事件类型 (status, intermediate, report, pause, error, heartbeat)
        """
        response = client.post("/api/chat", json=valid_chat_request)
        content = response.text
        
        # 验证响应包含 SSE 事件格式
        assert "event:" in content
        assert "data:" in content

    def test_chat_returns_status_events(self, client, valid_chat_request):
        """测试 /chat 返回 status 事件
        
        Requirement 13.5: 实时推送 status 事件
        """
        response = client.post("/api/chat", json=valid_chat_request)
        content = response.text
        
        # 验证响应包含 status 事件
        assert "event: status" in content


# ============================================================================
# Tests: SSE Event Parsing
# ============================================================================


class TestSSEEventParsing:
    """测试 SSE 事件解析"""

    def test_status_event_has_correct_structure(self, client, valid_chat_request):
        """测试 status 事件结构正确
        
        Requirement 13.5: status 事件包含当前处理的智能体名称和处理进度
        """
        response = client.post("/api/chat", json=valid_chat_request)
        content = response.text
        
        # 解析 SSE 事件
        events = []
        for line in content.split("\n"):
            if line.startswith("data:"):
                data_str = line[5:].strip()
                try:
                    events.append(json.loads(data_str))
                except json.JSONDecodeError:
                    pass
        
        # 查找 status 事件
        status_events = [e for e in events if "data" in e and "agent_name" in e.get("data", {})]
        
        # 至少应该有一个 status 事件
        assert len(status_events) > 0
        
        # 验证事件结构
        for event in status_events:
            data = event.get("data", {})
            assert "agent_name" in data
            assert "progress" in data
            assert "percentage" in data
            assert 0 <= data["percentage"] <= 100


# ============================================================================
# Tests: Error Handling
# ============================================================================


class TestChatErrorHandling:
    """测试 /chat 错误处理"""

    def test_chat_handles_invalid_json(self, client):
        """测试处理无效 JSON"""
        response = client.post(
            "/api/chat",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 422

    def test_chat_handles_empty_body(self, client):
        """测试处理空请求体"""
        response = client.post(
            "/api/chat",
            content="{}",
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 422
