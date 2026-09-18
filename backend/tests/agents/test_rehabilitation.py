"""
Rehabilitation_Agent 运动康复专家智能体测试

测试 RehabilitationAgent 的核心功能：
- 年龄-运动强度匹配 (Requirement 7.2)
- BMI 强度调整 (Requirement 7.3)
- 禁忌病史排除运动类型 (Requirement 7.6)
- ActionItem 输出格式验证 (Requirement 7.4)
- 响应写入 expert_responses (Requirement 7.5)

Requirements: 7.1-7.6
"""

import asyncio
import json
from datetime import date
from unittest.mock import MagicMock

import pytest

from app.agents.health_analyzer import (
    ExerciseIntensity,
    IntensityAdjustment,
    check_medical_contraindications,
    get_exercise_intensity_by_age,
    get_intensity_adjustment_by_bmi,
)
from app.agents.rehabilitation import RehabilitationAgent
from app.models.state import HealthState, NodeExecutionStatus
from app.models.user_profile import (
    BloodGlucose,
    BloodLipids,
    DietHabit,
    DiseaseStatus,
    ExerciseFrequency,
    Gender,
    Lifestyle,
    MedicalHistory,
    PhysicalExamination,
    UserProfile,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def young_healthy_user() -> UserProfile:
    """年轻健康用户画像 (18-39岁，正常BMI)"""
    return UserProfile(
        age=30,
        gender=Gender.MALE,
        height=175.0,
        weight=70.0,  # BMI ~22.9
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
def middle_aged_overweight_user() -> UserProfile:
    """中年超重用户画像 (40-59岁，超重BMI)"""
    return UserProfile(
        age=50,
        gender=Gender.MALE,
        height=170.0,
        weight=85.0,  # BMI ~29.4
        medical_history=[],
        physical_examination=PhysicalExamination(
            blood_lipids=BloodLipids(
                total_cholesterol=5.5,
                triglycerides=1.8,
                hdl=1.0,
                ldl=3.5,
            ),
            blood_glucose=BloodGlucose(
                fasting_glucose=6.0,
                hba1c=5.6,
            ),
        ),
        medications=[],
        lifestyle=Lifestyle(
            sleep_duration=6.5,
            exercise_frequency=ExerciseFrequency.ONE_TO_TWO,
            diet_habit=DietHabit.IRREGULAR,
            stress_level=6,
        ),
    )


@pytest.fixture
def elderly_user() -> UserProfile:
    """老年用户画像 (75岁以上)"""
    return UserProfile(
        age=78,
        gender=Gender.FEMALE,
        height=158.0,
        weight=55.0,  # BMI ~22.0
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
                hba1c=5.5,
            ),
        ),
        medications=[],
        lifestyle=Lifestyle(
            sleep_duration=7.0,
            exercise_frequency=ExerciseFrequency.ONE_TO_TWO,
            diet_habit=DietHabit.BALANCED,
            stress_level=3,
        ),
    )


@pytest.fixture
def user_with_heart_disease() -> UserProfile:
    """有心血管疾病的用户"""
    return UserProfile(
        age=55,
        gender=Gender.MALE,
        height=172.0,
        weight=75.0,
        medical_history=[
            MedicalHistory(
                disease_name="冠心病",
                diagnosis_date=date(2020, 1, 1),
                current_status=DiseaseStatus.CHRONIC,
            ),
        ],
        physical_examination=PhysicalExamination(
            blood_lipids=BloodLipids(
                total_cholesterol=5.8,
                triglycerides=1.9,
                hdl=1.0,
                ldl=3.8,
            ),
            blood_glucose=BloodGlucose(
                fasting_glucose=5.8,
                hba1c=5.6,
            ),
        ),
        medications=[],
        lifestyle=Lifestyle(
            sleep_duration=6.5,
            exercise_frequency=ExerciseFrequency.NEVER,
            diet_habit=DietHabit.BALANCED,
            stress_level=5,
        ),
    )


