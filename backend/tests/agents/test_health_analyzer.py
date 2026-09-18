"""
健康指标检测辅助函数测试

覆盖血脂异常检测、血糖异常检测、年龄-运动强度匹配、BMI强度调整、
禁忌病史检查、压力等级-干预策略匹配、睡眠时长评估等功能的边界条件和核心逻辑。

Requirements: 6.3, 6.4, 7.2, 7.3, 7.6, 8.2, 8.3
"""

from datetime import date

import pytest

from app.agents.health_analyzer import (
    FASTING_GLUCOSE_THRESHOLD,
    HBA1C_THRESHOLD,
    HDL_THRESHOLD,
    LDL_THRESHOLD,
    TOTAL_CHOLESTEROL_THRESHOLD,
    TRIGLYCERIDES_THRESHOLD,
    ExerciseIntensity,
    IntensityAdjustment,
    SleepEvaluation,
    StressInterventionLevel,
    calculate_bmi,
    check_medical_contraindications,
    detect_glucose_abnormality,
    # Functions
    detect_lipid_abnormality,
    evaluate_sleep_duration,
    get_exercise_intensity_by_age,
    get_intensity_adjustment_by_bmi,
    get_stress_intervention_level,
)
from app.models.user_profile import (
    BloodGlucose,
    BloodLipids,
    DiseaseStatus,
    MedicalHistory,
)

# ============================================================================
# 血脂异常检测测试 (Property P6, Requirement 6.3)
# ============================================================================

