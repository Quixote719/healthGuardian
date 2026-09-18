"""
用户画像服务

实现用户画像的存储、检索和管理逻辑。

Requirements: 1.1-1.7
- 提供 get_user_profile() 函数获取用户画像
- 支持用户画像的存储和检索
"""

import logging
from datetime import date

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

# Setup logging
logger = logging.getLogger(__name__)


# ============================================================================
# In-Memory Storage (可替换为数据库实现)
# ============================================================================

# 存储用户画像的内存字典 {user_profile_id: UserProfile}
_user_profiles: dict[str, UserProfile] = {}


# ============================================================================
# Default/Demo User Profile
# ============================================================================


def _create_demo_user_profile() -> UserProfile:
    """创建演示用户画像

    用于开发和测试阶段的默认用户画像。

    Returns:
        UserProfile: 演示用户画像实例
    """
    return UserProfile(
        # 基础生理信息 (Requirement 1.1)
        age=45,
        gender=Gender.MALE,
        height=175.0,
        weight=78.0,
        # 既往病史 (Requirement 1.2)
        medical_history=[
            MedicalHistory(
                disease_name="高血压",
                diagnosis_date=date(2020, 3, 15),
                current_status=DiseaseStatus.CHRONIC,
            ),
            MedicalHistory(
                disease_name="胃溃疡",
                diagnosis_date=date(2018, 8, 20),
                current_status=DiseaseStatus.CURED,
            ),
        ],
        # 体检指标 (Requirement 1.3)
        physical_examination=PhysicalExamination(
            blood_lipids=BloodLipids(
                total_cholesterol=5.8,  # 偏高 (正常 <5.2)
                triglycerides=2.1,  # 偏高 (正常 <1.7)
                hdl=1.1,  # 正常
                ldl=3.6,  # 偏高 (正常 <3.4)
            ),
            blood_glucose=BloodGlucose(
                fasting_glucose=6.5,  # 偏高 (正常 <6.1)
                hba1c=6.0,  # 偏高 (正常 <5.7)
            ),
        ),
        # 用药史 (Requirement 1.4)
        medications=[
            Medication(
                drug_name="氨氯地平",
                dosage="5mg",
                frequency=MedicationFrequency.ONCE_DAILY,
                start_date=date(2020, 3, 20),
                end_date=None,
            ),
            Medication(
                drug_name="阿托伐他汀",
                dosage="20mg",
                frequency=MedicationFrequency.ONCE_DAILY,
                start_date=date(2022, 1, 10),
                end_date=None,
            ),
        ],
        # 生活方式基线 (Requirement 1.5)
        lifestyle=Lifestyle(
            sleep_duration=6.0,
            exercise_frequency=ExerciseFrequency.ONE_TO_TWO,
            diet_habit=DietHabit.MEAT_BASED,
            stress_level=7,
        ),
    )


# ============================================================================
# User Profile Service Functions
# ============================================================================


async def get_user_profile(user_profile_id: str) -> UserProfile | None:
    """获取用户画像

    根据用户画像ID检索用户画像数据。
    如果用户画像不存在，返回演示用户画像（开发阶段）。

    Requirements: 1.1-1.7

    Args:
        user_profile_id: 用户画像的唯一标识符

    Returns:
        UserProfile: 用户画像对象，不存在时返回演示用户画像

    Example:
        >>> profile = await get_user_profile("user_123")
        >>> print(profile.age, profile.gender)
    """
    logger.debug(f"Fetching user profile: {user_profile_id}")

    # 尝试从存储中获取
    profile = _user_profiles.get(user_profile_id)

    if profile is not None:
        logger.info(f"Found user profile: {user_profile_id}")
        return profile

    # 用户画像不存在，返回 None
    logger.info(f"User profile not found: {user_profile_id}")
    return None


async def save_user_profile(
    user_profile_id: str,
    profile: UserProfile,
) -> None:
    """保存用户画像

    将用户画像保存到存储中。

    Args:
        user_profile_id: 用户画像的唯一标识符
        profile: 用户画像对象

    Example:
        >>> profile = UserProfile(...)
        >>> await save_user_profile("user_123", profile)
    """
    logger.info(f"Saving user profile: {user_profile_id}")
    _user_profiles[user_profile_id] = profile


async def delete_user_profile(user_profile_id: str) -> bool:
    """删除用户画像

    从存储中删除指定的用户画像。

    Args:
        user_profile_id: 用户画像的唯一标识符

    Returns:
        bool: 删除成功返回 True，用户画像不存在返回 False
    """
    if user_profile_id in _user_profiles:
        del _user_profiles[user_profile_id]
        logger.info(f"Deleted user profile: {user_profile_id}")
        return True

    logger.warning(f"User profile not found for deletion: {user_profile_id}")
    return False


async def list_user_profile_ids() -> list[str]:
    """列出所有用户画像ID

    Returns:
        list[str]: 所有用户画像的ID列表
    """
    return list(_user_profiles.keys())


async def user_profile_exists(user_profile_id: str) -> bool:
    """检查用户画像是否存在

    Args:
        user_profile_id: 用户画像的唯一标识符

    Returns:
        bool: 存在返回 True，不存在返回 False
    """
    return user_profile_id in _user_profiles


def clear_all_profiles() -> None:
    """清除所有用户画像（仅用于测试）"""
    _user_profiles.clear()
    logger.warning("All user profiles cleared")


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "get_user_profile",
    "save_user_profile",
    "delete_user_profile",
    "list_user_profile_ids",
    "user_profile_exists",
    "clear_all_profiles",
]
