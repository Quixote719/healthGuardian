"""
Tests for the HITL (Human-in-the-Loop) Manager module

Tests cover:
- HITLManager initialization
- pause_workflow functionality
- resume_workflow with confirm/reject
- check_timeout functionality
- Session management operations
- Timeout auto-termination
- 30-minute max pause time requirement

Requirements: 10.3-10.6
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.workflow.hitl import (
    HITLManager,
    PausedSession,
    SessionStatus,
    LANGGRAPH_CHECKPOINTER_AVAILABLE,
)
from app.models.state import HealthState, SubTask, TargetAgent
from app.models.final_report import FinalReport, ConfirmationStatus
from app.models.action_item import ActionItem, ActionCategory, Priority, RiskLevel


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def hitl_manager():
    """Create a fresh HITLManager instance for each test"""
    return HITLManager()


@pytest.fixture
def hitl_manager_short_timeout():
    """Create an HITLManager with a short timeout for testing"""
    return HITLManager(max_pause_minutes=1)


@pytest.fixture
def sample_state() -> HealthState:
    """Create a sample HealthState for testing"""
    return {
        "user_query": "我想了解如何改善健康",
        "user_profile": None,
        "task_breakdown": [
            SubTask(task_id="t1", target_agent=TargetAgent.NUTRITION, task_description="test"),
        ],
        "expert_responses": {"controller": "任务分解完成"},
        "ui_interrupt_flag": True,
        "interrupt_reason": "检测到高风险干预",
        "node_execution_status": {},
        "error_info": [],
        "final_report": None,
    }


@pytest.fixture
def sample_state_with_report() -> HealthState:
    """Create a sample HealthState with FinalReport for testing"""
    return {
        "user_query": "我想了解如何改善健康",
        "user_profile": None,
        "task_breakdown": [],
        "expert_responses": {},
        "ui_interrupt_flag": True,
        "interrupt_reason": "需要确认高风险干预",
        "node_execution_status": {},
        "error_info": [],
        "final_report": FinalReport(
            deep_insight="测试洞察",
            action_plan=[],
            follow_up="测试随访计划",
            requires_confirmation=True,
            session_id="test_session",
            confirmation_status=ConfirmationStatus.PENDING,
        ),
    }


@pytest.fixture
def sample_high_risk_items():
    """Create sample high-risk action items for testing"""
    return [
        ActionItem(
            category=ActionCategory.NUTRITION,
            title="停药建议",
            description="建议停用当前降压药物",
            frequency="立即",
            priority=Priority.HIGH,
            risk_level=RiskLevel.HIGH,
            duration="1周",
        ),
        ActionItem(
            category=ActionCategory.REHABILITATION,
            title="高强度运动",
            description="建议进行高强度有氧运动",
            frequency="每日",
            priority=Priority.HIGH,
            risk_level=RiskLevel.HIGH,
            duration="4周",
        ),
    ]


# ============================================================================
# Module Import Tests
# ============================================================================


class TestModuleImports:
    """Test module imports and exports"""

    def test_can_import_hitl_manager(self):
        """Should be able to import HITLManager"""
        assert HITLManager is not None

    def test_can_import_paused_session(self):
        """Should be able to import PausedSession"""
        assert PausedSession is not None

    def test_can_import_session_status(self):
        """Should be able to import SessionStatus"""
        assert SessionStatus is not None

    def test_langgraph_checkpointer_available_is_bool(self):
        """LANGGRAPH_CHECKPOINTER_AVAILABLE should be a boolean"""
        assert isinstance(LANGGRAPH_CHECKPOINTER_AVAILABLE, bool)

    def test_can_import_from_workflow_module(self):
        """Should be able to import from app.workflow"""
        from app.workflow import HITLManager as ImportedHITLManager
        from app.workflow import SessionStatus as ImportedSessionStatus
        assert ImportedHITLManager is not None
        assert ImportedSessionStatus is not None


# ============================================================================
# HITLManager Initialization Tests
# ============================================================================


class TestHITLManagerInit:
    """Test HITLManager initialization"""

    def test_default_initialization(self):
        """HITLManager should initialize with default values"""
        manager = HITLManager()
        assert manager.checkpointer is None
        assert manager.max_pause_minutes == 30
        assert len(manager._paused_sessions) == 0
        assert manager._running is False

    def test_custom_checkpointer(self):
        """HITLManager should accept custom checkpointer"""
        mock_checkpointer = MagicMock()
        manager = HITLManager(checkpointer=mock_checkpointer)
        assert manager.checkpointer is mock_checkpointer

    def test_custom_max_pause_minutes(self):
        """HITLManager should accept custom max pause time"""
        manager = HITLManager(max_pause_minutes=60)
        assert manager.max_pause_minutes == 60

    def test_default_max_pause_minutes_is_30(self):
        """Default max pause time should be 30 minutes (Requirement 10.5)"""
        manager = HITLManager()
        assert manager.max_pause_minutes == HITLManager.DEFAULT_MAX_PAUSE_MINUTES
        assert HITLManager.DEFAULT_MAX_PAUSE_MINUTES == 30


# ============================================================================
# PausedSession Tests
# ============================================================================


class TestPausedSession:
    """Test PausedSession data class"""

    def test_paused_session_creation(self, sample_state, sample_high_risk_items):
        """PausedSession should be created with correct values"""
        session = PausedSession(
            session_id="test_123",
            state=sample_state,
            reason="高风险干预",
            high_risk_items=sample_high_risk_items,
        )
        
        assert session.session_id == "test_123"
        assert session.state == sample_state
        assert session.reason == "高风险干预"
        assert len(session.high_risk_items) == 2
        assert session.status == SessionStatus.PAUSED
        assert session.paused_at is not None

    def test_elapsed_seconds_calculation(self, sample_state):
        """PausedSession should correctly calculate elapsed time"""
        session = PausedSession(
            session_id="test_123",
            state=sample_state,
            reason="test",
        )
        
        # Should have some small elapsed time
        elapsed = session.elapsed_seconds()
        assert elapsed >= 0
        assert elapsed < 1  # Should be very small

    def test_elapsed_minutes_calculation(self, sample_state):
        """PausedSession should correctly calculate elapsed minutes"""
        session = PausedSession(
            session_id="test_123",
            state=sample_state,
            reason="test",
        )
        
        elapsed = session.elapsed_minutes()
        assert elapsed >= 0
        assert elapsed < 0.1  # Should be very small

    def test_to_dict(self, sample_state):
        """PausedSession should convert to dict correctly"""
        session = PausedSession(
            session_id="test_123",
            state=sample_state,
            reason="test reason",
        )
        
        result = session.to_dict()
        assert result["session_id"] == "test_123"
        assert result["reason"] == "test reason"
        assert result["status"] == SessionStatus.PAUSED.value
        assert "elapsed_seconds" in result
        assert "paused_at" in result


# ============================================================================
# pause_workflow Tests
# ============================================================================


class TestPauseWorkflow:
    """Test pause_workflow functionality"""

    @pytest.mark.asyncio
    async def test_pause_workflow_basic(self, hitl_manager, sample_state):
        """pause_workflow should store session correctly"""
        await hitl_manager.pause_workflow(
            session_id="sess_001",
            state=sample_state,
            reason="高风险干预检测",
        )
        
        assert "sess_001" in hitl_manager._paused_sessions
        session = hitl_manager._paused_sessions["sess_001"]
        assert session.state == sample_state
        assert session.reason == "高风险干预检测"
        assert session.status == SessionStatus.PAUSED

    @pytest.mark.asyncio
    async def test_pause_workflow_with_high_risk_items(
        self, hitl_manager, sample_state, sample_high_risk_items
    ):
        """pause_workflow should store high-risk items"""
        await hitl_manager.pause_workflow(
            session_id="sess_002",
            state=sample_state,
            reason="需要确认高风险干预",
            high_risk_items=sample_high_risk_items,
        )
        
        session = hitl_manager._paused_sessions["sess_002"]
        assert len(session.high_risk_items) == 2

    @pytest.mark.asyncio
    async def test_pause_workflow_empty_session_id_raises_error(self, hitl_manager, sample_state):
        """pause_workflow should raise ValueError for empty session_id"""
        with pytest.raises(ValueError, match="session_id cannot be empty"):
            await hitl_manager.pause_workflow(
                session_id="",
                state=sample_state,
                reason="test",
            )

    @pytest.mark.asyncio
    async def test_pause_workflow_multiple_sessions(self, hitl_manager, sample_state):
        """pause_workflow should handle multiple sessions"""
        await hitl_manager.pause_workflow("sess_a", sample_state, "reason_a")
        await hitl_manager.pause_workflow("sess_b", sample_state, "reason_b")
        await hitl_manager.pause_workflow("sess_c", sample_state, "reason_c")
        
        assert hitl_manager.get_session_count() == 3
        assert "sess_a" in hitl_manager._paused_sessions
        assert "sess_b" in hitl_manager._paused_sessions
        assert "sess_c" in hitl_manager._paused_sessions


# ============================================================================
# resume_workflow Tests
# ============================================================================


class TestResumeWorkflow:
    """Test resume_workflow functionality"""

    @pytest.mark.asyncio
    async def test_resume_workflow_confirmed(self, hitl_manager, sample_state):
        """resume_workflow with confirmed=True should clear interrupt flag"""
        await hitl_manager.pause_workflow("sess_001", sample_state, "test")
        
        result = await hitl_manager.resume_workflow("sess_001", confirmed=True)
        
        assert result is not None
        assert result["ui_interrupt_flag"] is False
        assert "sess_001" not in hitl_manager._paused_sessions

    @pytest.mark.asyncio
    async def test_resume_workflow_confirmed_with_final_report(
        self, hitl_manager, sample_state_with_report
    ):
        """resume_workflow with confirmed=True should set confirmation_status to CONFIRMED"""
        await hitl_manager.pause_workflow("sess_001", sample_state_with_report, "test")
        
        result = await hitl_manager.resume_workflow("sess_001", confirmed=True)
        
        assert result is not None
        assert result["final_report"].confirmation_status == ConfirmationStatus.CONFIRMED

    @pytest.mark.asyncio
    async def test_resume_workflow_rejected(self, hitl_manager, sample_state_with_report):
        """resume_workflow with confirmed=False should set confirmation_status to REJECTED"""
        await hitl_manager.pause_workflow("sess_001", sample_state_with_report, "test")
        
        result = await hitl_manager.resume_workflow("sess_001", confirmed=False)
        
        assert result is not None
        assert result["final_report"].confirmation_status == ConfirmationStatus.REJECTED

    @pytest.mark.asyncio
    async def test_resume_workflow_nonexistent_session(self, hitl_manager):
        """resume_workflow should return None for nonexistent session"""
        result = await hitl_manager.resume_workflow("nonexistent", confirmed=True)
        assert result is None

    @pytest.mark.asyncio
    async def test_resume_workflow_removes_session(self, hitl_manager, sample_state):
        """resume_workflow should remove session from storage"""
        await hitl_manager.pause_workflow("sess_001", sample_state, "test")
        assert hitl_manager.get_session_count() == 1
        
        await hitl_manager.resume_workflow("sess_001", confirmed=True)
        assert hitl_manager.get_session_count() == 0

    @pytest.mark.asyncio
    async def test_resume_workflow_handles_dict_final_report(self, hitl_manager):
        """resume_workflow should handle final_report as dict"""
        state: HealthState = {
            "user_query": "test",
            "ui_interrupt_flag": True,
            "final_report": {
                "deep_insight": "test",
                "action_plan": [],
                "follow_up": "test",
                "requires_confirmation": True,
                "session_id": "test",
                "confirmation_status": "pending",
            },
        }
        
        await hitl_manager.pause_workflow("sess_001", state, "test")
        result = await hitl_manager.resume_workflow("sess_001", confirmed=True)
        
        assert result is not None
        assert result["final_report"]["confirmation_status"] == ConfirmationStatus.CONFIRMED.value


# ============================================================================
# check_timeout Tests
# ============================================================================


class TestCheckTimeout:
    """Test check_timeout functionality"""

    @pytest.mark.asyncio
    async def test_check_timeout_not_expired(self, hitl_manager, sample_state):
        """check_timeout should return False for fresh session"""
        await hitl_manager.pause_workflow("sess_001", sample_state, "test")
        
        is_timeout = await hitl_manager.check_timeout("sess_001")
        assert is_timeout is False

    @pytest.mark.asyncio
    async def test_check_timeout_nonexistent_session(self, hitl_manager):
        """check_timeout should return False for nonexistent session"""
        is_timeout = await hitl_manager.check_timeout("nonexistent")
        assert is_timeout is False

    @pytest.mark.asyncio
    async def test_check_timeout_custom_minutes(self, hitl_manager, sample_state):
        """check_timeout should respect custom timeout_minutes"""
        await hitl_manager.pause_workflow("sess_001", sample_state, "test")
        
        # With very short timeout, should still not be expired for fresh session
        is_timeout = await hitl_manager.check_timeout("sess_001", timeout_minutes=1)
        assert is_timeout is False

    @pytest.mark.asyncio
    async def test_check_timeout_expired_session(self, hitl_manager, sample_state):
        """check_timeout should return True for expired session"""
        await hitl_manager.pause_workflow("sess_001", sample_state, "test")
        
        # Manipulate the paused_at time to simulate timeout
        session = hitl_manager._paused_sessions["sess_001"]
        session.paused_at = datetime.now(timezone.utc) - timedelta(minutes=35)
        
        is_timeout = await hitl_manager.check_timeout("sess_001")
        assert is_timeout is True

    @pytest.mark.asyncio
    async def test_check_timeout_uses_default_30_minutes(self, hitl_manager, sample_state):
        """check_timeout should use 30 minutes as default (Requirement 10.5)"""
        await hitl_manager.pause_workflow("sess_001", sample_state, "test")
        
        # Set paused_at to 29 minutes ago - should not be expired
        session = hitl_manager._paused_sessions["sess_001"]
        session.paused_at = datetime.now(timezone.utc) - timedelta(minutes=29)
        
        is_timeout = await hitl_manager.check_timeout("sess_001")
        assert is_timeout is False
        
        # Set paused_at to 31 minutes ago - should be expired
        session.paused_at = datetime.now(timezone.utc) - timedelta(minutes=31)
        
        is_timeout = await hitl_manager.check_timeout("sess_001")
        assert is_timeout is True


# ============================================================================
# Session Management Tests
# ============================================================================


class TestSessionManagement:
    """Test session management operations"""

    @pytest.mark.asyncio
    async def test_get_session_status(self, hitl_manager, sample_state):
        """get_session_status should return correct status"""
        await hitl_manager.pause_workflow("sess_001", sample_state, "test")
        
        status = hitl_manager.get_session_status("sess_001")
        assert status == SessionStatus.PAUSED

    def test_get_session_status_nonexistent(self, hitl_manager):
        """get_session_status should return None for nonexistent session"""
        status = hitl_manager.get_session_status("nonexistent")
        assert status is None

    @pytest.mark.asyncio
    async def test_get_session(self, hitl_manager, sample_state):
        """get_session should return PausedSession object"""
        await hitl_manager.pause_workflow("sess_001", sample_state, "test")
        
        session = hitl_manager.get_session("sess_001")
        assert session is not None
        assert isinstance(session, PausedSession)
        assert session.session_id == "sess_001"

    def test_get_session_nonexistent(self, hitl_manager):
        """get_session should return None for nonexistent session"""
        session = hitl_manager.get_session("nonexistent")
        assert session is None

    @pytest.mark.asyncio
    async def test_is_session_paused(self, hitl_manager, sample_state):
        """is_session_paused should return True for paused session"""
        await hitl_manager.pause_workflow("sess_001", sample_state, "test")
        
        assert hitl_manager.is_session_paused("sess_001") is True

    def test_is_session_paused_nonexistent(self, hitl_manager):
        """is_session_paused should return False for nonexistent session"""
        assert hitl_manager.is_session_paused("nonexistent") is False

    @pytest.mark.asyncio
    async def test_get_paused_session_ids(self, hitl_manager, sample_state):
        """get_paused_session_ids should return all session IDs"""
        await hitl_manager.pause_workflow("sess_a", sample_state, "test")
        await hitl_manager.pause_workflow("sess_b", sample_state, "test")
        
        ids = hitl_manager.get_paused_session_ids()
        assert len(ids) == 2
        assert "sess_a" in ids
        assert "sess_b" in ids

    @pytest.mark.asyncio
    async def test_get_session_count(self, hitl_manager, sample_state):
        """get_session_count should return correct count"""
        assert hitl_manager.get_session_count() == 0
        
        await hitl_manager.pause_workflow("sess_a", sample_state, "test")
        assert hitl_manager.get_session_count() == 1
        
        await hitl_manager.pause_workflow("sess_b", sample_state, "test")
        assert hitl_manager.get_session_count() == 2


# ============================================================================
# terminate_session Tests
# ============================================================================


class TestTerminateSession:
    """Test terminate_session functionality"""

    @pytest.mark.asyncio
    async def test_terminate_session(self, hitl_manager, sample_state):
        """terminate_session should remove and return state"""
        await hitl_manager.pause_workflow("sess_001", sample_state, "test")
        
        result = await hitl_manager.terminate_session("sess_001", reason="user request")
        
        assert result is not None
        assert "sess_001" not in hitl_manager._paused_sessions

    @pytest.mark.asyncio
    async def test_terminate_session_nonexistent(self, hitl_manager):
        """terminate_session should return None for nonexistent session"""
        result = await hitl_manager.terminate_session("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_terminate_session_sets_rejected_status(
        self, hitl_manager, sample_state_with_report
    ):
        """terminate_session should set confirmation_status to REJECTED"""
        await hitl_manager.pause_workflow("sess_001", sample_state_with_report, "test")
        
        result = await hitl_manager.terminate_session("sess_001")
        
        assert result["final_report"].confirmation_status == ConfirmationStatus.REJECTED


# ============================================================================
# cleanup_timeout_sessions Tests
# ============================================================================


class TestCleanupTimeoutSessions:
    """Test timeout auto-termination (Requirement 10.6)"""

    @pytest.mark.asyncio
    async def test_cleanup_timeout_sessions_no_timeout(self, hitl_manager, sample_state):
        """cleanup_timeout_sessions should not terminate fresh sessions"""
        await hitl_manager.pause_workflow("sess_001", sample_state, "test")
        
        terminated = await hitl_manager.cleanup_timeout_sessions()
        
        assert len(terminated) == 0
        assert hitl_manager.get_session_count() == 1

    @pytest.mark.asyncio
    async def test_cleanup_timeout_sessions_with_timeout(self, hitl_manager, sample_state):
        """cleanup_timeout_sessions should terminate expired sessions"""
        await hitl_manager.pause_workflow("sess_001", sample_state, "test")
        
        # Simulate timeout
        session = hitl_manager._paused_sessions["sess_001"]
        session.paused_at = datetime.now(timezone.utc) - timedelta(minutes=35)
        
        terminated = await hitl_manager.cleanup_timeout_sessions()
        
        assert len(terminated) == 1
        assert "sess_001" in terminated
        assert hitl_manager.get_session_count() == 0

    @pytest.mark.asyncio
    async def test_cleanup_timeout_sessions_mixed(self, hitl_manager, sample_state):
        """cleanup_timeout_sessions should only terminate expired sessions"""
        await hitl_manager.pause_workflow("sess_fresh", sample_state, "test")
        await hitl_manager.pause_workflow("sess_expired", sample_state, "test")
        
        # Expire only one session
        session = hitl_manager._paused_sessions["sess_expired"]
        session.paused_at = datetime.now(timezone.utc) - timedelta(minutes=35)
        
        terminated = await hitl_manager.cleanup_timeout_sessions()
        
        assert len(terminated) == 1
        assert "sess_expired" in terminated
        assert hitl_manager.get_session_count() == 1
        assert hitl_manager.is_session_paused("sess_fresh")

    @pytest.mark.asyncio
    async def test_cleanup_triggers_timeout_callback(self, hitl_manager, sample_state):
        """cleanup_timeout_sessions should trigger callback for terminated sessions"""
        callback = AsyncMock()
        hitl_manager.set_timeout_callback(callback)
        
        await hitl_manager.pause_workflow("sess_001", sample_state, "test")
        session = hitl_manager._paused_sessions["sess_001"]
        session.paused_at = datetime.now(timezone.utc) - timedelta(minutes=35)
        
        await hitl_manager.cleanup_timeout_sessions()
        
        callback.assert_called_once_with("sess_001")


# ============================================================================
# Timeout Callback Tests
# ============================================================================


class TestTimeoutCallback:
    """Test timeout callback functionality"""

    def test_set_timeout_callback(self, hitl_manager):
        """set_timeout_callback should set the callback"""
        callback = AsyncMock()
        hitl_manager.set_timeout_callback(callback)
        
        assert hitl_manager._on_timeout_callback is callback

    @pytest.mark.asyncio
    async def test_timeout_callback_handles_exception(self, hitl_manager, sample_state):
        """cleanup should continue even if callback raises exception"""
        callback = AsyncMock(side_effect=Exception("Callback error"))
        hitl_manager.set_timeout_callback(callback)
        
        await hitl_manager.pause_workflow("sess_001", sample_state, "test")
        session = hitl_manager._paused_sessions["sess_001"]
        session.paused_at = datetime.now(timezone.utc) - timedelta(minutes=35)
        
        # Should not raise exception
        terminated = await hitl_manager.cleanup_timeout_sessions()
        
        assert len(terminated) == 1


# ============================================================================
# Context Manager Tests
# ============================================================================


class TestContextManager:
    """Test async context manager functionality"""

    @pytest.mark.asyncio
    async def test_context_manager_entry(self):
        """Context manager should return manager on entry"""
        async with HITLManager() as manager:
            assert manager is not None
            assert isinstance(manager, HITLManager)

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self, sample_state):
        """Context manager should cleanup sessions on exit"""
        async with HITLManager() as manager:
            await manager.pause_workflow("sess_001", sample_state, "test")
            assert manager.get_session_count() == 1
        
        # After exiting context, sessions should be terminated
        assert manager.get_session_count() == 0


# ============================================================================
# Requirement Validation Tests
# ============================================================================


class TestRequirementValidation:
    """Tests that validate specific requirements"""

    @pytest.mark.asyncio
    async def test_req_10_3_pause_workflow_stores_state(self, hitl_manager, sample_state):
        """Requirement 10.3: pause_workflow should store state for later resume"""
        await hitl_manager.pause_workflow("sess_001", sample_state, "高风险干预")
        
        session = hitl_manager.get_session("sess_001")
        assert session is not None
        assert session.state == sample_state

    @pytest.mark.asyncio
    async def test_req_10_4_resume_workflow_confirmed(
        self, hitl_manager, sample_state_with_report
    ):
        """Requirement 10.4: resume_workflow should continue workflow on confirmation"""
        await hitl_manager.pause_workflow("sess_001", sample_state_with_report, "test")
        
        result = await hitl_manager.resume_workflow("sess_001", confirmed=True)
        
        assert result["ui_interrupt_flag"] is False
        assert result["final_report"].confirmation_status == ConfirmationStatus.CONFIRMED

    @pytest.mark.asyncio
    async def test_req_10_5_max_pause_30_minutes(self, hitl_manager):
        """Requirement 10.5: Max pause time should be 30 minutes"""
        assert hitl_manager.max_pause_minutes == 30

    @pytest.mark.asyncio
    async def test_req_10_6_auto_terminate_after_30_minutes(
        self, hitl_manager, sample_state
    ):
        """Requirement 10.6: Should auto-terminate sessions after 30 minutes"""
        await hitl_manager.pause_workflow("sess_001", sample_state, "test")
        
        # Simulate 31 minutes passed
        session = hitl_manager._paused_sessions["sess_001"]
        session.paused_at = datetime.now(timezone.utc) - timedelta(minutes=31)
        
        # Check timeout detection
        is_timeout = await hitl_manager.check_timeout("sess_001")
        assert is_timeout is True
        
        # Cleanup should terminate the session
        terminated = await hitl_manager.cleanup_timeout_sessions()
        assert "sess_001" in terminated
        assert hitl_manager.get_session_count() == 0


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_pause_same_session_twice(self, hitl_manager, sample_state):
        """Pausing same session twice should overwrite"""
        state1 = dict(sample_state)
        state1["user_query"] = "query_1"
        
        state2 = dict(sample_state)
        state2["user_query"] = "query_2"
        
        await hitl_manager.pause_workflow("sess_001", state1, "reason_1")
        await hitl_manager.pause_workflow("sess_001", state2, "reason_2")
        
        session = hitl_manager.get_session("sess_001")
        assert session.state["user_query"] == "query_2"
        assert session.reason == "reason_2"

    @pytest.mark.asyncio
    async def test_resume_already_resumed_session(self, hitl_manager, sample_state):
        """Resuming already resumed session should return None"""
        await hitl_manager.pause_workflow("sess_001", sample_state, "test")
        
        # First resume
        result1 = await hitl_manager.resume_workflow("sess_001", confirmed=True)
        assert result1 is not None
        
        # Second resume should return None
        result2 = await hitl_manager.resume_workflow("sess_001", confirmed=True)
        assert result2 is None

    @pytest.mark.asyncio
    async def test_state_not_mutated_during_pause(self, hitl_manager, sample_state):
        """State should not be mutated during pause period"""
        await hitl_manager.pause_workflow("sess_001", sample_state, "test")
        
        # Get session and verify state integrity
        session = hitl_manager.get_session("sess_001")
        assert session.state["user_query"] == sample_state["user_query"]
        assert session.state["ui_interrupt_flag"] == sample_state["ui_interrupt_flag"]

    def test_session_status_enum_values(self):
        """SessionStatus should have all expected values"""
        assert SessionStatus.ACTIVE.value == "active"
        assert SessionStatus.PAUSED.value == "paused"
        assert SessionStatus.RESUMED.value == "resumed"
        assert SessionStatus.TERMINATED.value == "terminated"
        assert SessionStatus.COMPLETED.value == "completed"
