"""
Controller_Agent 主控智能体测试

Tests for app/agents/controller.py
Requirements: 5.1-5.5

测试内容：
1. 基本结构和继承测试
2. 任务拆解逻辑测试（Requirement 5.2）
3. 高风险关键词检测和 ui_interrupt_flag 设置测试（Requirement 5.3）
4. 禁止关键词检测和终止测试（Requirement 5.4）
5. 超出服务范围检测测试（Requirement 5.4）
6. 超时处理测试（Requirement 5.5）
"""

import pytest
from datetime import date

from app.agents.base import BaseAgent
from app.agents.controller import ControllerAgent, CONTROLLER_TIMEOUT_SECONDS
from app.models.state import (
    ErrorInfo,
    HealthState,
    NodeExecutionStatus,
    SubTask,
    TargetAgent,
)
from app.models.user_profile import (
    BloodGlucose,
    BloodLipids,
    DietHabit,
    DiseaseStatus,
    ExerciseFrequency,
    Gender,
    Lifestyle,
    MedicalHistory,
    Medication,
    MedicationFrequency,
    PhysicalExamination,
    UserProfile,
)


@pytest.fixture
def controller_agent():
    """创建 ControllerAgent 实例"""
    return ControllerAgent()


@pytest.fixture
def sample_user_profile():
    """创建示例用户画像"""
    return UserProfile(
        age=45,
        gender=Gender.MALE,
        height=175.0,
        weight=78.0,
        medical_history=[
            MedicalHistory(
                disease_name="高血压",
                diagnosis_date=date(2020, 1, 15),
                current_status=DiseaseStatus.CHRONIC,
            )
        ],
        physical_examination=PhysicalExamination(
            blood_lipids=BloodLipids(
                total_cholesterol=5.8,
                triglycerides=2.1,
                hdl=1.2,
                ldl=3.6,
            ),
            blood_glucose=BloodGlucose(
                fasting_glucose=6.5,
                hba1c=6.2,
            ),
        ),
        medications=[
            Medication(
                drug_name="氨氯地平",
                dosage="5mg",
                frequency=MedicationFrequency.ONCE_DAILY,
                start_date=date(2020, 2, 1),
            )
        ],
        lifestyle=Lifestyle(
            sleep_duration=6.5,
            exercise_frequency=ExerciseFrequency.ONE_TO_TWO,
            diet_habit=DietHabit.BALANCED,
            stress_level=7,
        ),
    )


@pytest.fixture
def minimal_state():
    """创建最小化状态"""
    return HealthState(
        user_query="我血脂偏高，睡眠质量差，请给我一些建议",
    )


@pytest.fixture
def full_state(sample_user_profile):
    """创建包含用户画像的完整状态"""
    return HealthState(
        user_query="我血脂偏高，睡眠质量差，请给我一些建议",
        user_profile=sample_user_profile,
        expert_responses={},
        error_info=[],
        node_execution_status={},
    )


class TestControllerAgentStructure:
    """Controller_Agent 基本结构测试"""
    
    def test_controller_agent_inherits_from_base_agent(self, controller_agent):
        """测试 ControllerAgent 继承自 BaseAgent"""
        assert isinstance(controller_agent, BaseAgent)
    
    def test_controller_agent_name_property(self, controller_agent):
        """测试 name 属性返回正确的值"""
        assert controller_agent.name == "Controller_Agent"
    
    def test_controller_agent_get_system_prompt(self, controller_agent):
        """测试 get_system_prompt 方法返回非空字符串"""
        prompt = controller_agent.get_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        # 检查提示词包含关键内容
        assert "主控" in prompt or "Controller" in prompt
        assert "营养" in prompt or "nutrition" in prompt
        assert "康复" in prompt or "rehabilitation" in prompt
        assert "神经心理" in prompt or "neuropsychology" in prompt
    
    def test_controller_timeout_constant(self):
        """测试超时常量为30秒（Requirement 5.5）"""
        assert CONTROLLER_TIMEOUT_SECONDS == 30


