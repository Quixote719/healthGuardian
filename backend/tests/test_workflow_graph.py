"""
Tests for the LangGraph workflow graph module

Tests cover:
- Workflow creation and structure
- Conditional routing functions
- Compiled workflow factory
- Node function execution
- Integration with agent instances
- Timeout and exception handling (Requirements 10.7, 10.8)

Requirements: 10.1-10.3, 10.7, 10.8
"""

import asyncio
import pytest
from datetime import date
from unittest.mock import AsyncMock, patch, MagicMock

from app.workflow.graph import (
    LANGGRAPH_AVAILABLE,
    AGENT_TIMEOUT_SECONDS,
    create_health_workflow,
    create_sequential_health_workflow,
    create_parallel_health_workflow,
    get_compiled_workflow,
    get_persistent_workflow,
    should_interrupt_after_controller,
    should_interrupt_after_synthesis,
    with_timeout_and_error_handling,
    controller_node,
    nutrition_node,
    rehabilitation_node,
    neuropsychology_node,
    synthesis_node,
    controller_agent,
    nutrition_agent,
    rehabilitation_agent,
    neuropsychology_agent,
    synthesis_agent,
)
from app.models.state import HealthState, SubTask, TargetAgent, ErrorInfo, NodeExecutionStatus
from app.models.user_profile import (
    UserProfile,
    Gender,
    MedicalHistory,
    DiseaseStatus,
    Medication,
    MedicationFrequency,
    BloodLipids,
    BloodGlucose,
    PhysicalExamination,
    Lifestyle,
    ExerciseFrequency,
    DietHabit,
)
from app.models.final_report import FinalReport, ConfirmationStatus


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_user_profile():
    """Create a sample user profile for testing"""
    return UserProfile(
        age=35,
        gender=Gender.MALE,
        height=175.0,
        weight=70.0,
        medical_history=[],
        physical_examination=PhysicalExamination(
            blood_lipids=BloodLipids(
                total_cholesterol=5.0,
                triglycerides=1.5,
                hdl=1.2,
                ldl=3.0,
            ),
            blood_glucose=BloodGlucose(
                fasting_glucose=5.5,
                hba1c=5.4,
            ),
        ),
        medications=[],
        lifestyle=Lifestyle(
            sleep_duration=7.5,
            exercise_frequency=ExerciseFrequency.THREE_TO_FIVE,
            diet_habit=DietHabit.BALANCED,
            stress_level=4,
        ),
    )


@pytest.fixture
def sample_initial_state(sample_user_profile) -> HealthState:
    """Create a sample initial state for testing"""
    return {
        "user_query": "我想了解如何改善睡眠质量和运动计划",
        "user_profile": sample_user_profile,
        "task_breakdown": [],
        "expert_responses": {},
        "ui_interrupt_flag": False,
        "interrupt_reason": "",
        "node_execution_status": {},
        "error_info": [],
        "final_report": None,
    }


@pytest.fixture
def sample_high_risk_state(sample_user_profile) -> HealthState:
    """Create a state with high risk flag set"""
    return {
        "user_query": "我想停药并尝试水断食",
        "user_profile": sample_user_profile,
        "task_breakdown": [],
        "expert_responses": {},
        "ui_interrupt_flag": True,
        "interrupt_reason": "检测到高风险内容",
        "node_execution_status": {},
        "error_info": [],
        "final_report": None,
    }


@pytest.fixture
def sample_completed_state(sample_user_profile) -> HealthState:
    """Create a state with completed workflow"""
    return {
        "user_query": "健康咨询",
        "user_profile": sample_user_profile,
        "task_breakdown": [
            SubTask(
                task_id="t1",
                target_agent=TargetAgent.NUTRITION,
                task_description="营养分析",
            ),
        ],
        "expert_responses": {
            "controller": "任务分解完成",
            "nutrition": "营养建议",
            "rehabilitation": "康复建议",
            "neuropsychology": "心理建议",
        },
        "ui_interrupt_flag": False,
        "interrupt_reason": "",
        "node_execution_status": {},
        "error_info": [],
        "final_report": FinalReport(
            deep_insight="测试洞察",
            action_plan=[],
            follow_up="测试随访计划",
            requires_confirmation=False,
            session_id="test_session",
            confirmation_status=ConfirmationStatus.PENDING,
        ),
    }


# ============================================================================
# Module Import Tests
# ============================================================================