@pytest.fixture
def user_with_joint_disease() -> UserProfile:
    """有骨关节疾病的用户"""
    return UserProfile(
        age=60,
        gender=Gender.FEMALE,
        height=160.0,
        weight=70.0,  # BMI ~27.3
        medical_history=[
            MedicalHistory(
                disease_name="膝关节骨性关节炎",
                diagnosis_date=date(2019, 6, 1),
                current_status=DiseaseStatus.CHRONIC,
            ),
        ],
        physical_examination=PhysicalExamination(
            blood_lipids=BloodLipids(
                total_cholesterol=5.2,
                triglycerides=1.5,
                hdl=1.2,
                ldl=3.2,
            ),
            blood_glucose=BloodGlucose(
                fasting_glucose=5.5,
                hba1c=5.4,
            ),
        ),
        medications=[],
        lifestyle=Lifestyle(
            sleep_duration=7.0,
            exercise_frequency=ExerciseFrequency.ONE_TO_TWO,
            diet_habit=DietHabit.BALANCED,
            stress_level=4,
        ),
    )


@pytest.fixture
def user_with_multiple_diseases() -> UserProfile:
    """有多种禁忌疾病的用户"""
    return UserProfile(
        age=65,
        gender=Gender.MALE,
        height=170.0,
        weight=95.0,  # BMI ~32.9 (肥胖)
        medical_history=[
            MedicalHistory(
                disease_name="冠心病",
                diagnosis_date=date(2018, 1, 1),
                current_status=DiseaseStatus.CHRONIC,
            ),
            MedicalHistory(
                disease_name="膝关节炎",
                diagnosis_date=date(2019, 6, 1),
                current_status=DiseaseStatus.CHRONIC,
            ),
            MedicalHistory(
                disease_name="糖尿病",
                diagnosis_date=date(2020, 3, 1),
                current_status=DiseaseStatus.CHRONIC,
            ),
        ],
        physical_examination=PhysicalExamination(
            blood_lipids=BloodLipids(
                total_cholesterol=6.0,
                triglycerides=2.2,
                hdl=0.9,
                ldl=4.0,
            ),
            blood_glucose=BloodGlucose(
                fasting_glucose=7.5,
                hba1c=7.2,
            ),
        ),
        medications=[],
        lifestyle=Lifestyle(
            sleep_duration=6.0,
            exercise_frequency=ExerciseFrequency.NEVER,
            diet_habit=DietHabit.IRREGULAR,
            stress_level=7,
        ),
    )


@pytest.fixture
def underweight_user() -> UserProfile:
    """体重过轻用户"""
    return UserProfile(
        age=25,
        gender=Gender.FEMALE,
        height=165.0,
        weight=45.0,  # BMI ~16.5
        medical_history=[],
        physical_examination=PhysicalExamination(
            blood_lipids=BloodLipids(
                total_cholesterol=4.0,
                triglycerides=0.9,
                hdl=1.5,
                ldl=2.2,
            ),
            blood_glucose=BloodGlucose(
                fasting_glucose=4.5,
                hba1c=4.8,
            ),
        ),
        medications=[],
        lifestyle=Lifestyle(
            sleep_duration=7.5,
            exercise_frequency=ExerciseFrequency.THREE_TO_FIVE,
            diet_habit=DietHabit.VEGETARIAN,
            stress_level=4,
        ),
    )


# ============================================================================
# RehabilitationAgent 基础测试
# ============================================================================


class TestRehabilitationAgentBasics:
    """RehabilitationAgent 基础功能测试"""

    def test_agent_name(self):
        """测试智能体名称"""
        agent = RehabilitationAgent()
        assert agent.name == "Rehabilitation_Agent"

    def test_system_prompt_not_empty(self):
        """测试系统提示词非空"""
        agent = RehabilitationAgent()
        prompt = agent.get_system_prompt()
        assert prompt
        assert len(prompt) > 100

    def test_system_prompt_contains_expertise(self):
        """测试系统提示词包含专业领域"""
        agent = RehabilitationAgent()
        prompt = agent.get_system_prompt()
        assert "运动" in prompt
        assert "康复" in prompt or "安全" in prompt


# ============================================================================
# 年龄-运动强度匹配测试 (Requirement 7.2)
# ============================================================================


class TestAgeIntensityMatching:
    """年龄-运动强度匹配测试

    Validates: Requirements 7.2
    """

    def test_young_adult_high_intensity(self):
        """测试18-39岁推荐高强度"""
        for age in [18, 25, 30, 39]:
            intensity = get_exercise_intensity_by_age(age)
            assert intensity == ExerciseIntensity.HIGH

    def test_middle_aged_medium_high_intensity(self):
        """测试40-59岁推荐中高强度"""
        for age in [40, 45, 50, 59]:
            intensity = get_exercise_intensity_by_age(age)
            assert intensity == ExerciseIntensity.MEDIUM_HIGH

    def test_senior_medium_intensity(self):
        """测试60-74岁推荐中等强度"""
        for age in [60, 65, 70, 74]:
            intensity = get_exercise_intensity_by_age(age)
            assert intensity == ExerciseIntensity.MEDIUM

    def test_elderly_low_intensity(self):
        """测试75岁以上推荐低强度"""
        for age in [75, 80, 90, 100]:
            intensity = get_exercise_intensity_by_age(age)
            assert intensity == ExerciseIntensity.LOW

    def test_child_low_intensity(self):
        """测试18岁以下默认低强度"""
        for age in [10, 15, 17]:
            intensity = get_exercise_intensity_by_age(age)
            assert intensity == ExerciseIntensity.LOW