class TestTaskBreakdown:
    """任务拆解测试 (Requirement 5.2)"""
    
    @pytest.mark.asyncio
    async def test_task_breakdown_creates_three_subtasks(self, controller_agent, full_state):
        """测试任务拆解创建三个子任务"""
        result = await controller_agent.process(full_state)
        
        assert "task_breakdown" in result
        assert len(result["task_breakdown"]) == 3
    
    @pytest.mark.asyncio
    async def test_task_breakdown_has_correct_target_agents(self, controller_agent, full_state):
        """测试子任务目标智能体正确"""
        result = await controller_agent.process(full_state)
        
        target_agents = {task.target_agent for task in result["task_breakdown"]}
        expected_agents = {
            TargetAgent.NUTRITION,
            TargetAgent.REHABILITATION,
            TargetAgent.NEUROPSYCHOLOGY,
        }
        assert target_agents == expected_agents
    
    @pytest.mark.asyncio
    async def test_task_breakdown_has_unique_task_ids(self, controller_agent, full_state):
        """测试子任务有唯一的 task_id"""
        result = await controller_agent.process(full_state)
        
        task_ids = [task.task_id for task in result["task_breakdown"]]
        assert len(task_ids) == len(set(task_ids))
    
    @pytest.mark.asyncio
    async def test_task_breakdown_has_descriptions(self, controller_agent, full_state):
        """测试子任务有描述内容"""
        result = await controller_agent.process(full_state)
        
        for task in result["task_breakdown"]:
            assert isinstance(task.task_description, str)
            assert len(task.task_description) > 0
    
    @pytest.mark.asyncio
    async def test_task_description_includes_user_query(self, controller_agent, full_state):
        """测试子任务描述包含用户查询内容"""
        result = await controller_agent.process(full_state)
        
        # 至少有一个子任务描述应该包含用户查询的关键词
        user_query = full_state["user_query"]
        descriptions = " ".join([task.task_description for task in result["task_breakdown"]])
        # 检查用户查询被引用
        assert "血脂" in descriptions or user_query[:10] in descriptions


class TestUserProfileReading:
    """用户画像读取测试 (Requirement 5.1)"""
    
    @pytest.mark.asyncio
    async def test_reads_user_profile_for_nutrition_task(
        self, controller_agent, full_state
    ):
        """测试营养子任务包含血脂血糖信息"""
        result = await controller_agent.process(full_state)
        
        nutrition_task = next(
            task for task in result["task_breakdown"]
            if task.target_agent == TargetAgent.NUTRITION
        )
        
        # 检查描述中包含血脂或血糖相关信息
        desc = nutrition_task.task_description
        assert "血脂" in desc or "血糖" in desc or "胆固醇" in desc
    
    @pytest.mark.asyncio
    async def test_reads_user_profile_for_rehabilitation_task(
        self, controller_agent, full_state
    ):
        """测试康复子任务包含年龄/BMI信息"""
        result = await controller_agent.process(full_state)
        
        rehab_task = next(
            task for task in result["task_breakdown"]
            if task.target_agent == TargetAgent.REHABILITATION
        )
        
        desc = rehab_task.task_description
        # 检查描述中包含年龄或BMI相关信息
        assert "年龄" in desc or "BMI" in desc or "45" in desc
    
    @pytest.mark.asyncio
    async def test_reads_user_profile_for_neuropsychology_task(
        self, controller_agent, full_state
    ):
        """测试神经心理子任务包含压力/睡眠信息"""
        result = await controller_agent.process(full_state)
        
        neuro_task = next(
            task for task in result["task_breakdown"]
            if task.target_agent == TargetAgent.NEUROPSYCHOLOGY
        )
        
        desc = neuro_task.task_description
        # 检查描述中包含压力或睡眠相关信息
        assert "压力" in desc or "睡眠" in desc
    
    @pytest.mark.asyncio
    async def test_handles_missing_user_profile(self, controller_agent, minimal_state):
        """测试处理缺少用户画像的情况"""
        result = await controller_agent.process(minimal_state)
        
        # 应该仍然能够创建任务拆解
        assert "task_breakdown" in result
        assert len(result["task_breakdown"]) == 3


