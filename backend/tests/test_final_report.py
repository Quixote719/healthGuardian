"""
Tests for Final_Report data model

Requirements 3.1-3.8: 最终报告数据结构验证
"""

from datetime import datetime
from typing import Any

import pytest
from pydantic import ValidationError

from app.models.action_item import ActionCategory, ActionItem, Priority, RiskLevel
from app.models.final_report import ConfirmationStatus, FinalReport


@pytest.fixture
def valid_action_item() -> ActionItem:
    """有效的 ActionItem 实例"""
    return ActionItem(
        category=ActionCategory.NUTRITION,
        title="控制饱和脂肪摄入",
        description="每日饱和脂肪摄入量控制在总热量的7%以下，避免油炸食品和动物内脏。",
        frequency="每日三餐",
        priority=Priority.HIGH,
        risk_level=RiskLevel.LOW,
        duration="12周",
    )


@pytest.fixture
def valid_final_report_data(valid_action_item: ActionItem) -> dict[str, Any]:
    """有效的 FinalReport 数据"""
    return {
        "deep_insight": "根据您的健康画像分析，您当前存在血脂偏高的问题。",
        "action_plan": [valid_action_item],
        "follow_up": "建议14天后复查血脂指标，重点关注LDL变化",
        "requires_confirmation": False,
        "session_id": "sess_abc123",
    }


class TestConfirmationStatus:
    """ConfirmationStatus 枚举测试"""

    def test_confirmation_status_values(self) -> None:
        """Requirement 3.7: 枚举值为 pending/confirmed/rejected"""
        assert ConfirmationStatus.PENDING.value == "pending"
        assert ConfirmationStatus.CONFIRMED.value == "confirmed"
        assert ConfirmationStatus.REJECTED.value == "rejected"

    def test_confirmation_status_is_string_enum(self) -> None:
        """确保枚举值可以作为字符串使用（通过 .value 属性）"""
        # str(Enum) 继承自 str, 所以可以直接比较
        assert ConfirmationStatus.PENDING == "pending"
        assert ConfirmationStatus.CONFIRMED == "confirmed"
        assert ConfirmationStatus.REJECTED == "rejected"


class TestFinalReportCreation:
    """FinalReport 创建测试"""

    def test_create_final_report_with_required_fields(
        self, valid_final_report_data: dict[str, Any]
    ) -> None:
        """Requirement 3.1-3.6: 可以使用所有必需字段创建 FinalReport"""
        report = FinalReport(**valid_final_report_data)
        
        assert report.deep_insight == valid_final_report_data["deep_insight"]
        assert len(report.action_plan) == 1
        assert report.follow_up == valid_final_report_data["follow_up"]
        assert report.requires_confirmation is False
        assert report.session_id == "sess_abc123"

    def test_deep_insight_required(
        self, valid_final_report_data: dict[str, Any]
    ) -> None:
        """Requirement 3.1: deep_insight 字段是必需的"""
        del valid_final_report_data["deep_insight"]
        
        with pytest.raises(ValidationError) as exc_info:
            FinalReport(**valid_final_report_data)
        
        assert "deep_insight" in str(exc_info.value)

    def test_follow_up_required(
        self, valid_final_report_data: dict[str, Any]
    ) -> None:
        """Requirement 3.3: follow_up 字段是必需的"""
        del valid_final_report_data["follow_up"]
        
        with pytest.raises(ValidationError) as exc_info:
            FinalReport(**valid_final_report_data)
        
        assert "follow_up" in str(exc_info.value)

    def test_session_id_required(
        self, valid_final_report_data: dict[str, Any]
    ) -> None:
        """Requirement 3.6: session_id 字段是必需的"""
        del valid_final_report_data["session_id"]
        
        with pytest.raises(ValidationError) as exc_info:
            FinalReport(**valid_final_report_data)
        
        assert "session_id" in str(exc_info.value)


class TestFinalReportDefaults:
    """FinalReport 默认值测试"""

    def test_action_plan_default_empty_list(
        self, valid_final_report_data: dict[str, Any]
    ) -> None:
        """Requirement 3.2: action_plan 默认为空列表"""
        del valid_final_report_data["action_plan"]
        
        report = FinalReport(**valid_final_report_data)
        
        assert report.action_plan == []

    def test_requires_confirmation_default_false(
        self, valid_final_report_data: dict[str, Any]
    ) -> None:
        """Requirement 3.4: requires_confirmation 默认为 False"""
        del valid_final_report_data["requires_confirmation"]
        
        report = FinalReport(**valid_final_report_data)
        
        assert report.requires_confirmation is False

    def test_created_at_default_utc_now(
        self, valid_final_report_data: dict[str, Any]
    ) -> None:
        """Requirement 3.5: created_at 默认为当前 UTC 时间"""
        before = datetime.utcnow()
        report = FinalReport(**valid_final_report_data)
        after = datetime.utcnow()
        
        assert before <= report.created_at <= after

    def test_confirmation_status_default_pending(
        self, valid_final_report_data: dict[str, Any]
    ) -> None:
        """Requirement 3.7: confirmation_status 默认为 pending"""
        report = FinalReport(**valid_final_report_data)
        
        assert report.confirmation_status == ConfirmationStatus.PENDING


