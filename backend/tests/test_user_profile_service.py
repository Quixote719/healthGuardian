"""
用户画像服务测试

测试 app.services.user_profile 模块的功能
Requirements: 1.1-1.7
"""

from datetime import date

import pytest

from app.models.user_profile import (
    BloodGlucose,
    BloodLipids,
    DietHabit,
    DiseaseStatus,
    ExerciseFrequency,
    Gender,
    Lifestyle,
    MedicalHistory,
    MedicationFrequency,
    PhysicalExamination,
    UserProfile,
)
from app.services.user_profile import (
    clear_all_profiles,
    delete_user_profile,
    get_user_profile,
    list_user_profile_ids,
    save_user_profile,
    user_profile_exists,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_user_profile() -> UserProfile:
    """创建测试用用户画像"""
    return UserProfile(
        age=30,
        gender=Gender.FEMALE,
        height=165.0,
        weight=55.0,
        medical_history=[
            MedicalHistory(
                disease_name="过敏性鼻炎",
                diagnosis_date=date(2019, 5, 10),
                current_status=DiseaseStatus.CHRONIC,
            ),
        ],
        physical_examination=PhysicalExamination(
            blood_lipids=BloodLipids(
                total_cholesterol=4.5,
                triglycerides=1.2,
                hdl=1.5,
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


@pytest.fixture(autouse=True)
def cleanup_profiles():
    """每个测试前后清理用户画像存储"""
    clear_all_profiles()
    yield
    clear_all_profiles()


# ============================================================================
# Tests: get_user_profile
# ============================================================================


class TestGetUserProfile:
    """测试 get_user_profile 函数"""

    async def test_get_non_existent_profile_returns_demo(self):
        """测试获取不存在的用户画像时返回演示画像"""
        profile = await get_user_profile("non_existent_user")

        assert profile is not None
        assert isinstance(profile, UserProfile)
        # 验证返回的是演示用户画像
        assert profile.age == 45
        assert profile.gender == Gender.MALE

    async def test_get_existing_profile(self, sample_user_profile: UserProfile):
        """测试获取已存在的用户画像"""
        user_id = "test_user_123"
        await save_user_profile(user_id, sample_user_profile)

        retrieved = await get_user_profile(user_id)

        assert retrieved is not None
        assert retrieved.age == sample_user_profile.age
        assert retrieved.gender == sample_user_profile.gender
        assert retrieved.height == sample_user_profile.height


# ============================================================================
# Tests: save_user_profile
# ============================================================================


class TestSaveUserProfile:
    """测试 save_user_profile 函数"""

    async def test_save_new_profile(self, sample_user_profile: UserProfile):
        """测试保存新用户画像"""
        user_id = "new_user_456"

        await save_user_profile(user_id, sample_user_profile)

        assert await user_profile_exists(user_id) is True

    async def test_save_overwrite_existing_profile(self, sample_user_profile: UserProfile):
        """测试覆盖已存在的用户画像"""
        user_id = "overwrite_test"

        # 保存初始画像
        await save_user_profile(user_id, sample_user_profile)

        # 创建新画像并覆盖
        new_profile = UserProfile(
            age=25,
            gender=Gender.OTHER,
            height=170.0,
            weight=60.0,
            medical_history=[],
            physical_examination=PhysicalExamination(
                blood_lipids=BloodLipids(
                    total_cholesterol=4.0,
                    triglycerides=1.0,
                    hdl=1.3,
                    ldl=2.5,
                ),
                blood_glucose=BloodGlucose(
                    fasting_glucose=4.8,
                    hba1c=5.0,
                ),
            ),
            medications=[],
            lifestyle=Lifestyle(
                sleep_duration=8.0,
                exercise_frequency=ExerciseFrequency.DAILY,
                diet_habit=DietHabit.VEGETARIAN,
                stress_level=2,
            ),
        )
        await save_user_profile(user_id, new_profile)

        # 验证覆盖成功
        retrieved = await get_user_profile(user_id)
        assert retrieved.age == 25
        assert retrieved.gender == Gender.OTHER


# ============================================================================
# Tests: delete_user_profile
# ============================================================================


class TestDeleteUserProfile:
    """测试 delete_user_profile 函数"""

    async def test_delete_existing_profile(self, sample_user_profile: UserProfile):
        """测试删除已存在的用户画像"""
        user_id = "delete_test"
        await save_user_profile(user_id, sample_user_profile)

        result = await delete_user_profile(user_id)

        assert result is True
        assert await user_profile_exists(user_id) is False

    async def test_delete_non_existent_profile(self):
        """测试删除不存在的用户画像"""
        result = await delete_user_profile("non_existent_delete")

        assert result is False


# ============================================================================
# Tests: list_user_profile_ids
# ============================================================================


class TestListUserProfileIds:
    """测试 list_user_profile_ids 函数"""

    async def test_list_empty(self):
        """测试列出空的用户画像列表"""
        ids = await list_user_profile_ids()

        assert ids == []

    async def test_list_multiple_profiles(self, sample_user_profile: UserProfile):
        """测试列出多个用户画像"""
        user_ids = ["user_a", "user_b", "user_c"]
        for user_id in user_ids:
            await save_user_profile(user_id, sample_user_profile)

        ids = await list_user_profile_ids()

        assert set(ids) == set(user_ids)


# ============================================================================
# Tests: user_profile_exists
# ============================================================================


class TestUserProfileExists:
    """测试 user_profile_exists 函数"""

    async def test_exists_returns_true_for_saved_profile(self, sample_user_profile: UserProfile):
        """测试已保存的用户画像存在性检查"""
        user_id = "exists_test"
        await save_user_profile(user_id, sample_user_profile)

        assert await user_profile_exists(user_id) is True

    async def test_exists_returns_false_for_unsaved_profile(self):
        """测试未保存的用户画像存在性检查"""
        assert await user_profile_exists("unsaved_user") is False


# ============================================================================
# Tests: Demo User Profile
# ============================================================================


class TestDemoUserProfile:
    """测试演示用户画像的正确性"""

    async def test_demo_profile_has_valid_structure(self):
        """测试演示用户画像结构有效"""
        demo = await get_user_profile("any_non_existent_user")

        # 验证基础生理信息 (Requirement 1.1)
        assert 0 <= demo.age <= 150
        assert demo.gender in Gender
        assert 30 <= demo.height <= 300
        assert 0.5 <= demo.weight <= 500

        # 验证既往病史 (Requirement 1.2)
        assert len(demo.medical_history) <= 100
        for record in demo.medical_history:
            assert len(record.disease_name) <= 200
            assert record.current_status in DiseaseStatus

        # 验证体检指标 (Requirement 1.3)
        lipids = demo.physical_examination.blood_lipids
        assert 0 <= lipids.total_cholesterol <= 50
        assert 0 <= lipids.triglycerides <= 50
        assert 0 <= lipids.hdl <= 50
        assert 0 <= lipids.ldl <= 50

        glucose = demo.physical_examination.blood_glucose
        assert 0 <= glucose.fasting_glucose <= 50
        assert 0 <= glucose.hba1c <= 20

        # 验证用药史 (Requirement 1.4)
        assert len(demo.medications) <= 50
        for med in demo.medications:
            assert len(med.drug_name) <= 200
            assert len(med.dosage) <= 100
            assert med.frequency in MedicationFrequency

        # 验证生活方式基线 (Requirement 1.5)
        assert 0 <= demo.lifestyle.sleep_duration <= 24
        assert demo.lifestyle.exercise_frequency in ExerciseFrequency
        assert demo.lifestyle.diet_habit in DietHabit
        assert 1 <= demo.lifestyle.stress_level <= 10

    async def test_demo_profile_bmi_calculation(self):
        """测试演示用户画像 BMI 计算"""
        demo = await get_user_profile("bmi_test_user")

        # 演示用户: 身高 175cm, 体重 78kg
        # BMI = 78 / (1.75)^2 = 78 / 3.0625 ≈ 25.47
        expected_bmi = round(78 / (175 / 100) ** 2, 2)

        assert demo.bmi == expected_bmi