class TestModuleImports:
    """Test module imports and exports"""

    def test_langgraph_available_is_bool(self):
        """LANGGRAPH_AVAILABLE should be a boolean"""
        assert isinstance(LANGGRAPH_AVAILABLE, bool)

    def test_can_import_workflow_functions(self):
        """Should be able to import all workflow functions"""
        assert create_health_workflow is not None
        assert create_sequential_health_workflow is not None
        assert create_parallel_health_workflow is not None
        assert get_compiled_workflow is not None
        assert get_persistent_workflow is not None

    def test_can_import_routing_functions(self):
        """Should be able to import routing functions"""
        assert should_interrupt_after_controller is not None
        assert should_interrupt_after_synthesis is not None

    def test_can_import_agent_instances(self):
        """Should be able to import agent instances"""
        assert controller_agent is not None
        assert nutrition_agent is not None
        assert rehabilitation_agent is not None
        assert neuropsychology_agent is not None
        assert synthesis_agent is not None


# ============================================================================
# Agent Instance Tests
# ============================================================================


class TestAgentInstances:
    """Test agent instances are correctly initialized"""

    def test_controller_agent_name(self):
        """Controller agent should have correct name"""
        assert controller_agent.name == "Controller_Agent"

    def test_nutrition_agent_name(self):
        """Nutrition agent should have correct name"""
        assert nutrition_agent.name == "Nutrition_Agent"

    def test_rehabilitation_agent_name(self):
        """Rehabilitation agent should have correct name"""
        assert rehabilitation_agent.name == "Rehabilitation_Agent"

    def test_neuropsychology_agent_name(self):
        """Neuropsychology agent should have correct name"""
        assert neuropsychology_agent.name == "Neuropsychology_Agent"

    def test_synthesis_agent_name(self):
        """Synthesis agent should have correct name"""
        assert synthesis_agent.name == "Synthesis_Agent"


# ============================================================================
# Workflow Creation Tests
# ============================================================================


class TestWorkflowCreation:
    """Test workflow creation functions"""

    def test_create_health_workflow_returns_state_graph(self):
        """create_health_workflow should return a StateGraph"""
        workflow = create_health_workflow()
        assert workflow is not None
        assert hasattr(workflow, "nodes")

    def test_create_sequential_health_workflow_returns_state_graph(self):
        """create_sequential_health_workflow should return a StateGraph"""
        workflow = create_sequential_health_workflow()
        assert workflow is not None
        assert hasattr(workflow, "nodes")

    def test_create_parallel_health_workflow_returns_state_graph(self):
        """create_parallel_health_workflow should return a StateGraph"""
        workflow = create_parallel_health_workflow()
        assert workflow is not None
        assert hasattr(workflow, "nodes")

    def test_workflow_has_all_nodes(self):
        """Workflow should have all 5 agent nodes"""
        workflow = create_sequential_health_workflow()
        expected_nodes = ["controller", "nutrition", "rehabilitation", "neuropsychology", "synthesis"]
        for node_name in expected_nodes:
            assert node_name in workflow.nodes, f"Missing node: {node_name}"

    def test_workflow_has_controller_as_entry_point(self):
        """Workflow should have controller as entry point"""
        workflow = create_sequential_health_workflow()
        assert workflow._entry_point == "controller"

    def test_workflow_nodes_are_callable(self):
        """All workflow nodes should be callable functions"""
        workflow = create_sequential_health_workflow()
        for node_name, node_func in workflow.nodes.items():
            assert callable(node_func), f"Node {node_name} is not callable"


# ============================================================================
# Conditional Routing Tests
# ============================================================================


