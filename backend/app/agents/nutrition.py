"""
营养学专家智能体节点

提供基于专业知识库的个性化营养和补剂建议，包括血脂血糖异常检测、
药物-食物交互警告、以及标准化的干预措施输出。

Requirements: 6.1-6.7
"""

import asyncio
import json
from typing import Optional

from app.agents.base import BaseAgent
from app.agents.health_analyzer import (
    GlucoseAbnormalityResult,
    LipidAbnormalityResult,
    detect_glucose_abnormality,
    detect_lipid_abnormality,
)
from app.models.action_item import ActionCategory, ActionItem, Priority, RiskLevel
from app.models.state import HealthState, NodeExecutionStatus
from app.models.user_profile import Medication, UserProfile
from app.services.llm import get_llm_service

# ============================================================================
# 药物-食物交互配置 (Requirement 6.5)
# ============================================================================

# 药物关键词与交互警告的映射
DRUG_FOOD_INTERACTIONS: dict[str, dict] = {
    "华法林": {
        "keywords": ["华法林", "warfarin", "抗凝药", "抗凝血"],
        "warning": "华法林与维生素K食物交互警告：深绿色蔬菜（如菠菜、甘蓝、西兰花）富含维生素K，可能影响抗凝效果。建议保持稳定的维生素K摄入量，避免突然大量增加或减少绿叶蔬菜摄入。",
        "food_category": "维生素K食物（深绿色蔬菜）",
        "risk_level": RiskLevel.MEDIUM,
    },
    "他汀类": {
        "keywords": [
            "他汀",
            "阿托伐他汀",
            "瑞舒伐他汀",
            "辛伐他汀",
            "普伐他汀",
            "氟伐他汀",
            "洛伐他汀",
            "匹伐他汀",
            "statin",
            "降脂药",
        ],
        "warning": "他汀类药物与葡萄柚交互警告：葡萄柚及其果汁可抑制药物代谢酶（CYP3A4），可能增加药物浓度，增加肌肉损伤风险。建议避免同时食用葡萄柚或葡萄柚汁。",
        "food_category": "葡萄柚及其果汁",
        "risk_level": RiskLevel.MEDIUM,
    },
    "二甲双胍": {
        "keywords": ["二甲双胍", "metformin", "格华止", "降糖药"],
        "warning": "二甲双胍与酒精交互警告：酒精可能增加乳酸酸中毒风险，尤其是空腹饮酒时。建议限制或避免饮酒，如需饮酒应随餐少量。",
        "food_category": "酒精",
        "risk_level": RiskLevel.HIGH,
    },
    "ACEI/ARB": {
        "keywords": [
            "普利",
            "沙坦",
            "依那普利",
            "贝那普利",
            "赖诺普利",
            "卡托普利",
            "氯沙坦",
            "缬沙坦",
            "厄贝沙坦",
            "替米沙坦",
            "奥美沙坦",
            "坎地沙坦",
            "ACEI",
            "ARB",
            "血管紧张素",
        ],
        "warning": "ACEI/ARB类降压药与高钾食物交互警告：这类药物可能导致血钾升高，同时摄入大量高钾食物（香蕉、橙子、土豆、菠菜）可能导致高钾血症。建议监测血钾水平，适度控制高钾食物摄入。",
        "food_category": "高钾食物（香蕉、橙子、土豆、菠菜等）",
        "risk_level": RiskLevel.MEDIUM,
    },
    "甲状腺激素": {
        "keywords": ["左甲状腺素", "优甲乐", "levothyroxine", "甲状腺素", "雷替斯"],
        "warning": "甲状腺激素类药物与大豆/高纤维食物交互警告：大豆制品和高纤维食物可能影响药物吸收。建议服药后至少间隔4小时再食用大豆制品或高纤维食物。",
        "food_category": "大豆制品、高纤维食物",
        "risk_level": RiskLevel.LOW,
    },
}


# ============================================================================
# 基础营养建议库 (Requirement 6.2 降级时使用)
# ============================================================================

