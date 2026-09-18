"""
运动康复专家智能体节点

负责根据用户健康画像生成个性化的运动康复建议。
调用 Markdown_RAG 检索运动康复知识库，根据年龄、BMI 和禁忌病史
调整运动强度和排除不适合的运动类型。

Requirements: 7.1-7.6
Design Reference: LangGraph 工作流设计 - Rehabilitation_Agent 节点
"""

import asyncio
import json
from datetime import UTC

from app.agents.base import BaseAgent
from app.agents.health_analyzer import (
    ContraindicationResult,
    ExerciseIntensity,
    IntensityAdjustment,
    check_medical_contraindications,
    get_exercise_intensity_by_age,
    get_intensity_adjustment_by_bmi,
)
from app.models.action_item import ActionCategory, ActionItem, Priority, RiskLevel
from app.models.state import HealthState, NodeExecutionStatus
from app.models.user_profile import MedicalHistory
from app.services.llm import get_llm_service
from app.tools.markdown_rag import MarkdownRAG, create_rehabilitation_rag

# 基于年龄-强度和BMI调整的内置运动建议
EXERCISE_RECOMMENDATIONS = {
    ExerciseIntensity.HIGH: [
        {
            "title": "高强度间歇训练(HIIT)",
            "description": "每组运动20-30秒全力冲刺，休息10-20秒，循环8-12组。包括波比跳、深蹲跳、登山跑等动作。注意充分热身，运动后做好拉伸放松。",
            "frequency": "每周3-4次，每次20-30分钟",
            "priority": Priority.MEDIUM,
            "risk_level": RiskLevel.MEDIUM,
            "duration": "12周",
            "tags": ["高冲击运动", "高强度有氧", "跳跃运动"],
        },
        {
            "title": "力量训练",
            "description": "全身力量训练计划，包括深蹲、硬拉、卧推、划船等复合动作。从中等重量开始，逐渐增加负重。每个动作3-4组，每组8-12次。",
            "frequency": "每周3-4次，分上下肢训练",
            "priority": Priority.HIGH,
            "risk_level": RiskLevel.MEDIUM,
            "duration": "12周",
            "tags": ["负重训练", "深蹲", "硬拉", "举重"],
        },
        {
            "title": "有氧耐力训练",
            "description": "中高强度有氧运动，如跑步、游泳、骑行。保持心率在最大心率的70-85%。建议使用心率监测设备确保运动强度。建议长期坚持。",
            "frequency": "每周4-5次，每次40-60分钟",
            "priority": Priority.MEDIUM,
            "risk_level": RiskLevel.LOW,
            "duration": "24周",
            "tags": ["跑步", "高强度有氧"],
        },
    ],
    ExerciseIntensity.MEDIUM_HIGH: [
        {
            "title": "中高强度有氧运动",
            "description": "适度的有氧运动如慢跑、快走、椭圆机、游泳。保持心率在最大心率的60-75%。注意运动中保持呼吸顺畅。",
            "frequency": "每周4-5次，每次30-45分钟",
            "priority": Priority.HIGH,
            "risk_level": RiskLevel.LOW,
            "duration": "12周",
            "tags": ["跑步", "游泳"],
        },
        {
            "title": "抗阻力训练",
            "description": "使用弹力带、哑铃或器械进行肌肉力量训练。重点加强核心肌群、下肢和上肢力量。每个部位2-3组，每组12-15次。",
            "frequency": "每周2-3次，每次40-50分钟",
            "priority": Priority.MEDIUM,
            "risk_level": RiskLevel.LOW,
            "duration": "12周",
            "tags": ["负重训练"],
        },
        {
            "title": "功能性训练",
            "description": "结合日常活动模式的功能性动作训练，如单腿站立、平板支撑、深蹲起立。提升身体协调性和稳定性。",
            "frequency": "每周2-3次，每次20-30分钟",
            "priority": Priority.MEDIUM,
            "risk_level": RiskLevel.LOW,
            "duration": "8周",
            "tags": ["平衡要求高的运动", "单腿站立", "深蹲"],
        },
    ],
    ExerciseIntensity.MEDIUM: [
        {
            "title": "适度有氧运动",
            "description": "温和的有氧运动如快走、慢骑自行车、水中有氧。保持心率在最大心率的50-65%。选择对关节冲击小的运动方式。",
            "frequency": "每周5次，每次30-40分钟",
            "priority": Priority.HIGH,
            "risk_level": RiskLevel.LOW,
            "duration": "12周",
            "tags": ["游泳"],
        },
        {
            "title": "太极拳或瑜伽",
            "description": "通过太极拳或瑜伽练习提升身体柔韧性、平衡能力和内心平静。选择适合初学者的课程，循序渐进。避免过度拉伸和高难度体式。建议长期坚持。",
            "frequency": "每周3-4次，每次45-60分钟",
            "priority": Priority.MEDIUM,
            "risk_level": RiskLevel.LOW,
            "duration": "24周",
            "tags": ["瑜伽倒立"],
        },
        {
            "title": "轻度力量训练",
            "description": "使用轻重量或自重进行力量训练，如坐姿推举、弹力带训练、墙壁俯卧撑。注重动作质量而非重量。",
            "frequency": "每周2-3次，每次20-30分钟",
            "priority": Priority.MEDIUM,
            "risk_level": RiskLevel.LOW,
            "duration": "8周",
            "tags": [],
        },
    ],
    ExerciseIntensity.LOW: [
        {
            "title": "散步运动",
            "description": "每日散步是最安全有效的运动方式。选择平坦的路面，穿舒适的鞋子。可以分次进行，如早晚各15-20分钟。建议长期坚持。",
            "frequency": "每日30-45分钟，可分次进行",
            "priority": Priority.HIGH,
            "risk_level": RiskLevel.LOW,
            "duration": "24周",
            "tags": [],
        },
        {
            "title": "椅上运动操",
            "description": "坐在稳固的椅子上进行的轻柔运动，包括手臂抬举、腿部伸展、肩部绕环等。适合行动不便或平衡能力较差者。建议长期坚持。",
            "frequency": "每日2-3次，每次15-20分钟",
            "priority": Priority.MEDIUM,
            "risk_level": RiskLevel.LOW,
            "duration": "24周",
            "tags": [],
        },
        {
            "title": "水中运动",
            "description": "在温水泳池中进行轻柔的水中运动，如水中行走、水中伸展。水的浮力减少关节负担，适合关节问题者。",
            "frequency": "每周2-3次，每次20-30分钟",
            "priority": Priority.MEDIUM,
            "risk_level": RiskLevel.LOW,
            "duration": "12周",
            "tags": ["游泳"],
        },
    ],
}

