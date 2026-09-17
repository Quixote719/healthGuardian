"""
User_Profile 数据模型单元测试

测试 Requirements 1.1-1.7:
- 基础生理信息字段验证
- 既往病史字段验证
- 体检指标字段验证
- 用药史字段验证
- 生活方式基线字段验证
- Pydantic 模型验证和 JSON 序列化
- BMI 计算属性
"""

from datetime import date
from typing import Any

import pytest
from pydantic import ValidationError

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


# ==================== Fixtures ====================

@pytest.fixture
def valid_blood_lipids() -> BloodLipids:
    """有效的血脂指标"""
    return BloodLipids(
        total_cholesterol=5.0,
        triglycerides=1.5,
        hdl=1.2,
        ldl=3.0,
    )


@pytest.fixture
def valid_blood_glucose() -> BloodGlucose:
    """有效的血糖指标"""
    return BloodGlucose(
        fasting_glucose=5.5,
        hba1c=5.6,
    )


@pytest.fixture
def valid_physical_examination(
    valid_blood_lipids: BloodLipids,
    valid_blood_glucose: BloodGlucose,
) -> PhysicalExamination:
    """有效的体检指标"""
    return PhysicalExamination(
        blood_lipids=valid_blood_lipids,
        blood_glucose=valid_blood_glucose,
    )


@pytest.fixture
def valid_lifestyle() -> Lifestyle:
    """有效的生活方式基线"""
    return Lifestyle(
        sleep_duration=7.5,
        exercise_frequency=ExerciseFrequency.THREE_TO_FIVE,
        diet_habit=DietHabit.BALANCED,
        stress_level=5,
    )


@pytest.fixture
def valid_medical_history() -> MedicalHistory:
    """有效的既往病史记录"""
    return MedicalHistory(
        disease_name="高血压",
        diagnosis_date=date(2020, 5, 15),
        current_status=DiseaseStatus.CHRONIC,
    )


@pytest.fixture
def valid_medication() -> Medication:
    """有效的用药记录"""
    return Medication(
        drug_name="阿托伐他汀",
        dosage="20mg",
        frequency=MedicationFrequency.ONCE_DAILY,
        start_date=date(2021, 1, 10),
        end_date=None,
    )


@pytest.fixture
def valid_user_profile(
    valid_physical_examination: PhysicalExamination,
    valid_lifestyle: Lifestyle,
    valid_medical_history: MedicalHistory,
    valid_medication: Medication,
) -> UserProfile:
    """有效的用户健康画像"""
    return UserProfile(
        age=45,
        gender=Gender.MALE,
        height=175.0,
        weight=75.0,
        medical_history=[valid_medical_history],
        physical_examination=valid_physical_examination,
        medications=[valid_medication],
        lifestyle=valid_lifestyle,
    )


# ==================== Enum Tests ====================

class TestEnums:
    """测试所有枚举类型"""
    
    def test_gender_values(self) -> None:
        """Requirement 1.1: 性别枚举值"""
        assert Gender.MALE.value == "男"
        assert Gender.FEMALE.value == "女"
        assert Gender.OTHER.value == "其他"
    
    def test_disease_status_values(self) -> None:
        """Requirement 1.2: 疾病状态枚举值"""
        assert DiseaseStatus.CURED.value == "已治愈"
        assert DiseaseStatus.TREATING.value == "治疗中"
        assert DiseaseStatus.CHRONIC.value == "慢性管理"
    
    def test_medication_frequency_values(self) -> None:
        """Requirement 1.4: 用药频率枚举值"""
        assert MedicationFrequency.ONCE_DAILY.value == "每日一次"
        assert MedicationFrequency.TWICE_DAILY.value == "每日两次"
        assert MedicationFrequency.THREE_TIMES_DAILY.value == "每日三次"
        assert MedicationFrequency.AS_NEEDED.value == "按需服用"
        assert MedicationFrequency.OTHER.value == "其他"
    
    def test_exercise_frequency_values(self) -> None:
        """Requirement 1.5: 运动频率枚举值"""
        assert ExerciseFrequency.NEVER.value == "从不"
        assert ExerciseFrequency.ONE_TO_TWO.value == "每周1-2次"
        assert ExerciseFrequency.THREE_TO_FIVE.value == "每周3-5次"
        assert ExerciseFrequency.DAILY.value == "每天"
    
    def test_diet_habit_values(self) -> None:
        """Requirement 1.5: 饮食习惯枚举值"""
        assert DietHabit.BALANCED.value == "荤素均衡"
        assert DietHabit.VEGETARIAN.value == "素食为主"
        assert DietHabit.MEAT_BASED.value == "肉食为主"
        assert DietHabit.IRREGULAR.value == "不规律"