class TestDetectLipidAbnormality:
    """血脂异常检测测试类"""

    def test_all_normal_values(self):
        """所有指标都正常时应返回不异常"""
        result = detect_lipid_abnormality(
            total_cholesterol=4.0,  # < 5.2
            ldl=2.5,  # < 3.4
            hdl=1.5,  # >= 1.0
            triglycerides=1.0,  # < 1.7
        )
        assert result.is_abnormal is False
        assert len(result.abnormal_items) == 0

    def test_all_abnormal_values(self):
        """所有指标都异常时应返回异常"""
        result = detect_lipid_abnormality(
            total_cholesterol=6.0,  # >= 5.2
            ldl=4.0,  # >= 3.4
            hdl=0.8,  # < 1.0
            triglycerides=2.0,  # >= 1.7
        )
        assert result.is_abnormal is True
        assert len(result.abnormal_items) == 4
        assert "总胆固醇偏高" in result.abnormal_items
        assert "LDL偏高" in result.abnormal_items
        assert "HDL偏低" in result.abnormal_items
        assert "甘油三酯偏高" in result.abnormal_items

    # --- 总胆固醇边界测试 ---
    def test_total_cholesterol_at_threshold(self):
        """总胆固醇恰好等于阈值 (5.2) 时应为异常"""
        result = detect_lipid_abnormality(
            total_cholesterol=TOTAL_CHOLESTEROL_THRESHOLD,
            ldl=2.0,
            hdl=1.5,
            triglycerides=1.0,
        )
        assert result.is_abnormal is True
        assert "总胆固醇偏高" in result.abnormal_items

    def test_total_cholesterol_just_below_threshold(self):
        """总胆固醇略低于阈值时应正常"""
        result = detect_lipid_abnormality(
            total_cholesterol=5.19,  # < 5.2
            ldl=2.0,
            hdl=1.5,
            triglycerides=1.0,
        )
        assert "总胆固醇偏高" not in result.abnormal_items

    def test_total_cholesterol_above_threshold(self):
        """总胆固醇高于阈值时应为异常"""
        result = detect_lipid_abnormality(
            total_cholesterol=5.5,  # > 5.2
            ldl=2.0,
            hdl=1.5,
            triglycerides=1.0,
        )
        assert result.is_abnormal is True
        assert "总胆固醇偏高" in result.abnormal_items

    # --- LDL 边界测试 ---
    def test_ldl_at_threshold(self):
        """LDL 恰好等于阈值 (3.4) 时应为异常"""
        result = detect_lipid_abnormality(
            total_cholesterol=4.0,
            ldl=LDL_THRESHOLD,
            hdl=1.5,
            triglycerides=1.0,
        )
        assert result.is_abnormal is True
        assert "LDL偏高" in result.abnormal_items

    def test_ldl_just_below_threshold(self):
        """LDL 略低于阈值时应正常"""
        result = detect_lipid_abnormality(
            total_cholesterol=4.0,
            ldl=3.39,  # < 3.4
            hdl=1.5,
            triglycerides=1.0,
        )
        assert "LDL偏高" not in result.abnormal_items

    # --- HDL 边界测试 (低于阈值为异常) ---
    def test_hdl_at_threshold(self):
        """HDL 恰好等于阈值 (1.0) 时应正常（>= 1.0 正常）"""
        result = detect_lipid_abnormality(
            total_cholesterol=4.0,
            ldl=2.0,
            hdl=HDL_THRESHOLD,  # 1.0，正好等于阈值，不是 < 1.0
            triglycerides=1.0,
        )
        # HDL < 1.0 为异常，HDL = 1.0 不是 < 1.0，所以正常
        assert "HDL偏低" not in result.abnormal_items

    def test_hdl_just_below_threshold(self):
        """HDL 略低于阈值时应为异常"""
        result = detect_lipid_abnormality(
            total_cholesterol=4.0,
            ldl=2.0,
            hdl=0.99,  # < 1.0
            triglycerides=1.0,
        )
        assert result.is_abnormal is True
        assert "HDL偏低" in result.abnormal_items

    def test_hdl_above_threshold(self):
        """HDL 高于阈值时应正常"""
        result = detect_lipid_abnormality(
            total_cholesterol=4.0,
            ldl=2.0,
            hdl=1.5,  # > 1.0
            triglycerides=1.0,
        )
        assert "HDL偏低" not in result.abnormal_items

    # --- 甘油三酯边界测试 ---
    def test_triglycerides_at_threshold(self):
        """甘油三酯恰好等于阈值 (1.7) 时应为异常"""
        result = detect_lipid_abnormality(
            total_cholesterol=4.0,
            ldl=2.0,
            hdl=1.5,
            triglycerides=TRIGLYCERIDES_THRESHOLD,
        )
        assert result.is_abnormal is True
        assert "甘油三酯偏高" in result.abnormal_items

    def test_triglycerides_just_below_threshold(self):
        """甘油三酯略低于阈值时应正常"""
        result = detect_lipid_abnormality(
            total_cholesterol=4.0,
            ldl=2.0,
            hdl=1.5,
            triglycerides=1.69,  # < 1.7
        )
        assert "甘油三酯偏高" not in result.abnormal_items

    # --- 使用 BloodLipids 对象 ---
    def test_with_blood_lipids_object(self):
        """使用 BloodLipids 对象时应正确检测"""
        blood_lipids = BloodLipids(
            total_cholesterol=6.0,
            triglycerides=2.0,
            hdl=0.8,
            ldl=4.0,
        )
        result = detect_lipid_abnormality(blood_lipids)
        assert result.is_abnormal is True
        assert len(result.abnormal_items) == 4

    def test_details_contain_correct_info(self):
        """详情信息应包含正确的值和阈值"""
        result = detect_lipid_abnormality(
            total_cholesterol=5.2,
            ldl=3.4,
            hdl=1.0,
            triglycerides=1.7,
        )
        assert result.details["total_cholesterol"]["value"] == 5.2
        assert result.details["total_cholesterol"]["threshold"] == 5.2
        assert result.details["ldl"]["threshold"] == 3.4

    def test_partial_values(self):
        """只提供部分指标时应只检测提供的指标"""
        result = detect_lipid_abnormality(
            total_cholesterol=6.0,
            ldl=None,
            hdl=None,
            triglycerides=None,
        )
        assert result.is_abnormal is True
        assert len(result.abnormal_items) == 1
        assert "总胆固醇偏高" in result.abnormal_items


# ============================================================================
# 血糖异常检测测试 (Property P6, Requirement 6.4)
# ============================================================================

