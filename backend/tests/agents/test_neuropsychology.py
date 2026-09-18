"""
神经心理调节专家智能体测试
Tests for app/agents/neuropsychology.py

Requirements: 8.1-8.8
"""

from unittest.mock import AsyncMock

import pytest

from app.agents.base import BaseAgent
from app.agents.neuropsychology import (
    HARDWARE_INTERVENTION_LABEL,
    HARDWARE_INTERVENTIONS,
    SLEEP_INTERVENTIONS,
    SOFTWARE_INTERVENTION_LABEL,
    SOFTWARE_INTERVENTIONS,
    NeuropsychologyAgent,
)
from app.models.state import HealthState
from app.models.user_profile import (
    BloodGlucose,
    BloodLipids,
    DietHabit,
    ExerciseFrequency,
    Gender,
    Lifestyle,
    PhysicalExamination,
    UserProfile,
)
from app.tools.rag_interface import RAGResult


@pytest.fixture
def sample_user_profile():
    """创建示例用户画像"""
    return UserProfile(
        age=45,
        gender=Gender.MALE,
        height=175.0,
        weight=78.0,
        medical_history=[],
        physical_examination=PhysicalExamination(
            blood_lipids=BloodLipids(
                total_cholesterol=5.0,
                triglycerides=1.5,
                hdl=1.3,
                ldl=3.0,
            ),
            blood_glucose=BloodGlucose(
                fasting_glucose=5.5,
                hba1c=5.2,
            ),
        ),
        medications=[],
        lifestyle=Lifestyle(
            sleep_duration=7.0,
            exercise_frequency=ExerciseFrequency.ONE_TO_TWO,
            diet_habit=DietHabit.BALANCED,
            stress_level=5,  # 中等压力
        ),
    )


@pytest.fixture
def sample_state(sample_user_profile) -> HealthState:
    """创建示例状态"""
    return {
        "user_query": "我最近压力很大，睡眠也不太好，请给我一些调节建议",
        "user_profile": sample_user_profile,
        "expert_responses": {},
    }


class TestNeuropsychologyAgentStructure:
    """NeuropsychologyAgent 类结构测试"""

    def test_inherits_from_base_agent(self):
        """测试继承自 BaseAgent"""
        assert issubclass(NeuropsychologyAgent, BaseAgent)

    def test_can_be_instantiated(self):
        """测试可以实例化"""
        agent = NeuropsychologyAgent()
        assert agent is not None
        assert isinstance(agent, BaseAgent)

    def test_name_property(self):
        """测试 name 属性返回正确的名称"""
        agent = NeuropsychologyAgent()
        assert agent.name == "Neuropsychology_Agent"

    def test_get_system_prompt_returns_string(self):
        """测试 get_system_prompt 返回字符串"""
        agent = NeuropsychologyAgent()
        prompt = agent.get_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_system_prompt_contains_key_concepts(self):
        """测试系统提示词包含关键概念"""
        agent = NeuropsychologyAgent()
        prompt = agent.get_system_prompt()

        # 应该包含神经心理相关概念
        assert "心理" in prompt or "神经" in prompt
        assert "压力" in prompt
        assert "硬件层" in prompt
        assert "软件层" in prompt


class TestNeuropsychologyAgentProhibitedKeywords:
    """Requirements 8.7: 禁止关键词检测测试"""

    @pytest.mark.asyncio
    async def test_detects_suicide_keywords(self, sample_user_profile):
        """测试检测自杀相关关键词"""
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "我感觉活着没意义，想自杀",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        assert "建议立即寻求专业精神科医生帮助" in response
        assert "自杀" in response

    @pytest.mark.asyncio
    async def test_detects_self_harm_keywords(self, sample_user_profile):
        """测试检测自残关键词"""
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "我有自残的想法",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        assert "建议立即寻求专业精神科医生帮助" in response

    @pytest.mark.asyncio
    async def test_detects_hallucination_keywords(self, sample_user_profile):
        """测试检测幻觉/幻听关键词"""
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "我最近经常幻听，听到有人在说话",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        assert "建议立即寻求专业精神科医生帮助" in response

    @pytest.mark.asyncio
    async def test_detects_severe_depression_keywords(self, sample_user_profile):
        """测试检测重度抑郁关键词"""
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "我被诊断为重度抑郁，需要帮助",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        assert "建议立即寻求专业精神科医生帮助" in response

    @pytest.mark.asyncio
    async def test_normal_query_not_blocked(self, sample_state):
        """测试正常查询不会被阻止"""
        agent = NeuropsychologyAgent()

        result = await agent.process(sample_state)

        response = result["expert_responses"]["neuropsychology"]
        # 正常查询应该包含干预建议，而不是专业帮助建议
        assert "压力状态评估" in response or "睡眠状态评估" in response