class TestFinalReportActionPlan:
    """FinalReport action_plan 字段测试"""

    def test_action_plan_max_length_50(
        self, valid_final_report_data: dict[str, Any], valid_action_item: ActionItem
    ) -> None:
        """Requirement 3.2: action_plan 列表长度范围 0-50 项"""
        valid_final_report_data["action_plan"] = [valid_action_item] * 51
        
        with pytest.raises(ValidationError) as exc_info:
            FinalReport(**valid_final_report_data)
        
        # Pydantic v2 max_length 验证会触发错误
        assert "action_plan" in str(exc_info.value).lower() or "50" in str(exc_info.value)

    def test_action_plan_accepts_50_items(
        self, valid_final_report_data: dict[str, Any], valid_action_item: ActionItem
    ) -> None:
        """Requirement 3.2: action_plan 可以包含最多 50 项"""
        valid_final_report_data["action_plan"] = [valid_action_item] * 50
        
        report = FinalReport(**valid_final_report_data)
        
        assert len(report.action_plan) == 50

    def test_action_plan_accepts_empty_list(
        self, valid_final_report_data: dict[str, Any]
    ) -> None:
        """Requirement 3.2: action_plan 可以是空列表"""
        valid_final_report_data["action_plan"] = []
        
        report = FinalReport(**valid_final_report_data)
        
        assert report.action_plan == []


class TestFinalReportConfirmationStatus:
    """FinalReport confirmation_status 字段测试"""

    def test_confirmation_status_can_be_confirmed(
        self, valid_final_report_data: dict[str, Any]
    ) -> None:
        """Requirement 3.7: confirmation_status 可以设置为 confirmed"""
        valid_final_report_data["confirmation_status"] = ConfirmationStatus.CONFIRMED
        
        report = FinalReport(**valid_final_report_data)
        
        assert report.confirmation_status == ConfirmationStatus.CONFIRMED

    def test_confirmation_status_can_be_rejected(
        self, valid_final_report_data: dict[str, Any]
    ) -> None:
        """Requirement 3.7: confirmation_status 可以设置为 rejected"""
        valid_final_report_data["confirmation_status"] = ConfirmationStatus.REJECTED
        
        report = FinalReport(**valid_final_report_data)
        
        assert report.confirmation_status == ConfirmationStatus.REJECTED

    def test_confirmation_status_invalid_value_raises_error(
        self, valid_final_report_data: dict[str, Any]
    ) -> None:
        """Requirement 3.7: 无效的 confirmation_status 值会抛出错误"""
        valid_final_report_data["confirmation_status"] = "invalid"
        
        with pytest.raises(ValidationError):
            FinalReport(**valid_final_report_data)


class TestFinalReportSerialization:
    """FinalReport JSON 序列化测试"""

    def test_json_serialization(
        self, valid_final_report_data: dict[str, Any]
    ) -> None:
        """Requirement 3.8: 支持 JSON 序列化"""
        report = FinalReport(**valid_final_report_data)
        
        json_str = report.model_dump_json()
        
        assert isinstance(json_str, str)
        assert "deep_insight" in json_str
        assert "action_plan" in json_str
        assert "follow_up" in json_str
        assert "session_id" in json_str

    def test_json_deserialization(
        self, valid_final_report_data: dict[str, Any]
    ) -> None:
        """Requirement 3.8: 支持从 JSON 反序列化"""
        original = FinalReport(**valid_final_report_data)
        json_str = original.model_dump_json()
        
        restored = FinalReport.model_validate_json(json_str)
        
        assert restored.deep_insight == original.deep_insight
        assert restored.follow_up == original.follow_up
        assert restored.session_id == original.session_id
        assert restored.requires_confirmation == original.requires_confirmation
        assert restored.confirmation_status == original.confirmation_status
        assert len(restored.action_plan) == len(original.action_plan)

    def test_model_dump_dict(
        self, valid_final_report_data: dict[str, Any]
    ) -> None:
        """Requirement 3.8: 支持转换为字典"""
        report = FinalReport(**valid_final_report_data)
        
        data = report.model_dump()
        
        assert isinstance(data, dict)
        assert data["deep_insight"] == valid_final_report_data["deep_insight"]
        assert data["follow_up"] == valid_final_report_data["follow_up"]
        assert data["session_id"] == "sess_abc123"


class TestFinalReportWithCustomCreatedAt:
    """FinalReport 自定义 created_at 测试"""

    def test_custom_created_at(
        self, valid_final_report_data: dict[str, Any]
    ) -> None:
        """Requirement 3.5: 可以指定自定义的 created_at 时间"""
        custom_time = datetime(2024, 1, 15, 10, 30, 0)
        valid_final_report_data["created_at"] = custom_time
        
        report = FinalReport(**valid_final_report_data)
        
        assert report.created_at == custom_time


class TestFinalReportRequiresConfirmation:
    """FinalReport requires_confirmation 字段测试"""

    def test_requires_confirmation_true(
        self, valid_final_report_data: dict[str, Any]
    ) -> None:
        """Requirement 3.4: requires_confirmation 可以设置为 True"""
        valid_final_report_data["requires_confirmation"] = True
        
        report = FinalReport(**valid_final_report_data)
        
        assert report.requires_confirmation is True

    def test_requires_confirmation_false(
        self, valid_final_report_data: dict[str, Any]
    ) -> None:
        """Requirement 3.4: requires_confirmation 可以设置为 False"""
        valid_final_report_data["requires_confirmation"] = False
        
        report = FinalReport(**valid_final_report_data)
        
        assert report.requires_confirmation is False
