"""
Action_Item 数据模型单元测试

测试 ActionCategory, Priority, RiskLevel 枚举类型和 ActionItem 模型
验证字段约束和 duration 格式验证器

Requirements: 2.1-2.9
"""

import pytest
from pydantic import ValidationError

from app.models.action_item import (
    ActionCategory,
    ActionItem,
    Priority,
    RiskLevel,
)


class TestActionCategory:
    """ActionCategory 枚举测试 (Requirement 2.1)"""

    def test_category_values(self):
        """测试枚举值正确性"""
        assert ActionCategory.NUTRITION.value == "营养"
        assert ActionCategory.REHABILITATION.value == "康复"
        assert ActionCategory.NEUROPSYCHOLOGY.value == "神经心理"

    def test_category_count(self):
        """测试枚举仅包含三个值"""
        assert len(ActionCategory) == 3

    def test_category_string_conversion(self):
        """测试枚举可转换为字符串（StrEnum 直接返回值）"""
        assert str(ActionCategory.NUTRITION) == "营养"
        assert ActionCategory.NUTRITION == "营养"


class TestPriority:
    """Priority 枚举测试 (Requirement 2.5)"""

    def test_priority_values(self):
        """测试枚举值正确性"""
        assert Priority.HIGH.value == "高"
        assert Priority.MEDIUM.value == "中"
        assert Priority.LOW.value == "低"

    def test_priority_count(self):
        """测试枚举仅包含三个值"""
        assert len(Priority) == 3


class TestRiskLevel:
    """RiskLevel 枚举测试 (Requirement 2.6)"""

    def test_risk_level_values(self):
        """测试枚举值正确性"""
        assert RiskLevel.HIGH.value == "高风险"
        assert RiskLevel.MEDIUM.value == "中风险"
        assert RiskLevel.LOW.value == "低风险"

    def test_risk_level_count(self):
        """测试枚举仅包含三个值"""
        assert len(RiskLevel) == 3


