"""
综合反思与安全检查智能体节点

Synthesis_Agent 负责整合所有专家智能体的响应，生成深度洞察报告，
执行干预措施去重和冲突检测，并构建最终的健康干预方案。

Requirements: 9.1-9.7
"""

import difflib
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Set, Tuple

from app.agents.base import BaseAgent
from app.models.action_item import ActionCategory, ActionItem, Priority, RiskLevel
from app.models.final_report import ConfirmationStatus, FinalReport
from app.models.state import ErrorInfo, HealthState, NodeExecutionStatus
from app.models.user_profile import UserProfile


# ============================================================================
# 常量定义
# ============================================================================

# 去重时 description 相似度阈值 (Requirement 9.3)
DESCRIPTION_SIMILARITY_THRESHOLD = 0.80

# 类别优先级 (Requirement 9.3: 营养 > 康复 > 神经心理)
CATEGORY_PRIORITY = {
    ActionCategory.NUTRITION: 0,
    ActionCategory.REHABILITATION: 1,
    ActionCategory.NEUROPSYCHOLOGY: 2,
}

# 高风险关键词 (Requirement 9.5)
HIGH_RISK_KEYWORDS = {
    "medication_adjustment": ["停药", "换药", "加药", "减药", "调整药物", "调整处方"],
    "fasting": ["断食超过24小时", "24小时断食", "水断食", "长期断食", "超过24小时断食"],
    "cardiovascular_exercise": ["高强度有氧", "高强度间歇", "HIIT", "负重训练"],
    "supplements": ["补剂", "补充剂", "保健品"],
}

# 药物-营养交互冲突配置 (Requirement 9.4)
DRUG_NUTRITION_CONFLICTS = {
    "华法林": {
        "conflict_keywords": ["维生素K", "绿叶蔬菜", "菠菜", "甘蓝", "西兰花"],
        "description": "华法林与维生素K摄入可能产生交互",
    },
    "他汀类": {
        "conflict_keywords": ["葡萄柚", "柚子"],
        "description": "他汀类药物与葡萄柚可能产生交互",
    },
    "二甲双胍": {
        "conflict_keywords": ["酒精", "饮酒"],
        "description": "二甲双胍与酒精可能增加乳酸酸中毒风险",
    },
    "ACEI": {
        "conflict_keywords": ["高钾", "钾补充"],
        "description": "ACEI/ARB类药物与高钾食物可能导致高钾血症",
    },
    "ARB": {
        "conflict_keywords": ["高钾", "钾补充"],
        "description": "ACEI/ARB类药物与高钾食物可能导致高钾血症",
    },
}

# 运动-病史禁忌冲突配置 (Requirement 9.4)
EXERCISE_MEDICAL_CONFLICTS = {
    "心血管疾病": {
        "conflict_exercises": ["高强度有氧", "HIIT", "高强度间歇", "负重训练", "举重"],
        "description": "心血管疾病患者不宜进行高强度运动",
    },
    "骨关节疾病": {
        "conflict_exercises": ["高冲击运动", "跳跃", "深蹲", "跑步"],
        "description": "骨关节疾病患者应避免高冲击运动",
    },
    "呼吸系统疾病": {
        "conflict_exercises": ["高强度有氧", "长时间耐力运动"],
        "description": "呼吸系统疾病患者应限制高强度有氧运动",
    },
}

# 措施矛盾冲突配置 (Requirement 9.4)
CONTRADICTORY_MEASURES = [
    {
        "keywords_a": ["增加热量", "增加摄入", "热量增加"],
        "keywords_b": ["减少热量", "热量限制", "控制热量", "低热量"],
        "description": "热量摄入建议存在矛盾",
    },
    {
        "keywords_a": ["增加运动强度", "提高运动强度", "高强度运动"],
        "keywords_b": ["降低运动强度", "减少运动强度", "低强度运动"],
        "description": "运动强度建议存在矛盾",
    },
    {
        "keywords_a": ["增加蛋白质", "高蛋白"],
        "keywords_b": ["限制蛋白质", "低蛋白"],
        "description": "蛋白质摄入建议存在矛盾",
    },
]