class TestDetectGlucoseAbnormality:
    """血糖异常检测测试类"""

    def test_all_normal_values(self):
        """所有指标都正常时应返回不异常"""
        result = detect_glucose_abnormality(
            fasting_glucose=5.0,  # < 6.1
            hba1c=5.0,  # < 5.7
        )
        assert result.is_abnormal is False
        assert len(result.abnormal_items) == 0

    def test_all_abnormal_values(self):
        """所有指标都异常时应返回异常"""
        result = detect_glucose_abnormality(
            fasting_glucose=7.0,  # >= 6.1
            hba1c=6.5,  # >= 5.7
        )
        assert result.is_abnormal is True
        assert len(result.abnormal_items) == 2
        assert "空腹血糖偏高" in result.abnormal_items
        assert "糖化血红蛋白偏高" in result.abnormal_items

    # --- 空腹血糖边界测试 ---
    def test_fasting_glucose_at_threshold(self):
        """空腹血糖恰好等于阈值 (6.1) 时应为异常"""
        result = detect_glucose_abnormality(
            fasting_glucose=FASTING_GLUCOSE_THRESHOLD,
            hba1c=5.0,
        )
        assert result.is_abnormal is True
        assert "空腹血糖偏高" in result.abnormal_items

    def test_fasting_glucose_just_below_threshold(self):
        """空腹血糖略低于阈值时应正常"""
        result = detect_glucose_abnormality(
            fasting_glucose=6.09,  # < 6.1
            hba1c=5.0,
        )
        assert result.is_abnormal is False
        assert "空腹血糖偏高" not in result.abnormal_items

    def test_fasting_glucose_above_threshold(self):
        """空腹血糖高于阈值时应为异常"""
        result = detect_glucose_abnormality(
            fasting_glucose=7.5,  # > 6.1
            hba1c=5.0,
        )
        assert result.is_abnormal is True
        assert "空腹血糖偏高" in result.abnormal_items

    # --- 糖化血红蛋白边界测试 ---
    def test_hba1c_at_threshold(self):
        """糖化血红蛋白恰好等于阈值 (5.7) 时应为异常"""
        result = detect_glucose_abnormality(
            fasting_glucose=5.0,
            hba1c=HBA1C_THRESHOLD,
        )
        assert result.is_abnormal is True
        assert "糖化血红蛋白偏高" in result.abnormal_items

    def test_hba1c_just_below_threshold(self):
        """糖化血红蛋白略低于阈值时应正常"""
        result = detect_glucose_abnormality(
            fasting_glucose=5.0,
            hba1c=5.69,  # < 5.7
        )
        assert result.is_abnormal is False
        assert "糖化血红蛋白偏高" not in result.abnormal_items

    def test_hba1c_above_threshold(self):
        """糖化血红蛋白高于阈值时应为异常"""
        result = detect_glucose_abnormality(
            fasting_glucose=5.0,
            hba1c=6.5,  # > 5.7
        )
        assert result.is_abnormal is True
        assert "糖化血红蛋白偏高" in result.abnormal_items

    # --- 使用 BloodGlucose 对象 ---
    def test_with_blood_glucose_object(self):
        """使用 BloodGlucose 对象时应正确检测"""
        blood_glucose = BloodGlucose(
            fasting_glucose=7.0,
            hba1c=6.5,
        )
        result = detect_glucose_abnormality(blood_glucose)
        assert result.is_abnormal is True
        assert len(result.abnormal_items) == 2

    def test_only_fasting_glucose_abnormal(self):
        """只有空腹血糖异常时应返回单个异常项"""
        result = detect_glucose_abnormality(
            fasting_glucose=7.0,  # >= 6.1
            hba1c=5.0,  # < 5.7
        )
        assert result.is_abnormal is True
        assert len(result.abnormal_items) == 1
        assert "空腹血糖偏高" in result.abnormal_items

    def test_only_hba1c_abnormal(self):
        """只有糖化血红蛋白异常时应返回单个异常项"""
        result = detect_glucose_abnormality(
            fasting_glucose=5.0,  # < 6.1
            hba1c=6.0,  # >= 5.7
        )
        assert result.is_abnormal is True
        assert len(result.abnormal_items) == 1
        assert "糖化血红蛋白偏高" in result.abnormal_items


# ============================================================================
# 年龄-运动强度匹配测试 (Property P8, Requirement 7.2)
# ============================================================================