class TestActionItem:
    """ActionItem 模型测试 (Requirements 2.1-2.9)"""

    @pytest.fixture
    def valid_action_item_data(self):
        """有效的 ActionItem 数据"""
        return {
            "category": "营养",
            "title": "低脂饮食计划",
            "description": "减少饱和脂肪酸摄入，每日脂肪摄入量控制在50g以下。",
            "frequency": "每日三餐执行",
            "priority": "高",
            "risk_level": "低风险",
            "duration": "30天"
        }

    def test_valid_action_item(self, valid_action_item_data):
        """测试有效数据创建 ActionItem"""
        item = ActionItem(**valid_action_item_data)

        assert item.category == ActionCategory.NUTRITION
        assert item.title == "低脂饮食计划"
        assert item.description == "减少饱和脂肪酸摄入，每日脂肪摄入量控制在50g以下。"
        assert item.frequency == "每日三餐执行"
        assert item.priority == Priority.HIGH
        assert item.risk_level == RiskLevel.LOW
        assert item.duration == "30天"

    def test_all_categories(self, valid_action_item_data):
        """测试所有类别值 (Requirement 2.1)"""
        for category in ["营养", "康复", "神经心理"]:
            valid_action_item_data["category"] = category
            item = ActionItem(**valid_action_item_data)
            assert item.category.value == category

    def test_invalid_category(self, valid_action_item_data):
        """测试无效类别值抛出 ValidationError (Requirement 2.8)"""
        valid_action_item_data["category"] = "无效类别"
        with pytest.raises(ValidationError) as exc_info:
            ActionItem(**valid_action_item_data)
        assert "category" in str(exc_info.value)

    def test_title_min_length(self, valid_action_item_data):
        """测试 title 最小长度为1 (Requirement 2.2)"""
        valid_action_item_data["title"] = ""
        with pytest.raises(ValidationError) as exc_info:
            ActionItem(**valid_action_item_data)
        assert "title" in str(exc_info.value)

    def test_title_max_length(self, valid_action_item_data):
        """测试 title 最大长度为100 (Requirement 2.2)"""
        valid_action_item_data["title"] = "a" * 101
        with pytest.raises(ValidationError) as exc_info:
            ActionItem(**valid_action_item_data)
        assert "title" in str(exc_info.value)

    def test_title_valid_lengths(self, valid_action_item_data):
        """测试 title 边界有效值"""
        # 最小有效长度 (1)
        valid_action_item_data["title"] = "a"
        item = ActionItem(**valid_action_item_data)
        assert len(item.title) == 1

        # 最大有效长度 (100)
        valid_action_item_data["title"] = "a" * 100
        item = ActionItem(**valid_action_item_data)
        assert len(item.title) == 100

    def test_description_min_length(self, valid_action_item_data):
        """测试 description 最小长度为1 (Requirement 2.3)"""
        valid_action_item_data["description"] = ""
        with pytest.raises(ValidationError) as exc_info:
            ActionItem(**valid_action_item_data)
        assert "description" in str(exc_info.value)

    def test_description_max_length(self, valid_action_item_data):
        """测试 description 最大长度为2000 (Requirement 2.3)"""
        valid_action_item_data["description"] = "a" * 2001
        with pytest.raises(ValidationError) as exc_info:
            ActionItem(**valid_action_item_data)
        assert "description" in str(exc_info.value)

    def test_description_valid_lengths(self, valid_action_item_data):
        """测试 description 边界有效值"""
        # 最小有效长度 (1)
        valid_action_item_data["description"] = "a"
        item = ActionItem(**valid_action_item_data)
        assert len(item.description) == 1

        # 最大有效长度 (2000)
        valid_action_item_data["description"] = "a" * 2000
        item = ActionItem(**valid_action_item_data)
        assert len(item.description) == 2000

    def test_frequency_min_length(self, valid_action_item_data):
        """测试 frequency 最小长度为1 (Requirement 2.4)"""
        valid_action_item_data["frequency"] = ""
        with pytest.raises(ValidationError) as exc_info:
            ActionItem(**valid_action_item_data)
        assert "frequency" in str(exc_info.value)

    def test_frequency_max_length(self, valid_action_item_data):
        """测试 frequency 最大长度为200 (Requirement 2.4)"""
        valid_action_item_data["frequency"] = "a" * 201
        with pytest.raises(ValidationError) as exc_info:
            ActionItem(**valid_action_item_data)
        assert "frequency" in str(exc_info.value)

    def test_all_priorities(self, valid_action_item_data):
        """测试所有优先级值 (Requirement 2.5)"""
        for priority in ["高", "中", "低"]:
            valid_action_item_data["priority"] = priority
            item = ActionItem(**valid_action_item_data)
            assert item.priority.value == priority

    def test_invalid_priority(self, valid_action_item_data):
        """测试无效优先级抛出 ValidationError (Requirement 2.8)"""
        valid_action_item_data["priority"] = "极高"
        with pytest.raises(ValidationError) as exc_info:
            ActionItem(**valid_action_item_data)
        assert "priority" in str(exc_info.value)

    def test_all_risk_levels(self, valid_action_item_data):
        """测试所有风险级别值 (Requirement 2.6)"""
        for risk_level in ["高风险", "中风险", "低风险"]:
            valid_action_item_data["risk_level"] = risk_level
            item = ActionItem(**valid_action_item_data)
            assert item.risk_level.value == risk_level

    def test_invalid_risk_level(self, valid_action_item_data):
        """测试无效风险级别抛出 ValidationError (Requirement 2.8)"""
        valid_action_item_data["risk_level"] = "无风险"
        with pytest.raises(ValidationError) as exc_info:
            ActionItem(**valid_action_item_data)
        assert "risk_level" in str(exc_info.value)


class TestDurationValidator:
    """Duration 格式验证器测试 (Requirements 2.7, 2.8)"""

    @pytest.fixture
    def base_data(self):
        """基础测试数据"""
        return {
            "category": "营养",
            "title": "测试",
            "description": "测试描述",
            "frequency": "每日",
            "priority": "高",
            "risk_level": "低风险",
        }

    @pytest.mark.parametrize("duration", [
        "1天",
        "7天",
        "14天",
        "365天",
        "1周",
        "2周",
        "52周",
        "1月",
        "3月",
        "12月",
        "100天",
        "1 天",   # 带空格
        "2 周",
        "3 月",
    ])
    def test_valid_duration_formats(self, base_data, duration):
        """测试有效的 duration 格式"""
        base_data["duration"] = duration
        item = ActionItem(**base_data)
        assert item.duration == duration

    @pytest.mark.parametrize("duration,reason", [
        ("0天", "零不是正整数"),
        ("-1天", "负数不是正整数"),
        ("天", "缺少数字"),
        ("7", "缺少时间单位"),
        ("7日", "日不是有效时间单位"),
        ("7年", "年不是有效时间单位"),
        ("2weeks", "英文单位无效"),
        ("1.5天", "小数不是正整数"),
        ("七天", "中文数字无效"),
        ("", "空字符串"),
        ("   ", "仅空白字符"),
        ("01天", "前导零"),
        ("007天", "前导零"),
    ])
    def test_invalid_duration_formats(self, base_data, duration, reason):
        """测试无效的 duration 格式 - {reason}"""
        base_data["duration"] = duration
        with pytest.raises(ValidationError) as exc_info:
            ActionItem(**base_data)
        error = exc_info.value
        assert "duration" in str(error).lower()