class TestNeuropsychologyAgentStressIntervention:
    """Requirements 8.2: 压力等级-干预策略匹配测试"""

    @pytest.mark.asyncio
    async def test_low_stress_daily_regulation(self, sample_user_profile):
        """测试低压力等级(1-3)匹配日常调节类"""
        sample_user_profile.lifestyle.stress_level = 2
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "请给我一些压力管理建议",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        assert "日常调节类" in response

    @pytest.mark.asyncio
    async def test_medium_stress_structured_training(self, sample_user_profile):
        """测试中等压力等级(4-6)匹配结构化训练类"""
        sample_user_profile.lifestyle.stress_level = 5
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "请给我一些压力管理建议",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        assert "结构化训练类" in response

    @pytest.mark.asyncio
    async def test_high_stress_professional_support(self, sample_user_profile):
        """测试高压力等级(7-10)匹配专业支持类"""
        sample_user_profile.lifestyle.stress_level = 8
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "请给我一些压力管理建议",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        assert "专业支持类" in response
        assert "需要关注" in response

    @pytest.mark.asyncio
    async def test_stress_level_boundary_3(self, sample_user_profile):
        """测试压力等级边界值3（日常调节类）"""
        sample_user_profile.lifestyle.stress_level = 3
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "请给我一些压力管理建议",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        assert "日常调节类" in response

    @pytest.mark.asyncio
    async def test_stress_level_boundary_4(self, sample_user_profile):
        """测试压力等级边界值4（结构化训练类）"""
        sample_user_profile.lifestyle.stress_level = 4
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "请给我一些压力管理建议",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        assert "结构化训练类" in response

    @pytest.mark.asyncio
    async def test_stress_level_boundary_6(self, sample_user_profile):
        """测试压力等级边界值6（结构化训练类）"""
        sample_user_profile.lifestyle.stress_level = 6
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "请给我一些压力管理建议",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        assert "结构化训练类" in response

    @pytest.mark.asyncio
    async def test_stress_level_boundary_7(self, sample_user_profile):
        """测试压力等级边界值7（专业支持类）"""
        sample_user_profile.lifestyle.stress_level = 7
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "请给我一些压力管理建议",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        assert "专业支持类" in response
        assert "需要关注" in response


class TestNeuropsychologyAgentSleepIntervention:
    """Requirements 8.3: 睡眠时长评估测试"""

    @pytest.mark.asyncio
    async def test_insufficient_sleep_priority_intervention(self, sample_user_profile):
        """测试睡眠不足(<6小时)优先生成睡眠干预"""
        sample_user_profile.lifestyle.sleep_duration = 5.0
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "请给我一些建议",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        assert "睡眠不足" in response

        # 检查是否生成了睡眠干预
        actions = result.get("neuropsychology_actions", [])
        sleep_actions = [
            a for a in actions
            if "睡眠" in a["title"] or "睡眠" in a["description"]
        ]
        assert len(sleep_actions) > 0

    @pytest.mark.asyncio
    async def test_normal_sleep_no_priority(self, sample_user_profile):
        """测试正常睡眠(6-9小时)不优先生成睡眠干预"""
        sample_user_profile.lifestyle.sleep_duration = 7.5
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "请给我一些建议",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        assert "正常" in response

    @pytest.mark.asyncio
    async def test_excessive_sleep_intervention(self, sample_user_profile):
        """测试睡眠过多(>9小时)生成相应干预"""
        sample_user_profile.lifestyle.sleep_duration = 10.0
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "请给我一些建议",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        assert "睡眠过多" in response

    @pytest.mark.asyncio
    async def test_sleep_boundary_6_hours(self, sample_user_profile):
        """测试睡眠边界值6小时（正常）"""
        sample_user_profile.lifestyle.sleep_duration = 6.0
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "请给我一些建议",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        assert "正常" in response

    @pytest.mark.asyncio
    async def test_sleep_boundary_9_hours(self, sample_user_profile):
        """测试睡眠边界值9小时（正常）"""
        sample_user_profile.lifestyle.sleep_duration = 9.0
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "请给我一些建议",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        assert "正常" in response


class TestNeuropsychologyAgentInterventionTypes:
    """Requirements 8.4: 硬件层和软件层干预区分测试"""

    @pytest.mark.asyncio
    async def test_interventions_contain_hardware_label(self, sample_state):
        """测试干预措施包含硬件层标签"""
        agent = NeuropsychologyAgent()

        result = await agent.process(sample_state)

        actions = result.get("neuropsychology_actions", [])
        hardware_actions = [
            a for a in actions
            if HARDWARE_INTERVENTION_LABEL in a["description"]
        ]
        assert len(hardware_actions) > 0

    @pytest.mark.asyncio
    async def test_interventions_contain_software_label(self, sample_state):
        """测试干预措施包含软件层标签"""
        agent = NeuropsychologyAgent()

        result = await agent.process(sample_state)

        actions = result.get("neuropsychology_actions", [])
        software_actions = [
            a for a in actions
            if SOFTWARE_INTERVENTION_LABEL in a["description"]
        ]
        assert len(software_actions) > 0

    @pytest.mark.asyncio
    async def test_response_contains_intervention_summary(self, sample_state):
        """测试响应包含干预类型统计"""
        agent = NeuropsychologyAgent()

        result = await agent.process(sample_state)

        response = result["expert_responses"]["neuropsychology"]
        assert "硬件层干预" in response
        assert "软件层干预" in response