class TestShouldInterruptAfterController:
    """Test the should_interrupt_after_controller routing function"""

    def test_returns_parallel_when_no_interrupt_flag(self):
        """Should return 'parallel' when ui_interrupt_flag is False"""
        state: HealthState = {
            "ui_interrupt_flag": False,
            "task_breakdown": [
                SubTask(task_id="t1", target_agent=TargetAgent.NUTRITION, task_description="test"),
            ],
        }
        result = should_interrupt_after_controller(state)
        assert result == "parallel"

    def test_returns_interrupt_when_flag_is_true(self):
        """Should return 'interrupt' when ui_interrupt_flag is True"""
        state: HealthState = {
            "ui_interrupt_flag": True,
            "task_breakdown": [],
        }
        result = should_interrupt_after_controller(state)
        assert result == "interrupt"

    def test_returns_interrupt_when_no_task_breakdown(self):
        """Should return 'interrupt' when task_breakdown is empty"""
        state: HealthState = {
            "ui_interrupt_flag": False,
            "task_breakdown": [],
        }
        result = should_interrupt_after_controller(state)
        assert result == "interrupt"

    def test_returns_interrupt_when_task_breakdown_missing(self):
        """Should return 'interrupt' when task_breakdown key is missing"""
        state: HealthState = {
            "ui_interrupt_flag": False,
        }
        result = should_interrupt_after_controller(state)
        assert result == "interrupt"

    def test_returns_parallel_with_valid_tasks(self):
        """Should return 'parallel' when there are valid tasks"""
        state: HealthState = {
            "ui_interrupt_flag": False,
            "task_breakdown": [
                SubTask(task_id="t1", target_agent=TargetAgent.NUTRITION, task_description="nutrition task"),
                SubTask(task_id="t2", target_agent=TargetAgent.REHABILITATION, task_description="rehab task"),
            ],
        }
        result = should_interrupt_after_controller(state)
        assert result == "parallel"

    def test_interrupt_takes_priority_over_tasks(self):
        """ui_interrupt_flag should take priority even with valid tasks"""
        state: HealthState = {
            "ui_interrupt_flag": True,
            "task_breakdown": [
                SubTask(task_id="t1", target_agent=TargetAgent.NUTRITION, task_description="test"),
            ],
        }
        result = should_interrupt_after_controller(state)
        assert result == "interrupt"


class TestShouldInterruptAfterSynthesis:
    """Test the should_interrupt_after_synthesis routing function"""

    def test_returns_end_when_no_final_report(self):
        """Should return 'end' when final_report is None"""
        state: HealthState = {
            "final_report": None,
        }
        result = should_interrupt_after_synthesis(state)
        assert result == "end"

    def test_returns_end_when_no_confirmation_required(self):
        """Should return 'end' when requires_confirmation is False"""
        state: HealthState = {
            "final_report": FinalReport(
                deep_insight="test",
                action_plan=[],
                follow_up="test followup",
                requires_confirmation=False,
                session_id="test",
            ),
        }
        result = should_interrupt_after_synthesis(state)
        assert result == "end"

    def test_returns_interrupt_when_confirmation_required(self):
        """Should return 'interrupt' when requires_confirmation is True"""
        state: HealthState = {
            "final_report": FinalReport(
                deep_insight="test",
                action_plan=[],
                follow_up="test followup",
                requires_confirmation=True,
                session_id="test",
            ),
        }
        result = should_interrupt_after_synthesis(state)
        assert result == "interrupt"

    def test_handles_dict_final_report(self):
        """Should handle final_report as dict (not FinalReport object)"""
        state: HealthState = {
            "final_report": {
                "deep_insight": "test",
                "action_plan": [],
                "follow_up": "test",
                "requires_confirmation": True,
                "session_id": "test",
            },
        }
        result = should_interrupt_after_synthesis(state)
        assert result == "interrupt"

    def test_handles_dict_no_confirmation(self):
        """Should handle dict final_report with no confirmation required"""
        state: HealthState = {
            "final_report": {
                "requires_confirmation": False,
            },
        }
        result = should_interrupt_after_synthesis(state)
        assert result == "end"


# ============================================================================
# Compiled Workflow Tests
# ============================================================================


class TestGetCompiledWorkflow:
    """Test the get_compiled_workflow function"""

    def test_returns_compiled_workflow(self):
        """Should return a compiled workflow"""
        workflow = get_compiled_workflow()
        assert workflow is not None

    def test_accepts_custom_checkpointer(self):
        """Should accept a custom checkpointer"""
        # Using mock SqliteSaver since LangGraph may not be available
        from app.workflow.graph import SqliteSaver
        checkpointer = SqliteSaver.from_conn_string(":memory:")
        workflow = get_compiled_workflow(checkpointer=checkpointer)
        assert workflow is not None

    def test_has_ainvoke_method(self):
        """Compiled workflow should have ainvoke method"""
        workflow = get_compiled_workflow()
        assert hasattr(workflow, "ainvoke")
        assert callable(workflow.ainvoke)


class TestGetPersistentWorkflow:
    """Test the get_persistent_workflow function"""

    def test_returns_compiled_workflow(self):
        """Should return a compiled workflow"""
        workflow = get_persistent_workflow(db_path=":memory:")
        assert workflow is not None

    def test_accepts_custom_db_path(self):
        """Should accept a custom database path"""
        workflow = get_persistent_workflow(db_path=":memory:")
        assert workflow is not None