# ==================== BloodLipids Tests ====================

class TestBloodLipids:
    """血脂指标测试"""
    
    def test_valid_blood_lipids(self, valid_blood_lipids: BloodLipids) -> None:
        """Requirement 1.3: 有效的血脂指标"""
        assert valid_blood_lipids.total_cholesterol == 5.0
        assert valid_blood_lipids.triglycerides == 1.5
        assert valid_blood_lipids.hdl == 1.2
        assert valid_blood_lipids.ldl == 3.0
    
    def test_blood_lipids_boundary_values(self) -> None:
        """Requirement 1.3: 血脂指标边界值测试 (0-50 mmol/L)"""
        # 最小值
        lipids_min = BloodLipids(
            total_cholesterol=0.0,
            triglycerides=0.0,
            hdl=0.0,
            ldl=0.0,
        )
        assert lipids_min.total_cholesterol == 0.0
        
        # 最大值
        lipids_max = BloodLipids(
            total_cholesterol=50.0,
            triglycerides=50.0,
            hdl=50.0,
            ldl=50.0,
        )
        assert lipids_max.total_cholesterol == 50.0
    
    def test_blood_lipids_invalid_negative(self) -> None:
        """Requirement 1.7: 负值应该触发 ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            BloodLipids(
                total_cholesterol=-1.0,
                triglycerides=1.5,
                hdl=1.2,
                ldl=3.0,
            )
        assert "total_cholesterol" in str(exc_info.value)
    
    def test_blood_lipids_invalid_above_max(self) -> None:
        """Requirement 1.7: 超过最大值应该触发 ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            BloodLipids(
                total_cholesterol=51.0,
                triglycerides=1.5,
                hdl=1.2,
                ldl=3.0,
            )
        assert "total_cholesterol" in str(exc_info.value)


# ==================== BloodGlucose Tests ====================

class TestBloodGlucose:
    """血糖指标测试"""
    
    def test_valid_blood_glucose(self, valid_blood_glucose: BloodGlucose) -> None:
        """Requirement 1.3: 有效的血糖指标"""
        assert valid_blood_glucose.fasting_glucose == 5.5
        assert valid_blood_glucose.hba1c == 5.6
    
    def test_blood_glucose_boundary_values(self) -> None:
        """Requirement 1.3: 血糖指标边界值测试"""
        # 最小值
        glucose_min = BloodGlucose(fasting_glucose=0.0, hba1c=0.0)
        assert glucose_min.fasting_glucose == 0.0
        
        # 最大值
        glucose_max = BloodGlucose(fasting_glucose=50.0, hba1c=20.0)
        assert glucose_max.fasting_glucose == 50.0
        assert glucose_max.hba1c == 20.0
    
    def test_blood_glucose_invalid_fasting_glucose(self) -> None:
        """Requirement 1.7: 空腹血糖超出范围应该触发 ValidationError"""
        with pytest.raises(ValidationError):
            BloodGlucose(fasting_glucose=51.0, hba1c=5.6)
    
    def test_blood_glucose_invalid_hba1c(self) -> None:
        """Requirement 1.7: 糖化血红蛋白超出范围应该触发 ValidationError"""
        with pytest.raises(ValidationError):
            BloodGlucose(fasting_glucose=5.5, hba1c=21.0)


# ==================== MedicalHistory Tests ====================