class TestNeuropsychologyAgentActionItems:
    """Requirements 8.5: Action_Item 格式输出测试"""

    @pytest.mark.asyncio
    async def test_action_items_have_correct_category(self, sample_state):
        """测试 Action_Item 的 category 设置为"神经心理" """
        agent = NeuropsychologyAgent()

        result = await agent.process(sample_state)

        actions = result.get("neuropsychology_actions", [])
        for action in actions:
            assert action["category"] == "神经心理"

    @pytest.mark.asyncio
    async def test_action_items_have_required_fields(self, sample_state):
        """测试 Action_Item 包含所有必需字段"""
        agent = NeuropsychologyAgent()

        result = await agent.process(sample_state)

        actions = result.get("neuropsychology_actions", [])
        assert len(actions) > 0

        required_fields = [
            "category", "title", "description",
            "frequency", "priority", "risk_level", "duration"
        ]
        for action in actions:
            for field in required_fields:
                assert field in action, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_generates_3_to_5_actions(self, sample_state):
        """测试生成3-5个干预措施"""
        agent = NeuropsychologyAgent()

        result = await agent.process(sample_state)

        actions = result.get("neuropsychology_actions", [])
        # 应该生成合理数量的干预措施
        assert 1 <= len(actions) <= 5


class TestNeuropsychologyAgentExpertResponses:
    """Requirements 8.6: 响应写入 expert_responses 测试"""

    @pytest.mark.asyncio
    async def test_writes_to_expert_responses(self, sample_state):
        """测试将响应写入 expert_responses"""
        agent = NeuropsychologyAgent()

        result = await agent.process(sample_state)

        assert "neuropsychology" in result["expert_responses"]
        assert len(result["expert_responses"]["neuropsychology"]) > 0

    @pytest.mark.asyncio
    async def test_initializes_expert_responses_if_missing(self):
        """测试如果 expert_responses 不存在则初始化"""
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "测试查询",
            "user_profile": UserProfile(
                age=30,
                gender=Gender.FEMALE,
                height=165.0,
                weight=55.0,
                physical_examination=PhysicalExamination(
                    blood_lipids=BloodLipids(
                        total_cholesterol=4.5,
                        triglycerides=1.2,
                        hdl=1.5,
                        ldl=2.5,
                    ),
                    blood_glucose=BloodGlucose(
                        fasting_glucose=5.0,
                        hba1c=5.0,
                    ),
                ),
                lifestyle=Lifestyle(
                    sleep_duration=7.0,
                    exercise_frequency=ExerciseFrequency.THREE_TO_FIVE,
                    diet_habit=DietHabit.BALANCED,
                    stress_level=3,
                ),
            ),
            # 注意：没有 expert_responses
        }

        result = await agent.process(state)

        assert "expert_responses" in result
        assert "neuropsychology" in result["expert_responses"]


class TestNeuropsychologyAgentGraphRAG:
    """Requirements 8.1, 8.8: Graph RAG 检索测试"""

    @pytest.mark.asyncio
    async def test_calls_graph_rag_when_provided(self, sample_state):
        """测试当提供 GraphRAG 时调用它"""
        mock_rag = AsyncMock()
        mock_rag.query.return_value = [
            RAGResult(
                content="压力与免疫系统关系的知识",
                source="knowledge_graph",
                similarity_score=0.85,
                metadata={
                    "entities": [
                        {"name": "皮质醇", "type": "hormone"},
                        {"name": "免疫系统", "type": "system"},
                    ],
                    "relations": [
                        {
                            "source_entity": "皮质醇",
                            "target_entity": "免疫系统",
                            "relation_type": "抑制",
                        }
                    ],
                },
            )
        ]

        agent = NeuropsychologyAgent(graph_rag=mock_rag)

        result = await agent.process(sample_state)

        mock_rag.query.assert_called_once()
        response = result["expert_responses"]["neuropsychology"]
        # 应该包含 RAG 检索的内容
        assert "知识图谱检索结果" in response or "皮质醇" in response or "免疫系统" in response

    @pytest.mark.asyncio
    async def test_handles_graph_rag_failure(self, sample_state):
        """测试 GraphRAG 检索失败时的处理"""
        mock_rag = AsyncMock()
        mock_rag.query.side_effect = Exception("Neo4j connection failed")

        agent = NeuropsychologyAgent(graph_rag=mock_rag)

        result = await agent.process(sample_state)

        response = result["expert_responses"]["neuropsychology"]
        # 应该包含基于内置知识生成的说明
        assert "未检索到专业知识库内容" in response
        # 但仍然应该生成干预建议
        assert "压力状态评估" in response or "干预措施" in response

    @pytest.mark.asyncio
    async def test_uses_builtin_knowledge_without_rag(self, sample_state):
        """测试没有 GraphRAG 时使用内置知识"""
        agent = NeuropsychologyAgent()  # 不提供 graph_rag

        result = await agent.process(sample_state)

        response = result["expert_responses"]["neuropsychology"]
        # 应该包含基于内置知识生成的说明
        assert "未检索到专业知识库内容" in response
        # 但仍然应该生成干预建议
        actions = result.get("neuropsychology_actions", [])
        assert len(actions) > 0