class TestGetExerciseIntensityByAge:
    """年龄-运动强度匹配测试类"""

    # --- 18-39岁（高强度）边界测试 ---
    def test_age_18_returns_high(self):
        """18岁应返回高强度"""
        result = get_exercise_intensity_by_age(18)
        assert result == ExerciseIntensity.HIGH

    def test_age_39_returns_high(self):
        """39岁应返回高强度"""
        result = get_exercise_intensity_by_age(39)
        assert result == ExerciseIntensity.HIGH

    def test_age_25_returns_high(self):
        """25岁应返回高强度"""
        result = get_exercise_intensity_by_age(25)
        assert result == ExerciseIntensity.HIGH

    # --- 40-59岁（中高强度）边界测试 ---
    def test_age_40_returns_medium_high(self):
        """40岁应返回中高强度"""
        result = get_exercise_intensity_by_age(40)
        assert result == ExerciseIntensity.MEDIUM_HIGH

    def test_age_59_returns_medium_high(self):
        """59岁应返回中高强度"""
        result = get_exercise_intensity_by_age(59)
        assert result == ExerciseIntensity.MEDIUM_HIGH

    def test_age_50_returns_medium_high(self):
        """50岁应返回中高强度"""
        result = get_exercise_intensity_by_age(50)
        assert result == ExerciseIntensity.MEDIUM_HIGH

    # --- 60-74岁（中等强度）边界测试 ---
    def test_age_60_returns_medium(self):
        """60岁应返回中等强度"""
        result = get_exercise_intensity_by_age(60)
        assert result == ExerciseIntensity.MEDIUM

    def test_age_74_returns_medium(self):
        """74岁应返回中等强度"""
        result = get_exercise_intensity_by_age(74)
        assert result == ExerciseIntensity.MEDIUM

    def test_age_67_returns_medium(self):
        """67岁应返回中等强度"""
        result = get_exercise_intensity_by_age(67)
        assert result == ExerciseIntensity.MEDIUM

    # --- 75岁以上（低强度）边界测试 ---
    def test_age_75_returns_low(self):
        """75岁应返回低强度"""
        result = get_exercise_intensity_by_age(75)
        assert result == ExerciseIntensity.LOW

    def test_age_80_returns_low(self):
        """80岁应返回低强度"""
        result = get_exercise_intensity_by_age(80)
        assert result == ExerciseIntensity.LOW

    def test_age_100_returns_low(self):
        """100岁应返回低强度"""
        result = get_exercise_intensity_by_age(100)
        assert result == ExerciseIntensity.LOW

    # --- 边界情况测试 ---
    def test_age_17_returns_low(self):
        """17岁（未成年）应返回低强度"""
        result = get_exercise_intensity_by_age(17)
        assert result == ExerciseIntensity.LOW

    def test_age_0_returns_low(self):
        """0岁应返回低强度"""
        result = get_exercise_intensity_by_age(0)
        assert result == ExerciseIntensity.LOW


# ============================================================================
# BMI 计算和强度调整测试 (Property P9, Requirement 7.3)
# ============================================================================

class TestCalculateBmi:
    """BMI 计算测试类"""

    def test_normal_bmi_calculation(self):
        """正常 BMI 计算"""
        # BMI = 70 / (1.75)^2 = 22.86
        bmi = calculate_bmi(height=175.0, weight=70.0)
        assert bmi == 22.86

    def test_bmi_rounding(self):
        """BMI 应保留两位小数"""
        bmi = calculate_bmi(height=170.0, weight=65.0)
        # BMI = 65 / (1.7)^2 = 22.49134...
        assert bmi == 22.49

    def test_invalid_height_raises_error(self):
        """无效身高应抛出错误"""
        with pytest.raises(ValueError, match="身高必须大于0"):
            calculate_bmi(height=0, weight=70.0)
        with pytest.raises(ValueError, match="身高必须大于0"):
            calculate_bmi(height=-10, weight=70.0)

    def test_invalid_weight_raises_error(self):
        """无效体重应抛出错误"""
        with pytest.raises(ValueError, match="体重必须大于0"):
            calculate_bmi(height=175.0, weight=0)
        with pytest.raises(ValueError, match="体重必须大于0"):
            calculate_bmi(height=175.0, weight=-10)