# 随访计划配置 (Requirement 9.6)
FOLLOW_UP_PLANS = {
    RiskLevel.HIGH: {
        "days": 7,
        "description": "7天后随访",
        "focus_items": ["高风险干预执行情况", "不良反应监测", "指标复查"],
    },
    RiskLevel.MEDIUM: {
        "days": 14,
        "description": "14天后随访",
        "focus_items": ["干预措施执行情况", "症状改善评估", "计划调整建议"],
    },
    RiskLevel.LOW: {
        "days": 30,
        "description": "30天后随访",
        "focus_items": ["整体健康状态评估", "长期干预效果", "后续建议"],
    },
}


# ============================================================================
# 辅助函数
# ============================================================================


def calculate_description_similarity(desc1: str, desc2: str) -> float:
    """计算两个描述文本的相似度
    
    使用 difflib.SequenceMatcher 计算相似度。
    
    Args:
        desc1: 第一个描述文本
        desc2: 第二个描述文本
    
    Returns:
        相似度值 (0.0 - 1.0)
    """
    if not desc1 or not desc2:
        return 0.0
    return difflib.SequenceMatcher(None, desc1, desc2).ratio()


def deduplicate_action_items(action_items: List[ActionItem]) -> List[ActionItem]:
    """对 Action_Item 列表进行去重
    
    去重规则 (Requirement 9.3):
    - title 相同 → 去重
    - description 相似度 > 80% → 去重
    - 按 营养 > 康复 > 神经心理 优先级保留
    
    Args:
        action_items: 原始 ActionItem 列表
    
    Returns:
        去重后的 ActionItem 列表
    """
    if not action_items:
        return []
    
    # 按类别优先级排序（营养 > 康复 > 神经心理）
    sorted_items = sorted(
        action_items, 
        key=lambda x: CATEGORY_PRIORITY.get(x.category, 999)
    )
    
    deduplicated: List[ActionItem] = []
    seen_titles: Set[str] = set()
    
    for item in sorted_items:
        # 检查 title 是否重复
        title_normalized = item.title.strip().lower()
        if title_normalized in seen_titles:
            continue
        
        # 检查 description 相似度是否超过阈值
        is_similar = False
        for existing in deduplicated:
            similarity = calculate_description_similarity(
                item.description, existing.description
            )
            if similarity > DESCRIPTION_SIMILARITY_THRESHOLD:
                is_similar = True
                break
        
        if not is_similar:
            deduplicated.append(item)
            seen_titles.add(title_normalized)
    
    return deduplicated


def detect_drug_nutrition_conflicts(
    action_items: List[ActionItem],
    user_profile: Optional[UserProfile],
) -> List[dict]:
    """检测药物-营养交互冲突
    
    Requirement 9.4: 检测药物-营养交互冲突
    
    Args:
        action_items: ActionItem 列表
        user_profile: 用户画像
    
    Returns:
        冲突列表，每个元素包含冲突描述
    """
    conflicts = []
    
    if user_profile is None:
        return conflicts
    
    # 获取用户当前用药
    current_medications = [
        med.drug_name 
        for med in user_profile.medications 
        if med.end_date is None
    ]
    
    if not current_medications:
        return conflicts
    
    # 检查每个药物与营养建议的冲突
    for med_name in current_medications:
        med_name_lower = med_name.lower()
        
        for drug_category, config in DRUG_NUTRITION_CONFLICTS.items():
            if drug_category.lower() in med_name_lower:
                # 检查营养类 action_items 是否包含冲突关键词
                for item in action_items:
                    if item.category != ActionCategory.NUTRITION:
                        continue
                    
                    item_text = f"{item.title} {item.description}".lower()
                    for keyword in config["conflict_keywords"]:
                        if keyword.lower() in item_text:
                            conflicts.append({
                                "type": "药物-营养冲突",
                                "drug": med_name,
                                "action_item": item.title,
                                "description": config["description"],
                            })
                            break
    
    return conflicts