# ============================================================================
# Workflow Execution Tests
# ============================================================================


class TestWorkflowExecution:
    """Test workflow execution with mock compiled graph"""

    @pytest.mark.asyncio
    async def test_workflow_executes_controller(self, sample_initial_state):
        """Workflow should execute controller node"""
        workflow = get_compiled_workflow()
        
        # Execute workflow
        result = await workflow.ainvoke(sample_initial_state, {"configurable": {"thread_id": "test_1"}})
        
        # Controller should have processed the state
        assert result is not None
        # Check that controller added its response or modified state
        assert "expert_responses" in result or "task_breakdown" in result

    @pytest.mark.asyncio
    async def test_workflow_handles_empty_state(self):
        """Workflow should handle empty state gracefully"""
        workflow = get_compiled_workflow()
        
        result = await workflow.ainvoke({}, {"configurable": {"thread_id": "test_2"}})
        assert result is not None

    @pytest.mark.asyncio
    async def test_workflow_handles_none_state(self):
        """Workflow should handle None state"""
        workflow = get_compiled_workflow()
        
        result = await workflow.ainvoke(None, {"configurable": {"thread_id": "test_3"}})
        assert result is not None


# ============================================================================
# Integration Tests
# ============================================================================


class TestWorkflowIntegration:
    """Integration tests for the workflow with agents"""

    def test_all_agents_have_process_method(self):
        """All agent instances should have async process method"""
        agents = [
            controller_agent,
            nutrition_agent,
            rehabilitation_agent,
            neuropsychology_agent,
            synthesis_agent,
        ]
        for agent in agents:
            assert hasattr(agent, "process")
            assert callable(agent.process)

    def test_all_agents_have_get_system_prompt_method(self):
        """All agent instances should have get_system_prompt method"""
        agents = [
            controller_agent,
            nutrition_agent,
            rehabilitation_agent,
            neuropsychology_agent,
            synthesis_agent,
        ]
        for agent in agents:
            assert hasattr(agent, "get_system_prompt")
            prompt = agent.get_system_prompt()
            assert isinstance(prompt, str)
            assert len(prompt) > 0

    @pytest.mark.asyncio
    async def test_controller_agent_processes_state(self, sample_initial_state):
        """Controller agent should process state correctly"""
        result = await controller_agent.process(sample_initial_state)
        
        # Controller should modify the state
        assert result is not None
        # Should have task_breakdown
        assert "task_breakdown" in result
        # Should have expert_responses
        assert "expert_responses" in result

    @pytest.mark.asyncio
    async def test_workflow_full_execution(self, sample_initial_state):
        """Test full workflow execution with sample state"""
        workflow = get_compiled_workflow()
        
        result = await workflow.ainvoke(
            sample_initial_state,
            {"configurable": {"thread_id": "full_test_1"}}
        )
        
        # Workflow should complete
        assert result is not None


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_routing_with_minimal_state(self):
        """Routing functions should handle minimal state"""
        minimal_state: HealthState = {}
        
        # Should not raise exceptions
        result1 = should_interrupt_after_controller(minimal_state)
        result2 = should_interrupt_after_synthesis(minimal_state)
        
        assert result1 in ["interrupt", "parallel"]
        assert result2 in ["interrupt", "end"]

    def test_workflow_creation_is_idempotent(self):
        """Multiple workflow creations should produce consistent results"""
        workflow1 = create_sequential_health_workflow()
        workflow2 = create_sequential_health_workflow()
        
        # Both should have same nodes
        assert set(workflow1.nodes.keys()) == set(workflow2.nodes.keys())

    def test_compiled_workflow_with_different_sessions(self):
        """Compiled workflow should handle different session IDs"""
        workflow = get_compiled_workflow()
        
        config1 = {"configurable": {"thread_id": "session_a"}}
        config2 = {"configurable": {"thread_id": "session_b"}}
        
        # Should be able to create configs for different sessions
        assert config1["configurable"]["thread_id"] != config2["configurable"]["thread_id"]


# ============================================================================
# Requirement Validation Tests
# ============================================================================