class TestGetIntensityAdjustmentByBmi:
    """BMI 强度调整测试类"""

    # --- BMI < 18.5（轻度增强）边界测试 ---
    def test_bmi_17_returns_slight_increase(self):
        """BMI 17 应返回轻度增强"""
        result = get_intensity_adjustment_by_bmi(bmi=17.0)
        assert result == IntensityAdjustment.SLIGHT_INCREASE

    def test_bmi_18_49_returns_slight_increase(self):
        """BMI 18.49 应返回轻度增强"""
        result = get_intensity_adjustment_by_bmi(bmi=18.49)
        assert result == IntensityAdjustment.SLIGHT_INCREASE

    # --- 18.5 <= BMI < 24（标准强度）边界测试 ---
    def test_bmi_18_5_returns_standard(self):
        """BMI 18.5 应返回标准强度"""
        result = get_intensity_adjustment_by_bmi(bmi=18.5)
        assert result == IntensityAdjustment.STANDARD

    def test_bmi_23_99_returns_standard(self):
        """BMI 23.99 应返回标准强度"""
        result = get_intensity_adjustment_by_bmi(bmi=23.99)
        assert result == IntensityAdjustment.STANDARD

    def test_bmi_22_returns_standard(self):
        """BMI 22 应返回标准强度"""
        result = get_intensity_adjustment_by_bmi(bmi=22.0)
        assert result == IntensityAdjustment.STANDARD

    # --- 24 <= BMI < 28（适度降低）边界测试 ---
    def test_bmi_24_returns_moderate_decrease(self):
        """BMI 24 应返回适度降低"""
        result = get_intensity_adjustment_by_bmi(bmi=24.0)
        assert result == IntensityAdjustment.MODERATE_DECREASE

    def test_bmi_27_99_returns_moderate_decrease(self):
        """BMI 27.99 应返回适度降低"""
        result = get_intensity_adjustment_by_bmi(bmi=27.99)
        assert result == IntensityAdjustment.MODERATE_DECREASE

    def test_bmi_26_returns_moderate_decrease(self):
        """BMI 26 应返回适度降低"""
        result = get_intensity_adjustment_by_bmi(bmi=26.0)
        assert result == IntensityAdjustment.MODERATE_DECREASE

    # --- BMI >= 28（显著降低）边界测试 ---
    def test_bmi_28_returns_significant_decrease(self):
        """BMI 28 应返回显著降低"""
        result = get_intensity_adjustment_by_bmi(bmi=28.0)
        assert result == IntensityAdjustment.SIGNIFICANT_DECREASE

    def test_bmi_30_returns_significant_decrease(self):
        """BMI 30 应返回显著降低"""
        result = get_intensity_adjustment_by_bmi(bmi=30.0)
        assert result == IntensityAdjustment.SIGNIFICANT_DECREASE

    def test_bmi_35_returns_significant_decrease(self):
        """BMI 35 应返回显著降低"""
        result = get_intensity_adjustment_by_bmi(bmi=35.0)
        assert result == IntensityAdjustment.SIGNIFICANT_DECREASE

    # --- 使用身高体重计算 ---
    def test_with_height_weight_underweight(self):
        """使用身高体重计算低体重"""
        # BMI = 45 / (1.7)^2 = 15.57
        result = get_intensity_adjustment_by_bmi(height=170.0, weight=45.0)
        assert result == IntensityAdjustment.SLIGHT_INCREASE

    def test_with_height_weight_normal(self):
        """使用身高体重计算正常体重"""
        # BMI = 65 / (1.7)^2 = 22.49
        result = get_intensity_adjustment_by_bmi(height=170.0, weight=65.0)
        assert result == IntensityAdjustment.STANDARD

    def test_with_height_weight_overweight(self):
        """使用身高体重计算超重"""
        # BMI = 80 / (1.7)^2 = 27.68
        result = get_intensity_adjustment_by_bmi(height=170.0, weight=80.0)
        assert result == IntensityAdjustment.MODERATE_DECREASE

    def test_with_height_weight_obese(self):
        """使用身高体重计算肥胖"""
        # BMI = 90 / (1.7)^2 = 31.14
        result = get_intensity_adjustment_by_bmi(height=170.0, weight=90.0)
        assert result == IntensityAdjustment.SIGNIFICANT_DECREASE

    def test_missing_parameters_raises_error(self):
        """缺少参数应抛出错误"""
        with pytest.raises(ValueError, match="必须提供 bmi 或同时提供 height 和 weight"):
            get_intensity_adjustment_by_bmi()
        with pytest.raises(ValueError, match="必须提供 bmi 或同时提供 height 和 weight"):
            get_intensity_adjustment_by_bmi(height=170.0)
        with pytest.raises(ValueError, match="必须提供 bmi 或同时提供 height 和 weight"):
            get_intensity_adjustment_by_bmi(weight=70.0)


# ============================================================================
# 禁忌病史检查测试 (Property P10, Requirement 7.6)
# ============================================================================