def detect_exercise_medical_conflicts(
    action_items: List[ActionItem],
    user_profile: Optional[UserProfile],
) -> List[dict]:
    """检测运动-病史禁忌冲突
    
    Requirement 9.4: 检测运动-病史禁忌冲突
    
    Args:
        action_items: ActionItem 列表
        user_profile: 用户画像
    
    Returns:
        冲突列表
    """
    conflicts = []
    
    if user_profile is None:
        return conflicts
    
    # 获取用户当前管理中的疾病
    active_conditions = [
        history.disease_name 
        for history in user_profile.medical_history 
        if history.current_status.value != "已治愈"
    ]
    
    if not active_conditions:
        return conflicts
    
    # 检查病史与运动建议的冲突
    for condition in active_conditions:
        condition_lower = condition.lower()
        
        for disease_category, config in EXERCISE_MEDICAL_CONFLICTS.items():
            if disease_category.lower() in condition_lower or any(
                kw.lower() in condition_lower 
                for kw in ["心血管", "心脏", "骨关节", "关节炎", "呼吸", "肺"]
                if disease_category.lower() in kw or kw in disease_category.lower()
            ):
                # 检查康复类 action_items 是否包含冲突运动
                for item in action_items:
                    if item.category != ActionCategory.REHABILITATION:
                        continue
                    
                    item_text = f"{item.title} {item.description}".lower()
                    for exercise in config["conflict_exercises"]:
                        if exercise.lower() in item_text:
                            conflicts.append({
                                "type": "运动-病史冲突",
                                "condition": condition,
                                "action_item": item.title,
                                "description": config["description"],
                            })
                            break
    
    return conflicts


def detect_contradictory_measures(action_items: List[ActionItem]) -> List[dict]:
    """检测措施矛盾冲突
    
    Requirement 9.4: 检测干预措施矛盾冲突
    
    Args:
        action_items: ActionItem 列表
    
    Returns:
        冲突列表
    """
    conflicts = []
    
    # 收集所有 action_item 的文本
    item_texts = [
        (item, f"{item.title} {item.description}".lower())
        for item in action_items
    ]
    
    # 检查每对矛盾配置
    for contradiction in CONTRADICTORY_MEASURES:
        items_a = []
        items_b = []
        
        for item, text in item_texts:
            has_a = any(kw.lower() in text for kw in contradiction["keywords_a"])
            has_b = any(kw.lower() in text for kw in contradiction["keywords_b"])
            
            if has_a:
                items_a.append(item)
            if has_b:
                items_b.append(item)
        
        # 如果同时存在矛盾的建议
        if items_a and items_b:
            conflicts.append({
                "type": "措施矛盾",
                "items_a": [item.title for item in items_a],
                "items_b": [item.title for item in items_b],
                "description": contradiction["description"],
            })
    
    return conflicts


def detect_all_conflicts(
    action_items: List[ActionItem],
    user_profile: Optional[UserProfile],
) -> Tuple[List[dict], List[ActionItem]]:
    """检测所有冲突并移除冲突项
    
    Requirement 9.4: 检测并处理所有类型的干预冲突
    
    Args:
        action_items: ActionItem 列表
        user_profile: 用户画像
    
    Returns:
        (冲突列表, 移除冲突后的ActionItem列表)
    """
    all_conflicts = []
    items_to_remove: Set[str] = set()
    
    # 检测药物-营养冲突
    drug_conflicts = detect_drug_nutrition_conflicts(action_items, user_profile)
    all_conflicts.extend(drug_conflicts)
    for conflict in drug_conflicts:
        items_to_remove.add(conflict["action_item"])
    
    # 检测运动-病史冲突
    exercise_conflicts = detect_exercise_medical_conflicts(action_items, user_profile)
    all_conflicts.extend(exercise_conflicts)
    for conflict in exercise_conflicts:
        items_to_remove.add(conflict["action_item"])
    
    # 检测措施矛盾
    contradictory_conflicts = detect_contradictory_measures(action_items)
    all_conflicts.extend(contradictory_conflicts)
    # 对于矛盾冲突，移除优先级较低的项目
    for conflict in contradictory_conflicts:
        # 保留 items_a 中的项目（通常是第一个检测到的），移除 items_b
        for title in conflict.get("items_b", []):
            items_to_remove.add(title)
    
    # 移除冲突项
    filtered_items = [
        item for item in action_items 
        if item.title not in items_to_remove
    ]
    
    return all_conflicts, filtered_items


