"""
健康指标检测辅助函数

提供血脂异常检测、血糖异常检测、年龄-运动强度匹配、BMI强度调整、
禁忌病史检查、压力等级-干预策略匹配、睡眠时长评估等功能。

Requirements: 6.3, 6.4, 7.2, 7.3, 7.6, 8.2, 8.3
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Set

from app.models.user_profile import BloodLipids, BloodGlucose, MedicalHistory


# ============================================================================
# 枚举和数据类定义
# ============================================================================

class ExerciseIntensity(str, Enum):
    """运动强度等级"""
    HIGH = "高强度"
    MEDIUM_HIGH = "中高强度"
    MEDIUM = "中等强度"
    LOW = "低强度"


class IntensityAdjustment(str, Enum):
    """BMI 强度调整"""
    SLIGHT_INCREASE = "轻度增强"
    STANDARD = "标准强度"
    MODERATE_DECREASE = "适度降低"
    SIGNIFICANT_DECREASE = "显著降低"


class StressInterventionLevel(str, Enum):
    """压力干预等级"""
    DAILY_REGULATION = "日常调节类"
    STRUCTURED_TRAINING = "结构化训练类"
    PROFESSIONAL_SUPPORT = "专业支持类"


class SleepEvaluation(str, Enum):
    """睡眠时长评估"""
    INSUFFICIENT = "睡眠不足"
    NORMAL = "正常"
    EXCESSIVE = "睡眠过多"


@dataclass
class LipidAbnormalityResult:
    """血脂异常检测结果"""
    is_abnormal: bool
    abnormal_items: List[str]
    details: dict


@dataclass
class GlucoseAbnormalityResult:
    """血糖异常检测结果"""
    is_abnormal: bool
    abnormal_items: List[str]
    details: dict


@dataclass
class StressInterventionResult:
    """压力干预等级结果"""
    level: StressInterventionLevel
    requires_attention: bool
    description: str


@dataclass
class SleepEvaluationResult:
    """睡眠评估结果"""
    evaluation: SleepEvaluation
    needs_priority_intervention: bool
    description: str


@dataclass
class ContraindicationResult:
    """禁忌病史检查结果"""
    has_contraindications: bool
    excluded_exercises: Set[str]
    contraindication_details: dict


# ============================================================================
# 血脂异常检测 (Property P6, Requirement 6.3)
# ============================================================================

# 血脂阈值常量
TOTAL_CHOLESTEROL_THRESHOLD = 5.2  # mmol/L
LDL_THRESHOLD = 3.4  # mmol/L
HDL_THRESHOLD = 1.0  # mmol/L (低于此值为异常)
TRIGLYCERIDES_THRESHOLD = 1.7  # mmol/L


def detect_lipid_abnormality(
    blood_lipids: Optional[BloodLipids] = None,
    *,
    total_cholesterol: Optional[float] = None,
    ldl: Optional[float] = None,
    hdl: Optional[float] = None,
    triglycerides: Optional[float] = None,
) -> LipidAbnormalityResult:
    """
    检测血脂异常
    
    根据以下阈值检测血脂异常 (Requirement 6.3):
    - 总胆固醇 ≥ 5.2 mmol/L → 异常
    - LDL ≥ 3.4 mmol/L → 异常
    - HDL < 1.0 mmol/L → 异常
    - 甘油三酯 ≥ 1.7 mmol/L → 异常
    
    Args:
        blood_lipids: BloodLipids 对象 (如果提供，将覆盖单独参数)
        total_cholesterol: 总胆固醇 (mmol/L)
        ldl: 低密度脂蛋白胆固醇 (mmol/L)
        hdl: 高密度脂蛋白胆固醇 (mmol/L)
        triglycerides: 甘油三酯 (mmol/L)
    
    Returns:
        LipidAbnormalityResult: 包含是否异常、异常项目列表和详细信息
    
    Validates: Requirements 6.3
    """
    # 如果提供了 BloodLipids 对象，使用其值
    if blood_lipids is not None:
        total_cholesterol = blood_lipids.total_cholesterol
        ldl = blood_lipids.ldl
        hdl = blood_lipids.hdl
        triglycerides = blood_lipids.triglycerides
    
    abnormal_items = []
    details = {}
    
    # 检测总胆固醇
    if total_cholesterol is not None:
        is_tc_abnormal = total_cholesterol >= TOTAL_CHOLESTEROL_THRESHOLD
        details["total_cholesterol"] = {
            "value": total_cholesterol,
            "threshold": TOTAL_CHOLESTEROL_THRESHOLD,
            "is_abnormal": is_tc_abnormal,
            "condition": "≥"
        }
        if is_tc_abnormal:
            abnormal_items.append("总胆固醇偏高")
    
    # 检测 LDL
    if ldl is not None:
        is_ldl_abnormal = ldl >= LDL_THRESHOLD
        details["ldl"] = {
            "value": ldl,
            "threshold": LDL_THRESHOLD,
            "is_abnormal": is_ldl_abnormal,
            "condition": "≥"
        }
        if is_ldl_abnormal:
            abnormal_items.append("LDL偏高")
    
    # 检测 HDL (低于阈值为异常)
    if hdl is not None:
        is_hdl_abnormal = hdl < HDL_THRESHOLD
        details["hdl"] = {
            "value": hdl,
            "threshold": HDL_THRESHOLD,
            "is_abnormal": is_hdl_abnormal,
            "condition": "<"
        }
        if is_hdl_abnormal:
            abnormal_items.append("HDL偏低")
    
    # 检测甘油三酯
    if triglycerides is not None:
        is_tg_abnormal = triglycerides >= TRIGLYCERIDES_THRESHOLD
        details["triglycerides"] = {
            "value": triglycerides,
            "threshold": TRIGLYCERIDES_THRESHOLD,
            "is_abnormal": is_tg_abnormal,
            "condition": "≥"
        }
        if is_tg_abnormal:
            abnormal_items.append("甘油三酯偏高")
    
    return LipidAbnormalityResult(
        is_abnormal=len(abnormal_items) > 0,
        abnormal_items=abnormal_items,
        details=details
    )


# ============================================================================
# 血糖异常检测 (Property P6, Requirement 6.4)
# ============================================================================

# 血糖阈值常量
FASTING_GLUCOSE_THRESHOLD = 6.1  # mmol/L
HBA1C_THRESHOLD = 5.7  # %


def detect_glucose_abnormality(
    blood_glucose: Optional[BloodGlucose] = None,
    *,
    fasting_glucose: Optional[float] = None,
    hba1c: Optional[float] = None,
) -> GlucoseAbnormalityResult:
    """
    检测血糖异常
    
    根据以下阈值检测血糖异常 (Requirement 6.4):
    - 空腹血糖 ≥ 6.1 mmol/L → 异常
    - 糖化血红蛋白 ≥ 5.7% → 异常
    
    Args:
        blood_glucose: BloodGlucose 对象 (如果提供，将覆盖单独参数)
        fasting_glucose: 空腹血糖 (mmol/L)
        hba1c: 糖化血红蛋白 (%)
    
    Returns:
        GlucoseAbnormalityResult: 包含是否异常、异常项目列表和详细信息
    
    Validates: Requirements 6.4
    """
    # 如果提供了 BloodGlucose 对象，使用其值
    if blood_glucose is not None:
        fasting_glucose = blood_glucose.fasting_glucose
        hba1c = blood_glucose.hba1c
    
    abnormal_items = []
    details = {}
    
    # 检测空腹血糖
    if fasting_glucose is not None:
        is_fg_abnormal = fasting_glucose >= FASTING_GLUCOSE_THRESHOLD
        details["fasting_glucose"] = {
            "value": fasting_glucose,
            "threshold": FASTING_GLUCOSE_THRESHOLD,
            "is_abnormal": is_fg_abnormal,
            "condition": "≥"
        }
        if is_fg_abnormal:
            abnormal_items.append("空腹血糖偏高")
    
    # 检测糖化血红蛋白
    if hba1c is not None:
        is_hba1c_abnormal = hba1c >= HBA1C_THRESHOLD
        details["hba1c"] = {
            "value": hba1c,
            "threshold": HBA1C_THRESHOLD,
            "is_abnormal": is_hba1c_abnormal,
            "condition": "≥"
        }
        if is_hba1c_abnormal:
            abnormal_items.append("糖化血红蛋白偏高")
    
    return GlucoseAbnormalityResult(
        is_abnormal=len(abnormal_items) > 0,
        abnormal_items=abnormal_items,
        details=details
    )


# ============================================================================
# 年龄-运动强度匹配 (Property P8, Requirement 7.2)
# ============================================================================

def get_exercise_intensity_by_age(age: int) -> ExerciseIntensity:
    """
    根据年龄匹配推荐运动强度
    
    年龄-运动强度匹配规则 (Requirement 7.2):
    - 18-39岁 → 高强度
    - 40-59岁 → 中高强度
    - 60-74岁 → 中等强度
    - ≥75岁 → 低强度
    
    注意: 年龄 < 18岁时默认返回低强度 (儿童/青少年需特殊考虑)
    
    Args:
        age: 用户年龄
    
    Returns:
        ExerciseIntensity: 推荐的运动强度等级
    
    Validates: Requirements 7.2
    """
    if age < 18:
        # 儿童和青少年需要特殊考虑，默认低强度
        return ExerciseIntensity.LOW
    elif 18 <= age <= 39:
        return ExerciseIntensity.HIGH
    elif 40 <= age <= 59:
        return ExerciseIntensity.MEDIUM_HIGH
    elif 60 <= age <= 74:
        return ExerciseIntensity.MEDIUM
    else:  # age >= 75
        return ExerciseIntensity.LOW


# ============================================================================
# BMI 强度调整 (Property P9, Requirement 7.3)
# ============================================================================

# BMI 阈值常量
BMI_UNDERWEIGHT_THRESHOLD = 18.5
BMI_NORMAL_UPPER_THRESHOLD = 24.0  # 设计文档使用24作为边界
BMI_OVERWEIGHT_THRESHOLD = 28.0


def calculate_bmi(height: float, weight: float) -> float:
    """
    计算 BMI (体重指数)
    
    Args:
        height: 身高 (厘米)
        weight: 体重 (千克)
    
    Returns:
        BMI 值，保留两位小数
    
    Raises:
        ValueError: 如果身高或体重无效
    """
    if height <= 0:
        raise ValueError("身高必须大于0")
    if weight <= 0:
        raise ValueError("体重必须大于0")
    
    height_m = height / 100
    return round(weight / (height_m ** 2), 2)


def get_intensity_adjustment_by_bmi(
    bmi: Optional[float] = None,
    *,
    height: Optional[float] = None,
    weight: Optional[float] = None,
) -> IntensityAdjustment:
    """
    根据 BMI 获取运动强度调整建议
    
    BMI 强度调整规则 (Requirement 7.3):
    - BMI < 18.5 → 轻度增强
    - 18.5 ≤ BMI < 24 → 标准强度
    - 24 ≤ BMI < 28 → 适度降低
    - BMI ≥ 28 → 显著降低（避免高冲击运动）
    
    Args:
        bmi: BMI 值 (如果提供，将直接使用)
        height: 身高 (厘米)
        weight: 体重 (千克)
    
    Returns:
        IntensityAdjustment: 强度调整建议
    
    Raises:
        ValueError: 如果未提供 BMI 且未提供 height/weight
    
    Validates: Requirements 7.3
    """
    # 计算 BMI (如果未直接提供)
    if bmi is None:
        if height is None or weight is None:
            raise ValueError("必须提供 bmi 或同时提供 height 和 weight")
        bmi = calculate_bmi(height, weight)
    
    if bmi < BMI_UNDERWEIGHT_THRESHOLD:
        return IntensityAdjustment.SLIGHT_INCREASE
    elif bmi < BMI_NORMAL_UPPER_THRESHOLD:  # 18.5 <= bmi < 24
        return IntensityAdjustment.STANDARD
    elif bmi < BMI_OVERWEIGHT_THRESHOLD:  # 24 <= bmi < 28
        return IntensityAdjustment.MODERATE_DECREASE
    else:  # bmi >= 28
        return IntensityAdjustment.SIGNIFICANT_DECREASE


# ============================================================================
# 禁忌病史检查 (Property P10, Requirement 7.6)
# ============================================================================

# 禁忌病史与排除运动类型映射
CONTRAINDICATION_MAPPINGS: dict[str, dict] = {
    "心血管疾病": {
        "keywords": ["心血管", "心脏病", "冠心病", "心肌梗死", "心绞痛", "心衰", "心力衰竭", 
                     "房颤", "心律失常", "高血压性心脏病", "心肌病"],
        "excluded_exercises": {"高强度有氧", "负重训练", "高强度间歇训练", "举重", "硬拉"},
        "description": "心血管疾病患者应避免高强度有氧和负重训练"
    },
    "骨关节疾病": {
        "keywords": ["骨关节", "关节炎", "骨质疏松", "腰椎间盘突出", "颈椎病", "膝关节", 
                     "髋关节", "肩周炎", "类风湿", "痛风性关节炎", "半月板"],
        "excluded_exercises": {"高冲击运动", "深蹲", "跳跃运动", "跑步", "跳绳", "登山"},
        "description": "骨关节疾病患者应避免高冲击运动和深蹲"
    },
    "呼吸系统疾病": {
        "keywords": ["呼吸系统", "哮喘", "慢阻肺", "肺气肿", "肺纤维化", "支气管扩张", 
                     "慢性支气管炎", "肺结核"],
        "excluded_exercises": {"高强度有氧", "高强度间歇训练", "长时间耐力运动"},
        "description": "呼吸系统疾病患者应限制高强度有氧运动"
    },
    "代谢性疾病": {
        "keywords": ["糖尿病", "代谢综合征", "甲状腺功能亢进", "甲亢", "低血糖"],
        "excluded_exercises": {"空腹运动", "长时间空腹有氧"},
        "description": "代谢性疾病患者应避免空腹运动"
    },
    "神经系统疾病": {
        "keywords": ["神经系统", "帕金森", "癫痫", "眩晕症", "前庭功能障碍", "小脑疾病", 
                     "中风", "脑卒中", "偏瘫"],
        "excluded_exercises": {"平衡要求高的运动", "单腿站立", "瑜伽倒立", "攀岩", "滑雪"},
        "description": "神经系统疾病患者应避免平衡要求高的运动"
    }
}


def _match_disease_category(disease_name: str) -> Optional[str]:
    """
    根据疾病名称匹配禁忌病史类别
    
    Args:
        disease_name: 疾病名称
    
    Returns:
        匹配到的类别名称，未匹配返回 None
    """
    disease_lower = disease_name.lower()
    for category, mapping in CONTRAINDICATION_MAPPINGS.items():
        for keyword in mapping["keywords"]:
            if keyword in disease_lower or keyword.lower() in disease_lower:
                return category
    return None


def check_medical_contraindications(
    medical_history: List[MedicalHistory],
) -> ContraindicationResult:
    """
    检查禁忌病史，返回需要排除的运动类型
    
    根据用户病史检查是否存在以下禁忌 (Requirement 7.6):
    - 心血管疾病 → 排除高强度有氧和负重训练
    - 骨关节疾病 → 排除高冲击运动和深蹲
    - 呼吸系统疾病 → 限制高强度有氧
    - 代谢性疾病 → 避免空腹运动
    - 神经系统疾病 → 禁止平衡要求高的运动
    
    Args:
        medical_history: 用户既往病史列表
    
    Returns:
        ContraindicationResult: 包含是否有禁忌、排除的运动类型和详情
    
    Validates: Requirements 7.6
    """
    excluded_exercises: Set[str] = set()
    contraindication_details: dict[str, dict] = {}
    
    for record in medical_history:
        # 只检查当前仍在管理中的疾病 (治疗中或慢性管理)
        if record.current_status.value in ["已治愈"]:
            continue
        
        category = _match_disease_category(record.disease_name)
        if category is not None:
            mapping = CONTRAINDICATION_MAPPINGS[category]
            excluded_exercises.update(mapping["excluded_exercises"])
            
            if category not in contraindication_details:
                contraindication_details[category] = {
                    "diseases": [],
                    "excluded_exercises": list(mapping["excluded_exercises"]),
                    "description": mapping["description"]
                }
            contraindication_details[category]["diseases"].append(record.disease_name)
    
    return ContraindicationResult(
        has_contraindications=len(excluded_exercises) > 0,
        excluded_exercises=excluded_exercises,
        contraindication_details=contraindication_details
    )


# ============================================================================
# 压力等级-干预策略匹配 (Property P11, Requirement 8.2)
# ============================================================================

def get_stress_intervention_level(stress_level: int) -> StressInterventionResult:
    """
    根据压力等级匹配干预策略
    
    压力等级-干预策略匹配规则 (Requirement 8.2):
    - 1-3级 (轻度) → 日常调节类
    - 4-6级 (中度) → 结构化训练类
    - 7-10级 (重度) → 专业支持类（标记需关注）
    
    Args:
        stress_level: 压力等级 (1-10)
    
    Returns:
        StressInterventionResult: 包含干预等级、是否需关注和描述
    
    Raises:
        ValueError: 如果压力等级不在 1-10 范围内
    
    Validates: Requirements 8.2
    """
    if stress_level < 1 or stress_level > 10:
        raise ValueError(f"压力等级必须在 1-10 范围内，当前值: {stress_level}")
    
    if stress_level <= 3:
        return StressInterventionResult(
            level=StressInterventionLevel.DAILY_REGULATION,
            requires_attention=False,
            description="轻度压力，建议日常调节：呼吸练习、散步、听音乐等"
        )
    elif stress_level <= 6:
        return StressInterventionResult(
            level=StressInterventionLevel.STRUCTURED_TRAINING,
            requires_attention=False,
            description="中度压力，建议结构化训练：正念冥想、渐进式肌肉放松、HRV生物反馈等"
        )
    else:  # stress_level >= 7
        return StressInterventionResult(
            level=StressInterventionLevel.PROFESSIONAL_SUPPORT,
            requires_attention=True,
            description="重度压力（需关注），建议专业支持：心理咨询、认知行为治疗等"
        )


# ============================================================================
# 睡眠时长评估 (Property P12, Requirement 8.3)
# ============================================================================

# 睡眠时长阈值常量
SLEEP_INSUFFICIENT_THRESHOLD = 6.0  # 小时
SLEEP_EXCESSIVE_THRESHOLD = 9.0  # 小时


def evaluate_sleep_duration(sleep_duration: float) -> SleepEvaluationResult:
    """
    评估睡眠时长
    
    睡眠时长评估规则 (Requirement 8.3):
    - < 6 小时 → 睡眠不足（优先生成睡眠干预）
    - 6-9 小时 → 正常
    - > 9 小时 → 睡眠过多
    
    Args:
        sleep_duration: 睡眠时长 (小时)
    
    Returns:
        SleepEvaluationResult: 包含评估结果、是否需要优先干预和描述
    
    Raises:
        ValueError: 如果睡眠时长不在有效范围内
    
    Validates: Requirements 8.3
    """
    if sleep_duration < 0 or sleep_duration > 24:
        raise ValueError(f"睡眠时长必须在 0-24 小时范围内，当前值: {sleep_duration}")
    
    if sleep_duration < SLEEP_INSUFFICIENT_THRESHOLD:
        return SleepEvaluationResult(
            evaluation=SleepEvaluation.INSUFFICIENT,
            needs_priority_intervention=True,
            description="睡眠不足（<6小时），建议优先改善睡眠：建立规律作息、睡前放松、优化睡眠环境"
        )
    elif sleep_duration <= SLEEP_EXCESSIVE_THRESHOLD:  # 6 <= sleep_duration <= 9
        return SleepEvaluationResult(
            evaluation=SleepEvaluation.NORMAL,
            needs_priority_intervention=False,
            description="睡眠时长正常（6-9小时），继续保持良好的睡眠习惯"
        )
    else:  # sleep_duration > 9
        return SleepEvaluationResult(
            evaluation=SleepEvaluation.EXCESSIVE,
            needs_priority_intervention=False,
            description="睡眠过多（>9小时），可能提示潜在健康问题，建议关注睡眠质量和日间精力"
        )