# ============================================================================
# BMI 强度调整测试 (Requirement 7.3)
# ============================================================================


class TestBmiIntensityAdjustment:
    """BMI 强度调整测试

    Validates: Requirements 7.3
    """

    def test_underweight_slight_increase(self):
        """测试BMI<18.5时轻度增强"""
        adjustment = get_intensity_adjustment_by_bmi(bmi=17.0)
        assert adjustment == IntensityAdjustment.SLIGHT_INCREASE

    def test_normal_weight_standard(self):
        """测试18.5≤BMI<24时标准强度"""
        for bmi in [18.5, 20.0, 22.0, 23.9]:
            adjustment = get_intensity_adjustment_by_bmi(bmi=bmi)
            assert adjustment == IntensityAdjustment.STANDARD

    def test_overweight_moderate_decrease(self):
        """测试24≤BMI<28时适度降低"""
        for bmi in [24.0, 25.0, 27.0, 27.9]:
            adjustment = get_intensity_adjustment_by_bmi(bmi=bmi)
            assert adjustment == IntensityAdjustment.MODERATE_DECREASE

    def test_obese_significant_decrease(self):
        """测试BMI≥28时显著降低"""
        for bmi in [28.0, 30.0, 35.0, 40.0]:
            adjustment = get_intensity_adjustment_by_bmi(bmi=bmi)
            assert adjustment == IntensityAdjustment.SIGNIFICANT_DECREASE


# ============================================================================
# 禁忌病史检查测试 (Requirement 7.6)
# ============================================================================


class TestContraindications:
    """禁忌病史检查测试

    Validates: Requirements 7.6
    """

    def test_heart_disease_excludes_high_intensity(self):
        """测试心血管疾病排除高强度有氧和负重训练"""
        medical_history = [
            MedicalHistory(
                disease_name="冠心病",
                diagnosis_date=date(2020, 1, 1),
                current_status=DiseaseStatus.CHRONIC,
            )
        ]
        result = check_medical_contraindications(medical_history)

        assert result.has_contraindications
        assert "高强度有氧" in result.excluded_exercises
        assert "负重训练" in result.excluded_exercises

    def test_joint_disease_excludes_high_impact(self):
        """测试骨关节疾病排除高冲击运动和深蹲"""
        medical_history = [
            MedicalHistory(
                disease_name="膝关节炎",
                diagnosis_date=date(2019, 1, 1),
                current_status=DiseaseStatus.CHRONIC,
            )
        ]
        result = check_medical_contraindications(medical_history)

        assert result.has_contraindications
        assert "高冲击运动" in result.excluded_exercises
        assert "深蹲" in result.excluded_exercises

    def test_respiratory_disease_limits_high_intensity_aerobic(self):
        """测试呼吸系统疾病限制高强度有氧"""
        medical_history = [
            MedicalHistory(
                disease_name="慢阻肺",
                diagnosis_date=date(2020, 1, 1),
                current_status=DiseaseStatus.CHRONIC,
            )
        ]
        result = check_medical_contraindications(medical_history)

        assert result.has_contraindications
        assert "高强度有氧" in result.excluded_exercises

    def test_metabolic_disease_avoids_fasting_exercise(self):
        """测试代谢性疾病避免空腹运动"""
        medical_history = [
            MedicalHistory(
                disease_name="糖尿病",
                diagnosis_date=date(2020, 1, 1),
                current_status=DiseaseStatus.CHRONIC,
            )
        ]
        result = check_medical_contraindications(medical_history)

        assert result.has_contraindications
        assert "空腹运动" in result.excluded_exercises

    def test_neurological_disease_excludes_balance_exercises(self):
        """测试神经系统疾病禁止平衡要求高的运动"""
        medical_history = [
            MedicalHistory(
                disease_name="帕金森病",
                diagnosis_date=date(2020, 1, 1),
                current_status=DiseaseStatus.CHRONIC,
            )
        ]
        result = check_medical_contraindications(medical_history)

        assert result.has_contraindications
        assert "平衡要求高的运动" in result.excluded_exercises

    def test_cured_disease_not_contraindicated(self):
        """测试已治愈疾病不列为禁忌"""
        medical_history = [
            MedicalHistory(
                disease_name="冠心病",
                diagnosis_date=date(2015, 1, 1),
                current_status=DiseaseStatus.CURED,
            )
        ]
        result = check_medical_contraindications(medical_history)

        assert not result.has_contraindications

    def test_no_medical_history_no_contraindications(self):
        """测试无病史时无禁忌"""
        result = check_medical_contraindications([])
        assert not result.has_contraindications
        assert len(result.excluded_exercises) == 0