def detect_high_risk_combinations(
    action_items: List[ActionItem],
    user_profile: Optional[UserProfile],
) -> Tuple[bool, List[str]]:
    """检测高风险干预组合
    
    Requirement 9.5: 检测以下高风险组合并设置 requires_confirmation:
    - 涉及停药或调整处方药
    - 超过24小时断食方案
    - 心血管病患者高强度运动
    - 超过3种补剂的方案
    
    Args:
        action_items: ActionItem 列表
        user_profile: 用户画像
    
    Returns:
        (是否需要确认, 高风险原因列表)
    """
    high_risk_reasons = []
    
    # 收集所有 action_item 文本
    all_texts = [
        f"{item.title} {item.description}".lower()
        for item in action_items
    ]
    combined_text = " ".join(all_texts)
    
    # 1. 检测停药或调整处方药
    for keyword in HIGH_RISK_KEYWORDS["medication_adjustment"]:
        if keyword in combined_text:
            high_risk_reasons.append(f"涉及药物调整（{keyword}）")
            break
    
    # 2. 检测超过24小时断食方案
    for keyword in HIGH_RISK_KEYWORDS["fasting"]:
        if keyword in combined_text:
            high_risk_reasons.append(f"涉及长时间断食方案（{keyword}）")
            break
    
    # 3. 检测心血管病患者高强度运动
    if user_profile is not None:
        has_cardiovascular = any(
            "心血管" in h.disease_name or "心脏" in h.disease_name
            for h in user_profile.medical_history
            if h.current_status.value != "已治愈"
        )
        
        if has_cardiovascular:
            for keyword in HIGH_RISK_KEYWORDS["cardiovascular_exercise"]:
                if keyword.lower() in combined_text:
                    high_risk_reasons.append(
                        f"心血管疾病患者进行高强度运动（{keyword}）"
                    )
                    break
    
    # 4. 检测超过3种补剂的方案
    supplement_count = 0
    for keyword in HIGH_RISK_KEYWORDS["supplements"]:
        supplement_count += combined_text.count(keyword)
    
    if supplement_count > 3:
        high_risk_reasons.append(f"涉及多种补剂方案（{supplement_count}种）")
    
    # 5. 检测是否有高风险等级的干预措施
    high_risk_items = [item for item in action_items if item.risk_level == RiskLevel.HIGH]
    if high_risk_items:
        high_risk_reasons.append(
            f"包含{len(high_risk_items)}项高风险干预措施"
        )
    
    requires_confirmation = len(high_risk_reasons) > 0
    return requires_confirmation, high_risk_reasons


def get_overall_risk_level(action_items: List[ActionItem]) -> RiskLevel:
    """获取整体风险等级
    
    取所有 ActionItem 中的最高风险等级。
    
    Args:
        action_items: ActionItem 列表
    
    Returns:
        整体风险等级
    """
    if not action_items:
        return RiskLevel.LOW
    
    risk_priority = {
        RiskLevel.HIGH: 0,
        RiskLevel.MEDIUM: 1,
        RiskLevel.LOW: 2,
    }
    
    highest_risk = RiskLevel.LOW
    for item in action_items:
        if risk_priority.get(item.risk_level, 2) < risk_priority.get(highest_risk, 2):
            highest_risk = item.risk_level
    
    return highest_risk