class TestRequirementValidation:
    """Tests that validate specific requirements"""

    def test_req_10_1_uses_state_graph(self):
        """Requirement 10.1: Uses StateGraph to create workflow"""
        workflow = create_sequential_health_workflow()
        # Verify it has StateGraph-like structure
        assert hasattr(workflow, "nodes")
        assert hasattr(workflow, "add_node")
        assert hasattr(workflow, "add_edge")
        assert hasattr(workflow, "set_entry_point")

    def test_req_10_1_five_agent_nodes(self):
        """Requirement 10.1: Has 5 agent nodes"""
        workflow = create_sequential_health_workflow()
        expected_nodes = ["controller", "nutrition", "rehabilitation", "neuropsychology", "synthesis"]
        assert len(workflow.nodes) >= 5
        for node in expected_nodes:
            assert node in workflow.nodes

    def test_req_10_1_controller_is_entry_point(self):
        """Requirement 10.1: Controller is entry point"""
        workflow = create_sequential_health_workflow()
        assert workflow._entry_point == "controller"

    def test_req_10_2_interrupt_after_controller(self):
        """Requirement 10.2: Implements ui_interrupt_flag check after controller"""
        # Test interrupt condition
        state_interrupt: HealthState = {"ui_interrupt_flag": True, "task_breakdown": []}
        assert should_interrupt_after_controller(state_interrupt) == "interrupt"
        
        # Test continue condition
        state_continue: HealthState = {
            "ui_interrupt_flag": False,
            "task_breakdown": [
                SubTask(task_id="t1", target_agent=TargetAgent.NUTRITION, task_description="test")
            ],
        }
        assert should_interrupt_after_controller(state_continue) == "parallel"

    def test_req_10_3_interrupt_after_synthesis(self):
        """Requirement 10.3: Implements requires_confirmation check after synthesis"""
        # Test requires confirmation
        state_confirm: HealthState = {
            "final_report": FinalReport(
                deep_insight="test",
                action_plan=[],
                follow_up="test",
                requires_confirmation=True,
                session_id="test",
            ),
        }
        assert should_interrupt_after_synthesis(state_confirm) == "interrupt"
        
        # Test no confirmation needed
        state_no_confirm: HealthState = {
            "final_report": FinalReport(
                deep_insight="test",
                action_plan=[],
                follow_up="test",
                requires_confirmation=False,
                session_id="test",
            ),
        }
        assert should_interrupt_after_synthesis(state_no_confirm) == "end"

    def test_req_10_3_checkpointer_support(self):
        """Requirement 10.3: Supports checkpointer persistence"""
        from app.workflow.graph import SqliteSaver
        
        # Should be able to create checkpointer
        checkpointer = SqliteSaver.from_conn_string(":memory:")
        assert checkpointer is not None
        
        # Should be able to use checkpointer in workflow
        workflow = get_compiled_workflow(checkpointer=checkpointer)
        assert workflow is not None


# ============================================================================
# Timeout and Exception Handling Tests (Requirements 10.7, 10.8)
# ============================================================================


class TestTimeoutConstant:
    """Test timeout constant configuration"""

    def test_agent_timeout_is_30_seconds(self):
        """Requirement 10.7: Agent timeout should be 30 seconds"""
        assert AGENT_TIMEOUT_SECONDS == 30

    def test_timeout_constant_is_positive(self):
        """Timeout should be a positive integer"""
        assert AGENT_TIMEOUT_SECONDS > 0
        assert isinstance(AGENT_TIMEOUT_SECONDS, int)