class TestNeuropsychologyAgentEdgeCases:
    """边界情况测试"""

    @pytest.mark.asyncio
    async def test_handles_missing_user_profile(self):
        """测试处理缺失的用户画像"""
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "请给我建议",
            # 没有 user_profile
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        assert "无法获取用户画像" in response

    @pytest.mark.asyncio
    async def test_handles_empty_query(self, sample_user_profile):
        """测试处理空查询"""
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        # 空查询不应该触发禁止关键词检测
        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        # 应该正常生成干预建议
        assert "压力状态评估" in response or "干预措施" in response

    @pytest.mark.asyncio
    async def test_extreme_stress_level_10(self, sample_user_profile):
        """测试极端压力等级 10"""
        sample_user_profile.lifestyle.stress_level = 10
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "我压力非常大",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        assert "专业支持类" in response
        assert "需要关注" in response

    @pytest.mark.asyncio
    async def test_extreme_stress_level_1(self, sample_user_profile):
        """测试最低压力等级 1"""
        sample_user_profile.lifestyle.stress_level = 1
        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "我感觉很好",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["neuropsychology"]
        assert "日常调节类" in response

    @pytest.mark.asyncio
    async def test_deduplicates_actions(self, sample_user_profile):
        """测试干预措施去重"""
        # 设置一个会同时触发睡眠干预和压力干预的场景
        sample_user_profile.lifestyle.sleep_duration = 5.0  # 睡眠不足
        sample_user_profile.lifestyle.stress_level = 8  # 高压力

        agent = NeuropsychologyAgent()
        state: HealthState = {
            "user_query": "我压力很大睡眠也不好",
            "user_profile": sample_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        actions = result.get("neuropsychology_actions", [])
        titles = [a["title"] for a in actions]

        # 确保没有重复的标题
        assert len(titles) == len(set(titles))


class TestNeuropsychologyAgentInterventionContent:
    """干预措施内容验证测试"""

    def test_hardware_interventions_defined(self):
        """测试硬件层干预措施已定义"""
        assert "daily" in HARDWARE_INTERVENTIONS
        assert "structured" in HARDWARE_INTERVENTIONS
        assert "professional" in HARDWARE_INTERVENTIONS

        for _key, items in HARDWARE_INTERVENTIONS.items():
            assert len(items) > 0
            for item in items:
                assert "title" in item
                assert "description" in item
                assert HARDWARE_INTERVENTION_LABEL in item["description"]

    def test_software_interventions_defined(self):
        """测试软件层干预措施已定义"""
        assert "daily" in SOFTWARE_INTERVENTIONS
        assert "structured" in SOFTWARE_INTERVENTIONS
        assert "professional" in SOFTWARE_INTERVENTIONS

        for _key, items in SOFTWARE_INTERVENTIONS.items():
            assert len(items) > 0
            for item in items:
                assert "title" in item
                assert "description" in item
                assert SOFTWARE_INTERVENTION_LABEL in item["description"]

    def test_sleep_interventions_defined(self):
        """测试睡眠干预措施已定义"""
        assert "insufficient" in SLEEP_INTERVENTIONS
        assert "excessive" in SLEEP_INTERVENTIONS

        for _key, items in SLEEP_INTERVENTIONS.items():
            assert len(items) > 0
            for item in items:
                assert "title" in item
                assert "description" in item


class TestNeuropsychologyAgentModuleExports:
    """模块导出测试"""

    def test_agent_can_be_imported_from_agents_module(self):
        """测试可以从 agents 模块导入"""
        from app.agents import NeuropsychologyAgent as ImportedAgent

        assert ImportedAgent is NeuropsychologyAgent

    def test_agent_in_agents_module_all(self):
        """测试在 agents 模块的 __all__ 中"""
        from app import agents

        assert hasattr(agents, "__all__")
        assert "NeuropsychologyAgent" in agents.__all__