def generate_follow_up_plan(
    risk_level: RiskLevel,
    action_items: List[ActionItem],
    user_profile: Optional[UserProfile],
) -> str:
    """根据风险等级生成随访计划
    
    Requirement 9.6:
    - 高风险 → 7天后随访
    - 中风险 → 14天后随访
    - 低风险 → 30天后随访
    
    Args:
        risk_level: 整体风险等级
        action_items: ActionItem 列表
        user_profile: 用户画像
    
    Returns:
        随访计划文本
    """
    plan_config = FOLLOW_UP_PLANS.get(risk_level, FOLLOW_UP_PLANS[RiskLevel.LOW])
    
    parts = []
    parts.append(f"建议{plan_config['description']}复查。")
    parts.append("")
    parts.append("**随访重点：**")
    
    for i, item in enumerate(plan_config["focus_items"], 1):
        parts.append(f"{i}. {item}")
    
    parts.append("")
    parts.append("**需关注的指标：**")
    
    # 根据 action_items 生成关注指标
    indicators = []
    
    # 检查营养类建议
    nutrition_items = [i for i in action_items if i.category == ActionCategory.NUTRITION]
    if nutrition_items:
        indicators.append("血脂四项（TC、TG、HDL、LDL）")
        indicators.append("血糖指标（空腹血糖、糖化血红蛋白）")
    
    # 检查康复类建议
    rehab_items = [i for i in action_items if i.category == ActionCategory.REHABILITATION]
    if rehab_items:
        indicators.append("运动耐力和体能变化")
        indicators.append("关节活动度和疼痛评估")
    
    # 检查神经心理类建议
    neuro_items = [i for i in action_items if i.category == ActionCategory.NEUROPSYCHOLOGY]
    if neuro_items:
        indicators.append("压力水平自评")
        indicators.append("睡眠质量评估")
    
    # 根据用户画像添加特定指标
    if user_profile is not None:
        if user_profile.physical_examination.blood_lipids.ldl >= 3.4:
            if "血脂四项" not in " ".join(indicators):
                indicators.append("LDL 胆固醇复查")
        
        if user_profile.physical_examination.blood_glucose.fasting_glucose >= 6.1:
            if "血糖指标" not in " ".join(indicators):
                indicators.append("空腹血糖复查")
    
    for i, indicator in enumerate(indicators[:5], 1):  # 最多5个指标
        parts.append(f"- {indicator}")
    
    return "\n".join(parts)


