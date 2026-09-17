"""
Health_State 状态模型单元测试

测试 Requirements 4.1-4.10:
- TargetAgent 枚举验证
- NodeExecutionStatus 枚举验证
- SubTask 模型验证
- ErrorInfo 模型验证
- HealthState TypedDict 兼容性验证
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest
from pydantic import ValidationError

from app.models.state import (
    ErrorInfo,
    HealthState,
    NodeExecutionStatus,
    SubTask,
    TargetAgent,
)


# ==================== TargetAgent Enum Tests ====================

class TestTargetAgent:
    """TargetAgent 枚举测试 (Requirement 4.3)"""
    
    def test_target_agent_values(self) -> None:
        """Requirement 4.3: target_agent 枚举值正确"""
        assert TargetAgent.NUTRITION.value == "nutrition"
        assert TargetAgent.REHABILITATION.value == "rehabilitation"
        assert TargetAgent.NEUROPSYCHOLOGY.value == "neuropsychology"
    
    def test_target_agent_from_string(self) -> None:
        """TargetAgent 可以从字符串创建"""
        assert TargetAgent("nutrition") == TargetAgent.NUTRITION
        assert TargetAgent("rehabilitation") == TargetAgent.REHABILITATION
        assert TargetAgent("neuropsychology") == TargetAgent.NEUROPSYCHOLOGY
    
    def test_target_agent_is_string_enum(self) -> None:
        """TargetAgent 继承自 str, Enum"""
        assert isinstance(TargetAgent.NUTRITION, str)
        assert TargetAgent.NUTRITION == "nutrition"
    
    def test_target_agent_invalid_value(self) -> None:
        """无效的 TargetAgent 值应该抛出 ValueError"""
        with pytest.raises(ValueError):
            TargetAgent("invalid_agent")
    
    def test_target_agent_all_values(self) -> None:
        """验证 TargetAgent 包含三个智能体"""
        all_values = [agent.value for agent in TargetAgent]
        assert len(all_values) == 3
        assert "nutrition" in all_values
        assert "rehabilitation" in all_values
        assert "neuropsychology" in all_values


# ==================== NodeExecutionStatus Enum Tests ====================

class TestNodeExecutionStatus:
    """NodeExecutionStatus 枚举测试 (Requirement 4.7)"""
    
    def test_node_execution_status_values(self) -> None:
        """Requirement 4.7: 节点执行状态枚举值正确"""
        assert NodeExecutionStatus.PENDING.value == "pending"
        assert NodeExecutionStatus.RUNNING.value == "running"
        assert NodeExecutionStatus.COMPLETED.value == "completed"
        assert NodeExecutionStatus.FAILED.value == "failed"
        assert NodeExecutionStatus.SKIPPED.value == "skipped"
    
    def test_node_execution_status_from_string(self) -> None:
        """NodeExecutionStatus 可以从字符串创建"""
        assert NodeExecutionStatus("pending") == NodeExecutionStatus.PENDING
        assert NodeExecutionStatus("running") == NodeExecutionStatus.RUNNING
        assert NodeExecutionStatus("completed") == NodeExecutionStatus.COMPLETED
        assert NodeExecutionStatus("failed") == NodeExecutionStatus.FAILED
        assert NodeExecutionStatus("skipped") == NodeExecutionStatus.SKIPPED
    
    def test_node_execution_status_is_string_enum(self) -> None:
        """NodeExecutionStatus 继承自 str, Enum"""
        assert isinstance(NodeExecutionStatus.PENDING, str)
        assert NodeExecutionStatus.COMPLETED == "completed"
    
    def test_node_execution_status_invalid_value(self) -> None:
        """无效的 NodeExecutionStatus 值应该抛出 ValueError"""
        with pytest.raises(ValueError):
            NodeExecutionStatus("invalid_status")
    
    def test_node_execution_status_all_values(self) -> None:
        """Requirement 4.7: 验证包含5个状态"""
        all_values = [status.value for status in NodeExecutionStatus]
        assert len(all_values) == 5


# ==================== SubTask Model Tests ====================

class TestSubTask:
    """SubTask 模型测试 (Requirement 4.3)"""
    
    @pytest.fixture
    def valid_subtask(self) -> SubTask:
        """有效的子任务"""
        return SubTask(
            task_id="task_001",
            target_agent=TargetAgent.NUTRITION,
            task_description="分析用户饮食习惯并提供营养建议",
        )
    
    def test_valid_subtask(self, valid_subtask: SubTask) -> None:
        """Requirement 4.3: 有效的子任务结构"""
        assert valid_subtask.task_id == "task_001"
        assert valid_subtask.target_agent == TargetAgent.NUTRITION
        assert valid_subtask.task_description == "分析用户饮食习惯并提供营养建议"
    
    def test_subtask_with_different_agents(self) -> None:
        """Requirement 4.3: 子任务可以分配给不同的智能体"""
        nutrition_task = SubTask(
            task_id="task_n1",
            target_agent=TargetAgent.NUTRITION,
            task_description="营养分析",
        )
        assert nutrition_task.target_agent == TargetAgent.NUTRITION
        
        rehab_task = SubTask(
            task_id="task_r1",
            target_agent=TargetAgent.REHABILITATION,
            task_description="康复训练",
        )
        assert rehab_task.target_agent == TargetAgent.REHABILITATION
        
        neuro_task = SubTask(
            task_id="task_np1",
            target_agent=TargetAgent.NEUROPSYCHOLOGY,
            task_description="心理调节",
        )
        assert neuro_task.target_agent == TargetAgent.NEUROPSYCHOLOGY
    
    def test_subtask_from_dict(self) -> None:
        """SubTask 可以从字典创建"""
        data = {
            "task_id": "task_002",
            "target_agent": "rehabilitation",
            "task_description": "制定运动康复计划",
        }
        subtask = SubTask.model_validate(data)
        assert subtask.task_id == "task_002"
        assert subtask.target_agent == TargetAgent.REHABILITATION
    
    def test_subtask_missing_required_field(self) -> None:
        """缺少必填字段应该触发 ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            SubTask(
                task_id="task_003",
                target_agent=TargetAgent.NUTRITION,
                # 缺少 task_description
            )
        assert "task_description" in str(exc_info.value)
    
    def test_subtask_invalid_target_agent(self) -> None:
        """无效的 target_agent 应该触发 ValidationError"""
        with pytest.raises(ValidationError):
            SubTask(
                task_id="task_004",
                target_agent="invalid_agent",  # type: ignore
                task_description="测试任务",
            )
    
    def test_subtask_json_serialization(self, valid_subtask: SubTask) -> None:
        """SubTask 支持 JSON 序列化"""
        json_str = valid_subtask.model_dump_json()
        # Pydantic v2 doesn't include spaces after colons
        assert '"task_id":"task_001"' in json_str
        assert '"target_agent":"nutrition"' in json_str
    
    def test_subtask_json_roundtrip(self, valid_subtask: SubTask) -> None:
        """SubTask JSON 往返测试"""
        json_str = valid_subtask.model_dump_json()
        restored = SubTask.model_validate_json(json_str)
        
        assert restored.task_id == valid_subtask.task_id
        assert restored.target_agent == valid_subtask.target_agent
        assert restored.task_description == valid_subtask.task_description


