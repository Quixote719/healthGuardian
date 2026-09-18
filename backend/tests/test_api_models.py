"""
API 请求/响应模型测试
Tests for app/models/api.py

Requirements: 13.2, 14.2
"""


import pytest
from pydantic import ValidationError

from app.models.action_item import ActionCategory, ActionItem, Priority, RiskLevel
from app.models.api import (
    ChatRequest,
    ChatResponse,
    ConfirmRequest,
    ConfirmResponse,
    ErrorEventData,
    PauseEventData,
    StatusEventData,
)
from app.models.final_report import ConfirmationStatus, FinalReport


class TestChatRequest:
    """ChatRequest 模型测试

    Requirement 13.2: user_query(字符串，最大长度2000字符) 和 user_profile_id(字符串)
    """

    def test_valid_chat_request(self):
        """测试有效的 ChatRequest 创建"""
        request = ChatRequest(
            user_query="我最近血脂偏高，睡眠质量差，请给我一些建议",
            user_profile_id="user_123"
        )
        assert request.user_query == "我最近血脂偏高，睡眠质量差，请给我一些建议"
        assert request.user_profile_id == "user_123"

    def test_user_query_max_length_valid(self):
        """测试 user_query 在2000字符限制内"""
        long_query = "健康咨询" * 400  # 1600 chars
        request = ChatRequest(
            user_query=long_query,
            user_profile_id="user_456"
        )
        assert len(request.user_query) == 1600

    def test_user_query_max_length_exactly_2000(self):
        """测试 user_query 刚好2000字符"""
        query = "a" * 2000
        request = ChatRequest(
            user_query=query,
            user_profile_id="user_789"
        )
        assert len(request.user_query) == 2000

    def test_user_query_exceeds_max_length(self):
        """测试 user_query 超过2000字符时抛出 ValidationError"""
        long_query = "a" * 2001
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(user_query=long_query, user_profile_id="user_123")
        assert "max_length" in str(exc_info.value).lower() or "2000" in str(exc_info.value)

    def test_missing_user_query(self):
        """测试缺少 user_query 时抛出 ValidationError"""
        with pytest.raises(ValidationError):
            ChatRequest(user_profile_id="user_123")

    def test_missing_user_profile_id(self):
        """测试缺少 user_profile_id 时抛出 ValidationError"""
        with pytest.raises(ValidationError):
            ChatRequest(user_query="测试查询")

    def test_json_serialization(self):
        """测试 JSON 序列化"""
        request = ChatRequest(
            user_query="测试查询",
            user_profile_id="user_123"
        )
        json_data = request.model_dump_json()
        assert "测试查询" in json_data
        assert "user_123" in json_data

    def test_json_deserialization(self):
        """测试 JSON 反序列化"""
        json_str = '{"user_query": "测试查询", "user_profile_id": "user_456"}'
        request = ChatRequest.model_validate_json(json_str)
        assert request.user_query == "测试查询"
        assert request.user_profile_id == "user_456"


class TestChatResponse:
    """ChatResponse 模型测试"""

    def test_valid_chat_response(self):
        """测试有效的 ChatResponse 创建"""
        response = ChatResponse(
            session_id="sess_abc123",
            status="processing"
        )
        assert response.session_id == "sess_abc123"
        assert response.status == "processing"

    def test_missing_session_id(self):
        """测试缺少 session_id 时抛出 ValidationError"""
        with pytest.raises(ValidationError):
            ChatResponse(status="processing")

    def test_missing_status(self):
        """测试缺少 status 时抛出 ValidationError"""
        with pytest.raises(ValidationError):
            ChatResponse(session_id="sess_123")

    def test_json_serialization(self):
        """测试 JSON 序列化"""
        response = ChatResponse(session_id="sess_123", status="completed")
        json_data = response.model_dump_json()
        assert "sess_123" in json_data
        assert "completed" in json_data


