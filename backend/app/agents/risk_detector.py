"""
风险检测模块

实现高风险关键词、禁止关键词和超出服务范围检测功能。
用于 Controller_Agent 在任务拆解前对用户请求进行安全检查。

Requirements: 5.3, 5.4, 8.7
"""

import re

# 高风险关键词列表 (Requirement 5.3)
# 用药调整类、断食类、极端饮食类、大剂量补剂类
HIGH_RISK_KEYWORDS = [
    # 用药调整类
    "停药",
    "换药",
    "加药",
    "减药",
    # 断食类
    "断食超过24小时",
    "24小时断食",
    "水断食",
    "全断食",
    "长期断食",
    # 极端饮食类
    "生酮饮食",
    "极低热量饮食",
    "低于800千卡",
    "800千卡以下",
    # 大剂量补剂类
    "大剂量补剂",
    "超剂量补剂",
    "高剂量补剂",
    "3倍RDA",
    "超过RDA",
]

# 高风险关键词模式（正则表达式）
HIGH_RISK_PATTERNS = [
    # 断食时间匹配 (超过24小时)
    r"断食\s*(\d+)\s*(小时|h|H)",
    # 热量限制匹配 (低于800千卡)
    r"(\d+)\s*(千卡|kcal|大卡|卡路里)",
    # RDA倍数匹配 (超过3倍)
    r"(\d+)\s*倍\s*(RDA|推荐量|推荐摄入量)",
]


# 禁止关键词列表 (Requirement 5.4, 8.7)
# 严重精神疾病相关，检测到需终止并建议寻求专业帮助
PROHIBITED_KEYWORDS = [
    "自杀",
    "自残",
    "幻觉",
    "幻听",
    "妄想",
    "躁狂发作",
    "重度抑郁",
    "精神分裂",
    "双相情感障碍急性发作",
    "自伤",
    "自我伤害",
    "不想活",
    "想死",
    "结束生命",
]


# 超出服务范围关键词和模式 (Requirement 5.4)
OUT_OF_SCOPE_KEYWORDS = {
    "诊断请求": [
        "诊断",
        "确诊",
        "鉴定",
        "检查是否",
        "判断是否患有",
        "是不是得了",
        "是否患有",
        "帮我看看是不是",
        "帮我诊断",
    ],
    "处方请求": [
        "开处方",
        "开药",
        "处方药",
        "需要什么药",
        "吃什么药",
        "用什么药治疗",
        "推荐处方",
    ],
    "急性症状": [
        "胸痛",
        "呼吸困难",
        "意识障碍",
        "高热超过39",
        "发烧39度",
        "39°C",
        "39度以上",
        "胸闷",
        "喘不上气",
        "昏迷",
        "意识模糊",
        "心绞痛",
        "心肌梗死",
    ],
    "需处方治疗疾病": [
        "感染性疾病",
        "细菌感染",
        "病毒感染",
        "肿瘤",
        "癌症",
        "恶性肿瘤",
        "化疗",
        "放疗",
    ],
    "儿科问题": [
        "12岁以下",
        "儿童",
        "幼儿",
        "婴儿",
        "小孩",
        "宝宝",
        "孩子生病",
        "孩子发烧",
        "小朋友",
    ],
}