BASIC_NUTRITION_ADVICE = {
    "lipid_general": {
        "title": "控制饱和脂肪摄入",
        "description": "每日饱和脂肪摄入量控制在总热量的7%以下。减少油炸食品、动物内脏、肥肉摄入。选择橄榄油、菜籽油等不饱和脂肪酸。",
        "frequency": "每日三餐执行",
        "priority": Priority.HIGH,
        "risk_level": RiskLevel.LOW,
        "duration": "12周",
    },
    "lipid_cholesterol": {
        "title": "增加膳食纤维摄入",
        "description": "每日摄入25-30克膳食纤维，包括燕麦、豆类、蔬菜和水果。可溶性纤维有助于降低LDL胆固醇。推荐食物：燕麦片、苹果、胡萝卜、豆类。",
        "frequency": "每日三餐",
        "priority": Priority.HIGH,
        "risk_level": RiskLevel.LOW,
        "duration": "12周",
    },
    "lipid_omega3": {
        "title": "增加Omega-3脂肪酸摄入",
        "description": "每周食用2-3次深海鱼类（三文鱼、鲭鱼、沙丁鱼），或补充亚麻籽、核桃等植物来源的Omega-3。有助于降低甘油三酯水平。",
        "frequency": "每周2-3次深海鱼",
        "priority": Priority.MEDIUM,
        "risk_level": RiskLevel.LOW,
        "duration": "12周",
    },
    "glucose_general": {
        "title": "控制碳水化合物摄入",
        "description": "选择低升糖指数（GI）食物，如全谷物、豆类、非淀粉类蔬菜。避免精制糖和白米白面，控制总碳水化合物摄入量。每餐碳水化合物占比控制在45-50%。",
        "frequency": "每日三餐执行",
        "priority": Priority.HIGH,
        "risk_level": RiskLevel.LOW,
        "duration": "12周",
    },
    "glucose_portion": {
        "title": "规律进餐与份量控制",
        "description": "保持三餐规律，避免暴饮暴食。使用份量控制法：1/2餐盘蔬菜，1/4餐盘蛋白质，1/4餐盘碳水化合物。饭前喝水或吃蔬菜增加饱腹感。",
        "frequency": "每日三餐定时定量",
        "priority": Priority.MEDIUM,
        "risk_level": RiskLevel.LOW,
        "duration": "8周",
    },
    "balanced_diet": {
        "title": "均衡膳食结构优化",
        "description": "遵循膳食指南，保证蛋白质、脂肪、碳水化合物的合理比例（蛋白质15-20%，脂肪20-30%，碳水化合物50-60%）。增加蔬果摄入，每日蔬菜400-500g，水果200-350g。",
        "frequency": "每日执行",
        "priority": Priority.MEDIUM,
        "risk_level": RiskLevel.LOW,
        "duration": "4周",
    },
}


def _detect_drug_food_interactions(
    medications: list[Medication],
) -> list[dict]:
    """检测药物-食物交互

    根据用户用药史检测潜在的药物-食物交互风险。

    Args:
        medications: 用户用药记录列表

    Returns:
        检测到的交互警告列表，每个包含药物名、警告信息和风险等级

    Validates: Requirements 6.5
    """
    interactions = []
    checked_categories = set()  # 避免重复警告

    for medication in medications:
        # 跳过已结束的用药
        if medication.end_date is not None:
            continue

        drug_name = medication.drug_name.lower()

        for category, interaction_info in DRUG_FOOD_INTERACTIONS.items():
            # 已检测过此类别则跳过
            if category in checked_categories:
                continue

            # 检查药物名称是否匹配关键词
            for keyword in interaction_info["keywords"]:
                if keyword.lower() in drug_name:
                    interactions.append(
                        {
                            "drug_category": category,
                            "drug_name": medication.drug_name,
                            "warning": interaction_info["warning"],
                            "food_category": interaction_info["food_category"],
                            "risk_level": interaction_info["risk_level"],
                        }
                    )
                    checked_categories.add(category)
                    break

    return interactions


