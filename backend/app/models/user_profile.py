"""
用户健康画像数据模型
包含用户基础生理信息、既往病史、体检指标、用药史和生活方式基线

Requirements: 1.1-1.7
"""

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class Gender(str, Enum):
    """性别枚举"""

    MALE = "男"
    FEMALE = "女"
    OTHER = "其他"


class DiseaseStatus(str, Enum):
    """疾病状态枚举"""

    CURED = "已治愈"
    TREATING = "治疗中"
    CHRONIC = "慢性管理"


class MedicationFrequency(str, Enum):
    """用药频率枚举"""

    ONCE_DAILY = "每日一次"
    TWICE_DAILY = "每日两次"
    THREE_TIMES_DAILY = "每日三次"
    AS_NEEDED = "按需服用"
    OTHER = "其他"


class ExerciseFrequency(str, Enum):
    """运动频率枚举"""

    NEVER = "从不"
    ONE_TO_TWO = "每周1-2次"
    THREE_TO_FIVE = "每周3-5次"
    DAILY = "每天"


class DietHabit(str, Enum):
    """饮食习惯枚举"""

    BALANCED = "荤素均衡"
    VEGETARIAN = "素食为主"
    MEAT_BASED = "肉食为主"
    IRREGULAR = "不规律"


class MedicalHistory(BaseModel):
    """既往病史记录

    Requirement 1.2: 包含疾病名称、诊断日期、当前状态
    """

    disease_name: str = Field(..., max_length=200, description="疾病名称")
    diagnosis_date: date = Field(..., description="诊断日期")
    current_status: DiseaseStatus = Field(..., description="当前状态")


class Medication(BaseModel):
    """用药记录

    Requirement 1.4: 包含药物名称、剂量、用药频率、起始日期、结束日期
    """

    drug_name: str = Field(..., max_length=200, description="药物名称")
    dosage: str = Field(..., max_length=100, description="剂量")
    frequency: MedicationFrequency = Field(..., description="用药频率")
    start_date: date = Field(..., description="起始日期")
    end_date: date | None = Field(None, description="结束日期（可选）")


class BloodLipids(BaseModel):
    """血脂指标

    Requirement 1.3: 总胆固醇、甘油三酯、HDL、LDL，范围0-50 mmol/L
    """

    total_cholesterol: float = Field(..., ge=0, le=50, description="总胆固醇 mmol/L")
    triglycerides: float = Field(..., ge=0, le=50, description="甘油三酯 mmol/L")
    hdl: float = Field(..., ge=0, le=50, description="HDL mmol/L")
    ldl: float = Field(..., ge=0, le=50, description="LDL mmol/L")


class BloodGlucose(BaseModel):
    """血糖指标

    Requirement 1.3: 空腹血糖(范围0-50 mmol/L)、糖化血红蛋白(范围0-20%)
    """

    fasting_glucose: float = Field(..., ge=0, le=50, description="空腹血糖 mmol/L")
    hba1c: float = Field(..., ge=0, le=20, description="糖化血红蛋白 %")


class PhysicalExamination(BaseModel):
    """体检指标

    Requirement 1.3: 包含血脂指标和血糖指标
    """

    blood_lipids: BloodLipids = Field(..., description="血脂指标")
    blood_glucose: BloodGlucose = Field(..., description="血糖指标")


class Lifestyle(BaseModel):
    """生活方式基线

    Requirement 1.5: 睡眠时长、运动频率、饮食习惯、压力水平
    """

    sleep_duration: float = Field(..., ge=0, le=24, description="睡眠时长(小时)")
    exercise_frequency: ExerciseFrequency = Field(..., description="运动频率")
    diet_habit: DietHabit = Field(..., description="饮食习惯")
    stress_level: int = Field(..., ge=1, le=10, description="压力水平 1-10")


class UserProfile(BaseModel):
    """用户健康画像

    Requirement 1.1-1.7: 完整的用户健康画像数据结构
    - 基础生理信息：年龄、性别、身高、体重
    - 既往病史：最多100条记录
    - 体检指标：血脂和血糖
    - 用药史：最多50条记录
    - 生活方式基线：睡眠、运动、饮食、压力
    """

    # 基础生理信息 (Requirement 1.1)
    age: int = Field(..., ge=0, le=150, description="年龄")
    gender: Gender = Field(..., description="性别")
    height: float = Field(..., ge=30, le=300, description="身高(厘米)")
    weight: float = Field(..., ge=0.5, le=500, description="体重(千克)")

    # 既往病史 (Requirement 1.2)
    medical_history: list[MedicalHistory] = Field(
        default_factory=list, max_length=100, description="既往病史（最多100条）"
    )

    # 体检指标 (Requirement 1.3)
    physical_examination: PhysicalExamination = Field(..., description="体检指标")

    # 用药史 (Requirement 1.4)
    medications: list[Medication] = Field(
        default_factory=list, max_length=50, description="用药史（最多50条）"
    )

    # 生活方式基线 (Requirement 1.5)
    lifestyle: Lifestyle = Field(..., description="生活方式基线")

    @property
    def bmi(self) -> float:
        """计算 BMI (体重指数)

        BMI = 体重(kg) / 身高(m)^2
        """
        height_m = self.height / 100
        return round(self.weight / (height_m**2), 2)