def generate_deep_insight(
    user_profile: Optional[UserProfile],
    expert_responses: dict,
    action_items: List[ActionItem],
    conflicts: List[dict],
) -> str:
    """生成深度洞察报告
    
    Requirement 9.2: 生成 deep_insight，包含四部分：
    - 健康现状总结
    - 跨学科关联分析
    - 核心问题归因
    - 干预逻辑说明
    
    Args:
        user_profile: 用户画像
        expert_responses: 专家响应字典
        action_items: ActionItem 列表
        conflicts: 冲突列表
    
    Returns:
        深度洞察 Markdown 文本
    """
    parts = []
    
    # 1. 健康现状总结
    parts.append("## 健康现状总结")
    parts.append("")
    
    if user_profile is not None:
        # 基础信息
        parts.append(f"**基础信息**: {user_profile.age}岁，{user_profile.gender.value}，"
                    f"BMI {user_profile.bmi}")
        parts.append("")
        
        # 体检指标
        lipids = user_profile.physical_examination.blood_lipids
        glucose = user_profile.physical_examination.blood_glucose
        
        lipid_status = []
        if lipids.total_cholesterol >= 5.2:
            lipid_status.append(f"总胆固醇 {lipids.total_cholesterol} mmol/L（偏高）")
        if lipids.ldl >= 3.4:
            lipid_status.append(f"LDL {lipids.ldl} mmol/L（偏高）")
        if lipids.hdl < 1.0:
            lipid_status.append(f"HDL {lipids.hdl} mmol/L（偏低）")
        if lipids.triglycerides >= 1.7:
            lipid_status.append(f"甘油三酯 {lipids.triglycerides} mmol/L（偏高）")
        
        if lipid_status:
            parts.append("**血脂指标异常**: " + "，".join(lipid_status))
            parts.append("")
        
        glucose_status = []
        if glucose.fasting_glucose >= 6.1:
            glucose_status.append(f"空腹血糖 {glucose.fasting_glucose} mmol/L（偏高）")
        if glucose.hba1c >= 5.7:
            glucose_status.append(f"糖化血红蛋白 {glucose.hba1c}%（偏高）")
        
        if glucose_status:
            parts.append("**血糖指标异常**: " + "，".join(glucose_status))
            parts.append("")
        
        # 生活方式
        lifestyle = user_profile.lifestyle
        lifestyle_issues = []
        if lifestyle.sleep_duration < 6:
            lifestyle_issues.append(f"睡眠不足（{lifestyle.sleep_duration}小时）")
        elif lifestyle.sleep_duration > 9:
            lifestyle_issues.append(f"睡眠过多（{lifestyle.sleep_duration}小时）")
        
        if lifestyle.stress_level >= 7:
            lifestyle_issues.append(f"压力较高（{lifestyle.stress_level}级）")
        
        if lifestyle.exercise_frequency.value == "从不":
            lifestyle_issues.append("缺乏运动")
        
        if lifestyle_issues:
            parts.append("**生活方式关注点**: " + "，".join(lifestyle_issues))
            parts.append("")
    else:
        parts.append("用户健康画像信息不完整，无法提供详细健康现状分析。")
        parts.append("")
    
    # 2. 跨学科关联分析
    parts.append("## 跨学科关联分析")
    parts.append("")
    
    # 分析各专家响应之间的关联
    nutrition_response = expert_responses.get("nutrition", "")
    rehabilitation_response = expert_responses.get("rehabilitation", "")
    neuropsychology_response = expert_responses.get("neuropsychology", "")
    
    correlations = []
    
    # 血脂异常与运动的关联
    if "血脂" in nutrition_response and rehabilitation_response:
        correlations.append("血脂异常与运动不足存在关联，规律运动可辅助改善血脂水平")
    
    # 睡眠与代谢的关联
    if "睡眠" in neuropsychology_response:
        correlations.append("睡眠质量与代谢健康密切相关，改善睡眠有助于血糖和血脂控制")
    
    # 压力与整体健康的关联
    if "压力" in neuropsychology_response:
        correlations.append("心理压力可通过神经-内分泌-免疫轴影响身体健康，"
                          "压力管理是综合健康干预的重要组成部分")
    
    if correlations:
        for correlation in correlations:
            parts.append(f"- {correlation}")
        parts.append("")
    else:
        parts.append("基于当前数据，各健康维度之间存在潜在关联，"
                    "建议综合考虑营养、运动和心理调节的协同效应。")
        parts.append("")
    
    # 3. 核心问题归因
    parts.append("## 核心问题归因")
    parts.append("")
    
    # 根据 action_items 的优先级和数量分析核心问题
    high_priority_items = [i for i in action_items if i.priority == Priority.HIGH]
    
    if high_priority_items:
        parts.append("**优先处理的健康问题：**")
        parts.append("")
        for item in high_priority_items[:3]:  # 最多列出3个
            parts.append(f"- **{item.title}**（{item.category.value}）")
        parts.append("")
    
    # 分析问题根源
    parts.append("**问题归因分析：**")
    parts.append("")
    
    if user_profile is not None:
        if user_profile.lifestyle.diet_habit.value in ["肉食为主", "不规律"]:
            parts.append("- 饮食结构不合理可能是代谢异常的主要原因")
        
        if user_profile.lifestyle.exercise_frequency.value in ["从不", "每周1-2次"]:
            parts.append("- 运动不足影响能量代谢和心血管健康")
        
        if user_profile.lifestyle.stress_level >= 5:
            parts.append("- 慢性压力可能通过皮质醇升高影响代谢功能")
        
        if user_profile.lifestyle.sleep_duration < 7:
            parts.append("- 睡眠不足影响激素调节和身体恢复")
    
    parts.append("")
    
    # 4. 干预逻辑说明
    parts.append("## 干预逻辑说明")
    parts.append("")
    
    # 按类别统计 action_items
    nutrition_count = len([i for i in action_items if i.category == ActionCategory.NUTRITION])
    rehab_count = len([i for i in action_items if i.category == ActionCategory.REHABILITATION])
    neuro_count = len([i for i in action_items if i.category == ActionCategory.NEUROPSYCHOLOGY])
    
    parts.append(f"本方案包含 **{len(action_items)}** 项干预措施：")
    parts.append(f"- 营养干预：{nutrition_count}项")
    parts.append(f"- 运动康复：{rehab_count}项")
    parts.append(f"- 神经心理：{neuro_count}项")
    parts.append("")
    
    parts.append("**干预优先级安排：**")
    parts.append("")
    parts.append("1. **高优先级措施**应立即执行，这些措施针对最紧迫的健康问题")
    parts.append("2. **中优先级措施**应在1-2周内逐步引入")
    parts.append("3. **低优先级措施**可在基础措施稳定后补充")
    parts.append("")
    
    # 冲突处理说明
    if conflicts:
        parts.append("**冲突处理说明：**")
        parts.append("")
        parts.append(f"检测到 {len(conflicts)} 个潜在冲突，已自动移除冲突项：")
        for conflict in conflicts[:3]:  # 最多显示3个
            parts.append(f"- {conflict.get('description', conflict.get('type', '未知冲突'))}")
        parts.append("")
    
    return "\n".join(parts)