def _generate_lipid_action_items(
    lipid_result: LipidAbnormalityResult,
) -> list[ActionItem]:
    """根据血脂异常结果生成营养干预措施

    Args:
        lipid_result: 血脂异常检测结果

    Returns:
        针对血脂异常的 ActionItem 列表
    """
    items = []

    if not lipid_result.is_abnormal:
        return items

    # 总胆固醇或LDL偏高 - 控制饱和脂肪
    if any(item in lipid_result.abnormal_items for item in ["总胆固醇偏高", "LDL偏高"]):
        advice = BASIC_NUTRITION_ADVICE["lipid_general"]
        abnormal_details = []
        if "总胆固醇偏高" in lipid_result.abnormal_items:
            tc_info = lipid_result.details.get("total_cholesterol", {})
            abnormal_details.append(f"总胆固醇 {tc_info.get('value', '?')} mmol/L")
        if "LDL偏高" in lipid_result.abnormal_items:
            ldl_info = lipid_result.details.get("ldl", {})
            abnormal_details.append(f"LDL {ldl_info.get('value', '?')} mmol/L")

        description = f"检测到{', '.join(abnormal_details)}异常。{advice['description']}"

        items.append(
            ActionItem(
                category=ActionCategory.NUTRITION,
                title=advice["title"],
                description=description,
                frequency=advice["frequency"],
                priority=advice["priority"],
                risk_level=advice["risk_level"],
                duration=advice["duration"],
            )
        )

        # 增加膳食纤维
        fiber_advice = BASIC_NUTRITION_ADVICE["lipid_cholesterol"]
        items.append(
            ActionItem(
                category=ActionCategory.NUTRITION,
                title=fiber_advice["title"],
                description=fiber_advice["description"],
                frequency=fiber_advice["frequency"],
                priority=fiber_advice["priority"],
                risk_level=fiber_advice["risk_level"],
                duration=fiber_advice["duration"],
            )
        )

    # 甘油三酯偏高 - Omega-3
    if "甘油三酯偏高" in lipid_result.abnormal_items:
        tg_info = lipid_result.details.get("triglycerides", {})
        omega3_advice = BASIC_NUTRITION_ADVICE["lipid_omega3"]
        description = f"检测到甘油三酯 {tg_info.get('value', '?')} mmol/L 偏高。{omega3_advice['description']}"

        items.append(
            ActionItem(
                category=ActionCategory.NUTRITION,
                title=omega3_advice["title"],
                description=description,
                frequency=omega3_advice["frequency"],
                priority=omega3_advice["priority"],
                risk_level=omega3_advice["risk_level"],
                duration=omega3_advice["duration"],
            )
        )

    # HDL偏低 - 需要综合干预
    if "HDL偏低" in lipid_result.abnormal_items:
        hdl_info = lipid_result.details.get("hdl", {})
        items.append(
            ActionItem(
                category=ActionCategory.NUTRITION,
                title="提升HDL水平的饮食调整",
                description=f"检测到HDL {hdl_info.get('value', '?')} mmol/L 偏低。增加单不饱和脂肪酸摄入（橄榄油、牛油果、坚果），适量食用富含抗氧化剂的食物（蓝莓、深色蔬菜），限制反式脂肪酸摄入。",
                frequency="每日执行",
                priority=Priority.MEDIUM,
                risk_level=RiskLevel.LOW,
                duration="12周",
            )
        )

    return items


def _generate_glucose_action_items(
    glucose_result: GlucoseAbnormalityResult,
) -> list[ActionItem]:
    """根据血糖异常结果生成营养干预措施

    Args:
        glucose_result: 血糖异常检测结果

    Returns:
        针对血糖异常的 ActionItem 列表
    """
    items = []

    if not glucose_result.is_abnormal:
        return items

    # 空腹血糖偏高
    if "空腹血糖偏高" in glucose_result.abnormal_items:
        fg_info = glucose_result.details.get("fasting_glucose", {})
        carb_advice = BASIC_NUTRITION_ADVICE["glucose_general"]
        description = (
            f"检测到空腹血糖 {fg_info.get('value', '?')} mmol/L 偏高。{carb_advice['description']}"
        )

        items.append(
            ActionItem(
                category=ActionCategory.NUTRITION,
                title=carb_advice["title"],
                description=description,
                frequency=carb_advice["frequency"],
                priority=carb_advice["priority"],
                risk_level=carb_advice["risk_level"],
                duration=carb_advice["duration"],
            )
        )

    # 糖化血红蛋白偏高
    if "糖化血红蛋白偏高" in glucose_result.abnormal_items:
        hba1c_info = glucose_result.details.get("hba1c", {})
        portion_advice = BASIC_NUTRITION_ADVICE["glucose_portion"]
        description = f"检测到糖化血红蛋白 {hba1c_info.get('value', '?')}% 偏高，表明近期血糖控制欠佳。{portion_advice['description']}"

        items.append(
            ActionItem(
                category=ActionCategory.NUTRITION,
                title=portion_advice["title"],
                description=description,
                frequency=portion_advice["frequency"],
                priority=portion_advice["priority"],
                risk_level=portion_advice["risk_level"],
                duration=portion_advice["duration"],
            )
        )

    return items