def detect_high_risk_keywords(text: str) -> tuple[bool, list[str]]:
    """
    检测文本中的高风险关键词

    根据 Requirement 5.3，检测以下高风险关键词或模式：
    - 用药调整类（停药、换药、加药、减药）
    - 断食类（断食超过24小时、水断食）
    - 极端饮食类（生酮饮食、极低热量饮食低于800千卡/天）
    - 补剂类（大剂量补剂超过RDA推荐量3倍）

    检测到高风险关键词时，应将 ui_interrupt_flag 设置为 True。

    Args:
        text: 用户输入的文本

    Returns:
        Tuple of (is_high_risk: bool, matched_keywords: List[str])
        - is_high_risk: 是否检测到高风险关键词
        - matched_keywords: 匹配到的关键词列表
    """
    if not text or not isinstance(text, str):
        return (False, [])

    matched_keywords: list[str] = []
    text_lower = text.lower()

    # 检测静态关键词
    for keyword in HIGH_RISK_KEYWORDS:
        if keyword in text:
            matched_keywords.append(keyword)

    # 检测动态模式
    # 断食时间模式：检测超过24小时
    fasting_pattern = r"断食\s*(\d+)\s*(小时|h|H|天|日)"
    fasting_matches = re.findall(fasting_pattern, text)
    for match in fasting_matches:
        hours = int(match[0])
        unit = match[1].lower()
        # 如果单位是天/日，转换为小时
        if unit in ["天", "日"]:
            hours = hours * 24
        if hours >= 24:
            keyword = f"断食{match[0]}{match[1]}"
            if keyword not in matched_keywords:
                matched_keywords.append(keyword)

    # 热量限制模式：检测低于800千卡
    calorie_pattern = r"(\d+)\s*(千卡|kcal|大卡|卡路里)"
    calorie_matches = re.findall(calorie_pattern, text_lower)
    for match in calorie_matches:
        calories = int(match[0])
        if calories < 800 and calories > 0:
            keyword = f"极低热量饮食({match[0]}{match[1]})"
            if keyword not in matched_keywords:
                matched_keywords.append(keyword)

    # RDA倍数模式：检测超过3倍
    rda_pattern = r"(\d+)\s*倍\s*(RDA|推荐量|推荐摄入量)"
    rda_matches = re.findall(rda_pattern, text, re.IGNORECASE)
    for match in rda_matches:
        multiplier = int(match[0])
        if multiplier >= 3:
            keyword = f"大剂量补剂({match[0]}倍{match[1]})"
            if keyword not in matched_keywords:
                matched_keywords.append(keyword)

    # 去重（保持顺序）
    seen = set()
    unique_keywords = []
    for kw in matched_keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    return (len(unique_keywords) > 0, unique_keywords)


def detect_prohibited_keywords(text: str) -> tuple[bool, list[str]]:
    """
    检测文本中的禁止关键词（严重精神疾病相关）

    根据 Requirement 5.4 和 8.7，检测以下关键词：
    自杀、自残、幻觉、幻听、妄想、躁狂发作、重度抑郁、
    精神分裂、双相情感障碍急性发作

    检测到禁止关键词时，应返回建议寻求专业精神科帮助并终止处理。

    Args:
        text: 用户输入的文本

    Returns:
        Tuple of (is_prohibited: bool, matched_keywords: List[str])
        - is_prohibited: 是否检测到禁止关键词
        - matched_keywords: 匹配到的关键词列表
    """
    if not text or not isinstance(text, str):
        return (False, [])

    matched_keywords: list[str] = []

    for keyword in PROHIBITED_KEYWORDS:
        if keyword in text:
            matched_keywords.append(keyword)

    # 去重（保持顺序）
    seen = set()
    unique_keywords = []
    for kw in matched_keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    return (len(unique_keywords) > 0, unique_keywords)