class TestWithTimeoutAndErrorHandling:
    """Test the timeout and error handling wrapper function"""

    @pytest.fixture
    def minimal_state(self) -> HealthState:
        """Minimal state for testing"""
        return {
            "user_query": "test query",
            "error_info": [],
            "node_execution_status": {},
        }

    @pytest.mark.asyncio
    async def test_successful_execution_returns_result(self, minimal_state):
        """Successful agent execution should return the result"""
        async def mock_agent(state):
            return {**state, "processed": True}
        
        result = await with_timeout_and_error_handling(
            agent_process_func=mock_agent,
            state=minimal_state,
            node_name="test_agent",
        )
        
        assert result["processed"] is True
        assert result["node_execution_status"]["test_agent"] == NodeExecutionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_successful_execution_sets_completed_status(self, minimal_state):
        """Successful execution should set node status to COMPLETED"""
        async def mock_agent(state):
            return {**state, "done": True}
        
        result = await with_timeout_and_error_handling(
            agent_process_func=mock_agent,
            state=minimal_state,
            node_name="my_agent",
        )
        
        assert result["node_execution_status"]["my_agent"] == NodeExecutionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_timeout_records_error_info(self, minimal_state):
        """Timeout should record error in error_info list"""
        async def slow_agent(state):
            await asyncio.sleep(5)  # Longer than our test timeout
            return state
        
        result = await with_timeout_and_error_handling(
            agent_process_func=slow_agent,
            state=minimal_state,
            node_name="slow_agent",
            timeout_seconds=1,  # Use short timeout for test
        )
        
        # Should have error recorded
        assert len(result["error_info"]) == 1
        error = result["error_info"][0]
        assert error.node_name == "slow_agent"
        assert error.error_type == "agent_timeout"
        assert "超时" in error.error_message

    @pytest.mark.asyncio
    async def test_timeout_sets_failed_status(self, minimal_state):
        """Timeout should set node status to FAILED"""
        async def slow_agent(state):
            await asyncio.sleep(5)
            return state
        
        result = await with_timeout_and_error_handling(
            agent_process_func=slow_agent,
            state=minimal_state,
            node_name="slow_agent",
            timeout_seconds=1,
        )
        
        assert result["node_execution_status"]["slow_agent"] == NodeExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_exception_records_error_info(self, minimal_state):
        """Exception should record error in error_info list"""
        async def failing_agent(state):
            raise ValueError("Test error message")
        
        result = await with_timeout_and_error_handling(
            agent_process_func=failing_agent,
            state=minimal_state,
            node_name="failing_agent",
        )
        
        # Should have error recorded
        assert len(result["error_info"]) == 1
        error = result["error_info"][0]
        assert error.node_name == "failing_agent"
        assert error.error_type == "ValueError"
        assert "Test error message" in error.error_message

    @pytest.mark.asyncio
    async def test_exception_sets_failed_status(self, minimal_state):
        """Exception should set node status to FAILED"""
        async def failing_agent(state):
            raise RuntimeError("Something went wrong")
        
        result = await with_timeout_and_error_handling(
            agent_process_func=failing_agent,
            state=minimal_state,
            node_name="failing_agent",
        )
        
        assert result["node_execution_status"]["failing_agent"] == NodeExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_error_message_truncated_to_1000_chars(self, minimal_state):
        """Error message should be truncated to max 1000 characters"""
        long_message = "A" * 2000
        
        async def failing_agent(state):
            raise ValueError(long_message)
        
        result = await with_timeout_and_error_handling(
            agent_process_func=failing_agent,
            state=minimal_state,
            node_name="failing_agent",
        )
        
        error = result["error_info"][0]
        assert len(error.error_message) <= 1000

    @pytest.mark.asyncio
    async def test_preserves_existing_error_info(self, minimal_state):
        """New errors should be appended to existing error_info"""
        existing_error = ErrorInfo(
            node_name="previous_agent",
            error_type="PreviousError",
            error_message="Previous error",
        )
        minimal_state["error_info"] = [existing_error]
        
        async def failing_agent(state):
            raise ValueError("New error")
        
        result = await with_timeout_and_error_handling(
            agent_process_func=failing_agent,
            state=minimal_state,
            node_name="new_agent",
        )
        
        assert len(result["error_info"]) == 2
        assert result["error_info"][0].node_name == "previous_agent"
        assert result["error_info"][1].node_name == "new_agent"

    @pytest.mark.asyncio
    async def test_preserves_existing_node_status(self, minimal_state):
        """New node status should not overwrite existing status"""
        minimal_state["node_execution_status"] = {
            "previous_agent": NodeExecutionStatus.COMPLETED
        }
        
        async def mock_agent(state):
            return {**state, "done": True}
        
        result = await with_timeout_and_error_handling(
            agent_process_func=mock_agent,
            state=minimal_state,
            node_name="new_agent",
        )
        
        assert result["node_execution_status"]["previous_agent"] == NodeExecutionStatus.COMPLETED
        assert result["node_execution_status"]["new_agent"] == NodeExecutionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_graceful_degradation_returns_state(self, minimal_state):
        """On error, should return state (not raise exception)"""
        async def failing_agent(state):
            raise Exception("Critical error")
        
        # Should not raise
        result = await with_timeout_and_error_handling(
            agent_process_func=failing_agent,
            state=minimal_state,
            node_name="failing_agent",
        )
        
        # Should return a valid state dict
        assert isinstance(result, dict)
        assert "error_info" in result