def _generate_drug_interaction_warnings(
    interactions: list[dict],
) -> list[ActionItem]:
    """根据药物-食物交互检测结果生成警告

    Args:
        interactions: 检测到的药物-食物交互列表

    Returns:
        药物-食物交互警告的 ActionItem 列表
    """
    items = []

    for interaction in interactions:
        items.append(
            ActionItem(
                category=ActionCategory.NUTRITION,
                title=f"⚠️ {interaction['drug_category']}药物饮食注意事项",
                description=interaction["warning"],
                frequency="用药期间持续注意",
                priority=Priority.HIGH,
                risk_level=interaction["risk_level"],
                duration="12周",  # 使用标准格式，实际应持续用药期间
            )
        )

    return items


class NutritionAgent(BaseAgent):
    """营养学专家智能体

    提供基于专业知识库的个性化营养和补剂建议。

    功能:
    - 调用 Markdown_RAG 检索营养学知识库
    - 根据血脂血糖阈值生成针对性建议
    - 检测药物-食物交互并附加警告信息
    - 输出 3-5 个标准化 Action_Item

    Requirements:
        6.1: 调用 Markdown_RAG 检索营养学知识库，超时时间为10秒
        6.2: RAG 检索失败或超时时，基于内置基础营养知识生成通用建议
        6.3: 根据血脂阈值生成针对性建议
        6.4: 根据血糖阈值生成针对性建议
        6.5: 检测药物-食物交互并附加警告
        6.6: 输出 3-5 个 Action_Item，category 设置为"营养"
        6.7: 将响应结果写入 Health_State 的 expert_responses 字段
    """

    # RAG 查询超时时间（秒）
    RAG_TIMEOUT_SECONDS = 10

    def __init__(
        self,
        markdown_rag: Optional["MarkdownRAG"] = None,  # type: ignore  # noqa: F821
    ) -> None:
        """初始化营养学专家智能体

        Args:
            markdown_rag: 可选的 Markdown RAG 实例，用于知识库检索
        """
        self._markdown_rag = markdown_rag

    @property
    def name(self) -> str:
        """智能体名称"""
        return "Nutrition_Agent"

    def get_system_prompt(self) -> str:
        """获取系统提示词

        Returns:
            营养学专家的系统提示词
        """
        return """你是一位专业的营养学专家，专注于个性化营养干预和膳食建议。

你的专业领域包括：
1. 血脂异常的营养管理（高胆固醇、高甘油三酯、HDL偏低）
2. 血糖控制的饮食策略（前驱糖尿病、血糖波动）
3. 药物-食物交互识别和安全建议
4. 微量营养素缺乏的膳食补充
5. 功能性食品和营养补剂的循证建议

输出要求：
- 所有建议必须有科学依据，优先引用知识库内容
- 关注用户的用药情况，识别潜在的药物-食物交互
- 建议应具体可操作，包含食物种类、份量和频率
- 按优先级排列建议，高风险问题优先处理
- 输出 3-5 个结构化的干预措施"""

    async def _query_rag_with_timeout(
        self,
        query: str,
    ) -> list[dict]:
        """带超时的 RAG 查询

        Args:
            query: 查询文本

        Returns:
            RAG 检索结果列表，超时或失败返回空列表

        Note:
            Requirement 6.1: 调用 Markdown_RAG 检索营养学知识库，超时时间为10秒
            Requirement 6.2: RAG 检索失败或超时时返回空列表，由调用方使用基础知识
        """
        if self._markdown_rag is None:
            return []

        try:
            # 使用 asyncio.wait_for 设置超时
            results = await asyncio.wait_for(
                self._markdown_rag.query(
                    query_text=query,
                    top_k=5,
                    similarity_threshold=0.7,
                    category="营养学",
                ),
                timeout=self.RAG_TIMEOUT_SECONDS,
            )
            return [
                {
                    "content": r.content,
                    "source": r.source,
                    "score": r.similarity_score,
                }
                for r in results
            ]
        except TimeoutError:
            # Requirement 6.2: 超时时返回空列表
            return []
        except Exception:
            # Requirement 6.2: 失败时返回空列表
            return []

    async def process(self, state: HealthState) -> HealthState:
        """处理营养学分析任务

        从 Health_State 读取用户画像和查询，调用 LLM 生成个性化营养建议。
        LLM 返回结构化 JSON，直接驱动 action_items 生成。

        Args:
            state: 当前的 LangGraph 全局状态

        Returns:
            更新后的 HealthState，包含营养学专家的响应

        Requirements:
            6.1-6.7: 完整的营养学分析流程
        """
        # 更新节点执行状态
        if "node_execution_status" not in state:
            state["node_execution_status"] = {}
        state["node_execution_status"][self.name] = NodeExecutionStatus.RUNNING

        # 获取用户查询
        user_query = state.get("user_query", "")

        # 获取用户画像（可能为 None）
        user_profile: UserProfile | None = state.get("user_profile")

        # 初始化响应结构
        action_items: list[ActionItem] = []
        rag_results: list[dict] = []
        analysis_notes: list[str] = []
        interactions: list[dict] = []
        lipid_result: LipidAbnormalityResult | None = None
        glucose_result: GlucoseAbnormalityResult | None = None
        deep_insight = ""

        # 如果有用户画像，进行个性化分析
        if user_profile is not None:
            # 1. 检测药物-食物交互 (Requirement 6.5)
            interactions = _detect_drug_food_interactions(user_profile.medications)
            if interactions:
                drug_names = [i["drug_name"] for i in interactions]
                analysis_notes.append(f"药物-食物交互风险: {', '.join(drug_names)}")

            # 2. 检测血脂异常 (Requirement 6.3)
            blood_lipids = user_profile.physical_examination.blood_lipids
            lipid_result = detect_lipid_abnormality(blood_lipids=blood_lipids)
            if lipid_result.is_abnormal:
                analysis_notes.append(f"血脂异常: {', '.join(lipid_result.abnormal_items)}")

            # 3. 检测血糖异常 (Requirement 6.4)
            blood_glucose = user_profile.physical_examination.blood_glucose
            glucose_result = detect_glucose_abnormality(blood_glucose=blood_glucose)
            if glucose_result.is_abnormal:
                analysis_notes.append(f"血糖异常: {', '.join(glucose_result.abnormal_items)}")

        # 4. RAG 知识检索 (Requirement 6.1)
        rag_content = ""
        if user_query:
            search_queries = [user_query]
            if lipid_result and lipid_result.is_abnormal:
                search_queries.append("血脂异常营养干预")
            if glucose_result and glucose_result.is_abnormal:
                search_queries.append("血糖控制饮食建议")

            for query in search_queries:
                results = await self._query_rag_with_timeout(query)
                rag_results.extend(results)

            # 提取 RAG 内容用于 LLM
            if rag_results:
                rag_content = "\n\n".join(
                    [r.get("content", "") for r in rag_results if r.get("content")]
                )

        # 5. 构建用户健康上下文（如果有用户画像）
        user_context = ""
        if user_profile is not None:
            user_context = self._build_user_context(
                user_profile, lipid_result, glucose_result, interactions
            )
        else:
            user_context = "（用户未提供个人健康档案，请提供通用建议）"

        # 6. 调用 LLM 生成结构化建议（核心改动：LLM 驱动 action_items）
        if user_query:
            try:
                llm_service = get_llm_service()
                llm_result = await llm_service.generate_structured_advice(
                    agent_type="nutrition",
                    system_prompt=self.get_system_prompt(),
                    user_query=user_query,
                    user_context=user_context,
                    rag_knowledge=rag_content,
                )

                # 提取 deep_insight
                deep_insight = llm_result.get("deep_insight", "")

                # 解析 LLM 返回的 action_items
                for item_data in llm_result.get("action_items", []):
                    try:
                        # 确保 category 是营养
                        item_data["category"] = "营养"
                        action_items.append(ActionItem(**item_data))
                    except Exception:
                        # 跳过无效的 action item
                        continue

            except Exception as e:
                # LLM 调用失败，直接返回错误状态
                error_response = {
                    "has_user_profile": user_profile is not None,
                    "error": True,
                    "error_type": type(e).__name__,
                    "error_message": f"LLM 服务不可用：{type(e).__name__}",
                    "action_items": [],
                }
                state["expert_responses"]["nutrition"] = json.dumps(
                    error_response, ensure_ascii=False
                )
                state["node_execution_status"][self.name] = NodeExecutionStatus.FAILED
                return state

        # 限制最多 5 个
        action_items = action_items[:5]

        # 8. 构建响应结果 (Requirement 6.7)
        response_data = {
            "has_user_profile": user_profile is not None,
            "analysis_summary": "; ".join(analysis_notes)
            if analysis_notes
            else "未提供个人健康档案"
            if user_profile is None
            else "未检测到明显异常",
            "deep_insight": deep_insight,
            "rag_results_count": len(rag_results),
            "action_items": [item.model_dump() for item in action_items],
            "drug_interactions": [
                {
                    "drug_name": i["drug_name"],
                    "drug_category": i["drug_category"],
                    "food_category": i["food_category"],
                }
                for i in interactions
            ],
        }

        # 更新状态
        if "expert_responses" not in state:
            state["expert_responses"] = {}
        state["expert_responses"]["nutrition"] = json.dumps(response_data, ensure_ascii=False)
        state["node_execution_status"][self.name] = NodeExecutionStatus.COMPLETED

        return state

    def _build_user_context(
        self,
        user_profile: UserProfile,
        lipid_result: LipidAbnormalityResult,
        glucose_result: GlucoseAbnormalityResult,
        interactions: list[dict],
    ) -> str:
        """构建用户健康上下文描述

        Args:
            user_profile: 用户画像
            lipid_result: 血脂检测结果
            glucose_result: 血糖检测结果
            interactions: 药物-食物交互列表

        Returns:
            用户健康上下文的文本描述
        """
        context_parts = [
            "### 基本信息",
            f"- 年龄: {user_profile.age}岁",
            f"- 性别: {user_profile.gender}",
            f"- BMI: {user_profile.bmi}",
            "",
            "### 血脂指标",
        ]

        blood_lipids = user_profile.physical_examination.blood_lipids
        context_parts.extend(
            [
                f"- 总胆固醇: {blood_lipids.total_cholesterol} mmol/L",
                f"- LDL: {blood_lipids.ldl} mmol/L",
                f"- HDL: {blood_lipids.hdl} mmol/L",
                f"- 甘油三酯: {blood_lipids.triglycerides} mmol/L",
            ]
        )

        if lipid_result.is_abnormal:
            context_parts.append(f"- ⚠️ 异常项: {', '.join(lipid_result.abnormal_items)}")

        context_parts.extend(
            [
                "",
                "### 血糖指标",
            ]
        )

        blood_glucose = user_profile.physical_examination.blood_glucose
        context_parts.extend(
            [
                f"- 空腹血糖: {blood_glucose.fasting_glucose} mmol/L",
                f"- 糖化血红蛋白: {blood_glucose.hba1c}%",
            ]
        )

        if glucose_result.is_abnormal:
            context_parts.append(f"- ⚠️ 异常项: {', '.join(glucose_result.abnormal_items)}")

        # 用药情况
        if user_profile.medications:
            context_parts.extend(
                [
                    "",
                    "### 当前用药",
                ]
            )
            for med in user_profile.medications:
                if med.end_date is None:  # 只显示当前用药
                    context_parts.append(f"- {med.drug_name}: {med.dosage}, {med.frequency}")

        # 药物-食物交互警告
        if interactions:
            context_parts.extend(
                [
                    "",
                    "### 药物-食物交互警告",
                ]
            )
            for interaction in interactions:
                context_parts.append(f"- {interaction['drug_category']}: {interaction['warning']}")

        return "\n".join(context_parts)

    def _generate_fallback_advice(
        self,
        lipid_result: LipidAbnormalityResult,
        glucose_result: GlucoseAbnormalityResult,
        interactions: list[dict],
    ) -> str:
        """生成降级建议（当 LLM 不可用时）

        Args:
            lipid_result: 血脂检测结果
            glucose_result: 血糖检测结果
            interactions: 药物-食物交互列表

        Returns:
            基础建议文本
        """
        advice_parts = []

        if lipid_result.is_abnormal:
            advice_parts.append(
                "**血脂管理建议**: 减少饱和脂肪摄入，增加膳食纤维，每周食用2-3次深海鱼。"
            )

        if glucose_result.is_abnormal:
            advice_parts.append(
                "**血糖控制建议**: 选择低GI食物，控制总碳水化合物摄入，保持规律进餐。"
            )

        if interactions:
            advice_parts.append("**用药期间注意**: 请留意药物-食物交互警告，避免影响药效的食物。")

        if not advice_parts:
            advice_parts.append(
                "**均衡饮食建议**: 保持膳食多样化，蔬果充足，适量蛋白质，控制油盐糖。"
            )

        return "\n\n".join(advice_parts)