class TestHighRiskKeywordDetection:
    """高风险关键词检测测试 (Requirement 5.3)"""
    
    @pytest.mark.asyncio
    async def test_detects_medication_adjustment_keywords(self, controller_agent):
        """测试检测用药调整类关键词"""
        state = HealthState(user_query="我想停药，不想再吃降压药了")
        result = await controller_agent.process(state)
        
        assert result["ui_interrupt_flag"] is True
        assert "停药" in result["interrupt_reason"]
    
    @pytest.mark.asyncio
    async def test_detects_fasting_keywords(self, controller_agent):
        """测试检测断食类关键词"""
        # 使用精确匹配的关键词 "水断食" 
        state = HealthState(user_query="我想尝试水断食")
        result = await controller_agent.process(state)
        
        assert result["ui_interrupt_flag"] is True
        assert "高风险" in result["interrupt_reason"] or "断食" in result["interrupt_reason"]
    
    @pytest.mark.asyncio
    async def test_detects_fasting_duration_pattern(self, controller_agent):
        """测试检测断食时间模式（超过24小时）"""
        # 测试断食时间正则匹配
        state = HealthState(user_query="我想断食48小时")
        result = await controller_agent.process(state)
        
        assert result["ui_interrupt_flag"] is True
    
    @pytest.mark.asyncio
    async def test_detects_extreme_diet_keywords(self, controller_agent):
        """测试检测极端饮食类关键词"""
        state = HealthState(user_query="我想尝试生酮饮食减肥")
        result = await controller_agent.process(state)
        
        assert result["ui_interrupt_flag"] is True
        assert "生酮" in result["interrupt_reason"] or "高风险" in result["interrupt_reason"]
    
    @pytest.mark.asyncio
    async def test_detects_high_dose_supplement_keywords(self, controller_agent):
        """测试检测大剂量补剂类关键词"""
        state = HealthState(user_query="我想服用5倍RDA剂量的维生素D")
        result = await controller_agent.process(state)
        
        assert result["ui_interrupt_flag"] is True
    
    @pytest.mark.asyncio
    async def test_no_interrupt_for_normal_query(self, controller_agent, full_state):
        """测试正常查询不触发中断"""
        result = await controller_agent.process(full_state)
        
        assert result["ui_interrupt_flag"] is False
        assert result["interrupt_reason"] == ""
    
    @pytest.mark.asyncio
    async def test_still_creates_tasks_with_high_risk(self, controller_agent):
        """测试检测到高风险时仍然创建任务（等待用户确认后执行）"""
        state = HealthState(user_query="我想停药")
        result = await controller_agent.process(state)
        
        assert result["ui_interrupt_flag"] is True
        assert len(result["task_breakdown"]) == 3


class TestProhibitedKeywordDetection:
    """禁止关键词检测测试 (Requirement 5.4)"""
    
    @pytest.mark.asyncio
    async def test_detects_suicide_keyword(self, controller_agent):
        """测试检测自杀关键词"""
        state = HealthState(user_query="我有自杀的想法")
        result = await controller_agent.process(state)
        
        # 应该终止，不创建任务
        assert len(result["task_breakdown"]) == 0
        assert "精神科" in result["expert_responses"]["controller"] or \
               "专业" in result["expert_responses"]["controller"]
    
    @pytest.mark.asyncio
    async def test_detects_self_harm_keyword(self, controller_agent):
        """测试检测自残关键词"""
        state = HealthState(user_query="我想自残")
        result = await controller_agent.process(state)
        
        assert len(result["task_breakdown"]) == 0
    
    @pytest.mark.asyncio
    async def test_detects_hallucination_keyword(self, controller_agent):
        """测试检测幻觉关键词"""
        state = HealthState(user_query="我最近经常有幻听")
        result = await controller_agent.process(state)
        
        assert len(result["task_breakdown"]) == 0
    
    @pytest.mark.asyncio
    async def test_returns_professional_help_suggestion(self, controller_agent):
        """测试返回专业帮助建议"""
        state = HealthState(user_query="我有自杀倾向")
        result = await controller_agent.process(state)
        
        response = result["expert_responses"]["controller"]
        assert "精神科" in response or "专业" in response or "帮助" in response


class TestOutOfScopeDetection:
    """超出服务范围检测测试 (Requirement 5.4)"""
    
    @pytest.mark.asyncio
    async def test_detects_diagnosis_request(self, controller_agent):
        """测试检测诊断请求"""
        state = HealthState(user_query="帮我诊断一下我是不是得了糖尿病")
        result = await controller_agent.process(state)
        
        assert len(result["task_breakdown"]) == 0
        assert "诊断" in result["expert_responses"]["controller"] or \
               "医疗" in result["expert_responses"]["controller"]
    
    @pytest.mark.asyncio
    async def test_detects_prescription_request(self, controller_agent):
        """测试检测处方请求"""
        # 使用精确匹配的关键词 "开处方"
        state = HealthState(user_query="请帮我开处方治疗感冒")
        result = await controller_agent.process(state)
        
        assert len(result["task_breakdown"]) == 0
    
    @pytest.mark.asyncio
    async def test_detects_acute_symptoms(self, controller_agent):
        """测试检测急性症状"""
        state = HealthState(user_query="我现在胸痛，呼吸困难")
        result = await controller_agent.process(state)
        
        assert len(result["task_breakdown"]) == 0
        response = result["expert_responses"]["controller"]
        assert "急" in response or "医院" in response
    
    @pytest.mark.asyncio
    async def test_detects_pediatric_request(self, controller_agent):
        """测试检测儿科问题"""
        state = HealthState(user_query="我5岁的孩子发烧了")
        result = await controller_agent.process(state)
        
        assert len(result["task_breakdown"]) == 0


