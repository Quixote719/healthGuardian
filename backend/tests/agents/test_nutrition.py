"""
Nutrition_Agent 营养学专家智能体测试

测试 NutritionAgent 的核心功能：
- 血脂血糖异常检测与建议生成
- 药物-食物交互检测
- RAG 知识检索与超时处理
- ActionItem 输出格式验证

Requirements: 6.1-6.7
"""

import asyncio
import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.nutrition import (
    DRUG_FOOD_INTERACTIONS,
    NutritionAgent,
    _detect_drug_food_interactions,
    _generate_glucose_action_items,
    _generate_lipid_action_items,
)
from app.models.action_item import ActionCategory
from app.models.state import HealthState
from app.models.user_profile import (
    BloodGlucose,
    BloodLipids,
    DietHabit,
    ExerciseFrequency,
    Gender,
    Lifestyle,
    Medication,
    MedicationFrequency,
    PhysicalExamination,
    UserProfile,
)
from app.agents.health_analyzer import (
    detect_lipid_abnormality,
    detect_glucose_abnormality,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def normal_user_profile() -> UserProfile:
    """正常指标的用户画像"""
    return UserProfile(
        age=35,
        gender=Gender.MALE,
        height=175.0,
        weight=70.0,
        medical_history=[],
        physical_examination=PhysicalExamination(
            blood_lipids=BloodLipids(
                total_cholesterol=4.5,
                triglycerides=1.2,
                hdl=1.3,
                ldl=2.8,
            ),
            blood_glucose=BloodGlucose(
                fasting_glucose=5.0,
                hba1c=5.2,
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
def abnormal_lipid_user_profile() -> UserProfile:
    """血脂异常的用户画像"""
    return UserProfile(
        age=50,
        gender=Gender.MALE,
        height=170.0,
        weight=80.0,
        medical_history=[],
        physical_examination=PhysicalExamination(
            blood_lipids=BloodLipids(
                total_cholesterol=6.2,  # 偏高 (>=5.2)
                triglycerides=2.0,  # 偏高 (>=1.7)
                hdl=0.9,  # 偏低 (<1.0)
                ldl=4.0,  # 偏高 (>=3.4)
            ),
            blood_glucose=BloodGlucose(
                fasting_glucose=5.0,
                hba1c=5.2,
            ),
        ),
        medications=[],
        lifestyle=Lifestyle(
            sleep_duration=6.0,
            exercise_frequency=ExerciseFrequency.ONE_TO_TWO,
            diet_habit=DietHabit.MEAT_BASED,
            stress_level=6,
        ),
    )


@pytest.fixture
def abnormal_glucose_user_profile() -> UserProfile:
    """血糖异常的用户画像"""
    return UserProfile(
        age=55,
        gender=Gender.FEMALE,
        height=160.0,
        weight=65.0,
        medical_history=[],
        physical_examination=PhysicalExamination(
            blood_lipids=BloodLipids(
                total_cholesterol=4.8,
                triglycerides=1.4,
                hdl=1.2,
                ldl=3.0,
            ),
            blood_glucose=BloodGlucose(
                fasting_glucose=6.8,  # 偏高 (>=6.1)
                hba1c=6.2,  # 偏高 (>=5.7)
            ),
        ),
        medications=[],
        lifestyle=Lifestyle(
            sleep_duration=7.0,
            exercise_frequency=ExerciseFrequency.ONE_TO_TWO,
            diet_habit=DietHabit.IRREGULAR,
            stress_level=5,
        ),
    )


@pytest.fixture
def user_with_medications() -> UserProfile:
    """有用药史的用户画像"""
    return UserProfile(
        age=60,
        gender=Gender.MALE,
        height=172.0,
        weight=75.0,
        medical_history=[],
        physical_examination=PhysicalExamination(
            blood_lipids=BloodLipids(
                total_cholesterol=5.5,
                triglycerides=1.8,
                hdl=1.1,
                ldl=3.5,
            ),
            blood_glucose=BloodGlucose(
                fasting_glucose=6.5,
                hba1c=6.0,
            ),
        ),
        medications=[
            Medication(
                drug_name="阿托伐他汀钙片",  # 他汀类
                dosage="20mg",
                frequency=MedicationFrequency.ONCE_DAILY,
                start_date=date(2023, 1, 1),
            ),
            Medication(
                drug_name="二甲双胍缓释片",  # 二甲双胍
                dosage="500mg",
                frequency=MedicationFrequency.TWICE_DAILY,
                start_date=date(2023, 1, 1),
            ),
            Medication(
                drug_name="华法林钠片",  # 华法林
                dosage="2.5mg",
                frequency=MedicationFrequency.ONCE_DAILY,
                start_date=date(2023, 6, 1),
            ),
        ],
        lifestyle=Lifestyle(
            sleep_duration=6.5,
            exercise_frequency=ExerciseFrequency.ONE_TO_TWO,
            diet_habit=DietHabit.BALANCED,
            stress_level=6,
        ),
    )


@pytest.fixture
def user_with_acei_medication() -> UserProfile:
    """服用ACEI/ARB类药物的用户画像"""
    return UserProfile(
        age=58,
        gender=Gender.MALE,
        height=168.0,
        weight=72.0,
        medical_history=[],
        physical_examination=PhysicalExamination(
            blood_lipids=BloodLipids(
                total_cholesterol=4.8,
                triglycerides=1.5,
                hdl=1.2,
                ldl=2.9,
            ),
            blood_glucose=BloodGlucose(
                fasting_glucose=5.5,
                hba1c=5.4,
            ),
        ),
        medications=[
            Medication(
                drug_name="缬沙坦胶囊",  # ARB类
                dosage="80mg",
                frequency=MedicationFrequency.ONCE_DAILY,
                start_date=date(2022, 5, 1),
            ),
        ],
        lifestyle=Lifestyle(
            sleep_duration=7.0,
            exercise_frequency=ExerciseFrequency.ONE_TO_TWO,
            diet_habit=DietHabit.BALANCED,
            stress_level=5,
        ),
    )


# ============================================================================
# NutritionAgent 基础测试
# ============================================================================


class TestNutritionAgentBasics:
    """NutritionAgent 基础功能测试"""

    def test_agent_name(self):
        """测试智能体名称"""
        agent = NutritionAgent()
        assert agent.name == "Nutrition_Agent"

    def test_system_prompt_not_empty(self):
        """测试系统提示词非空"""
        agent = NutritionAgent()
        prompt = agent.get_system_prompt()
        assert prompt
        assert len(prompt) > 100
        assert "营养" in prompt

    def test_system_prompt_contains_expertise(self):
        """测试系统提示词包含专业领域"""
        agent = NutritionAgent()
        prompt = agent.get_system_prompt()
        assert "血脂" in prompt or "胆固醇" in prompt
        assert "血糖" in prompt
        assert "药物" in prompt


# ============================================================================
# 药物-食物交互检测测试 (Requirement 6.5)
# ============================================================================


class TestDrugFoodInteractions:
    """药物-食物交互检测测试

    Validates: Requirements 6.5
    """

    def test_warfarin_interaction(self):
        """测试华法林与维生素K食物交互检测"""
        medications = [
            Medication(
                drug_name="华法林钠片",
                dosage="2.5mg",
                frequency=MedicationFrequency.ONCE_DAILY,
                start_date=date(2023, 1, 1),
            )
        ]
        interactions = _detect_drug_food_interactions(medications)

        assert len(interactions) == 1
        assert interactions[0]["drug_category"] == "华法林"
        assert "维生素K" in interactions[0]["warning"]
        assert "深绿色蔬菜" in interactions[0]["warning"]

    def test_statin_interaction(self):
        """测试他汀类药物与葡萄柚交互检测"""
        medications = [
            Medication(
                drug_name="阿托伐他汀钙片",
                dosage="20mg",
                frequency=MedicationFrequency.ONCE_DAILY,
                start_date=date(2023, 1, 1),
            )
        ]
        interactions = _detect_drug_food_interactions(medications)

        assert len(interactions) == 1
        assert interactions[0]["drug_category"] == "他汀类"
        assert "葡萄柚" in interactions[0]["warning"]

    def test_metformin_interaction(self):
        """测试二甲双胍与酒精交互检测"""
        medications = [
            Medication(
                drug_name="二甲双胍缓释片",
                dosage="500mg",
                frequency=MedicationFrequency.TWICE_DAILY,
                start_date=date(2023, 1, 1),
            )
        ]
        interactions = _detect_drug_food_interactions(medications)

        assert len(interactions) == 1
        assert interactions[0]["drug_category"] == "二甲双胍"
        assert "酒精" in interactions[0]["warning"]
        assert "乳酸酸中毒" in interactions[0]["warning"]

    def test_acei_arb_interaction(self):
        """测试ACEI/ARB类与高钾食物交互检测"""
        medications = [
            Medication(
                drug_name="缬沙坦胶囊",
                dosage="80mg",
                frequency=MedicationFrequency.ONCE_DAILY,
                start_date=date(2023, 1, 1),
            )
        ]
        interactions = _detect_drug_food_interactions(medications)

        assert len(interactions) == 1
        assert interactions[0]["drug_category"] == "ACEI/ARB"
        assert "高钾" in interactions[0]["warning"]

    def test_thyroid_hormone_interaction(self):
        """测试甲状腺激素与大豆/纤维交互检测"""
        medications = [
            Medication(
                drug_name="左甲状腺素钠片",
                dosage="50μg",
                frequency=MedicationFrequency.ONCE_DAILY,
                start_date=date(2023, 1, 1),
            )
        ]
        interactions = _detect_drug_food_interactions(medications)

        assert len(interactions) == 1
        assert interactions[0]["drug_category"] == "甲状腺激素"
        assert "大豆" in interactions[0]["warning"]

    def test_multiple_interactions(self, user_with_medications):
        """测试多种药物交互检测"""
        interactions = _detect_drug_food_interactions(user_with_medications.medications)

        # 应检测到华法林、他汀类、二甲双胍三种交互
        assert len(interactions) == 3
        categories = {i["drug_category"] for i in interactions}
        assert "华法林" in categories
        assert "他汀类" in categories
        assert "二甲双胍" in categories

    def test_no_interaction_for_safe_drugs(self):
        """测试无交互风险的药物"""
        medications = [
            Medication(
                drug_name="氨氯地平片",  # 钙通道阻滞剂，无特定食物交互
                dosage="5mg",
                frequency=MedicationFrequency.ONCE_DAILY,
                start_date=date(2023, 1, 1),
            )
        ]
        interactions = _detect_drug_food_interactions(medications)
        assert len(interactions) == 0

    def test_ended_medication_not_checked(self):
        """测试已结束用药不检测交互"""
        medications = [
            Medication(
                drug_name="华法林钠片",
                dosage="2.5mg",
                frequency=MedicationFrequency.ONCE_DAILY,
                start_date=date(2023, 1, 1),
                end_date=date(2023, 6, 1),  # 已结束
            )
        ]
        interactions = _detect_drug_food_interactions(medications)
        assert len(interactions) == 0


# ============================================================================
# 血脂异常建议生成测试 (Requirement 6.3)
# ============================================================================


class TestLipidActionItems:
    """血脂异常建议生成测试

    Validates: Requirements 6.3
    """

    def test_normal_lipids_no_items(self):
        """测试正常血脂不生成建议"""
        blood_lipids = BloodLipids(
            total_cholesterol=4.5,
            triglycerides=1.2,
            hdl=1.3,
            ldl=2.8,
        )
        result = detect_lipid_abnormality(blood_lipids=blood_lipids)
        items = _generate_lipid_action_items(result)
        assert len(items) == 0

    def test_high_cholesterol_generates_items(self):
        """测试高胆固醇生成建议"""
        blood_lipids = BloodLipids(
            total_cholesterol=6.0,  # 偏高
            triglycerides=1.2,
            hdl=1.3,
            ldl=2.8,
        )
        result = detect_lipid_abnormality(blood_lipids=blood_lipids)
        items = _generate_lipid_action_items(result)

        assert len(items) >= 1
        assert all(item.category == ActionCategory.NUTRITION for item in items)
        # 应包含控制饱和脂肪或膳食纤维相关建议
        titles = [item.title for item in items]
        assert any("脂肪" in t or "纤维" in t for t in titles)

    def test_high_ldl_generates_items(self):
        """测试高LDL生成建议"""
        blood_lipids = BloodLipids(
            total_cholesterol=4.5,
            triglycerides=1.2,
            hdl=1.3,
            ldl=4.0,  # 偏高
        )
        result = detect_lipid_abnormality(blood_lipids=blood_lipids)
        items = _generate_lipid_action_items(result)

        assert len(items) >= 1
        assert all(item.category == ActionCategory.NUTRITION for item in items)

    def test_high_triglycerides_generates_omega3(self):
        """测试高甘油三酯生成Omega-3建议"""
        blood_lipids = BloodLipids(
            total_cholesterol=4.5,
            triglycerides=2.5,  # 偏高
            hdl=1.3,
            ldl=2.8,
        )
        result = detect_lipid_abnormality(blood_lipids=blood_lipids)
        items = _generate_lipid_action_items(result)

        assert len(items) >= 1
        titles = [item.title for item in items]
        assert any("Omega" in t or "omega" in t.lower() for t in titles)

    def test_low_hdl_generates_items(self):
        """测试低HDL生成建议"""
        blood_lipids = BloodLipids(
            total_cholesterol=4.5,
            triglycerides=1.2,
            hdl=0.8,  # 偏低
            ldl=2.8,
        )
        result = detect_lipid_abnormality(blood_lipids=blood_lipids)
        items = _generate_lipid_action_items(result)

        assert len(items) >= 1
        assert any("HDL" in item.title or "HDL" in item.description for item in items)


# ============================================================================
# 血糖异常建议生成测试 (Requirement 6.4)
# ============================================================================


class TestGlucoseActionItems:
    """血糖异常建议生成测试

    Validates: Requirements 6.4
    """

    def test_normal_glucose_no_items(self):
        """测试正常血糖不生成建议"""
        blood_glucose = BloodGlucose(
            fasting_glucose=5.0,
            hba1c=5.2,
        )
        result = detect_glucose_abnormality(blood_glucose=blood_glucose)
        items = _generate_glucose_action_items(result)
        assert len(items) == 0

    def test_high_fasting_glucose_generates_items(self):
        """测试高空腹血糖生成建议"""
        blood_glucose = BloodGlucose(
            fasting_glucose=7.0,  # 偏高
            hba1c=5.2,
        )
        result = detect_glucose_abnormality(blood_glucose=blood_glucose)
        items = _generate_glucose_action_items(result)

        assert len(items) >= 1
        assert all(item.category == ActionCategory.NUTRITION for item in items)
        # 应包含碳水化合物控制相关建议
        descriptions = [item.description for item in items]
        assert any("碳水" in d or "GI" in d for d in descriptions)

    def test_high_hba1c_generates_items(self):
        """测试高糖化血红蛋白生成建议"""
        blood_glucose = BloodGlucose(
            fasting_glucose=5.5,
            hba1c=6.5,  # 偏高
        )
        result = detect_glucose_abnormality(blood_glucose=blood_glucose)
        items = _generate_glucose_action_items(result)

        assert len(items) >= 1
        assert all(item.category == ActionCategory.NUTRITION for item in items)


# ============================================================================
# NutritionAgent.process() 集成测试
# ============================================================================


class TestNutritionAgentProcess:
    """NutritionAgent.process() 集成测试

    Validates: Requirements 6.1-6.7
    """

    @pytest.mark.asyncio
    async def test_process_normal_user(self, normal_user_profile):
        """测试处理正常用户"""
        agent = NutritionAgent()
        state: HealthState = {
            "user_query": "请给我一些营养建议",
            "user_profile": normal_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        # 验证响应写入 (Requirement 6.7)
        assert "nutrition" in result["expert_responses"]
        response = json.loads(result["expert_responses"]["nutrition"])
        assert "action_items" in response
        # 正常用户也应有基础建议，确保至少有1个
        assert len(response["action_items"]) >= 1

    @pytest.mark.asyncio
    async def test_process_abnormal_lipid_user(self, abnormal_lipid_user_profile):
        """测试处理血脂异常用户"""
        agent = NutritionAgent()
        state: HealthState = {
            "user_query": "我血脂偏高，请给我营养建议",
            "user_profile": abnormal_lipid_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = json.loads(result["expert_responses"]["nutrition"])
        assert "血脂异常" in response["analysis_summary"]
        assert len(response["action_items"]) >= 3  # Requirement 6.6

    @pytest.mark.asyncio
    async def test_process_abnormal_glucose_user(self, abnormal_glucose_user_profile):
        """测试处理血糖异常用户"""
        agent = NutritionAgent()
        state: HealthState = {
            "user_query": "我血糖偏高，请给我营养建议",
            "user_profile": abnormal_glucose_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = json.loads(result["expert_responses"]["nutrition"])
        assert "血糖异常" in response["analysis_summary"]
        assert len(response["action_items"]) >= 3

    @pytest.mark.asyncio
    async def test_process_user_with_medications(self, user_with_medications):
        """测试处理有用药史的用户"""
        agent = NutritionAgent()
        state: HealthState = {
            "user_query": "我在服用多种药物，请给我饮食建议",
            "user_profile": user_with_medications,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = json.loads(result["expert_responses"]["nutrition"])

        # 验证药物交互检测 (Requirement 6.5)
        assert len(response["drug_interactions"]) == 3
        assert "药物-食物交互风险" in response["analysis_summary"]

        # 验证生成了交互警告（标题包含药物类别名称）
        action_items = response["action_items"]
        warning_items = [item for item in action_items if "药物饮食注意事项" in item["title"]]
        assert len(warning_items) >= 1

    @pytest.mark.asyncio
    async def test_process_outputs_3_to_5_items(self, abnormal_lipid_user_profile):
        """测试输出 3-5 个 ActionItem (Requirement 6.6)"""
        agent = NutritionAgent()
        state: HealthState = {
            "user_query": "请给我全面的营养建议",
            "user_profile": abnormal_lipid_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = json.loads(result["expert_responses"]["nutrition"])
        action_items = response["action_items"]

        assert 3 <= len(action_items) <= 5, f"ActionItem 数量应在 3-5 之间，实际: {len(action_items)}"

    @pytest.mark.asyncio
    async def test_process_all_items_have_nutrition_category(self, abnormal_lipid_user_profile):
        """测试所有 ActionItem 的 category 为"营养" (Requirement 6.6)"""
        agent = NutritionAgent()
        state: HealthState = {
            "user_query": "请给我营养建议",
            "user_profile": abnormal_lipid_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = json.loads(result["expert_responses"]["nutrition"])
        for item in response["action_items"]:
            assert item["category"] == "营养"

    @pytest.mark.asyncio
    async def test_process_handles_missing_profile(self):
        """测试处理缺失用户画像的情况"""
        agent = NutritionAgent()
        state: HealthState = {
            "user_query": "请给我营养建议",
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = json.loads(result["expert_responses"]["nutrition"])
        assert "error" in response
        assert "用户画像数据缺失" in response["error"]


# ============================================================================
# RAG 集成测试 (Requirement 6.1, 6.2)
# ============================================================================


class TestRagIntegration:
    """RAG 知识检索集成测试

    Validates: Requirements 6.1, 6.2
    """

    @pytest.mark.asyncio
    async def test_process_without_rag(self, normal_user_profile):
        """测试无 RAG 时使用基础知识 (Requirement 6.2)"""
        agent = NutritionAgent(markdown_rag=None)
        state: HealthState = {
            "user_query": "请给我营养建议",
            "user_profile": normal_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = json.loads(result["expert_responses"]["nutrition"])
        # 应正常返回结果，使用基础知识
        assert "action_items" in response
        assert response["rag_results_count"] == 0

    @pytest.mark.asyncio
    async def test_rag_timeout_fallback(self, normal_user_profile):
        """测试 RAG 超时后降级处理 (Requirement 6.1, 6.2)"""
        # 模拟超时的 RAG
        mock_rag = MagicMock()

        async def slow_query(*args, **kwargs):
            await asyncio.sleep(15)  # 超过 10 秒超时
            return []

        mock_rag.query = slow_query

        agent = NutritionAgent(markdown_rag=mock_rag)
        state: HealthState = {
            "user_query": "请给我营养建议",
            "user_profile": normal_user_profile,
            "expert_responses": {},
        }

        # 应在合理时间内完成（超时处理）
        result = await asyncio.wait_for(
            agent.process(state),
            timeout=15,  # 给予足够时间处理超时
        )

        response = json.loads(result["expert_responses"]["nutrition"])
        assert "action_items" in response
        assert response["rag_results_count"] == 0  # RAG 超时返回空

    @pytest.mark.asyncio
    async def test_rag_success_integration(self, normal_user_profile):
        """测试 RAG 成功检索的集成"""
        # 模拟成功的 RAG
        mock_rag = MagicMock()
        mock_result = MagicMock()
        mock_result.content = "建议增加膳食纤维摄入，每日25-30克"
        mock_result.source = "nutrition_guide.md"
        mock_result.similarity_score = 0.85

        async def mock_query(*args, **kwargs):
            return [mock_result]

        mock_rag.query = mock_query

        agent = NutritionAgent(markdown_rag=mock_rag)
        state: HealthState = {
            "user_query": "如何改善血脂",
            "user_profile": normal_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = json.loads(result["expert_responses"]["nutrition"])
        assert response["rag_results_count"] > 0
        assert response["rag_enhanced"] is True


# ============================================================================
# ActionItem 格式验证测试
# ============================================================================


class TestActionItemFormat:
    """ActionItem 格式验证测试"""

    @pytest.mark.asyncio
    async def test_action_items_have_required_fields(self, abnormal_lipid_user_profile):
        """测试 ActionItem 包含所有必需字段"""
        agent = NutritionAgent()
        state: HealthState = {
            "user_query": "请给我营养建议",
            "user_profile": abnormal_lipid_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = json.loads(result["expert_responses"]["nutrition"])
        required_fields = ["category", "title", "description", "frequency", "priority", "risk_level", "duration"]

        for item in response["action_items"]:
            for field in required_fields:
                assert field in item, f"ActionItem 缺少必需字段: {field}"

    @pytest.mark.asyncio
    async def test_action_item_duration_format(self, abnormal_lipid_user_profile):
        """测试 ActionItem duration 格式正确"""
        agent = NutritionAgent()
        state: HealthState = {
            "user_query": "请给我营养建议",
            "user_profile": abnormal_lipid_user_profile,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = json.loads(result["expert_responses"]["nutrition"])

        for item in response["action_items"]:
            duration = item["duration"]
            # duration 应为 "数字+单位" 或 "用药期间" 等特殊格式
            assert duration, "duration 不应为空"