class TestConfirmRequest:
    """ConfirmRequest 模型测试

    Requirement 14.2: session_id(字符串) 和 confirmed(布尔值)
    """

    def test_valid_confirm_request_true(self):
        """测试有效的确认请求（确认）"""
        request = ConfirmRequest(
            session_id="sess_abc123",
            confirmed=True
        )
        assert request.session_id == "sess_abc123"
        assert request.confirmed is True

    def test_valid_confirm_request_false(self):
        """测试有效的确认请求（拒绝）"""
        request = ConfirmRequest(
            session_id="sess_xyz789",
            confirmed=False
        )
        assert request.session_id == "sess_xyz789"
        assert request.confirmed is False

    def test_missing_session_id(self):
        """测试缺少 session_id 时抛出 ValidationError"""
        with pytest.raises(ValidationError):
            ConfirmRequest(confirmed=True)

    def test_missing_confirmed(self):
        """测试缺少 confirmed 时抛出 ValidationError"""
        with pytest.raises(ValidationError):
            ConfirmRequest(session_id="sess_123")

    def test_json_serialization(self):
        """测试 JSON 序列化"""
        request = ConfirmRequest(session_id="sess_123", confirmed=True)
        json_data = request.model_dump_json()
        assert "sess_123" in json_data
        assert "true" in json_data.lower()

    def test_json_deserialization(self):
        """测试 JSON 反序列化"""
        json_str = '{"session_id": "sess_456", "confirmed": false}'
        request = ConfirmRequest.model_validate_json(json_str)
        assert request.session_id == "sess_456"
        assert request.confirmed is False


class TestConfirmResponse:
    """ConfirmResponse 模型测试

    Requirement 14.8: status("resumed"或"terminated") 和 partial_report(仅在拒绝时包含)
    """

    def test_resumed_response_without_report(self):
        """测试确认后的响应（无报告）"""
        response = ConfirmResponse(
            status="resumed",
            partial_report=None
        )
        assert response.status == "resumed"
        assert response.partial_report is None

    def test_terminated_response_without_report(self):
        """测试终止响应（无报告）"""
        response = ConfirmResponse(
            status="terminated"
        )
        assert response.status == "terminated"
        assert response.partial_report is None

    def test_terminated_response_with_partial_report(self):
        """测试终止响应（包含部分报告）"""
        action_item = ActionItem(
            category=ActionCategory.NUTRITION,
            title="控制饱和脂肪摄入",
            description="每日饱和脂肪摄入量控制在总热量的7%以下",
            frequency="每日三餐",
            priority=Priority.HIGH,
            risk_level=RiskLevel.LOW,
            duration="12周"
        )
        report = FinalReport(
            deep_insight="部分分析结果",
            action_plan=[action_item],
            follow_up="14天后复查",
            requires_confirmation=True,
            session_id="sess_abc123",
            confirmation_status=ConfirmationStatus.REJECTED
        )
        response = ConfirmResponse(
            status="terminated",
            partial_report=report
        )
        assert response.status == "terminated"
        assert response.partial_report is not None
        assert response.partial_report.deep_insight == "部分分析结果"
        assert len(response.partial_report.action_plan) == 1

    def test_missing_status(self):
        """测试缺少 status 时抛出 ValidationError"""
        with pytest.raises(ValidationError):
            ConfirmResponse()

    def test_json_serialization_resumed(self):
        """测试恢复状态的 JSON 序列化"""
        response = ConfirmResponse(status="resumed")
        json_data = response.model_dump_json()
        assert "resumed" in json_data

    def test_json_serialization_with_report(self):
        """测试包含报告的 JSON 序列化"""
        report = FinalReport(
            deep_insight="测试洞察",
            action_plan=[],
            follow_up="测试随访",
            session_id="sess_test"
        )
        response = ConfirmResponse(status="terminated", partial_report=report)
        json_data = response.model_dump_json()
        assert "terminated" in json_data
        assert "测试洞察" in json_data