class TestCheckMedicalContraindications:
    """禁忌病史检查测试类"""

    def test_no_medical_history(self):
        """无病史时应无禁忌"""
        result = check_medical_contraindications([])
        assert result.has_contraindications is False
        assert len(result.excluded_exercises) == 0

    def test_cured_disease_no_contraindication(self):
        """已治愈的疾病不应产生禁忌"""
        medical_history = [
            MedicalHistory(
                disease_name="冠心病",
                diagnosis_date=date(2020, 1, 1),
                current_status=DiseaseStatus.CURED,
            )
        ]
        result = check_medical_contraindications(medical_history)
        assert result.has_contraindications is False

    # --- 心血管疾病测试 ---
    def test_cardiovascular_disease(self):
        """心血管疾病应排除高强度有氧和负重训练"""
        medical_history = [
            MedicalHistory(
                disease_name="冠心病",
                diagnosis_date=date(2020, 1, 1),
                current_status=DiseaseStatus.CHRONIC,
            )
        ]
        result = check_medical_contraindications(medical_history)
        assert result.has_contraindications is True
        assert "高强度有氧" in result.excluded_exercises
        assert "负重训练" in result.excluded_exercises
        assert "心血管疾病" in result.contraindication_details

    def test_heart_disease_variations(self):
        """各种心脏病名称应被正确识别"""
        for disease_name in ["心脏病", "心绞痛", "心肌梗死", "心力衰竭", "房颤", "心律失常"]:
            medical_history = [
                MedicalHistory(
                    disease_name=disease_name,
                    diagnosis_date=date(2020, 1, 1),
                    current_status=DiseaseStatus.TREATING,
                )
            ]
            result = check_medical_contraindications(medical_history)
            assert result.has_contraindications is True, f"{disease_name} 应被识别为心血管疾病"

    # --- 骨关节疾病测试 ---
    def test_joint_disease(self):
        """骨关节疾病应排除高冲击运动和深蹲"""
        medical_history = [
            MedicalHistory(
                disease_name="膝关节炎",
                diagnosis_date=date(2020, 1, 1),
                current_status=DiseaseStatus.CHRONIC,
            )
        ]
        result = check_medical_contraindications(medical_history)
        assert result.has_contraindications is True
        assert "高冲击运动" in result.excluded_exercises
        assert "深蹲" in result.excluded_exercises
        assert "骨关节疾病" in result.contraindication_details

    def test_joint_disease_variations(self):
        """各种骨关节病名称应被正确识别"""
        for disease_name in ["骨质疏松", "腰椎间盘突出", "颈椎病", "类风湿关节炎", "半月板损伤"]:
            medical_history = [
                MedicalHistory(
                    disease_name=disease_name,
                    diagnosis_date=date(2020, 1, 1),
                    current_status=DiseaseStatus.TREATING,
                )
            ]
            result = check_medical_contraindications(medical_history)
            assert result.has_contraindications is True, f"{disease_name} 应被识别为骨关节疾病"

    # --- 呼吸系统疾病测试 ---
    def test_respiratory_disease(self):
        """呼吸系统疾病应限制高强度有氧"""
        medical_history = [
            MedicalHistory(
                disease_name="慢阻肺",
                diagnosis_date=date(2020, 1, 1),
                current_status=DiseaseStatus.CHRONIC,
            )
        ]
        result = check_medical_contraindications(medical_history)
        assert result.has_contraindications is True
        assert "高强度有氧" in result.excluded_exercises
        assert "呼吸系统疾病" in result.contraindication_details

    # --- 代谢性疾病测试 ---
    def test_metabolic_disease(self):
        """代谢性疾病应避免空腹运动"""
        medical_history = [
            MedicalHistory(
                disease_name="糖尿病",
                diagnosis_date=date(2020, 1, 1),
                current_status=DiseaseStatus.CHRONIC,
            )
        ]
        result = check_medical_contraindications(medical_history)
        assert result.has_contraindications is True
        assert "空腹运动" in result.excluded_exercises
        assert "代谢性疾病" in result.contraindication_details

    # --- 神经系统疾病测试 ---
    def test_neurological_disease(self):
        """神经系统疾病应禁止平衡要求高的运动"""
        medical_history = [
            MedicalHistory(
                disease_name="帕金森病",
                diagnosis_date=date(2020, 1, 1),
                current_status=DiseaseStatus.CHRONIC,
            )
        ]
        result = check_medical_contraindications(medical_history)
        assert result.has_contraindications is True
        assert "平衡要求高的运动" in result.excluded_exercises
        assert "神经系统疾病" in result.contraindication_details

    # --- 多种疾病组合测试 ---
    def test_multiple_diseases(self):
        """多种疾病时应合并所有排除项"""
        medical_history = [
            MedicalHistory(
                disease_name="冠心病",
                diagnosis_date=date(2020, 1, 1),
                current_status=DiseaseStatus.CHRONIC,
            ),
            MedicalHistory(
                disease_name="膝关节炎",
                diagnosis_date=date(2021, 6, 15),
                current_status=DiseaseStatus.TREATING,
            ),
        ]
        result = check_medical_contraindications(medical_history)
        assert result.has_contraindications is True
        # 应包含心血管和骨关节两种禁忌的所有排除运动
        assert "高强度有氧" in result.excluded_exercises
        assert "负重训练" in result.excluded_exercises
        assert "高冲击运动" in result.excluded_exercises
        assert "深蹲" in result.excluded_exercises
        assert "心血管疾病" in result.contraindication_details
        assert "骨关节疾病" in result.contraindication_details

    def test_unrecognized_disease(self):
        """无法识别的疾病不应产生禁忌"""
        medical_history = [
            MedicalHistory(
                disease_name="普通感冒",
                diagnosis_date=date(2023, 1, 1),
                current_status=DiseaseStatus.CURED,
            )
        ]
        result = check_medical_contraindications(medical_history)
        assert result.has_contraindications is False