def parse_action_items_from_response(response: str) -> List[ActionItem]:
    """从专家响应中解析 ActionItem 列表
    
    Args:
        response: 专家响应文本
    
    Returns:
        解析出的 ActionItem 列表
    """
    items = []
    
    # 尝试从 JSON 块中解析
    try:
        # 查找 JSON 代码块
        if "```json" in response:
            json_start = response.find("```json") + 7
            json_end = response.find("```", json_start)
            if json_end > json_start:
                json_str = response[json_start:json_end].strip()
                data = json.loads(json_str)
                
                # 处理列表形式
                if isinstance(data, list):
                    for item_data in data:
                        try:
                            items.append(ActionItem(**item_data))
                        except Exception:
                            continue
                
                # 处理字典形式（包含 action_items 键）
                elif isinstance(data, dict) and "action_items" in data:
                    for item_data in data["action_items"]:
                        try:
                            items.append(ActionItem(**item_data))
                        except Exception:
                            continue
    except json.JSONDecodeError:
        pass
    
    # 尝试从整个响应解析 JSON
    if not items:
        try:
            data = json.loads(response)
            if isinstance(data, dict) and "action_items" in data:
                for item_data in data["action_items"]:
                    try:
                        items.append(ActionItem(**item_data))
                    except Exception:
                        continue
        except json.JSONDecodeError:
            pass
    
    return items


# ============================================================================
# Synthesis_Agent 实现
# ============================================================================


class SynthesisAgent(BaseAgent):
    """综合反思与安全检查智能体
    
    负责整合所有专家智能体的响应，生成深度洞察报告，
    执行干预措施去重和冲突检测，并构建最终的健康干预方案。
    
    Requirements:
        - 9.1: 从 Health_State 读取所有 expert_responses
        - 9.2: 生成 deep_insight（健康现状、跨学科关联、核心问题归因、干预逻辑）
        - 9.3: 执行 Action_Item 去重（title相同或description相似度>80%）
        - 9.4: 检测干预冲突（药物-营养、运动-病史、措施矛盾）
        - 9.5: 检测高风险干预组合，设置 requires_confirmation
        - 9.6: 根据风险等级生成随访计划
        - 9.7: 将完整 Final_Report 写入 Health_State
    
    Example:
        >>> agent = SynthesisAgent()
        >>> state = await agent.process(initial_state)
        >>> print(state["final_report"].deep_insight)
    """
    
    @property
    def name(self) -> str:
        """智能体名称"""
        return "Synthesis_Agent"
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一位综合健康管理专家，负责整合多学科专家的建议，
生成协调一致且安全的综合健康干预方案。

你的职责是：
1. 综合分析营养、运动康复、神经心理三个维度的专家建议
2. 识别并解决不同专家建议之间的潜在冲突
3. 检测高风险干预组合并标记需要用户确认
4. 生成深度洞察报告，阐明健康问题的跨学科关联
5. 制定分级随访计划，确保干预方案的安全执行