class TestStatusEventData:
    """StatusEventData 模型测试

    Requirement 13.5: 包含当前处理的智能体名称和处理进度
    """

    def test_valid_status_event(self):
        """测试有效的状态事件数据"""
        status = StatusEventData(
            agent_name="Controller_Agent",
            progress="正在分析请求...",
            percentage=25
        )
        assert status.agent_name == "Controller_Agent"
        assert status.progress == "正在分析请求..."
        assert status.percentage == 25

    def test_percentage_zero(self):
        """测试进度百分比为0"""
        status = StatusEventData(
            agent_name="Nutrition_Agent",
            progress="开始处理",
            percentage=0
        )
        assert status.percentage == 0

    def test_percentage_hundred(self):
        """测试进度百分比为100"""
        status = StatusEventData(
            agent_name="Synthesis_Agent",
            progress="处理完成",
            percentage=100
        )
        assert status.percentage == 100

    def test_percentage_below_zero(self):
        """测试进度百分比低于0时抛出 ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            StatusEventData(
                agent_name="Test_Agent",
                progress="测试",
                percentage=-1
            )
        assert "percentage" in str(exc_info.value).lower() or "ge" in str(exc_info.value).lower()

    def test_percentage_above_hundred(self):
        """测试进度百分比高于100时抛出 ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            StatusEventData(
                agent_name="Test_Agent",
                progress="测试",
                percentage=101
            )
        assert "percentage" in str(exc_info.value).lower() or "le" in str(exc_info.value).lower()

    def test_missing_agent_name(self):
        """测试缺少 agent_name 时抛出 ValidationError"""
        with pytest.raises(ValidationError):
            StatusEventData(progress="测试", percentage=50)

    def test_missing_progress(self):
        """测试缺少 progress 时抛出 ValidationError"""
        with pytest.raises(ValidationError):
            StatusEventData(agent_name="Test_Agent", percentage=50)

    def test_missing_percentage(self):
        """测试缺少 percentage 时抛出 ValidationError"""
        with pytest.raises(ValidationError):
            StatusEventData(agent_name="Test_Agent", progress="测试")

    def test_json_serialization(self):
        """测试 JSON 序列化"""
        status = StatusEventData(
            agent_name="Controller_Agent",
            progress="任务拆解完成",
            percentage=20
        )
        json_data = status.model_dump_json()
        assert "Controller_Agent" in json_data
        assert "任务拆解完成" in json_data
        assert "20" in json_data


class TestPauseEventData:
    """PauseEventData 模型测试

    Requirement 13.8: 包含 session_id 和需要确认的高风险干预内容
    """

    def test_valid_pause_event_with_default_timeout(self):
        """测试有效的暂停事件数据（默认超时）"""
        action_item = ActionItem(
            category=ActionCategory.NUTRITION,
            title="停止服用他汀类药物",
            description="建议在医生指导下调整用药方案",
            frequency="立即执行",
            priority=Priority.HIGH,
            risk_level=RiskLevel.HIGH,
            duration="1周"
        )
        pause = PauseEventData(
            session_id="sess_xyz789",
            high_risk_items=[action_item]
        )
        assert pause.session_id == "sess_xyz789"
        assert len(pause.high_risk_items) == 1
        assert pause.timeout_seconds == 600  # default

    def test_custom_timeout(self):
        """测试自定义超时时间"""
        pause = PauseEventData(
            session_id="sess_test",
            high_risk_items=[],
            timeout_seconds=300
        )
        assert pause.timeout_seconds == 300

    def test_empty_high_risk_items(self):
        """测试空的高风险项列表"""
        pause = PauseEventData(
            session_id="sess_empty",
            high_risk_items=[]
        )
        assert len(pause.high_risk_items) == 0

    def test_multiple_high_risk_items(self):
        """测试多个高风险项"""
        items = [
            ActionItem(
                category=ActionCategory.NUTRITION,
                title="断食方案",
                description="建议在医生指导下进行",
                frequency="每周一次",
                priority=Priority.HIGH,
                risk_level=RiskLevel.HIGH,
                duration="4周"
            ),
            ActionItem(
                category=ActionCategory.REHABILITATION,
                title="高强度运动",
                description="对心血管病患者可能有风险",
                frequency="每周3次",
                priority=Priority.MEDIUM,
                risk_level=RiskLevel.HIGH,
                duration="8周"
            )
        ]
        pause = PauseEventData(
            session_id="sess_multi",
            high_risk_items=items,
            timeout_seconds=900
        )
        assert len(pause.high_risk_items) == 2
        assert pause.high_risk_items[0].title == "断食方案"
        assert pause.high_risk_items[1].title == "高强度运动"

    def test_missing_session_id(self):
        """测试缺少 session_id 时抛出 ValidationError"""
        with pytest.raises(ValidationError):
            PauseEventData(high_risk_items=[])

    def test_missing_high_risk_items(self):
        """测试缺少 high_risk_items 时抛出 ValidationError"""
        with pytest.raises(ValidationError):
            PauseEventData(session_id="sess_test")

    def test_json_serialization(self):
        """测试 JSON 序列化"""
        item = ActionItem(
            category=ActionCategory.NUTRITION,
            title="测试干预",
            description="测试描述",
            frequency="每日",
            priority=Priority.HIGH,
            risk_level=RiskLevel.HIGH,
            duration="2周"
        )
        pause = PauseEventData(
            session_id="sess_json",
            high_risk_items=[item],
            timeout_seconds=600
        )
        json_data = pause.model_dump_json()
        assert "sess_json" in json_data
        assert "测试干预" in json_data
        assert "600" in json_data