# ============================================================================
# 压力等级-干预策略匹配测试 (Property P11, Requirement 8.2)
# ============================================================================

class TestGetStressInterventionLevel:
    """压力等级-干预策略匹配测试类"""

    # --- 1-3级（日常调节类）边界测试 ---
    def test_stress_level_1(self):
        """压力等级 1 应返回日常调节类"""
        result = get_stress_intervention_level(1)
        assert result.level == StressInterventionLevel.DAILY_REGULATION
        assert result.requires_attention is False

    def test_stress_level_2(self):
        """压力等级 2 应返回日常调节类"""
        result = get_stress_intervention_level(2)
        assert result.level == StressInterventionLevel.DAILY_REGULATION
        assert result.requires_attention is False

    def test_stress_level_3(self):
        """压力等级 3 应返回日常调节类"""
        result = get_stress_intervention_level(3)
        assert result.level == StressInterventionLevel.DAILY_REGULATION
        assert result.requires_attention is False

    # --- 4-6级（结构化训练类）边界测试 ---
    def test_stress_level_4(self):
        """压力等级 4 应返回结构化训练类"""
        result = get_stress_intervention_level(4)
        assert result.level == StressInterventionLevel.STRUCTURED_TRAINING
        assert result.requires_attention is False

    def test_stress_level_5(self):
        """压力等级 5 应返回结构化训练类"""
        result = get_stress_intervention_level(5)
        assert result.level == StressInterventionLevel.STRUCTURED_TRAINING
        assert result.requires_attention is False

    def test_stress_level_6(self):
        """压力等级 6 应返回结构化训练类"""
        result = get_stress_intervention_level(6)
        assert result.level == StressInterventionLevel.STRUCTURED_TRAINING
        assert result.requires_attention is False

    # --- 7-10级（专业支持类，需关注）边界测试 ---
    def test_stress_level_7(self):
        """压力等级 7 应返回专业支持类且标记需关注"""
        result = get_stress_intervention_level(7)
        assert result.level == StressInterventionLevel.PROFESSIONAL_SUPPORT
        assert result.requires_attention is True

    def test_stress_level_8(self):
        """压力等级 8 应返回专业支持类且标记需关注"""
        result = get_stress_intervention_level(8)
        assert result.level == StressInterventionLevel.PROFESSIONAL_SUPPORT
        assert result.requires_attention is True

    def test_stress_level_9(self):
        """压力等级 9 应返回专业支持类且标记需关注"""
        result = get_stress_intervention_level(9)
        assert result.level == StressInterventionLevel.PROFESSIONAL_SUPPORT
        assert result.requires_attention is True

    def test_stress_level_10(self):
        """压力等级 10 应返回专业支持类且标记需关注"""
        result = get_stress_intervention_level(10)
        assert result.level == StressInterventionLevel.PROFESSIONAL_SUPPORT
        assert result.requires_attention is True

    # --- 边界错误测试 ---
    def test_stress_level_0_raises_error(self):
        """压力等级 0 应抛出错误"""
        with pytest.raises(ValueError, match="压力等级必须在 1-10 范围内"):
            get_stress_intervention_level(0)

    def test_stress_level_11_raises_error(self):
        """压力等级 11 应抛出错误"""
        with pytest.raises(ValueError, match="压力等级必须在 1-10 范围内"):
            get_stress_intervention_level(11)

    def test_negative_stress_level_raises_error(self):
        """负数压力等级应抛出错误"""
        with pytest.raises(ValueError, match="压力等级必须在 1-10 范围内"):
            get_stress_intervention_level(-1)

    def test_description_contains_content(self):
        """结果应包含描述信息"""
        result = get_stress_intervention_level(5)
        assert len(result.description) > 0