class TestJsonSerialization:
    """JSON 序列化测试 (Requirement 2.9)"""

    @pytest.fixture
    def action_item(self):
        """创建测试用 ActionItem"""
        return ActionItem(
            category="营养",
            title="测试计划",
            description="测试描述内容",
            frequency="每日一次",
            priority="高",
            risk_level="低风险",
            duration="7天"
        )

    def test_json_serialization(self, action_item):
        """测试 JSON 序列化"""
        json_str = action_item.model_dump_json()
        assert isinstance(json_str, str)
        assert "营养" in json_str
        assert "测试计划" in json_str

    def test_json_deserialization(self, action_item):
        """测试 JSON 反序列化"""
        json_str = action_item.model_dump_json()
        restored = ActionItem.model_validate_json(json_str)

        assert restored.category == action_item.category
        assert restored.title == action_item.title
        assert restored.description == action_item.description
        assert restored.frequency == action_item.frequency
        assert restored.priority == action_item.priority
        assert restored.risk_level == action_item.risk_level
        assert restored.duration == action_item.duration

    def test_dict_conversion(self, action_item):
        """测试字典转换"""
        data = action_item.model_dump()

        assert data["category"] == "营养"
        assert data["title"] == "测试计划"
        assert data["priority"] == "高"
        assert data["risk_level"] == "低风险"
        assert data["duration"] == "7天"

    def test_roundtrip_serialization(self, action_item):
        """测试往返序列化一致性"""
        dict_data = action_item.model_dump()
        restored = ActionItem(**dict_data)

        assert restored == action_item


class TestMissingRequiredFields:
    """缺失必填字段测试 (Requirement 2.8)"""

    def test_missing_category(self):
        """测试缺失 category 字段"""
        with pytest.raises(ValidationError) as exc_info:
            ActionItem(
                title="测试",
                description="描述",
                frequency="每日",
                priority="高",
                risk_level="低风险",
                duration="7天"
            )
        assert "category" in str(exc_info.value)

    def test_missing_title(self):
        """测试缺失 title 字段"""
        with pytest.raises(ValidationError) as exc_info:
            ActionItem(
                category="营养",
                description="描述",
                frequency="每日",
                priority="高",
                risk_level="低风险",
                duration="7天"
            )
        assert "title" in str(exc_info.value)

    def test_missing_description(self):
        """测试缺失 description 字段"""
        with pytest.raises(ValidationError) as exc_info:
            ActionItem(
                category="营养",
                title="测试",
                frequency="每日",
                priority="高",
                risk_level="低风险",
                duration="7天"
            )
        assert "description" in str(exc_info.value)

    def test_missing_frequency(self):
        """测试缺失 frequency 字段"""
        with pytest.raises(ValidationError) as exc_info:
            ActionItem(
                category="营养",
                title="测试",
                description="描述",
                priority="高",
                risk_level="低风险",
                duration="7天"
            )
        assert "frequency" in str(exc_info.value)

    def test_missing_priority(self):
        """测试缺失 priority 字段"""
        with pytest.raises(ValidationError) as exc_info:
            ActionItem(
                category="营养",
                title="测试",
                description="描述",
                frequency="每日",
                risk_level="低风险",
                duration="7天"
            )
        assert "priority" in str(exc_info.value)

    def test_missing_risk_level(self):
        """测试缺失 risk_level 字段"""
        with pytest.raises(ValidationError) as exc_info:
            ActionItem(
                category="营养",
                title="测试",
                description="描述",
                frequency="每日",
                priority="高",
                duration="7天"
            )
        assert "risk_level" in str(exc_info.value)

    def test_missing_duration(self):
        """测试缺失 duration 字段"""
        with pytest.raises(ValidationError) as exc_info:
            ActionItem(
                category="营养",
                title="测试",
                description="描述",
                frequency="每日",
                priority="高",
                risk_level="低风险"
            )
        assert "duration" in str(exc_info.value)