class TestNodeFunctionsWithTimeout:
    """Test that node functions use timeout wrapper"""

    @pytest.fixture
    def sample_state(self, sample_user_profile) -> HealthState:
        """Sample state for node tests"""
        return {
            "user_query": "测试健康咨询",
            "user_profile": sample_user_profile,
            "task_breakdown": [],
            "expert_responses": {},
            "ui_interrupt_flag": False,
            "interrupt_reason": "",
            "node_execution_status": {},
            "error_info": [],
            "final_report": None,
        }

    @pytest.mark.asyncio
    async def test_controller_node_sets_execution_status(self, sample_state):
        """Controller node should set execution status"""
        result = await controller_node(sample_state)
        
        assert "node_execution_status" in result
        # Should have controller status set
        assert "controller" in result["node_execution_status"]

    @pytest.mark.asyncio
    async def test_nutrition_node_sets_execution_status(self, sample_state):
        """Nutrition node should set execution status"""
        # Add task breakdown so nutrition can run
        sample_state["task_breakdown"] = [
            SubTask(task_id="t1", target_agent=TargetAgent.NUTRITION, task_description="test")
        ]
        
        result = await nutrition_node(sample_state)
        
        assert "node_execution_status" in result
        assert "nutrition" in result["node_execution_status"]

    @pytest.mark.asyncio
    async def test_rehabilitation_node_sets_execution_status(self, sample_state):
        """Rehabilitation node should set execution status"""
        sample_state["task_breakdown"] = [
            SubTask(task_id="t1", target_agent=TargetAgent.REHABILITATION, task_description="test")
        ]
        
        result = await rehabilitation_node(sample_state)
        
        assert "node_execution_status" in result
        assert "rehabilitation" in result["node_execution_status"]

    @pytest.mark.asyncio
    async def test_neuropsychology_node_sets_execution_status(self, sample_state):
        """Neuropsychology node should set execution status"""
        sample_state["task_breakdown"] = [
            SubTask(task_id="t1", target_agent=TargetAgent.NEUROPSYCHOLOGY, task_description="test")
        ]
        
        result = await neuropsychology_node(sample_state)
        
        assert "node_execution_status" in result
        assert "neuropsychology" in result["node_execution_status"]

    @pytest.mark.asyncio
    async def test_synthesis_node_sets_execution_status(self, sample_state):
        """Synthesis node should set execution status"""
        sample_state["expert_responses"] = {
            "nutrition": "test",
            "rehabilitation": "test",
            "neuropsychology": "test",
        }
        
        result = await synthesis_node(sample_state)
        
        assert "node_execution_status" in result
        assert "synthesis" in result["node_execution_status"]


class TestSingleAgentFailureIsolation:
    """Test that single agent failure doesn't affect others (Requirement 10.8)"""

    @pytest.mark.asyncio
    async def test_one_failing_agent_doesnt_stop_others(self):
        """One agent failing should not prevent other agents from executing"""
        state: HealthState = {
            "user_query": "test",
            "error_info": [],
            "node_execution_status": {},
        }
        
        # Simulate first agent failing
        async def failing_agent(s):
            raise ValueError("Agent 1 failed")
        
        result1 = await with_timeout_and_error_handling(
            agent_process_func=failing_agent,
            state=state,
            node_name="agent1",
        )
        
        # First agent should be marked as failed
        assert result1["node_execution_status"]["agent1"] == NodeExecutionStatus.FAILED
        
        # Second agent should still be able to execute
        async def success_agent(s):
            return {**s, "agent2_completed": True}
        
        result2 = await with_timeout_and_error_handling(
            agent_process_func=success_agent,
            state=result1,
            node_name="agent2",
        )
        
        # Second agent should complete successfully
        assert result2["node_execution_status"]["agent2"] == NodeExecutionStatus.COMPLETED
        assert result2["agent2_completed"] is True
        
        # First agent's failed status should still be there
        assert result2["node_execution_status"]["agent1"] == NodeExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_errors_accumulate_across_agents(self):
        """Errors from multiple agents should accumulate in error_info"""
        state: HealthState = {
            "user_query": "test",
            "error_info": [],
            "node_execution_status": {},
        }
        
        async def failing_agent1(s):
            raise ValueError("Error from agent 1")
        
        async def failing_agent2(s):
            raise RuntimeError("Error from agent 2")
        
        result1 = await with_timeout_and_error_handling(
            agent_process_func=failing_agent1,
            state=state,
            node_name="agent1",
        )
        
        result2 = await with_timeout_and_error_handling(
            agent_process_func=failing_agent2,
            state=result1,
            node_name="agent2",
        )
        
        # Should have both errors recorded
        assert len(result2["error_info"]) == 2
        error_nodes = [e.node_name for e in result2["error_info"]]
        assert "agent1" in error_nodes
        assert "agent2" in error_nodes