# BMI 调整说明
BMI_ADJUSTMENT_NOTES = {
    IntensityAdjustment.SLIGHT_INCREASE: "您的体重偏轻，建议适度增加训练强度和营养摄入，促进肌肉增长。",
    IntensityAdjustment.STANDARD: "您的体重在健康范围内，可以按照标准强度进行训练。",
    IntensityAdjustment.MODERATE_DECREASE: "您的体重略微超标，建议适度降低运动强度，选择对关节冲击较小的运动。",
    IntensityAdjustment.SIGNIFICANT_DECREASE: "您的体重明显超标，建议显著降低运动强度，避免高冲击运动，优先选择游泳、骑行等低冲击运动。",
}


class RehabilitationAgent(BaseAgent):
    """运动康复专家智能体

    负责根据用户健康画像生成个性化的运动康复建议。

    功能:
    - 调用 Markdown_RAG 检索运动康复知识库 (Requirement 7.1)
    - 根据年龄匹配运动强度 (Requirement 7.2)
    - 根据 BMI 调整运动强度 (Requirement 7.3)
    - 输出 3-5 个 Action_Item (Requirement 7.4)
    - 将结果写入 expert_responses (Requirement 7.5)
    - 根据禁忌病史排除运动类型 (Requirement 7.6)

    Attributes:
        _rag: MarkdownRAG 实例，用于检索运动康复知识库
        _rag_timeout: RAG 查询超时时间（秒）
    """

    def __init__(
        self,
        rag: MarkdownRAG | None = None,
        rag_timeout: float = 10.0,
    ) -> None:
        """初始化运动康复专家智能体

        Args:
            rag: MarkdownRAG 实例，如果未提供则创建默认实例
            rag_timeout: RAG 查询超时时间（秒），默认 10 秒
        """
        self._rag = rag or create_rehabilitation_rag()
        self._rag_timeout = rag_timeout

    @property
    def name(self) -> str:
        """智能体名称"""
        return "Rehabilitation_Agent"

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一位专业的运动康复专家，拥有运动科学、物理治疗和康复医学背景。
你的职责是根据用户的健康画像，制定个性化的运动康复方案。