def detect_out_of_scope(text: str) -> tuple[bool, str]:
    """
    检测是否超出系统服务范围

    根据 Requirement 5.4，检测以下超出系统能力范围的请求：
    - 急性症状（胸痛、呼吸困难、意识障碍、高热超过39°C）
    - 需处方治疗的疾病（感染性疾病、肿瘤）
    - 精神科范畴（通过 detect_prohibited_keywords 处理）
    - 诊断请求
    - 儿科问题（12岁以下儿童）

    Args:
        text: 用户输入的文本

    Returns:
        Tuple of (is_out_of_scope: bool, reason: str)
        - is_out_of_scope: 是否超出服务范围
        - reason: 超出范围的原因说明
    """
    if not text or not isinstance(text, str):
        return (False, "")

    detected_categories: list[str] = []
    detected_keywords: list[str] = []

    # 检测各类别关键词
    for category, keywords in OUT_OF_SCOPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                if category not in detected_categories:
                    detected_categories.append(category)
                detected_keywords.append(keyword)

    # 检测年龄模式（12岁以下）
    age_pattern = r"(\d+)\s*(岁|周岁)"
    age_matches = re.findall(age_pattern, text)
    for match in age_matches:
        age = int(match[0])
        if age < 12:
            if "儿科问题" not in detected_categories:
                detected_categories.append("儿科问题")
            detected_keywords.append(f"{match[0]}{match[1]}儿童")

    # 检测高热模式（39度以上）
    fever_pattern = r"(\d+(?:\.\d+)?)\s*(度|°C|°c|摄氏度)"
    fever_matches = re.findall(fever_pattern, text)
    for match in fever_matches:
        temp = float(match[0])
        if temp >= 39:
            if "急性症状" not in detected_categories:
                detected_categories.append("急性症状")
            detected_keywords.append(f"高热({match[0]}{match[1]})")

    if not detected_categories:
        return (False, "")

    # 构建原因说明
    reason_parts = []

    if "急性症状" in detected_categories:
        reason_parts.append("您描述的症状可能需要紧急医疗处理，建议立即前往医院急诊科就诊")

    if "需处方治疗疾病" in detected_categories:
        reason_parts.append("该疾病需要专业医生诊断和处方治疗，建议前往相关专科就诊")

    if "诊断请求" in detected_categories:
        reason_parts.append("本系统不提供医学诊断服务，建议前往正规医疗机构进行专业检查和诊断")

    if "处方请求" in detected_categories:
        reason_parts.append("本系统不提供处方药建议，建议咨询执业医生获取处方")

    if "儿科问题" in detected_categories:
        reason_parts.append("本系统不适用于12岁以下儿童，建议前往儿科医院就诊")

    reason = (
        "；".join(reason_parts)
        if reason_parts
        else f"检测到超出服务范围的请求类型：{', '.join(detected_categories)}"
    )

    return (True, reason)


def get_professional_help_suggestion() -> str:
    """
    获取建议寻求专业帮助的标准回复文本

    Returns:
        专业帮助建议文本
    """
    return "建议立即寻求专业精神科医生帮助。如有紧急情况，请拨打心理援助热线：全国心理援助热线 400-161-9995，或前往最近医院的精神科/心理科就诊。"


def perform_safety_check(text: str) -> dict:
    """
    执行完整的安全检查

    综合检测高风险关键词、禁止关键词和超出服务范围。

    Args:
        text: 用户输入的文本

    Returns:
        dict: 安全检查结果，包含：
            - is_safe: bool - 是否安全（可继续处理）
            - ui_interrupt_flag: bool - 是否需要设置中断标志
            - terminate: bool - 是否需要终止处理
            - high_risk_keywords: List[str] - 高风险关键词列表
            - prohibited_keywords: List[str] - 禁止关键词列表
            - out_of_scope_reason: str - 超出范围原因
            - message: str - 给用户的提示消息
    """
    result = {
        "is_safe": True,
        "ui_interrupt_flag": False,
        "terminate": False,
        "high_risk_keywords": [],
        "prohibited_keywords": [],
        "out_of_scope_reason": "",
        "message": "",
    }

    # 检测禁止关键词（优先级最高，需终止）
    is_prohibited, prohibited_keywords = detect_prohibited_keywords(text)
    if is_prohibited:
        result["is_safe"] = False
        result["terminate"] = True
        result["prohibited_keywords"] = prohibited_keywords
        result["message"] = get_professional_help_suggestion()
        return result

    # 检测超出服务范围
    is_out_of_scope, out_of_scope_reason = detect_out_of_scope(text)
    if is_out_of_scope:
        result["is_safe"] = False
        result["terminate"] = True
        result["out_of_scope_reason"] = out_of_scope_reason
        result["message"] = out_of_scope_reason
        return result

    # 检测高风险关键词（需要用户确认，但不终止）
    is_high_risk, high_risk_keywords = detect_high_risk_keywords(text)
    if is_high_risk:
        result["ui_interrupt_flag"] = True
        result["high_risk_keywords"] = high_risk_keywords
        result["message"] = f"检测到高风险内容（{', '.join(high_risk_keywords)}），需要您确认后继续"

    return result