class TestRequirement10_7_Timeout:
    """Specific tests for Requirement 10.7: Agent timeout"""

    def test_timeout_is_30_seconds(self):
        """Requirement 10.7: Single agent timeout is 30 seconds"""
        assert AGENT_TIMEOUT_SECONDS == 30

    @pytest.mark.asyncio
    async def test_timeout_terminates_agent(self):
        """Requirement 10.7: Timeout terminates agent execution"""
        state: HealthState = {
            "error_info": [],
            "node_execution_status": {},
        }
        
        execution_completed = False
        
        async def slow_agent(s):
            nonlocal execution_completed
            await asyncio.sleep(10)  # Would take 10 seconds
            execution_completed = True
            return s
        
        # Use 1 second timeout for test speed
        result = await with_timeout_and_error_handling(
            agent_process_func=slow_agent,
            state=state,
            node_name="slow_agent",
            timeout_seconds=1,
        )
        
        # Agent should have been terminated
        assert execution_completed is False
        assert result["node_execution_status"]["slow_agent"] == NodeExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_timeout_records_status(self):
        """Requirement 10.7: Timeout records status in state"""
        state: HealthState = {
            "error_info": [],
            "node_execution_status": {},
        }
        
        async def slow_agent(s):
            await asyncio.sleep(10)
            return s
        
        result = await with_timeout_and_error_handling(
            agent_process_func=slow_agent,
            state=state,
            node_name="timeout_agent",
            timeout_seconds=1,
        )
        
        # Status should be recorded
        assert result["node_execution_status"]["timeout_agent"] == NodeExecutionStatus.FAILED
        
        # Error info should be recorded
        assert len(result["error_info"]) == 1
        error = result["error_info"][0]
        assert error.error_type == "agent_timeout"


class TestRequirement10_8_ExceptionHandling:
    """Specific tests for Requirement 10.8: Exception handling"""

    @pytest.mark.asyncio
    async def test_exception_is_captured(self):
        """Requirement 10.8: Exceptions are captured"""
        state: HealthState = {
            "error_info": [],
            "node_execution_status": {},
        }
        
        async def failing_agent(s):
            raise KeyError("missing_key")
        
        # Should not raise
        result = await with_timeout_and_error_handling(
            agent_process_func=failing_agent,
            state=state,
            node_name="failing_agent",
        )
        
        # Should have captured the error
        assert len(result["error_info"]) == 1

    @pytest.mark.asyncio
    async def test_error_info_is_recorded(self):
        """Requirement 10.8: Error info is recorded in state"""
        state: HealthState = {
            "error_info": [],
            "node_execution_status": {},
        }
        
        async def failing_agent(s):
            raise TypeError("invalid type")
        
        result = await with_timeout_and_error_handling(
            agent_process_func=failing_agent,
            state=state,
            node_name="type_error_agent",
        )
        
        error = result["error_info"][0]
        assert error.node_name == "type_error_agent"
        assert error.error_type == "TypeError"
        assert "invalid type" in error.error_message
        assert error.timestamp is not None

    @pytest.mark.asyncio
    async def test_workflow_continues_after_exception(self):
        """Requirement 10.8: Single agent failure doesn't affect others"""
        state: HealthState = {
            "error_info": [],
            "node_execution_status": {},
            "data": "initial",
        }
        
        # First agent fails
        async def agent1(s):
            raise Exception("Agent 1 crashed")
        
        result1 = await with_timeout_and_error_handling(
            agent_process_func=agent1,
            state=state,
            node_name="agent1",
        )
        
        # Workflow can continue with second agent
        async def agent2(s):
            return {**s, "data": "modified by agent2"}
        
        result2 = await with_timeout_and_error_handling(
            agent_process_func=agent2,
            state=result1,
            node_name="agent2",
        )
        
        # Agent 2 successfully modified state
        assert result2["data"] == "modified by agent2"
        assert result2["node_execution_status"]["agent2"] == NodeExecutionStatus.COMPLETED