# ============================================================================
# 睡眠时长评估测试 (Property P12, Requirement 8.3)
# ============================================================================

class TestEvaluateSleepDuration:
    """睡眠时长评估测试类"""

    # --- < 6 小时（睡眠不足）边界测试 ---
    def test_sleep_0_hours(self):
        """0 小时睡眠应返回睡眠不足"""
        result = evaluate_sleep_duration(0.0)
        assert result.evaluation == SleepEvaluation.INSUFFICIENT
        assert result.needs_priority_intervention is True

    def test_sleep_5_hours(self):
        """5 小时睡眠应返回睡眠不足"""
        result = evaluate_sleep_duration(5.0)
        assert result.evaluation == SleepEvaluation.INSUFFICIENT
        assert result.needs_priority_intervention is True

    def test_sleep_5_99_hours(self):
        """5.99 小时睡眠应返回睡眠不足"""
        result = evaluate_sleep_duration(5.99)
        assert result.evaluation == SleepEvaluation.INSUFFICIENT
        assert result.needs_priority_intervention is True

    # --- 6-9 小时（正常）边界测试 ---
    def test_sleep_6_hours(self):
        """6 小时睡眠应返回正常"""
        result = evaluate_sleep_duration(6.0)
        assert result.evaluation == SleepEvaluation.NORMAL
        assert result.needs_priority_intervention is False

    def test_sleep_7_5_hours(self):
        """7.5 小时睡眠应返回正常"""
        result = evaluate_sleep_duration(7.5)
        assert result.evaluation == SleepEvaluation.NORMAL
        assert result.needs_priority_intervention is False

    def test_sleep_9_hours(self):
        """9 小时睡眠应返回正常"""
        result = evaluate_sleep_duration(9.0)
        assert result.evaluation == SleepEvaluation.NORMAL
        assert result.needs_priority_intervention is False

    # --- > 9 小时（睡眠过多）边界测试 ---
    def test_sleep_9_01_hours(self):
        """9.01 小时睡眠应返回睡眠过多"""
        result = evaluate_sleep_duration(9.01)
        assert result.evaluation == SleepEvaluation.EXCESSIVE
        assert result.needs_priority_intervention is False

    def test_sleep_10_hours(self):
        """10 小时睡眠应返回睡眠过多"""
        result = evaluate_sleep_duration(10.0)
        assert result.evaluation == SleepEvaluation.EXCESSIVE
        assert result.needs_priority_intervention is False

    def test_sleep_12_hours(self):
        """12 小时睡眠应返回睡眠过多"""
        result = evaluate_sleep_duration(12.0)
        assert result.evaluation == SleepEvaluation.EXCESSIVE
        assert result.needs_priority_intervention is False

    # --- 边界错误测试 ---
    def test_negative_sleep_raises_error(self):
        """负数睡眠时长应抛出错误"""
        with pytest.raises(ValueError, match="睡眠时长必须在 0-24 小时范围内"):
            evaluate_sleep_duration(-1.0)

    def test_over_24_hours_raises_error(self):
        """超过 24 小时睡眠应抛出错误"""
        with pytest.raises(ValueError, match="睡眠时长必须在 0-24 小时范围内"):
            evaluate_sleep_duration(25.0)

    def test_description_contains_content(self):
        """结果应包含描述信息"""
        result = evaluate_sleep_duration(7.0)
        assert len(result.description) > 0

    def test_insufficient_sleep_priority_intervention(self):
        """睡眠不足时应标记需要优先干预"""
        result = evaluate_sleep_duration(4.0)
        assert result.needs_priority_intervention is True
        assert "优先" in result.description or "睡眠不足" in result.description