核心原则：
1. 安全第一：根据用户的年龄、BMI和病史，选择安全适宜的运动类型
2. 循序渐进：从低强度开始，逐步增加运动量和强度
3. 个性化定制：考虑用户的身体状况、生活方式和运动偏好
4. 全面发展：兼顾有氧耐力、肌肉力量、柔韧性和平衡能力

输出要求：
- 生成 3-5 个具体的运动干预措施
- 每个措施包含清晰的执行说明和频率
- 标注运动的风险等级
- 考虑可能的运动禁忌"""

    async def process(self, state: HealthState) -> HealthState:
        """处理状态并返回更新后的状态

        根据用户健康画像和查询生成运动康复建议。
        LLM 返回结构化 JSON，直接驱动 action_items 生成。

        Args:
            state: 当前的 HealthState

        Returns:
            更新后的 HealthState

        Requirements: 7.1-7.6
        """
        # 初始化 expert_responses 和 node_execution_status
        if "expert_responses" not in state:
            state["expert_responses"] = {}
        if "node_execution_status" not in state:
            state["node_execution_status"] = {}
        if "error_info" not in state:
            state["error_info"] = []

        # 更新节点状态为运行中
        state["node_execution_status"][self.name] = NodeExecutionStatus.RUNNING

        try:
            # 获取用户查询
            user_query = state.get("user_query", "")

            # 获取用户画像（可能为 None）
            user_profile = state.get("user_profile")

            # 如果有用户画像，进行个性化分析
            age_intensity = None
            bmi_adjustment = None
            final_intensity = None
            contraindication_result = None
            rag_results: list[str] = []
            deep_insight = ""
            action_items: list[ActionItem] = []

            if user_profile is not None:
                # 提取关键信息
                age = user_profile.age
                bmi = user_profile.bmi
                medical_history: list[MedicalHistory] = user_profile.medical_history

                # 1. 根据年龄获取推荐运动强度 (Requirement 7.2)
                age_intensity = get_exercise_intensity_by_age(age)

                # 2. 根据 BMI 获取强度调整建议 (Requirement 7.3)
                bmi_adjustment = get_intensity_adjustment_by_bmi(bmi=bmi)

                # 3. 检查禁忌病史 (Requirement 7.6)
                contraindication_result = check_medical_contraindications(medical_history)

                # 4. 尝试调用 RAG 检索知识库 (Requirement 7.1)
                rag_results = await self._query_rag_with_timeout(
                    user_profile, age_intensity, contraindication_result
                )

                # 5. 综合各因素调整最终运动强度
                final_intensity = self._adjust_intensity(age_intensity, bmi_adjustment)
            else:
                # 没有用户画像时，只根据查询检索 RAG
                if user_query:
                    try:
                        results = await asyncio.wait_for(
                            self._rag.query_rehabilitation(
                                query_text=user_query,
                                top_k=5,
                                similarity_threshold=0.7,
                            ),
                            timeout=self._rag_timeout,
                        )
                        rag_results = [r.content for r in results]
                    except Exception:
                        rag_results = []

            rag_content = "\n\n".join(rag_results) if rag_results else ""

            # 6. 构建用户健康上下文
            if user_profile is not None:
                user_context = self._build_user_context(
                    user_profile=user_profile,
                    age_intensity=age_intensity,
                    bmi_adjustment=bmi_adjustment,
                    final_intensity=final_intensity,
                    contraindication_result=contraindication_result,
                )
            else:
                user_context = "（用户未提供个人健康档案，请提供通用运动建议）"

            # 7. 调用 LLM 生成结构化建议（核心改动：LLM 驱动 action_items）
            if user_query:
                try:
                    llm_service = get_llm_service()
                    llm_result = await llm_service.generate_structured_advice(
                        agent_type="rehabilitation",
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
                            # 确保 category 是康复
                            item_data["category"] = "康复"
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
                    state["expert_responses"]["rehabilitation"] = json.dumps(
                        error_response, ensure_ascii=False
                    )
                    state["node_execution_status"][self.name] = NodeExecutionStatus.FAILED
                    return state

            # 限制最多 5 个
            action_items = action_items[:5]

            # 9. 构建响应内容
            response_data = {
                "has_user_profile": user_profile is not None,
                "deep_insight": deep_insight,
                "rag_used": len(rag_results) > 0,
                "action_items": [item.model_dump() for item in action_items],
            }

            if user_profile is not None:
                response_data.update(
                    {
                        "age": user_profile.age,
                        "age_intensity": age_intensity.value if age_intensity else None,
                        "bmi": user_profile.bmi,
                        "bmi_adjustment": bmi_adjustment.value if bmi_adjustment else None,
                        "final_intensity": final_intensity.value if final_intensity else None,
                        "has_contraindications": contraindication_result.has_contraindications
                        if contraindication_result
                        else False,
                    }
                )

            # 10. 写入 expert_responses (Requirement 7.5)
            state["expert_responses"]["rehabilitation"] = json.dumps(
                response_data, ensure_ascii=False
            )
            state["node_execution_status"][self.name] = NodeExecutionStatus.COMPLETED

        except Exception as e:
            # 记录错误信息
            from datetime import datetime

            from app.models.state import ErrorInfo

            error = ErrorInfo(
                node_name=self.name,
                error_type=type(e).__name__,
                error_message=str(e)[:1000],
                timestamp=datetime.now(UTC),
            )
            state["error_info"].append(error)
            state["node_execution_status"][self.name] = NodeExecutionStatus.FAILED

            # 即使出错也尝试返回基础建议
            state["expert_responses"]["rehabilitation"] = self._generate_fallback_response()

        return state

    def _build_generic_response(
        self,
        action_items: list[ActionItem],
        llm_response: str,
        rag_used: bool,
    ) -> str:
        """构建无用户画像时的通用响应

        Args:
            action_items: 生成的 Action_Item 列表
            llm_response: LLM 生成的建议
            rag_used: 是否使用了 RAG 检索

        Returns:
            格式化的响应字符串
        """
        response_parts = [
            "## 运动康复建议",
            "",
        ]

        # 添加 LLM 生成的建议（如果有）
        if llm_response:
            response_parts.extend(
                [
                    "### 针对您问题的建议",
                    "",
                    llm_response,
                    "",
                ]
            )

        if not rag_used:
            response_parts.extend(
                [
                    "> 注：本建议基于通用运动康复知识生成。如需获得个性化建议，请提供您的健康档案信息。",
                    "",
                ]
            )

        # 添加运动建议
        response_parts.extend(
            [
                "### 通用运动建议",
                "",
            ]
        )

        for i, item in enumerate(action_items, 1):
            response_parts.extend(
                [
                    f"#### {i}. {item.title}",
                    "",
                    f"**说明**: {item.description}",
                    "",
                    f"**频率**: {item.frequency}",
                    "",
                    f"**持续时间**: {item.duration}",
                    "",
                ]
            )

        return "\n".join(response_parts)

    def _build_user_context(
        self,
        user_profile,
        age_intensity: ExerciseIntensity,
        bmi_adjustment: IntensityAdjustment,
        final_intensity: ExerciseIntensity,
        contraindication_result: ContraindicationResult,
    ) -> str:
        """构建用户健康上下文描述

        Args:
            user_profile: 用户画像
            age_intensity: 年龄对应的运动强度
            bmi_adjustment: BMI 调整建议
            final_intensity: 最终推荐强度
            contraindication_result: 禁忌病史检查结果

        Returns:
            用户健康上下文的文本描述
        """
        context_parts = [
            "### 基本信息",
            f"- 年龄: {user_profile.age}岁",
            f"- 性别: {user_profile.gender}",
            f"- BMI: {user_profile.bmi}",
            "",
            "### 运动能力评估",
            f"- 基于年龄的推荐强度: {age_intensity.value}",
            f"- BMI 调整建议: {BMI_ADJUSTMENT_NOTES.get(bmi_adjustment, '标准强度')}",
            f"- 最终推荐强度: {final_intensity.value}",
        ]

        # 生活方式信息
        lifestyle = user_profile.lifestyle
        context_parts.extend(
            [
                "",
                "### 生活方式",
                f"- 运动频率: {lifestyle.exercise_frequency}",
                f"- 睡眠时长: {lifestyle.sleep_duration}小时",
                f"- 压力等级: {lifestyle.stress_level}/10",
            ]
        )

        # 禁忌信息
        if contraindication_result.has_contraindications:
            context_parts.extend(
                [
                    "",
                    "### 运动禁忌",
                    f"需要避免的运动类型: {', '.join(contraindication_result.excluded_exercises)}",
                ]
            )
            for category, details in contraindication_result.contraindication_details.items():
                context_parts.append(f"- {category}: {details['description']}")

        return "\n".join(context_parts)

    async def _query_rag_with_timeout(
        self,
        user_profile,
        age_intensity: ExerciseIntensity,
        contraindication_result: ContraindicationResult,
    ) -> list[str]:
        """带超时的 RAG 查询

        Args:
            user_profile: 用户画像
            age_intensity: 年龄对应的运动强度
            contraindication_result: 禁忌病史检查结果

        Returns:
            检索到的知识内容列表
        """
        try:
            # 构建查询文本
            query_parts = [
                "运动康复建议",
                f"年龄{user_profile.age}岁",
                f"BMI {user_profile.bmi}",
                f"推荐{age_intensity.value}运动",
            ]

            # 添加禁忌信息
            if contraindication_result.has_contraindications:
                query_parts.append(f"需避免{', '.join(contraindication_result.excluded_exercises)}")

            query_text = " ".join(query_parts)

            # 带超时执行 RAG 查询
            results = await asyncio.wait_for(
                self._rag.query_rehabilitation(
                    query_text=query_text,
                    top_k=5,
                    similarity_threshold=0.7,
                ),
                timeout=self._rag_timeout,
            )

            return [r.content for r in results]

        except TimeoutError:
            # RAG 查询超时，返回空结果
            return []
        except Exception:
            # RAG 查询失败，返回空结果
            return []

    def _adjust_intensity(
        self,
        age_intensity: ExerciseIntensity,
        bmi_adjustment: IntensityAdjustment,
    ) -> ExerciseIntensity:
        """根据 BMI 调整最终运动强度

        Args:
            age_intensity: 年龄对应的基础运动强度
            bmi_adjustment: BMI 调整建议

        Returns:
            调整后的运动强度
        """
        # 强度等级映射（从低到高）
        intensity_levels = [
            ExerciseIntensity.LOW,
            ExerciseIntensity.MEDIUM,
            ExerciseIntensity.MEDIUM_HIGH,
            ExerciseIntensity.HIGH,
        ]

        current_index = intensity_levels.index(age_intensity)

        # 根据 BMI 调整
        if bmi_adjustment == IntensityAdjustment.SLIGHT_INCREASE:
            # 轻度增强：提升一级（如果可能）
            new_index = min(current_index + 1, len(intensity_levels) - 1)
        elif bmi_adjustment == IntensityAdjustment.MODERATE_DECREASE:
            # 适度降低：降低一级
            new_index = max(current_index - 1, 0)
        elif bmi_adjustment == IntensityAdjustment.SIGNIFICANT_DECREASE:
            # 显著降低：降低两级，但最低为低强度
            new_index = max(current_index - 2, 0)
        else:
            # 标准强度：不调整
            new_index = current_index

        return intensity_levels[new_index]

    def _generate_action_items(
        self,
        final_intensity: ExerciseIntensity,
        bmi_adjustment: IntensityAdjustment,
        contraindication_result: ContraindicationResult,
        rag_results: list[str],
        user_profile,
    ) -> list[ActionItem]:
        """生成运动康复 Action_Item 列表

        Args:
            final_intensity: 最终运动强度
            bmi_adjustment: BMI 调整建议
            contraindication_result: 禁忌病史检查结果
            rag_results: RAG 检索结果
            user_profile: 用户画像

        Returns:
            Action_Item 列表（3-5个）

        Requirement 7.4, 7.6
        """
        action_items: list[ActionItem] = []
        excluded_exercises = contraindication_result.excluded_exercises

        # 获取对应强度的推荐运动
        recommendations = EXERCISE_RECOMMENDATIONS.get(final_intensity, [])

        for rec in recommendations:
            # 检查是否有禁忌 (Requirement 7.6)
            tags = rec.get("tags", [])
            has_contraindication = any(tag in excluded_exercises for tag in tags)

            if has_contraindication:
                # 跳过有禁忌的运动
                continue

            # 根据 BMI 调整风险等级和描述
            risk_level = rec["risk_level"]
            description = rec["description"]

            if bmi_adjustment == IntensityAdjustment.SIGNIFICANT_DECREASE:
                # BMI ≥ 28 时，提升高冲击运动的风险等级
                if any(tag in tags for tag in ["高冲击运动", "高强度有氧", "跳跃运动"]):
                    risk_level = RiskLevel.HIGH
                    description += " 注意：由于体重因素，请特别注意关节保护，建议在专业指导下进行。"

            action_item = ActionItem(
                category=ActionCategory.REHABILITATION,
                title=rec["title"],
                description=description,
                frequency=rec["frequency"],
                priority=rec["priority"],
                risk_level=risk_level,
                duration=rec["duration"],
            )
            action_items.append(action_item)

            # 限制为 3-5 个
            if len(action_items) >= 5:
                break

        # 如果因禁忌排除太多导致不足 3 个，添加通用安全建议
        while len(action_items) < 3:
            safe_recommendations = self._get_safe_fallback_recommendations(
                excluded_exercises, existing_titles=[a.title for a in action_items]
            )
            for safe_rec in safe_recommendations:
                if len(action_items) >= 3:
                    break
                action_items.append(safe_rec)

        return action_items[:5]

    def _get_safe_fallback_recommendations(
        self,
        excluded_exercises: set,
        existing_titles: list[str],
    ) -> list[ActionItem]:
        """获取安全的备选建议

        当因禁忌排除太多运动时，提供通用的安全建议。

        Args:
            excluded_exercises: 需要排除的运动类型
            existing_titles: 已添加的建议标题

        Returns:
            安全的 Action_Item 列表
        """
        fallback_items = []

        safe_options = [
            ActionItem(
                category=ActionCategory.REHABILITATION,
                title="渐进式步行计划",
                description="从每日10分钟轻松散步开始，每周增加5分钟，逐步达到每日30-45分钟。选择平坦路面，穿舒适的运动鞋。",
                frequency="每日1-2次",
                priority=Priority.HIGH,
                risk_level=RiskLevel.LOW,
                duration="8周",
            ),
            ActionItem(
                category=ActionCategory.REHABILITATION,
                title="呼吸配合伸展运动",
                description="在家进行简单的伸展运动，配合深呼吸。包括颈部转动、肩部绕环、手臂伸展、腿部拉伸。每个动作保持15-30秒。建议长期坚持。",
                frequency="每日早晚各一次，每次10-15分钟",
                priority=Priority.MEDIUM,
                risk_level=RiskLevel.LOW,
                duration="24周",
            ),
            ActionItem(
                category=ActionCategory.REHABILITATION,
                title="核心稳定性训练",
                description="安全的核心训练动作，如仰卧起坐替代动作（死虫式）、平板支撑（可从墙壁版本开始）、骨盆倾斜练习。",
                frequency="每周3次，每次15-20分钟",
                priority=Priority.MEDIUM,
                risk_level=RiskLevel.LOW,
                duration="8周",
            ),
        ]

        for item in safe_options:
            if item.title not in existing_titles:
                fallback_items.append(item)

        return fallback_items

    def _build_response(
        self,
        action_items: list[ActionItem],
        age: int,
        age_intensity: ExerciseIntensity,
        bmi: float,
        bmi_adjustment: IntensityAdjustment,
        final_intensity: ExerciseIntensity,
        contraindication_result: ContraindicationResult,
        rag_used: bool,
        llm_response: str = "",
    ) -> str:
        """构建响应内容

        Args:
            action_items: 生成的 Action_Item 列表
            age: 用户年龄
            age_intensity: 年龄对应的运动强度
            bmi: 用户 BMI
            bmi_adjustment: BMI 调整建议
            final_intensity: 最终运动强度
            contraindication_result: 禁忌病史检查结果
            rag_used: 是否使用了 RAG 检索
            llm_response: LLM 生成的个性化建议

        Returns:
            格式化的响应字符串
        """
        response_parts = [
            "## 运动康复评估与建议",
            "",
        ]

        # 添加 LLM 生成的个性化建议（如果有）
        if llm_response:
            response_parts.extend(
                [
                    "### 个性化建议",
                    "",
                    llm_response,
                    "",
                ]
            )

        response_parts.extend(
            [
                "### 个人运动能力评估",
                "",
                f"**年龄**: {age}岁 → 推荐基础强度: {age_intensity.value}",
                f"**BMI**: {bmi} → {BMI_ADJUSTMENT_NOTES.get(bmi_adjustment, '')}",
                f"**最终推荐强度**: {final_intensity.value}",
                "",
            ]
        )

        # 添加禁忌信息
        if contraindication_result.has_contraindications:
            response_parts.extend(
                [
                    "### 运动禁忌提示",
                    "",
                    "根据您的健康状况，以下运动类型需要避免或谨慎：",
                    "",
                ]
            )
            for category, details in contraindication_result.contraindication_details.items():
                response_parts.append(f"- **{category}**: {details['description']}")
            response_parts.append("")

        # 添加 RAG 使用说明
        if not rag_used:
            response_parts.extend(
                [
                    "> 注：本建议基于内置专业知识生成，未检索到专业知识库内容。",
                    "",
                ]
            )

        # 添加运动建议
        response_parts.extend(
            [
                "### 推荐运动计划",
                "",
            ]
        )

        for i, item in enumerate(action_items, 1):
            response_parts.extend(
                [
                    f"#### {i}. {item.title}",
                    "",
                    f"**说明**: {item.description}",
                    "",
                    f"**频率**: {item.frequency}",
                    "",
                    f"**持续时间**: {item.duration}",
                    "",
                    f"**优先级**: {item.priority.value} | **风险等级**: {item.risk_level.value}",
                    "",
                ]
            )

        # 添加 Action_Item JSON 数据
        response_parts.extend(
            [
                "---",
                "",
                "### 结构化数据",
                "",
                "```json",
                json.dumps(
                    [item.model_dump(mode="json") for item in action_items],
                    ensure_ascii=False,
                    indent=2,
                ),
                "```",
            ]
        )

        return "\n".join(response_parts)

    def _generate_fallback_response(self) -> str:
        """生成降级响应

        当处理出错时，返回基础的通用建议。

        Returns:
            降级响应字符串
        """
        fallback_items = [
            ActionItem(
                category=ActionCategory.REHABILITATION,
                title="每日散步",
                description="每天进行30分钟轻松散步，选择平坦路面和舒适的鞋子。根据身体感受调整步速和距离。建议长期坚持。",
                frequency="每日1次",
                priority=Priority.HIGH,
                risk_level=RiskLevel.LOW,
                duration="24周",
            ),
            ActionItem(
                category=ActionCategory.REHABILITATION,
                title="基础伸展运动",
                description="每天进行简单的全身伸展，帮助保持关节灵活性和肌肉弹性。建议长期坚持。",
                frequency="每日早晚各10分钟",
                priority=Priority.MEDIUM,
                risk_level=RiskLevel.LOW,
                duration="24周",
            ),
            ActionItem(
                category=ActionCategory.REHABILITATION,
                title="寻求专业指导",
                description="建议咨询运动康复师或物理治疗师，获取个性化的运动处方。初次评估后按医嘱执行。",
                frequency="初次评估后按医嘱",
                priority=Priority.HIGH,
                risk_level=RiskLevel.LOW,
                duration="4周",
            ),
        ]

        response_parts = [
            "## 运动康复建议",
            "",
            "> 注：由于系统处理异常，以下为通用安全建议。建议咨询专业人士获取个性化方案。",
            "",
            "### 推荐运动计划",
            "",
        ]

        for i, item in enumerate(fallback_items, 1):
            response_parts.extend(
                [
                    f"#### {i}. {item.title}",
                    "",
                    f"**说明**: {item.description}",
                    "",
                    f"**频率**: {item.frequency}",
                    "",
                    f"**持续时间**: {item.duration}",
                    "",
                ]
            )

        response_parts.extend(
            [
                "---",
                "",
                "### 结构化数据",
                "",
                "```json",
                json.dumps(
                    [item.model_dump(mode="json") for item in fallback_items],
                    ensure_ascii=False,
                    indent=2,
                ),
                "```",
            ]
        )

        return "\n".join(response_parts)