class TestMedicalHistory:
    """既往病史测试"""
    
    def test_valid_medical_history(self, valid_medical_history: MedicalHistory) -> None:
        """Requirement 1.2: 有效的既往病史记录"""
        assert valid_medical_history.disease_name == "高血压"
        assert valid_medical_history.diagnosis_date == date(2020, 5, 15)
        assert valid_medical_history.current_status == DiseaseStatus.CHRONIC
    
    def test_medical_history_max_disease_name_length(self) -> None:
        """Requirement 1.2: 疾病名称最大长度200字符"""
        history = MedicalHistory(
            disease_name="A" * 200,
            diagnosis_date=date(2020, 1, 1),
            current_status=DiseaseStatus.CURED,
        )
        assert len(history.disease_name) == 200
    
    def test_medical_history_disease_name_too_long(self) -> None:
        """Requirement 1.7: 疾病名称超过200字符应该触发 ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            MedicalHistory(
                disease_name="A" * 201,
                diagnosis_date=date(2020, 1, 1),
                current_status=DiseaseStatus.CURED,
            )
        assert "disease_name" in str(exc_info.value)


# ==================== Medication Tests ====================

class TestMedication:
    """用药记录测试"""
    
    def test_valid_medication(self, valid_medication: Medication) -> None:
        """Requirement 1.4: 有效的用药记录"""
        assert valid_medication.drug_name == "阿托伐他汀"
        assert valid_medication.dosage == "20mg"
        assert valid_medication.frequency == MedicationFrequency.ONCE_DAILY
        assert valid_medication.start_date == date(2021, 1, 10)
        assert valid_medication.end_date is None
    
    def test_medication_with_end_date(self) -> None:
        """Requirement 1.4: 用药记录包含结束日期"""
        medication = Medication(
            drug_name="阿莫西林",
            dosage="500mg",
            frequency=MedicationFrequency.THREE_TIMES_DAILY,
            start_date=date(2023, 6, 1),
            end_date=date(2023, 6, 7),
        )
        assert medication.end_date == date(2023, 6, 7)
    
    def test_medication_drug_name_too_long(self) -> None:
        """Requirement 1.7: 药物名称超过200字符应该触发 ValidationError"""
        with pytest.raises(ValidationError):
            Medication(
                drug_name="A" * 201,
                dosage="20mg",
                frequency=MedicationFrequency.ONCE_DAILY,
                start_date=date(2021, 1, 10),
            )
    
    def test_medication_dosage_too_long(self) -> None:
        """Requirement 1.7: 剂量超过100字符应该触发 ValidationError"""
        with pytest.raises(ValidationError):
            Medication(
                drug_name="阿托伐他汀",
                dosage="A" * 101,
                frequency=MedicationFrequency.ONCE_DAILY,
                start_date=date(2021, 1, 10),
            )


# ==================== Lifestyle Tests ====================

class TestLifestyle:
    """生活方式基线测试"""
    
    def test_valid_lifestyle(self, valid_lifestyle: Lifestyle) -> None:
        """Requirement 1.5: 有效的生活方式基线"""
        assert valid_lifestyle.sleep_duration == 7.5
        assert valid_lifestyle.exercise_frequency == ExerciseFrequency.THREE_TO_FIVE
        assert valid_lifestyle.diet_habit == DietHabit.BALANCED
        assert valid_lifestyle.stress_level == 5
    
    def test_lifestyle_sleep_duration_boundary(self) -> None:
        """Requirement 1.5: 睡眠时长边界值 (0-24小时)"""
        # 最小值
        lifestyle_min = Lifestyle(
            sleep_duration=0.0,
            exercise_frequency=ExerciseFrequency.NEVER,
            diet_habit=DietHabit.IRREGULAR,
            stress_level=1,
        )
        assert lifestyle_min.sleep_duration == 0.0
        
        # 最大值
        lifestyle_max = Lifestyle(
            sleep_duration=24.0,
            exercise_frequency=ExerciseFrequency.DAILY,
            diet_habit=DietHabit.BALANCED,
            stress_level=10,
        )
        assert lifestyle_max.sleep_duration == 24.0
    
    def test_lifestyle_stress_level_boundary(self) -> None:
        """Requirement 1.5: 压力水平边界值 (1-10)"""
        # 最小值
        lifestyle_min = Lifestyle(
            sleep_duration=7.0,
            exercise_frequency=ExerciseFrequency.NEVER,
            diet_habit=DietHabit.BALANCED,
            stress_level=1,
        )
        assert lifestyle_min.stress_level == 1
        
        # 最大值
        lifestyle_max = Lifestyle(
            sleep_duration=7.0,
            exercise_frequency=ExerciseFrequency.NEVER,
            diet_habit=DietHabit.BALANCED,
            stress_level=10,
        )
        assert lifestyle_max.stress_level == 10
    
    def test_lifestyle_invalid_sleep_duration(self) -> None:
        """Requirement 1.7: 睡眠时长超出范围应该触发 ValidationError"""
        with pytest.raises(ValidationError):
            Lifestyle(
                sleep_duration=25.0,
                exercise_frequency=ExerciseFrequency.NEVER,
                diet_habit=DietHabit.BALANCED,
                stress_level=5,
            )
    
    def test_lifestyle_invalid_stress_level_too_low(self) -> None:
        """Requirement 1.7: 压力水平小于1应该触发 ValidationError"""
        with pytest.raises(ValidationError):
            Lifestyle(
                sleep_duration=7.0,
                exercise_frequency=ExerciseFrequency.NEVER,
                diet_habit=DietHabit.BALANCED,
                stress_level=0,
            )
    
    def test_lifestyle_invalid_stress_level_too_high(self) -> None:
        """Requirement 1.7: 压力水平大于10应该触发 ValidationError"""
        with pytest.raises(ValidationError):
            Lifestyle(
                sleep_duration=7.0,
                exercise_frequency=ExerciseFrequency.NEVER,
                diet_habit=DietHabit.BALANCED,
                stress_level=11,
            )


# ==================== UserProfile Tests ====================

class TestUserProfile:
    """用户健康画像测试"""
    
    def test_valid_user_profile(self, valid_user_profile: UserProfile) -> None:
        """Requirement 1.1-1.5: 有效的用户健康画像"""
        assert valid_user_profile.age == 45
        assert valid_user_profile.gender == Gender.MALE
        assert valid_user_profile.height == 175.0
        assert valid_user_profile.weight == 75.0
        assert len(valid_user_profile.medical_history) == 1
        assert len(valid_user_profile.medications) == 1
    
    def test_user_profile_age_boundary(
        self,
        valid_physical_examination: PhysicalExamination,
        valid_lifestyle: Lifestyle,
    ) -> None:
        """Requirement 1.1: 年龄边界值 (0-150)"""
        # 最小值
        profile_min = UserProfile(
            age=0,
            gender=Gender.MALE,
            height=50.0,
            weight=3.0,
            physical_examination=valid_physical_examination,
            lifestyle=valid_lifestyle,
        )
        assert profile_min.age == 0
        
        # 最大值
        profile_max = UserProfile(
            age=150,
            gender=Gender.FEMALE,
            height=150.0,
            weight=50.0,
            physical_examination=valid_physical_examination,
            lifestyle=valid_lifestyle,
        )
        assert profile_max.age == 150
    
    def test_user_profile_height_boundary(
        self,
        valid_physical_examination: PhysicalExamination,
        valid_lifestyle: Lifestyle,
    ) -> None:
        """Requirement 1.1: 身高边界值 (30-300厘米)"""
        # 最小值
        profile_min = UserProfile(
            age=30,
            gender=Gender.MALE,
            height=30.0,
            weight=50.0,
            physical_examination=valid_physical_examination,
            lifestyle=valid_lifestyle,
        )
        assert profile_min.height == 30.0
        
        # 最大值
        profile_max = UserProfile(
            age=30,
            gender=Gender.MALE,
            height=300.0,
            weight=100.0,
            physical_examination=valid_physical_examination,
            lifestyle=valid_lifestyle,
        )
        assert profile_max.height == 300.0
    
    def test_user_profile_weight_boundary(
        self,
        valid_physical_examination: PhysicalExamination,
        valid_lifestyle: Lifestyle,
    ) -> None:
        """Requirement 1.1: 体重边界值 (0.5-500千克)"""
        # 最小值
        profile_min = UserProfile(
            age=30,
            gender=Gender.MALE,
            height=170.0,
            weight=0.5,
            physical_examination=valid_physical_examination,
            lifestyle=valid_lifestyle,
        )
        assert profile_min.weight == 0.5
        
        # 最大值
        profile_max = UserProfile(
            age=30,
            gender=Gender.MALE,
            height=170.0,
            weight=500.0,
            physical_examination=valid_physical_examination,
            lifestyle=valid_lifestyle,
        )
        assert profile_max.weight == 500.0
    
    def test_user_profile_bmi_calculation(self, valid_user_profile: UserProfile) -> None:
        """BMI 计算属性测试"""
        # BMI = 75 / (1.75 ^ 2) = 75 / 3.0625 ≈ 24.49
        assert valid_user_profile.bmi == 24.49
    
    def test_user_profile_bmi_calculation_various(
        self,
        valid_physical_examination: PhysicalExamination,
        valid_lifestyle: Lifestyle,
    ) -> None:
        """BMI 计算属性 - 多种情况测试"""
        # 标准体重
        profile_normal = UserProfile(
            age=30,
            gender=Gender.MALE,
            height=180.0,
            weight=72.0,
            physical_examination=valid_physical_examination,
            lifestyle=valid_lifestyle,
        )
        # BMI = 72 / (1.8 ^ 2) = 72 / 3.24 ≈ 22.22
        assert profile_normal.bmi == 22.22
        
        # 偏瘦
        profile_underweight = UserProfile(
            age=25,
            gender=Gender.FEMALE,
            height=165.0,
            weight=45.0,
            physical_examination=valid_physical_examination,
            lifestyle=valid_lifestyle,
        )
        # BMI = 45 / (1.65 ^ 2) = 45 / 2.7225 ≈ 16.53
        assert profile_underweight.bmi == 16.53
    
    def test_user_profile_invalid_age_negative(
        self,
        valid_physical_examination: PhysicalExamination,
        valid_lifestyle: Lifestyle,
    ) -> None:
        """Requirement 1.7: 年龄为负数应该触发 ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            UserProfile(
                age=-1,
                gender=Gender.MALE,
                height=170.0,
                weight=70.0,
                physical_examination=valid_physical_examination,
                lifestyle=valid_lifestyle,
            )
        assert "age" in str(exc_info.value)
    
    def test_user_profile_invalid_age_too_high(
        self,
        valid_physical_examination: PhysicalExamination,
        valid_lifestyle: Lifestyle,
    ) -> None:
        """Requirement 1.7: 年龄超过150应该触发 ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            UserProfile(
                age=151,
                gender=Gender.MALE,
                height=170.0,
                weight=70.0,
                physical_examination=valid_physical_examination,
                lifestyle=valid_lifestyle,
            )
        assert "age" in str(exc_info.value)
    
    def test_user_profile_invalid_height(
        self,
        valid_physical_examination: PhysicalExamination,
        valid_lifestyle: Lifestyle,
    ) -> None:
        """Requirement 1.7: 身高超出范围应该触发 ValidationError"""
        with pytest.raises(ValidationError):
            UserProfile(
                age=30,
                gender=Gender.MALE,
                height=29.0,  # 低于30
                weight=70.0,
                physical_examination=valid_physical_examination,
                lifestyle=valid_lifestyle,
            )
    
    def test_user_profile_invalid_weight(
        self,
        valid_physical_examination: PhysicalExamination,
        valid_lifestyle: Lifestyle,
    ) -> None:
        """Requirement 1.7: 体重超出范围应该触发 ValidationError"""
        with pytest.raises(ValidationError):
            UserProfile(
                age=30,
                gender=Gender.MALE,
                height=170.0,
                weight=0.4,  # 低于0.5
                physical_examination=valid_physical_examination,
                lifestyle=valid_lifestyle,
            )
    
    def test_user_profile_empty_lists(
        self,
        valid_physical_examination: PhysicalExamination,
        valid_lifestyle: Lifestyle,
    ) -> None:
        """Requirement 1.2, 1.4: 既往病史和用药史可以为空列表"""
        profile = UserProfile(
            age=30,
            gender=Gender.MALE,
            height=170.0,
            weight=70.0,
            physical_examination=valid_physical_examination,
            lifestyle=valid_lifestyle,
            medical_history=[],
            medications=[],
        )
        assert profile.medical_history == []
        assert profile.medications == []


# ==================== JSON Serialization Tests ====================

class TestJSONSerialization:
    """JSON 序列化/反序列化测试"""
    
    def test_user_profile_json_serialization(
        self, valid_user_profile: UserProfile
    ) -> None:
        """Requirement 1.6: Pydantic 模型支持 JSON 序列化"""
        json_str = valid_user_profile.model_dump_json()
        assert isinstance(json_str, str)
        # JSON 序列化可能不包含空格，使用更灵活的断言
        assert '"age":45' in json_str or '"age": 45' in json_str
        assert '"gender":"男"' in json_str or '"gender": "男"' in json_str
    
    def test_user_profile_json_deserialization(
        self, valid_user_profile: UserProfile
    ) -> None:
        """Requirement 1.6: Pydantic 模型支持 JSON 反序列化"""
        json_str = valid_user_profile.model_dump_json()
        restored = UserProfile.model_validate_json(json_str)
        
        assert restored.age == valid_user_profile.age
        assert restored.gender == valid_user_profile.gender
        assert restored.height == valid_user_profile.height
        assert restored.weight == valid_user_profile.weight
    
    def test_blood_lipids_json_roundtrip(
        self, valid_blood_lipids: BloodLipids
    ) -> None:
        """Requirement 1.6: BloodLipids JSON 往返测试"""
        json_str = valid_blood_lipids.model_dump_json()
        restored = BloodLipids.model_validate_json(json_str)
        
        assert restored.total_cholesterol == valid_blood_lipids.total_cholesterol
        assert restored.triglycerides == valid_blood_lipids.triglycerides
        assert restored.hdl == valid_blood_lipids.hdl
        assert restored.ldl == valid_blood_lipids.ldl
    
    def test_medical_history_json_roundtrip(
        self, valid_medical_history: MedicalHistory
    ) -> None:
        """Requirement 1.6: MedicalHistory JSON 往返测试"""
        json_str = valid_medical_history.model_dump_json()
        restored = MedicalHistory.model_validate_json(json_str)
        
        assert restored.disease_name == valid_medical_history.disease_name
        assert restored.diagnosis_date == valid_medical_history.diagnosis_date
        assert restored.current_status == valid_medical_history.current_status
    
    def test_medication_json_roundtrip(self, valid_medication: Medication) -> None:
        """Requirement 1.6: Medication JSON 往返测试"""
        json_str = valid_medication.model_dump_json()
        restored = Medication.model_validate_json(json_str)
        
        assert restored.drug_name == valid_medication.drug_name
        assert restored.dosage == valid_medication.dosage
        assert restored.frequency == valid_medication.frequency
        assert restored.start_date == valid_medication.start_date
        assert restored.end_date == valid_medication.end_date
    
    def test_user_profile_to_dict(self, valid_user_profile: UserProfile) -> None:
        """Requirement 1.6: Pydantic 模型支持字典转换"""
        profile_dict = valid_user_profile.model_dump()
        
        assert isinstance(profile_dict, dict)
        assert profile_dict["age"] == 45
        assert profile_dict["gender"] == "男"
        assert profile_dict["height"] == 175.0
        assert profile_dict["weight"] == 75.0