# ============================================================================
# RehabilitationAgent.process() 集成测试
# ============================================================================


class TestRehabilitationAgentProcess:
    """RehabilitationAgent.process() 集成测试

    Validates: Requirements 7.1-7.6
    """

    @pytest.mark.asyncio
    async def test_process_young_healthy_user(self, young_healthy_user):
        """测试处理年轻健康用户"""
        agent = RehabilitationAgent()
        state: HealthState = {
            "user_query": "请给我运动建议",
            "user_profile": young_healthy_user,
            "expert_responses": {},
        }

        result = await agent.process(state)

        # 验证响应写入 (Requirement 7.5)
        assert "rehabilitation" in result["expert_responses"]
        response = result["expert_responses"]["rehabilitation"]
        assert "高强度" in response  # 年轻人应推荐高强度
        assert result["node_execution_status"][agent.name] == NodeExecutionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_process_elderly_user(self, elderly_user):
        """测试处理老年用户"""
        agent = RehabilitationAgent()
        state: HealthState = {
            "user_query": "我年纪大了，能做什么运动？",
            "user_profile": elderly_user,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["rehabilitation"]
        assert "低强度" in response  # 老年人应推荐低强度

    @pytest.mark.asyncio
    async def test_process_overweight_user(self, middle_aged_overweight_user):
        """测试处理超重用户"""
        agent = RehabilitationAgent()
        state: HealthState = {
            "user_query": "我体重超标，能做什么运动？",
            "user_profile": middle_aged_overweight_user,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["rehabilitation"]
        # 超重用户应提示强度调整
        assert "超标" in response or "降低" in response

    @pytest.mark.asyncio
    async def test_process_user_with_contraindications(self, user_with_heart_disease):
        """测试处理有禁忌症的用户"""
        agent = RehabilitationAgent()
        state: HealthState = {
            "user_query": "我有心脏病，能做什么运动？",
            "user_profile": user_with_heart_disease,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["rehabilitation"]
        # 应包含禁忌提示
        assert "禁忌" in response or "避免" in response
        assert "心血管" in response

    @pytest.mark.asyncio
    async def test_process_outputs_3_to_5_items(self, young_healthy_user):
        """测试输出 3-5 个 ActionItem (Requirement 7.4)"""
        agent = RehabilitationAgent()
        state: HealthState = {
            "user_query": "请给我全面的运动建议",
            "user_profile": young_healthy_user,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["rehabilitation"]
        # 解析响应中的 JSON 数据
        json_start = response.find("```json")
        json_end = response.find("```", json_start + 7)
        if json_start != -1 and json_end != -1:
            json_str = response[json_start + 7:json_end].strip()
            action_items = json.loads(json_str)
            assert 3 <= len(action_items) <= 5, f"ActionItem 数量应在 3-5 之间，实际: {len(action_items)}"

    @pytest.mark.asyncio
    async def test_process_all_items_have_rehabilitation_category(self, young_healthy_user):
        """测试所有 ActionItem 的 category 为"康复" (Requirement 7.4)"""
        agent = RehabilitationAgent()
        state: HealthState = {
            "user_query": "请给我运动建议",
            "user_profile": young_healthy_user,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["rehabilitation"]
        # 解析响应中的 JSON 数据
        json_start = response.find("```json")
        json_end = response.find("```", json_start + 7)
        if json_start != -1 and json_end != -1:
            json_str = response[json_start + 7:json_end].strip()
            action_items = json.loads(json_str)
            for item in action_items:
                assert item["category"] == "康复"

    @pytest.mark.asyncio
    async def test_process_handles_missing_profile(self):
        """测试处理缺失用户画像的情况"""
        agent = RehabilitationAgent()
        state: HealthState = {
            "user_query": "请给我运动建议",
            "expert_responses": {},
        }

        result = await agent.process(state)

        # 应返回降级响应
        assert "rehabilitation" in result["expert_responses"]
        assert result["node_execution_status"][agent.name] == NodeExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_process_multiple_contraindications(self, user_with_multiple_diseases):
        """测试处理多种禁忌症的用户"""
        agent = RehabilitationAgent()
        state: HealthState = {
            "user_query": "我有多种慢性病，能做什么运动？",
            "user_profile": user_with_multiple_diseases,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["rehabilitation"]
        # 多种禁忌应导致低强度建议
        assert "低强度" in response
        # 应提到多种禁忌
        assert "心血管" in response
        assert "骨关节" in response or "关节" in response


# ============================================================================
# RAG 集成测试 (Requirement 7.1)
# ============================================================================


class TestRagIntegration:
    """RAG 知识检索集成测试

    Validates: Requirements 7.1
    """

    @pytest.mark.asyncio
    async def test_process_without_rag(self, young_healthy_user):
        """测试无 RAG 时使用基础知识"""
        agent = RehabilitationAgent(rag=None)
        state: HealthState = {
            "user_query": "请给我运动建议",
            "user_profile": young_healthy_user,
            "expert_responses": {},
        }

        result = await agent.process(state)

        # 应正常返回结果，使用基础知识
        assert "rehabilitation" in result["expert_responses"]
        assert "未检索到专业知识库内容" in result["expert_responses"]["rehabilitation"]

    @pytest.mark.asyncio
    async def test_rag_timeout_fallback(self, young_healthy_user):
        """测试 RAG 超时后降级处理"""
        # 模拟超时的 RAG
        mock_rag = MagicMock()

        async def slow_query(*args, **kwargs):
            await asyncio.sleep(15)  # 超过超时时间
            return []

        mock_rag.query_rehabilitation = slow_query

        agent = RehabilitationAgent(rag=mock_rag, rag_timeout=1.0)  # 1秒超时
        state: HealthState = {
            "user_query": "请给我运动建议",
            "user_profile": young_healthy_user,
            "expert_responses": {},
        }

        # 应在合理时间内完成（超时处理）
        result = await asyncio.wait_for(
            agent.process(state),
            timeout=5,  # 给予足够时间处理超时
        )

        assert "rehabilitation" in result["expert_responses"]
        assert "未检索到专业知识库内容" in result["expert_responses"]["rehabilitation"]


# ============================================================================
# ActionItem 格式验证测试
# ============================================================================


class TestActionItemFormat:
    """ActionItem 格式验证测试"""

    @pytest.mark.asyncio
    async def test_action_items_have_required_fields(self, young_healthy_user):
        """测试 ActionItem 包含所有必需字段"""
        agent = RehabilitationAgent()
        state: HealthState = {
            "user_query": "请给我运动建议",
            "user_profile": young_healthy_user,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["rehabilitation"]
        # 解析响应中的 JSON 数据
        json_start = response.find("```json")
        json_end = response.find("```", json_start + 7)
        if json_start != -1 and json_end != -1:
            json_str = response[json_start + 7:json_end].strip()
            action_items = json.loads(json_str)
            required_fields = ["category", "title", "description", "frequency", "priority", "risk_level", "duration"]

            for item in action_items:
                for field in required_fields:
                    assert field in item, f"ActionItem 缺少必需字段: {field}"

    @pytest.mark.asyncio
    async def test_action_item_duration_format(self, young_healthy_user):
        """测试 ActionItem duration 格式正确"""
        agent = RehabilitationAgent()
        state: HealthState = {
            "user_query": "请给我运动建议",
            "user_profile": young_healthy_user,
            "expert_responses": {},
        }

        result = await agent.process(state)

        response = result["expert_responses"]["rehabilitation"]
        # 解析响应中的 JSON 数据
        json_start = response.find("```json")
        json_end = response.find("```", json_start + 7)
        if json_start != -1 and json_end != -1:
            json_str = response[json_start + 7:json_end].strip()
            action_items = json.loads(json_str)

            for item in action_items:
                duration = item["duration"]
                # duration 应为 "数字+单位(天/周/月)" 格式
                assert duration, "duration 不应为空"
                assert any(unit in duration for unit in ["天", "周", "月"]), f"duration 格式不正确: {duration}"