# ==================== ErrorInfo Model Tests ====================

class TestErrorInfo:
    """ErrorInfo 模型测试 (Requirement 4.8)"""
    
    @pytest.fixture
    def valid_error_info(self) -> ErrorInfo:
        """有效的错误信息"""
        return ErrorInfo(
            node_name="nutrition_agent",
            error_type="RAGQueryError",
            error_message="知识库检索失败：连接超时",
        )
    
    def test_valid_error_info(self, valid_error_info: ErrorInfo) -> None:
        """Requirement 4.8: 有效的错误信息结构"""
        assert valid_error_info.node_name == "nutrition_agent"
        assert valid_error_info.error_type == "RAGQueryError"
        assert valid_error_info.error_message == "知识库检索失败：连接超时"
        assert isinstance(valid_error_info.timestamp, datetime)
    
    def test_error_info_default_timestamp(self) -> None:
        """Requirement 4.8: timestamp 默认为当前 UTC 时间"""
        before = datetime.now(timezone.utc)
        error = ErrorInfo(
            node_name="controller",
            error_type="TimeoutError",
            error_message="处理超时",
        )
        after = datetime.now(timezone.utc)
        
        assert before <= error.timestamp <= after
    
    def test_error_info_custom_timestamp(self) -> None:
        """ErrorInfo 可以指定自定义时间戳"""
        custom_time = datetime(2024, 1, 15, 10, 30, 0)
        error = ErrorInfo(
            node_name="synthesis",
            error_type="ProcessingError",
            error_message="综合分析失败",
            timestamp=custom_time,
        )
        assert error.timestamp == custom_time
    
    def test_error_info_message_max_length(self) -> None:
        """Requirement 4.8: error_message 最大长度1000字符"""
        # 正好1000字符应该有效
        long_message = "A" * 1000
        error = ErrorInfo(
            node_name="test_node",
            error_type="TestError",
            error_message=long_message,
        )
        assert len(error.error_message) == 1000
    
    def test_error_info_message_too_long(self) -> None:
        """Requirement 4.8: error_message 超过1000字符应该触发 ValidationError"""
        too_long_message = "A" * 1001
        with pytest.raises(ValidationError) as exc_info:
            ErrorInfo(
                node_name="test_node",
                error_type="TestError",
                error_message=too_long_message,
            )
        assert "error_message" in str(exc_info.value)
    
    def test_error_info_missing_required_field(self) -> None:
        """缺少必填字段应该触发 ValidationError"""
        with pytest.raises(ValidationError):
            ErrorInfo(
                node_name="test_node",
                # 缺少 error_type 和 error_message
            )
    
    def test_error_info_json_serialization(self, valid_error_info: ErrorInfo) -> None:
        """ErrorInfo 支持 JSON 序列化"""
        json_str = valid_error_info.model_dump_json()
        # Pydantic v2 doesn't include spaces after colons
        assert '"node_name":"nutrition_agent"' in json_str
        assert '"error_type":"RAGQueryError"' in json_str
    
    def test_error_info_json_roundtrip(self, valid_error_info: ErrorInfo) -> None:
        """ErrorInfo JSON 往返测试"""
        json_str = valid_error_info.model_dump_json()
        restored = ErrorInfo.model_validate_json(json_str)
        
        assert restored.node_name == valid_error_info.node_name
        assert restored.error_type == valid_error_info.error_type
        assert restored.error_message == valid_error_info.error_message
    
    def test_error_info_various_error_types(self) -> None:
        """ErrorInfo 可以记录各种类型的错误"""
        errors = [
            ErrorInfo(
                node_name="controller",
                error_type="AgentTimeoutError",
                error_message="Controller 处理超时",
            ),
            ErrorInfo(
                node_name="nutrition",
                error_type="RAGQueryError",
                error_message="Markdown RAG 检索失败",
            ),
            ErrorInfo(
                node_name="neuropsychology",
                error_type="GraphRAGError",
                error_message="Graph RAG 查询超时",
            ),
            ErrorInfo(
                node_name="synthesis",
                error_type="ValidationError",
                error_message="报告生成验证失败",
            ),
        ]
        
        assert len(errors) == 4
        assert all(isinstance(e, ErrorInfo) for e in errors)


