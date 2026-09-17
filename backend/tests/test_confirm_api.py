"""
/confirm API 端点测试

测试 app.api.routes.confirm 模块的功能
Requirements: 14.1-14.11
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes.chat import get_hitl_manager
from app.models.state import HealthState


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def hitl_manager():
    """获取 HITL 管理器"""
    return get_hitl_manager()


@pytest.fixture
async def paused_session(hitl_manager):
    """创建暂停的会话"""
    session_id = "test_paused_session"
    state: HealthState = {
        "user_query": "测试查询",
        "user_profile": None,
        "task_breakdown": [],
        "expert_responses": {},
        "ui_interrupt_flag": True,
        "interrupt_reason": "高风险干预测试",
        "node_execution_status": {},
        "error_info": [],
        "final_report": None,
    }
    
    await hitl_manager.pause_workflow(
        session_id=session_id,
        state=state,
        reason="高风险干预测试",
        high_risk_items=[],
    )
    
    yield session_id
    
    # 清理
    if hitl_manager.get_session(session_id):
        await hitl_manager.terminate_session(session_id)


# ============================================================================
# Tests: POST /api/confirm
# ============================================================================


class TestConfirmEndpoint:
    """测试 /confirm 端点"""

    def test_confirm_session_not_found(self, client):
        """测试会话不存在时返回 404
        
        Requirement 14.4: session_id 对应的会话不存在时返回 "session_not_found" 错误
        """
        response = client.post("/api/confirm", json={
            "session_id": "non_existent_session",
            "confirmed": True,
        })
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_type"] == "session_not_found"

    async def test_confirm_success_confirmed(self, client, paused_session):
        """测试确认执行成功
        
        Requirement 14.6: 用户确认执行时调用 resume_execution 继续工作流
        Requirement 14.8: 返回包含 status 字段的 JSON 响应体
        """
        response = client.post("/api/confirm", json={
            "session_id": paused_session,
            "confirmed": True,
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resumed"
        assert data["partial_report"] is None

    async def test_confirm_success_rejected(self, client, paused_session):
        """测试拒绝执行成功
        
        Requirement 14.7: 用户拒绝执行时终止工作流并返回部分结果
        Requirement 14.8: 返回包含 status 和 partial_report 字段的 JSON 响应体
        """
        response = client.post("/api/confirm", json={
            "session_id": paused_session,
            "confirmed": False,
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "terminated"

    def test_confirm_request_validation_missing_session_id(self, client):
        """测试缺少 session_id 时返回验证错误
        
        Requirement 14.2: 接收包含 session_id 和 confirmed 字段的 JSON 请求体
        """
        response = client.post("/api/confirm", json={
            "confirmed": True,
        })
        
        assert response.status_code == 422

    def test_confirm_request_validation_missing_confirmed(self, client):
        """测试缺少 confirmed 时返回验证错误
        
        Requirement 14.2: 接收包含 session_id 和 confirmed 字段的 JSON 请求体
        """
        response = client.post("/api/confirm", json={
            "session_id": "test_session",
        })
        
        assert response.status_code == 422


# ============================================================================
# Tests: GET /api/confirm/status/{session_id}
# ============================================================================


class TestConfirmStatusEndpoint:
    """测试 /confirm/status/{session_id} 端点"""

    def test_status_session_not_found(self, client):
        """测试会话不存在时返回 404"""
        response = client.get("/api/confirm/status/non_existent_session")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_type"] == "session_not_found"

    async def test_status_success(self, client, paused_session):
        """测试获取会话状态成功"""
        response = client.get(f"/api/confirm/status/{paused_session}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == paused_session
        assert data["status"] == "paused"
        assert "paused_at" in data
        assert "elapsed_seconds" in data
        assert "timeout_seconds" in data
        assert "remaining_seconds" in data
        assert "is_timeout" in data


# ============================================================================
# Tests: Timeout Handling
# ============================================================================


class TestConfirmTimeout:
    """测试超时处理
    
    Requirement 14.9: 对暂停状态的会话设置10分钟超时限制
    Requirement 14.10: 会话暂停超过10分钟未收到确认时自动终止并释放资源
    """

    async def test_timeout_check_not_exceeded(self, hitl_manager, paused_session):
        """测试未超时的会话检查"""
        is_timeout = await hitl_manager.check_timeout(
            session_id=paused_session,
            timeout_minutes=10,
        )
        
        assert is_timeout is False

    async def test_timeout_check_exceeded(self, hitl_manager):
        """测试超时的会话检查"""
        session_id = "timeout_test_session"
        state: HealthState = {
            "user_query": "测试",
            "user_profile": None,
            "task_breakdown": [],
            "expert_responses": {},
            "ui_interrupt_flag": True,
            "interrupt_reason": "测试",
            "node_execution_status": {},
            "error_info": [],
            "final_report": None,
        }
        
        await hitl_manager.pause_workflow(
            session_id=session_id,
            state=state,
            reason="测试",
        )
        
        # 检查使用很短的超时时间
        is_timeout = await hitl_manager.check_timeout(
            session_id=session_id,
            timeout_minutes=0,  # 立即超时
        )
        
        assert is_timeout is True
        
        # 清理
        await hitl_manager.terminate_session(session_id)


# ============================================================================
# Tests: Error Handling
# ============================================================================


class TestConfirmErrorHandling:
    """测试 /confirm 错误处理"""

    def test_confirm_handles_invalid_json(self, client):
        """测试处理无效 JSON"""
        response = client.post(
            "/api/confirm",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 422

    def test_confirm_handles_empty_body(self, client):
        """测试处理空请求体"""
        response = client.post(
            "/api/confirm",
            content="{}",
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 422

    def test_confirm_handles_invalid_confirmed_type(self, client):
        """测试处理无效的 confirmed 类型"""
        response = client.post("/api/confirm", json={
            "session_id": "test_session",
            "confirmed": "not_a_boolean",
        })
        
        assert response.status_code == 422