class TestNodeExecutionStatus:
    """节点执行状态测试"""
    
    @pytest.mark.asyncio
    async def test_sets_running_status_at_start(self, controller_agent, full_state):
        """测试开始时设置运行状态"""
        # 由于 process 是同步完成的，我们只能检查最终状态
        result = await controller_agent.process(full_state)
        
        assert "node_execution_status" in result
        assert "Controller_Agent" in result["node_execution_status"]
    
    @pytest.mark.asyncio
    async def test_sets_completed_status_on_success(self, controller_agent, full_state):
        """测试成功完成时设置完成状态"""
        result = await controller_agent.process(full_state)
        
        assert result["node_execution_status"]["Controller_Agent"] == NodeExecutionStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_sets_completed_status_on_prohibited(self, controller_agent):
        """测试检测到禁止内容时也设置完成状态"""
        state = HealthState(user_query="我想自杀")
        result = await controller_agent.process(state)
        
        assert result["node_execution_status"]["Controller_Agent"] == NodeExecutionStatus.COMPLETED


class TestExpertResponses:
    """专家响应测试"""
    
    @pytest.mark.asyncio
    async def test_writes_controller_response(self, controller_agent, full_state):
        """测试写入 Controller 响应"""
        result = await controller_agent.process(full_state)
        
        assert "expert_responses" in result
        assert "controller" in result["expert_responses"]
        assert len(result["expert_responses"]["controller"]) > 0
    
    @pytest.mark.asyncio
    async def test_response_mentions_task_count(self, controller_agent, full_state):
        """测试响应提及任务数量"""
        result = await controller_agent.process(full_state)
        
        response = result["expert_responses"]["controller"]
        assert "3" in response or "三" in response or "子任务" in response


class TestErrorHandling:
    """错误处理测试"""
    
    @pytest.mark.asyncio
    async def test_handles_empty_query(self, controller_agent):
        """测试处理空查询"""
        state = HealthState(user_query="")
        result = await controller_agent.process(state)
        
        # 应该能够正常完成，即使查询为空
        assert "task_breakdown" in result
        assert result["node_execution_status"]["Controller_Agent"] in [
            NodeExecutionStatus.COMPLETED,
            NodeExecutionStatus.FAILED,
        ]
    
    @pytest.mark.asyncio
    async def test_initializes_missing_fields(self, controller_agent):
        """测试初始化缺失字段"""
        state: HealthState = {"user_query": "测试查询"}
        result = await controller_agent.process(state)
        
        assert "expert_responses" in result
        assert "error_info" in result
        assert "node_execution_status" in result
        assert "ui_interrupt_flag" in result


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_workflow_normal_query(self, controller_agent, full_state):
        """测试完整工作流 - 正常查询"""
        result = await controller_agent.process(full_state)
        
        # 验证所有必要字段都已设置
        assert result["ui_interrupt_flag"] is False
        assert result["interrupt_reason"] == ""
        assert len(result["task_breakdown"]) == 3
        assert result["node_execution_status"]["Controller_Agent"] == NodeExecutionStatus.COMPLETED
        assert "controller" in result["expert_responses"]
    
    @pytest.mark.asyncio
    async def test_full_workflow_high_risk_query(self, controller_agent, sample_user_profile):
        """测试完整工作流 - 高风险查询"""
        # 使用精确匹配的关键词 "停药"
        state = HealthState(
            user_query="我想停药不再吃降压药",
            user_profile=sample_user_profile,
        )
        result = await controller_agent.process(state)
        
        # 验证高风险处理
        assert result["ui_interrupt_flag"] is True
        assert len(result["interrupt_reason"]) > 0
        # 仍然创建任务（等待确认）
        assert len(result["task_breakdown"]) == 3
        assert result["node_execution_status"]["Controller_Agent"] == NodeExecutionStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_full_workflow_prohibited_query(self, controller_agent):
        """测试完整工作流 - 禁止查询"""
        state = HealthState(user_query="我有自杀的想法，不想活了")
        result = await controller_agent.process(state)
        
        # 验证禁止处理
        assert len(result["task_breakdown"]) == 0
        assert result["node_execution_status"]["Controller_Agent"] == NodeExecutionStatus.COMPLETED
        assert "精神科" in result["expert_responses"]["controller"] or \
               "专业" in result["expert_responses"]["controller"]


class TestModuleExports:
    """模块导出测试"""
    
    def test_controller_agent_can_be_imported_from_agents_module(self):
        """测试 ControllerAgent 可以从 agents 模块导入"""
        from app.agents import ControllerAgent as ImportedControllerAgent
        
        assert ImportedControllerAgent is ControllerAgent
    
    def test_controller_agent_in_agents_module_all(self):
        """测试 ControllerAgent 在 agents 模块的 __all__ 中"""
        from app import agents
        
        assert hasattr(agents, "__all__")
        assert "ControllerAgent" in agents.__all__