# ==================== HealthState TypedDict Tests ====================

class TestHealthState:
    """HealthState TypedDict 测试 (Requirement 4.1-4.10)"""
    
    @pytest.fixture
    def sample_subtasks(self) -> List[SubTask]:
        """示例子任务列表"""
        return [
            SubTask(
                task_id="task_n1",
                target_agent=TargetAgent.NUTRITION,
                task_description="营养分析",
            ),
            SubTask(
                task_id="task_r1",
                target_agent=TargetAgent.REHABILITATION,
                task_description="康复建议",
            ),
            SubTask(
                task_id="task_np1",
                target_agent=TargetAgent.NEUROPSYCHOLOGY,
                task_description="心理调节",
            ),
        ]
    
    def test_health_state_is_typeddict(self) -> None:
        """Requirement 4.10: HealthState 是 TypedDict 类型"""
        # TypedDict 的特征是它有 __annotations__ 属性
        assert hasattr(HealthState, "__annotations__")
        assert "user_query" in HealthState.__annotations__
    
    def test_health_state_empty_initialization(self) -> None:
        """Requirement 4.10: HealthState 可以空初始化 (total=False)"""
        # 由于 total=False，所有字段都是可选的
        state: HealthState = {}
        assert isinstance(state, dict)
    
    def test_health_state_partial_initialization(self) -> None:
        """Requirement 4.10: HealthState 支持部分初始化"""
        state: HealthState = {
            "user_query": "我最近血脂偏高，请给我一些建议",
            "ui_interrupt_flag": False,
        }
        assert state["user_query"] == "我最近血脂偏高，请给我一些建议"
        assert state["ui_interrupt_flag"] is False
    
    def test_health_state_user_query(self) -> None:
        """Requirement 4.1: user_query 字段 (字符串类型)"""
        state: HealthState = {
            "user_query": "我的健康咨询请求内容",
        }
        assert isinstance(state["user_query"], str)
    
    def test_health_state_task_breakdown(self, sample_subtasks: List[SubTask]) -> None:
        """Requirement 4.3: task_breakdown 字段 (子任务列表)"""
        state: HealthState = {
            "task_breakdown": sample_subtasks,
        }
        assert len(state["task_breakdown"]) == 3
        assert all(isinstance(t, SubTask) for t in state["task_breakdown"])
    
    def test_health_state_expert_responses(self) -> None:
        """Requirement 4.4: expert_responses 字段 (字典类型)"""
        state: HealthState = {
            "expert_responses": {
                "nutrition_agent": "营养建议内容...",
                "rehabilitation_agent": "康复建议内容...",
                "neuropsychology_agent": "心理建议内容...",
            },
        }
        assert len(state["expert_responses"]) == 3
        assert "nutrition_agent" in state["expert_responses"]
    
    def test_health_state_ui_interrupt_flag(self) -> None:
        """Requirement 4.5: ui_interrupt_flag 布尔字段"""
        state_no_interrupt: HealthState = {"ui_interrupt_flag": False}
        assert state_no_interrupt["ui_interrupt_flag"] is False
        
        state_with_interrupt: HealthState = {"ui_interrupt_flag": True}
        assert state_with_interrupt["ui_interrupt_flag"] is True
    
    def test_health_state_interrupt_reason(self) -> None:
        """Requirement 4.6: interrupt_reason 字段"""
        state: HealthState = {
            "ui_interrupt_flag": True,
            "interrupt_reason": "检测到高风险干预：停药建议",
        }
        assert state["interrupt_reason"] == "检测到高风险干预：停药建议"
    
    def test_health_state_node_execution_status(self) -> None:
        """Requirement 4.7: node_execution_status 字段 (字典类型)"""
        state: HealthState = {
            "node_execution_status": {
                "controller": NodeExecutionStatus.COMPLETED,
                "nutrition": NodeExecutionStatus.RUNNING,
                "rehabilitation": NodeExecutionStatus.PENDING,
                "neuropsychology": NodeExecutionStatus.PENDING,
                "synthesis": NodeExecutionStatus.PENDING,
            },
        }
        assert state["node_execution_status"]["controller"] == NodeExecutionStatus.COMPLETED
        assert state["node_execution_status"]["nutrition"] == NodeExecutionStatus.RUNNING
    
    def test_health_state_error_info(self) -> None:
        """Requirement 4.8: error_info 字段 (列表类型)"""
        errors = [
            ErrorInfo(
                node_name="nutrition",
                error_type="TimeoutError",
                error_message="处理超时",
            ),
        ]
        state: HealthState = {"error_info": errors}
        assert len(state["error_info"]) == 1
        assert state["error_info"][0].node_name == "nutrition"
    
    def test_health_state_final_report_none(self) -> None:
        """Requirement 4.9: final_report 可以为 None"""
        state: HealthState = {"final_report": None}
        assert state["final_report"] is None
    
    def test_health_state_all_fields(self, sample_subtasks: List[SubTask]) -> None:
        """Requirement 4.1-4.9: HealthState 包含所有必要字段"""
        state: HealthState = {
            "user_query": "健康咨询请求",
            "task_breakdown": sample_subtasks,
            "expert_responses": {"nutrition": "response"},
            "ui_interrupt_flag": False,
            "interrupt_reason": "",
            "node_execution_status": {"controller": NodeExecutionStatus.COMPLETED},
            "error_info": [],
            "final_report": None,
        }
        
        # 验证所有字段都存在
        assert "user_query" in state
        assert "task_breakdown" in state
        assert "expert_responses" in state
        assert "ui_interrupt_flag" in state
        assert "interrupt_reason" in state
        assert "node_execution_status" in state
        assert "error_info" in state
        assert "final_report" in state
    
    def test_health_state_annotations(self) -> None:
        """验证 HealthState 的类型注解包含所有必要字段"""
        annotations = HealthState.__annotations__
        
        expected_fields = [
            "user_query",
            "user_profile",
            "task_breakdown",
            "expert_responses",
            "ui_interrupt_flag",
            "interrupt_reason",
            "node_execution_status",
            "error_info",
            "final_report",
        ]
        
        for field in expected_fields:
            assert field in annotations, f"Missing field: {field}"
    
    def test_health_state_as_dict_operations(self) -> None:
        """HealthState 支持标准字典操作"""
        state: HealthState = {"user_query": "test"}
        
        # 获取
        assert state.get("user_query") == "test"
        assert state.get("non_existent") is None
        
        # 更新
        state["ui_interrupt_flag"] = True
        assert state["ui_interrupt_flag"] is True
        
        # 删除
        del state["ui_interrupt_flag"]
        assert "ui_interrupt_flag" not in state