class TestErrorEventData:
    """ErrorEventData 模型测试

    Requirement 13.9: 包含错误类型标识和错误描述信息
    """

    def test_valid_error_event(self):
        """测试有效的错误事件数据"""
        error = ErrorEventData(
            error_type="session_not_found",
            error_message="会话不存在或已过期"
        )
        assert error.error_type == "session_not_found"
        assert error.error_message == "会话不存在或已过期"

    def test_timeout_error(self):
        """测试超时错误"""
        error = ErrorEventData(
            error_type="agent_timeout",
            error_message="Controller_Agent 处理超时（超过30秒）"
        )
        assert error.error_type == "agent_timeout"
        assert "30秒" in error.error_message

    def test_rag_query_error(self):
        """测试 RAG 查询错误"""
        error = ErrorEventData(
            error_type="rag_query_error",
            error_message="知识库检索失败：连接超时"
        )
        assert error.error_type == "rag_query_error"

    def test_session_timeout_error(self):
        """测试会话超时错误"""
        error = ErrorEventData(
            error_type="session_timeout",
            error_message="会话暂停超过10分钟，已自动终止"
        )
        assert error.error_type == "session_timeout"

    def test_session_not_paused_error(self):
        """测试会话未暂停错误"""
        error = ErrorEventData(
            error_type="session_not_paused",
            error_message="会话未处于暂停状态"
        )
        assert error.error_type == "session_not_paused"

    def test_missing_error_type(self):
        """测试缺少 error_type 时抛出 ValidationError"""
        with pytest.raises(ValidationError):
            ErrorEventData(error_message="测试错误")

    def test_missing_error_message(self):
        """测试缺少 error_message 时抛出 ValidationError"""
        with pytest.raises(ValidationError):
            ErrorEventData(error_type="test_error")

    def test_json_serialization(self):
        """测试 JSON 序列化"""
        error = ErrorEventData(
            error_type="validation_error",
            error_message="请求参数验证失败"
        )
        json_data = error.model_dump_json()
        assert "validation_error" in json_data
        assert "请求参数验证失败" in json_data

    def test_json_deserialization(self):
        """测试 JSON 反序列化"""
        json_str = '{"error_type": "network_error", "error_message": "网络连接失败"}'
        error = ErrorEventData.model_validate_json(json_str)
        assert error.error_type == "network_error"
        assert error.error_message == "网络连接失败"


class TestModelIntegration:
    """模型集成测试"""

    def test_full_sse_event_flow(self):
        """测试完整的 SSE 事件流数据模型"""
        # 1. 状态事件
        status = StatusEventData(
            agent_name="Controller_Agent",
            progress="正在分析请求",
            percentage=10
        )
        assert status.agent_name == "Controller_Agent"

        # 2. 暂停事件
        pause_item = ActionItem(
            category=ActionCategory.REHABILITATION,
            title="高强度运动训练",
            description="心血管病患者需谨慎",
            frequency="每周3次",
            priority=Priority.HIGH,
            risk_level=RiskLevel.HIGH,
            duration="12周"
        )
        pause = PauseEventData(
            session_id="sess_flow_test",
            high_risk_items=[pause_item],
            timeout_seconds=600
        )
        assert pause.timeout_seconds == 600

        # 3. 错误事件
        error = ErrorEventData(
            error_type="timeout",
            error_message="处理超时"
        )
        assert error.error_type == "timeout"

    def test_chat_confirm_flow(self):
        """测试聊天和确认流程数据模型"""
        # 1. 聊天请求
        chat_request = ChatRequest(
            user_query="我需要健康建议",
            user_profile_id="user_001"
        )

        # 2. 聊天响应
        chat_response = ChatResponse(
            session_id="sess_001",
            status="processing"
        )

        # 3. 确认请求
        confirm_request = ConfirmRequest(
            session_id=chat_response.session_id,
            confirmed=True
        )

        # 4. 确认响应
        confirm_response = ConfirmResponse(
            status="resumed"
        )

        assert chat_request.user_profile_id == "user_001"
        assert chat_response.session_id == confirm_request.session_id
        assert confirm_response.status == "resumed"