安全原则：
- 药物与营养建议不能产生交互风险
- 运动建议必须考虑用户的病史禁忌
- 高风险干预必须获得用户明确确认
- 干预措施不能相互矛盾"""
    
    async def process(self, state: HealthState) -> HealthState:
        """处理状态并生成最终报告
        
        Args:
            state: 当前的 LangGraph 全局状态
        
        Returns:
            更新后的状态，包含完整的 Final_Report
        
        Requirements: 9.1-9.7
        """
        # 初始化状态字段
        if "node_execution_status" not in state:
            state["node_execution_status"] = {}
        if "error_info" not in state:
            state["error_info"] = []
        
        # 更新节点状态为运行中
        state["node_execution_status"][self.name] = NodeExecutionStatus.RUNNING
        
        try:
            # Requirement 9.1: 从 Health_State 读取所有 expert_responses
            expert_responses = state.get("expert_responses", {})
            user_profile = state.get("user_profile")
            
            # 收集所有 ActionItem
            all_action_items: List[ActionItem] = []
            
            # 解析 nutrition 响应
            nutrition_response = expert_responses.get("nutrition", "")
            nutrition_items = parse_action_items_from_response(nutrition_response)
            all_action_items.extend(nutrition_items)
            
            # 解析 rehabilitation 响应
            rehabilitation_response = expert_responses.get("rehabilitation", "")
            rehabilitation_items = parse_action_items_from_response(rehabilitation_response)
            all_action_items.extend(rehabilitation_items)
            
            # 解析 neuropsychology 响应
            neuropsychology_response = expert_responses.get("neuropsychology", "")
            neuropsychology_items = parse_action_items_from_response(neuropsychology_response)
            all_action_items.extend(neuropsychology_items)
            
            # 检查 state 中是否有直接存储的 action_items
            if "neuropsychology_actions" in state:
                for item_data in state.get("neuropsychology_actions", []):
                    try:
                        all_action_items.append(ActionItem(**item_data))
                    except Exception:
                        continue
            
            # Requirement 9.3: 执行去重
            deduplicated_items = deduplicate_action_items(all_action_items)
            
            # Requirement 9.4: 检测冲突并移除冲突项
            conflicts, filtered_items = detect_all_conflicts(
                deduplicated_items, user_profile
            )
            
            # Requirement 9.5: 检测高风险组合
            requires_confirmation, high_risk_reasons = detect_high_risk_combinations(
                filtered_items, user_profile
            )
            
            # 获取整体风险等级
            overall_risk = get_overall_risk_level(filtered_items)
            
            # Requirement 9.6: 生成随访计划
            follow_up = generate_follow_up_plan(overall_risk, filtered_items, user_profile)
            
            # Requirement 9.2: 生成深度洞察
            deep_insight = generate_deep_insight(
                user_profile, expert_responses, filtered_items, conflicts
            )
            
            # 如果有高风险原因，添加到深度洞察中
            if high_risk_reasons:
                deep_insight += "\n\n## ⚠️ 高风险提示\n\n"
                deep_insight += "以下内容需要您特别关注和确认：\n\n"
                for reason in high_risk_reasons:
                    deep_insight += f"- {reason}\n"
            
            # 限制 action_plan 最多 50 项（Requirement 3.2）
            final_action_items = filtered_items[:50]
            
            # 生成 session_id
            session_id = state.get("session_id", str(uuid.uuid4()))
            
            # Requirement 9.7: 构建 Final_Report
            final_report = FinalReport(
                deep_insight=deep_insight,
                action_plan=final_action_items,
                follow_up=follow_up,
                requires_confirmation=requires_confirmation,
                created_at=datetime.now(timezone.utc),
                session_id=session_id,
                confirmation_status=ConfirmationStatus.PENDING,
            )
            
            # 写入状态
            state["final_report"] = final_report
            state["node_execution_status"][self.name] = NodeExecutionStatus.COMPLETED
            
            # 如果需要确认，设置中断标志
            if requires_confirmation:
                state["ui_interrupt_flag"] = True
                state["interrupt_reason"] = "检测到高风险干预组合，需要用户确认"
            
        except Exception as e:
            # 记录错误
            error = ErrorInfo(
                node_name=self.name,
                error_type=type(e).__name__,
                error_message=str(e)[:1000],
                timestamp=datetime.now(timezone.utc),
            )
            state["error_info"].append(error)
            state["node_execution_status"][self.name] = NodeExecutionStatus.FAILED
            
            # 生成降级报告
            state["final_report"] = self._generate_fallback_report(state)
        
        return state
    
    def _generate_fallback_report(self, state: HealthState) -> FinalReport:
        """生成降级报告
        
        当处理出错时，返回基础的降级报告。
        
        Args:
            state: 当前状态
        
        Returns:
            降级的 FinalReport
        """
        session_id = state.get("session_id", str(uuid.uuid4()))
        
        return FinalReport(
            deep_insight="## 系统提示\n\n"
                        "综合分析过程中出现异常，无法生成完整的深度洞察报告。\n\n"
                        "建议您：\n"
                        "1. 查看各专家的单独建议\n"
                        "2. 咨询专业医疗人员获取综合指导\n"
                        "3. 稍后重试系统分析",
            action_plan=[],
            follow_up="建议 14 天后重新进行健康评估，或根据专业医生建议安排随访。",
            requires_confirmation=False,
            created_at=datetime.now(timezone.utc),
            session_id=session_id,
            confirmation_status=ConfirmationStatus.PENDING,
        )