# ==================== Integration Tests ====================

class TestStateIntegration:
    """状态模型集成测试"""
    
    def test_subtask_in_health_state(self) -> None:
        """SubTask 可以在 HealthState 中使用"""
        subtask = SubTask(
            task_id="task_001",
            target_agent=TargetAgent.NUTRITION,
            task_description="分析用户血脂状况",
        )
        
        state: HealthState = {
            "task_breakdown": [subtask],
        }
        
        assert state["task_breakdown"][0] == subtask
    
    def test_error_info_in_health_state(self) -> None:
        """ErrorInfo 可以在 HealthState 中使用"""
        error = ErrorInfo(
            node_name="controller",
            error_type="ProcessingError",
            error_message="处理失败",
        )
        
        state: HealthState = {
            "error_info": [error],
        }
        
        assert state["error_info"][0] == error
    
    def test_node_execution_status_in_health_state(self) -> None:
        """NodeExecutionStatus 可以在 HealthState 中使用"""
        state: HealthState = {
            "node_execution_status": {
                "controller": NodeExecutionStatus.COMPLETED,
                "nutrition": NodeExecutionStatus.FAILED,
            },
        }
        
        assert state["node_execution_status"]["controller"] == "completed"
        assert state["node_execution_status"]["nutrition"] == "failed"
    
    def test_complete_workflow_state(self) -> None:
        """模拟完整工作流状态"""
        # 1. 初始状态
        state: HealthState = {
            "user_query": "我最近血脂偏高，睡眠质量差",
            "ui_interrupt_flag": False,
            "interrupt_reason": "",
            "node_execution_status": {
                "controller": NodeExecutionStatus.PENDING,
                "nutrition": NodeExecutionStatus.PENDING,
                "rehabilitation": NodeExecutionStatus.PENDING,
                "neuropsychology": NodeExecutionStatus.PENDING,
                "synthesis": NodeExecutionStatus.PENDING,
            },
            "error_info": [],
            "final_report": None,
        }
        
        # 2. Controller 完成后的状态
        state["task_breakdown"] = [
            SubTask(
                task_id="t1",
                target_agent=TargetAgent.NUTRITION,
                task_description="分析血脂",
            ),
            SubTask(
                task_id="t2",
                target_agent=TargetAgent.NEUROPSYCHOLOGY,
                task_description="分析睡眠",
            ),
        ]
        state["node_execution_status"]["controller"] = NodeExecutionStatus.COMPLETED
        
        assert len(state["task_breakdown"]) == 2
        assert state["node_execution_status"]["controller"] == NodeExecutionStatus.COMPLETED
        
        # 3. 专家完成后的状态
        state["expert_responses"] = {
            "nutrition": "建议减少饱和脂肪摄入...",
            "neuropsychology": "建议进行睡眠调整...",
        }
        state["node_execution_status"]["nutrition"] = NodeExecutionStatus.COMPLETED
        state["node_execution_status"]["neuropsychology"] = NodeExecutionStatus.COMPLETED
        
        assert len(state["expert_responses"]) == 2
